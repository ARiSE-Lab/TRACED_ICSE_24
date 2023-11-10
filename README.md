# TRACED: Execution-aware Pre-training for Source Code

## Install Dependencies

```
# Create conda env

conda create -n traced python=3.8.13;
conda activate traced;

# Install Python Packages

pip install -r requirements.txt;
pip install torch==1.12.1+cu113 torchvision==0.13.1+cu113 torchaudio==0.12.1 --extra-index-url https://download.pytorch.org/whl/cu113
https://github.com/NVIDIA/apex.git
cd apex;
pip install -v --disable-pip-version-check --no-cache-dir ./
```

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