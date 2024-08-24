MODEL_NAME_OR_PATH=/mnt/cz/models/Phi-3-mini-128k-instruct
# MODEL_NAME_OR_PATH=/home/chengzhang/models/Meta-Llama-3.1-8B
# MODEL_NAME_OR_PATH=princeton-nlp/SWE-Llama-13b
export VLLM_WORKER_MULTIPROC_METHOD=spawn
python -m swebench.inference.run_llama \
    --dataset_path princeton-nlp/SWE-bench_oracle \
    --model_name_or_path $MODEL_NAME_OR_PATH \
    --output_dir ./outputs \
    --split train \
    --temperature 0

python -m swebench.harness.run_evaluation \
    --predictions_path gold \
    --max_workers 1 \
    --instance_ids sympy__sympy-20590 \
    --run_id validate-gold
