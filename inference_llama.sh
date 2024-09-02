# MODEL_NAME_OR_PATH=/mnt/models/Phi-3-mini-128k-instruct
# MODEL_NAME_OR_PATH=/mnt/models/yuzhe/llama3.1-instruct
# MODEL_NAME_OR_PATH=/mnt/models/yuzhe/phi3-mini-128k-new
# MODEL_NAME_OR_PATH=/mnt/models/yuzhe/Phi3_1-mini-rope4_5_swebench_oracle_120/phi3
# MODEL_NAME_OR_PATH=/mnt/models/yuzhe/DeepSeek-Coder-V2-Lite-Instruct
MODEL_NAME_OR_PATH=/mnt/teamdrive/model/DeepSeek-Coder-V2-Lite-Instruct
# MODEL_NAME_OR_PATH=/mnt/teamdrive/model/DeepSeek-Coder-V2-Instruct
# MODEL_NAME_OR_PATH=/home/chengzhang/models/Meta-Llama-3.1-8B
# MODEL_NAME_OR_PATH=princeton-nlp/SWE-Llama-13b
export VLLM_WORKER_MULTIPROC_METHOD=spawn
# for i in {4..10}
# do
#     python -m swebench.inference.run_llama \
#     --dataset_path princeton-nlp/SWE-bench_oracle \
#     --model_name_or_path $MODEL_NAME_OR_PATH \
#     --output_dir ./outputs_long/$i \
#     --top_p 0.8 \
#     --split test \
#     --temperature 0.8
# done
# python -m swebench.inference.run_llama \
#     --dataset_path princeton-nlp/SWE-bench_oracle \
#     --model_name_or_path $MODEL_NAME_OR_PATH \
#     --output_dir ./outputs_long \
#     --split test \
#     --temperature 0
#  --dataset_path princeton-nlp/SWE-bench_oracle \
# --dataset_path princeton-nlp/SWE-bench_Verified \
for i in {1..10}
do
python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Verified \
    --split test \
    --predictions_path /mnt/yuzhe/SWE-bench/outputs_long/$i/princeton-nlp__SWE-bench_oracle__test__DeepSeek-Coder-V2-Lite-Instruct__temp-0.8__top-p-0.8.jsonl \
    --max_workers 1 \
    --instance_ids test_all \
    --run_id $i \
    --clean False
done