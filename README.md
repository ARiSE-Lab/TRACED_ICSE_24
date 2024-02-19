# TRACED: Execution-aware Pre-training for Source Code

## Install Dependencies

```sh
# Create conda env

conda create -n traced python=3.8.13;
conda activate traced;

# Install Python Packages

pip install -r requirements.txt;
pip install torch==1.12.1+cu113 torchvision==0.13.1+cu113 torchaudio==0.12.1 --extra-index-url https://download.pytorch.org/whl/cu113
git clone https://github.com/NVIDIA/apex.git
cd apex;
pip install -v --disable-pip-version-check --no-cache-dir ./

# Configure accelerate (required only for pre-training)

accelerate config;

>>>
In which compute environment are you running? ([0] This machine, [1] AWS (Amazon SageMaker)): 0
Which type of machine are you using? ([0] No distributed training, [1] multi-CPU, [2] multi-GPU, [3] TPU [4] MPS): 2
How many different machines will you use (use more than 1 for multi-node training)? [1]: 1
Do you want to use DeepSpeed? [yes/NO]: yes
Do you want to specify a json file to a DeepSpeed config? [yes/NO]: NO
What should be your DeepSpeed's ZeRO optimization stage (0, 1, 2, 3)? [2]: 2
Where to offload optimizer states? [none/cpu/nvme]: cpu
Where to offload parameters? [none/cpu/nvme]: cpu
How many gradient accumulation steps you're passing in your script? [1]: 64
Do you want to use gradient clipping? [yes/NO]: NO
Do you want to enable `deepspeed.zero.Init` when using ZeRO Stage-3 for constructing massive models? [yes/NO]: NO
How many GPU(s) should be used for distributed training? [1]:2
Do you wish to use FP16 or BF16 (mixed precision)? [NO/fp16/bf16]: fp16
>>>

```

## Pre-training data

See [tracer/README.md](./tracer/README.md).

> :warning: **WIP**: We are making the tracer tool available to foster further research.
> Please be aware that the currently-released version of the tracer tool may not reproduce our work, as we have not fully verified it end-to-end. Thank you!

## Data and pre-trained checkpoint

__Link:__ [Google Drive Link](https://drive.google.com/file/d/13hZj84I5a5R7ODvWJnW4mux9xS3kY9SU/view?usp=sharing)

__Important Note For Data Pre-processing:__ TRACED needs to align the execution states, such as dynamic values of identifiers, with syntactically valid code tokens, which requires the data pre-processing. To avoid the distribution shift, the task-specific fine-tuning data needs to do the same pre-processing with AST parser:
- Parse the source code with [Tree-sitter](https://github.com/tree-sitter/py-tree-sitter) and tokenize the sequence following the grammar of corresponding programming languages. 

Check out our data samples for the expected format of the pre-processed code.

## Tasks

- Clone Retrieval: Check `run_finetune_clone.py`

```sh

python finetune/run_finetune_clone.py \
    --task poj104 \
    --model_name_or_path checkpoints/traced_2e-5 \
    --train_batch_size 8 \
    --eval_batch_size 8 \
    --gradient_accumulation_steps 1 \
    --do_train \
    --do_eval \
    --do_test \
    --block_size 512 \
    --learning_rate 2e-5 \
    --num_train_epochs 2 \
    --output_dir $OUTPUT_DIR \
    --cache_dir $CACHE_DIR \
    --save_steps=1000 \
    --seed 42 \
    --fp16 \
    --warmup_ratio 0.1 \
    --train_data_file data/clone/train.jsonl \
    --eval_data_file data/clone/valid.jsonl \
    --test_data_file data/clone/test.jsonl \
    --overwrite_output_dir 2>&1 | tee $OUTPUT_DIR/log_finetune
```

- Vulnerablity Detection: Check `run_finetune_vul_detect.py`

```sh
python run_finetune_vul_detect.py \
	--task_name cxg_vd \
	--model_name_or_path checkpoints/traced_2e-5 \
	--per_device_eval_batch_size 8 \
	--per_device_train_batch_size 8 \
	--gradient_accumulation_steps 1 \
	--do_train \
	--do_eval \
	--do_predict \
	--load_best_model_at_end \
	--metric_for_best_model acc \
	--evaluation_strategy steps \
	--eval_steps 100 \
	--max_seq_length 512 \
	--learning_rate 8e-6 \
	--num_train_epochs 5 \
	--output_dir $OUTPUT_DIR \
	--cache_dir $CACHE_DIR \
	--save_steps=100 \
	--logging_steps=100 \
	--save_total_limit=1 \
	--seed 42 \
	--fp16 \
	--warmup_ratio 0.05 \
	--train_file data/vul_detect/CodeXGLUE/train_func.csv \
	--validation_file data/vul_detect/CodeXGLUE/valid_func.csv \
	--test_file data/vul_detect/CodeXGLUE/test_func.csv \
	--overwrite_output_dir 2>&1 | tee $OUTPUT_DIR/log_finetune

```