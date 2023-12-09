import logging
import math
import os
import random
from pathlib import Path

import datasets
import torch
from datasets import load_dataset
from torch.utils.data import DataLoader
from tqdm.auto import tqdm

import transformers
from accelerate import Accelerator
from accelerate.logging import get_logger
from accelerate.utils import set_seed
from huggingface_hub import Repository
from transformers import (
    AutoConfig,
    AutoTokenizer,
    get_scheduler,
)
from transformers.utils import check_min_version, get_full_repo_name

# local imports
from modeling import TracedModel
from utils.parse_args import parse_args
from utils.data_collator import DataCollatorForTraced
from utils.data_process_utils import process_quantized_value
from utils.utils import VAR_TYPE, VALUE_TYPE, QUANTIZED_VALUE


# Will error if the minimal version of Transformers is not installed.
check_min_version("4.24.0")

logger = get_logger(__name__)
        

def main():
    args = parse_args()

    # Sanity checks
    if args.train_file is None or args.validation_file is None:
        raise ValueError("Need train_file and validation_file for exec pretraining.")
    else:
        if args.train_file is not None:
            extension = args.train_file.split(".")[-1]
            assert extension in ["csv", "json"], "`train_file` should be a csv or a json file."
        if args.validation_file is not None:
            extension = args.validation_file.split(".")[-1]
            assert extension in ["csv", "json"], "`validation_file` should be a csv or a json file."

    if args.push_to_hub:
        assert args.output_dir is not None, "Need an `output_dir` to create a repo when `--push_to_hub` is passed."

    accelerator = (
        Accelerator(log_with=args.report_to, logging_dir=args.output_dir) if args.with_tracking else Accelerator()
    )
    # Make one log on every process with the configuration for debugging.
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        level=logging.INFO,
    )
    logger.info(accelerator.state, main_process_only=False)
    if accelerator.is_local_main_process:
        datasets.utils.logging.set_verbosity_warning()
        transformers.utils.logging.set_verbosity_info()
    else:
        datasets.utils.logging.set_verbosity_error()
        transformers.utils.logging.set_verbosity_error()

    # If passed along, set the training seed now.
    if args.seed is not None:
        set_seed(args.seed)

    # Handle the repository creation
    if accelerator.is_main_process:
        if args.push_to_hub:
            if args.hub_model_id is None:
                repo_name = get_full_repo_name(Path(args.output_dir).name, token=args.hub_token)
            else:
                repo_name = args.hub_model_id
            repo = Repository(args.output_dir, clone_from=repo_name)

            with open(os.path.join(args.output_dir, ".gitignore"), "w+") as gitignore:
                if "step_*" not in gitignore:
                    gitignore.write("step_*\n")
                if "epoch_*" not in gitignore:
                    gitignore.write("epoch_*\n")
        elif args.output_dir is not None:
            os.makedirs(args.output_dir, exist_ok=True)
    accelerator.wait_for_everyone()

    # Loading the dataset from local csv or json file.
    data_files = {}
    if args.train_file is not None:
        data_files["train"] = args.train_file
    if args.validation_file is not None:
        data_files["validation"] = args.validation_file
    extension = (args.train_file if args.train_file is not None else args.validation_file).split(".")[-1]
    raw_datasets = load_dataset(extension, data_files=data_files, cache_dir=args.cache_dir)

    config = AutoConfig.from_pretrained(args.model_name_or_path)
    tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path, use_fast=not args.use_slow_tokenizer)
        
    
    num_var_type=len(VAR_TYPE)
    num_value_type=len(VALUE_TYPE)
    num_abs_value=len(QUANTIZED_VALUE)
    logger.info(f"num_var_type: {num_var_type}, num_value_type: {num_value_type}, num_abs_value: {num_abs_value}")

    model = TracedModel.from_pretrained(
        args.model_name_or_path,
        from_tf=bool(".ckpt" in args.model_name_or_path),
        config=config,
        ignore_mismatched_sizes=args.ignore_mismatched_sizes,
        w_mlm=args.mlm_weight,
        w_var_type=args.var_type_weight,
        w_value_type=args.value_type_weight,
        w_abs_value=args.abs_value_weight,
        num_var_type=num_var_type, 
        num_value_type=num_value_type, 
        num_abs_value=num_abs_value,
    )

    # padding = "max_length" if not args.dynamic_padding else False

    def preprocess_function(examples):
        features = process_quantized_value(args, tokenizer, examples, args.abs_gran)
        return features


    with accelerator.main_process_first():
        processed_datasets = raw_datasets.map(
            preprocess_function,
            batched=True,
            num_proc=args.preprocessing_num_workers,
            remove_columns=raw_datasets["train"].column_names,
            load_from_cache_file=not args.overwrite_cache,
            desc="Running tokenizer on dataset",
        )

    train_dataset = processed_datasets["train"]
    eval_dataset = processed_datasets["validation"]

    # Log a few random samples from the training set:
    for index in random.sample(range(len(train_dataset)), 3):
        logger.info(f"Sample {index} of the training set: {train_dataset[index]}.")

    data_collator = DataCollatorForTraced(tokenizer)

    train_dataloader = DataLoader(
        train_dataset, shuffle=True, collate_fn=data_collator, batch_size=args.per_device_train_batch_size
    )
    eval_dataloader = DataLoader(eval_dataset, collate_fn=data_collator, batch_size=args.per_device_eval_batch_size)

    # Optimizer
    # Split weights in two groups, one with weight decay and the other not.
    no_decay = ["bias", "LayerNorm.weight"]
    optimizer_grouped_parameters = [
        {
            "params": [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
            "weight_decay": args.weight_decay,
        },
        {
            "params": [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)],
            "weight_decay": 0.0,
        },
    ]
    optimizer = torch.optim.AdamW(optimizer_grouped_parameters, lr=args.learning_rate)

    # Scheduler and math around the number of training steps.
    overrode_max_train_steps = False
    num_update_steps_per_epoch = math.ceil(len(train_dataloader) / args.gradient_accumulation_steps)
    if args.max_train_steps is None:
        args.max_train_steps = args.num_train_epochs * num_update_steps_per_epoch
        overrode_max_train_steps = True

    lr_scheduler = get_scheduler(
        name=args.lr_scheduler_type,
        optimizer=optimizer,
        num_warmup_steps=args.num_warmup_steps,
        num_training_steps=args.max_train_steps,
    )

    # Prepare everything with our `accelerator`.
    model, optimizer, train_dataloader, eval_dataloader, lr_scheduler = accelerator.prepare(
        model, optimizer, train_dataloader, eval_dataloader, lr_scheduler
    )

    # We need to recalculate our total training steps as the size of the training dataloader may have changed
    num_update_steps_per_epoch = math.ceil(len(train_dataloader) / args.gradient_accumulation_steps)
    if overrode_max_train_steps:
        args.max_train_steps = args.num_train_epochs * num_update_steps_per_epoch
    # Afterwards we recalculate our number of training epochs
    args.num_train_epochs = math.ceil(args.max_train_steps / num_update_steps_per_epoch)

    # Figure out how many steps we should save the Accelerator states
    checkpointing_steps = args.checkpointing_steps
    if checkpointing_steps is not None and checkpointing_steps.isdigit():
        checkpointing_steps = int(checkpointing_steps)

    # We need to initialize the trackers we use, and also store our configuration.
    # The trackers initializes automatically on the main process.
    if args.with_tracking:
        experiment_config = vars(args)
        # TensorBoard cannot log Enums, need the raw value
        experiment_config["lr_scheduler_type"] = experiment_config["lr_scheduler_type"].value
        accelerator.init_trackers("exec_pretrain", experiment_config)

    if not args.only_eval:
        # Train!
        total_batch_size = args.per_device_train_batch_size * accelerator.num_processes * args.gradient_accumulation_steps

        logger.info("***** Running training *****")
        logger.info(f"  Num examples = {len(train_dataset)}")
        logger.info(f"  Num Epochs = {args.num_train_epochs}")
        logger.info(f"  Instantaneous batch size per device = {args.per_device_train_batch_size}")
        logger.info(f"  Total train batch size (w. parallel, distributed & accumulation) = {total_batch_size}")
        logger.info(f"  Gradient Accumulation steps = {args.gradient_accumulation_steps}")
        logger.info(f"  Total optimization steps = {args.max_train_steps}")
        # Only show the progress bar once on each machine.
        progress_bar = tqdm(range(args.max_train_steps), disable=not accelerator.is_local_main_process)
        completed_steps = 0
        starting_epoch = 0
        # Potentially load in the weights and states from a previous save
        if args.resume_from_checkpoint:
            if args.resume_from_checkpoint is not None or args.resume_from_checkpoint != "":
                accelerator.print(f"Resumed from checkpoint: {args.resume_from_checkpoint}")
                accelerator.load_state(args.resume_from_checkpoint)
                path = os.path.basename(args.resume_from_checkpoint)
            else:
                # Get the most recent checkpoint
                dirs = [f.name for f in os.scandir(os.getcwd()) if f.is_dir()]
                dirs.sort(key=os.path.getctime)
                path = dirs[-1]  # Sorts folders by date modified, most recent checkpoint is the last
            # Extract `epoch_{i}` or `step_{i}`
            training_difference = os.path.splitext(path)[0]

            if "epoch" in training_difference:
                starting_epoch = int(training_difference.replace("epoch_", "")) + 1
                resume_step = None
            else:
                resume_step = int(training_difference.replace("step_", ""))
                starting_epoch = resume_step // len(train_dataloader)
                resume_step -= starting_epoch * len(train_dataloader)

        for epoch in range(starting_epoch, args.num_train_epochs):
            model.train()
            if args.with_tracking:
                total_loss = 0
                total_mlm_loss = 0
                total_var_type_loss = 0
                total_value_type_loss = 0
                total_abs_value_loss = 0
            for step, batch in enumerate(train_dataloader):
                # We need to skip steps until we reach the resumed step
                if args.resume_from_checkpoint and epoch == starting_epoch:
                    if resume_step is not None and step < resume_step:
                        completed_steps += 1
                        continue
                outputs = model(**batch)
                loss, mlm_loss, var_type_loss, value_type_loss, abs_value_loss = outputs[0], outputs[1], outputs[2], outputs[3], outputs[4]
                # log the training loss
                if args.loss_logging_steps > 0 and completed_steps > 0 and completed_steps % args.loss_logging_steps == 0:
                    # if args.with_tracking:
                    #     accelerator.log_metric("train_loss", loss.detach().float(), epoch=epoch, step=completed_steps)
                    logger.info(f"Epoch {epoch} Step {completed_steps}: loss {loss.detach().float()}")
                # We keep track of the loss at each epoch
                if args.with_tracking:
                    total_loss += loss.detach().float()
                    total_mlm_loss += mlm_loss.detach().float()
                    total_var_type_loss += var_type_loss.detach().float()
                    total_value_type_loss += value_type_loss.detach().float()
                    total_abs_value_loss += abs_value_loss.detach().float()
                loss = loss / args.gradient_accumulation_steps
                accelerator.backward(loss)
                if step % args.gradient_accumulation_steps == 0 or step == len(train_dataloader) - 1:
                    optimizer.step()
                    lr_scheduler.step()
                    optimizer.zero_grad()
                    progress_bar.update(1)
                    completed_steps += 1

                if isinstance(checkpointing_steps, int):
                    if completed_steps % checkpointing_steps == 0:
                        output_dir = f"step_{completed_steps }"
                        if args.output_dir is not None:
                            output_dir = os.path.join(args.output_dir, output_dir)
                        accelerator.save_state(output_dir)

                if completed_steps >= args.max_train_steps:
                    break

            model.eval()
            losses = []
            mlm_losses = []
            var_type_losses = []
            value_type_losses = []
            abs_value_losses = []
            logger.info("***** Running evaluation *****")
            for step, batch in tqdm(enumerate(eval_dataloader), total=len(eval_dataloader)):
                with torch.no_grad():
                    outputs = model(**batch)
                loss, mlm_loss, var_type_loss, value_type_loss, abs_value_loss = outputs[0], outputs[1], outputs[2], outputs[3], outputs[4]
                losses.append(accelerator.gather_for_metrics(loss.repeat(args.per_device_eval_batch_size)))
                mlm_losses.append(accelerator.gather_for_metrics(mlm_loss.repeat(args.per_device_eval_batch_size)))
                var_type_losses.append(accelerator.gather_for_metrics(var_type_loss.repeat(args.per_device_eval_batch_size)))
                value_type_losses.append(accelerator.gather_for_metrics(value_type_loss.repeat(args.per_device_eval_batch_size)))
                abs_value_losses.append(accelerator.gather_for_metrics(abs_value_loss.repeat(args.per_device_eval_batch_size)))

            losses = torch.cat(losses)
            eval_loss = torch.mean(losses)
            mlm_losses = torch.cat(mlm_losses)
            eval_mlm_loss = torch.mean(mlm_losses)
            var_type_losses = torch.cat(var_type_losses)
            eval_var_type_loss = torch.mean(var_type_losses)
            value_type_losses = torch.cat(value_type_losses)
            eval_value_type_loss = torch.mean(value_type_losses)
            abs_value_losses = torch.cat(abs_value_losses)
            eval_abs_value_loss = torch.mean(abs_value_losses)

            try:
                eval_loss = torch.mean(losses)
                perplexity = math.exp(eval_mlm_loss)
            except OverflowError:
                perplexity = float("inf")

            logger.info(f"epoch {epoch} --- eval_loss: {eval_loss}, eval_perplexity: {perplexity}, eval_mlm_loss: {eval_mlm_loss}, eval_var_type_loss: {eval_var_type_loss}, eval_value_type_loss: {eval_value_type_loss}, eval_abs_value_loss: {eval_abs_value_loss}")
            
            if args.with_tracking:
                accelerator.log(
                    {
                        "eval_loss": eval_loss,
                        "eval_perplexity": perplexity,
                        "eval_mlm_loss": eval_mlm_loss,
                        "eval_var_type_loss": eval_var_type_loss,
                        "eval_value_type_loss": eval_value_type_loss,
                        "eval_abs_value_loss": eval_abs_value_loss,
                        "train_loss": total_loss.item() / len(train_dataloader),
                        "train_mlm_loss": total_mlm_loss.item() / len(train_dataloader),
                        "train_var_type_loss": total_var_type_loss.item() / len(train_dataloader),
                        "train_value_type_loss": total_value_type_loss.item() / len(train_dataloader),
                        "train_abs_value_loss": total_abs_value_loss.item() / len(train_dataloader),
                        "epoch": epoch,
                        "step": completed_steps,
                    },
                    step=completed_steps,
                )

            if args.push_to_hub and epoch < args.num_train_epochs - 1:
                accelerator.wait_for_everyone()
                unwrapped_model = accelerator.unwrap_model(model)
                unwrapped_model.save_pretrained(
                    args.output_dir, is_main_process=accelerator.is_main_process, save_function=accelerator.save
                )
                if accelerator.is_main_process:
                    tokenizer.save_pretrained(args.output_dir)
                    repo.push_to_hub(
                        commit_message=f"Training in progress epoch {epoch}", blocking=False, auto_lfs_prune=True
                    )

            if args.checkpointing_steps == "epoch":
                output_dir = f"epoch_{epoch}"
                if args.output_dir is not None:
                    output_dir = os.path.join(args.output_dir, output_dir)
                accelerator.save_state(output_dir)

    else:
        # only evaluate
        pass

    if args.with_tracking:
        accelerator.end_training()

    if args.output_dir is not None:
        accelerator.wait_for_everyone()
        unwrapped_model = accelerator.unwrap_model(model) # this is the best model
        unwrapped_model.save_pretrained(
            args.output_dir, is_main_process=accelerator.is_main_process, save_function=accelerator.save
        )
        if accelerator.is_main_process:
            tokenizer.save_pretrained(args.output_dir)
            if args.push_to_hub:
                repo.push_to_hub(commit_message="End of training", auto_lfs_prune=True)
        


if __name__ == "__main__":
    main()