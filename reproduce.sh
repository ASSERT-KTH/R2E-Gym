#!/bin/bash
#SBATCH --job-name=deepswe-reproduce
#SBATCH --output=logs/deepswe-reproduce_%A_%a.out
#SBATCH --error=logs/deepswe-reproduce_%A_%a.err
#SBATCH --nodes=1
#SBATCH --gpus 8
#SBATCH --time=12:00:00
#SBATCH -C "fat"
#SBATCH --array=0

wait_for_vllm() {
  local url="$1"; local -i tries=180
  while (( tries-- > 0 )); do
    code=$(curl -s -o /dev/null -w "%{http_code}" "$url/models" || true)
    if [[ "$code" == "200" ]]; then return 0; fi
    sleep 10
  done
  return 1
}

# Start VLLM server with tensor parallelism across 8 GPUs
export MAX_CONTEXT_LEN=65536
export ENDPOINT="http://localhost:8000/v1"
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
CMD=(uv run vllm serve agentica-org/DeepSWE-Preview \
    --tensor-parallel-size 8 \
    --max-model-len $MAX_CONTEXT_LEN \
    --hf-overrides '{"max_position_embeddings": '$MAX_CONTEXT_LEN'}' \
    --enable_prefix_caching)
"${CMD[@]}" > "logs/vllm_${SLURM_JOB_ID:-$$}_${SLURM_ARRAY_TASK_ID:-0}.log" 2>&1 &
VLLM_PID=$!
trap 'if [[ -n "$VLLM_PID" ]]; then kill "$VLLM_PID" 2>/dev/null || true; fi' EXIT

echo "Waiting for vLLM to become ready at $ENDPOINT ..."
if ! wait_for_vllm "$ENDPOINT"; then
    echo "vLLM did not become ready in time" >&2
    exit 1
fi


# Set required environment variables
export RUN_ID="${SLURM_ARRAY_TASK_ID:-0}"
export TEMP=1.0
export EXP_NAME="deepswe_32b_agent_swebv_eval_temp_${TEMP}_run_${RUN_ID}"

# Run the DeepSWE agent on SWE-Bench Verified
time uv run python src/r2egym/agenthub/run/edit.py runagent_multiple \
    --traj_dir "./traj_deepswe32b_run_${RUN_ID}" \
    --max_workers 48 \
    --start_idx 0 \
    --k 500 \
    --dataset "R2E-Gym/SWE-Bench-Verified" \
    --split "test" \
    --llm_name "hosted_vllm/agentica-org/DeepSWE-Preview" \
    --scaffold "r2egym" \
    --use_fn_calling False \
    --exp_name "$EXP_NAME" \
    --temperature "$TEMP" \
    --max_steps_absolute 100 \
    --backend "apptainer" \
    --max_reward_calc_time 1200 \
    --max_tokens 65536

# Create SWE-Bench submission file
uv run python src/r2egym/agenthub/trajectory/create_swebench_submission.py \
    --traj_file_path "traj_deepswe32b_run_${RUN_ID}/${EXP_NAME}.jsonl" \
    --output_json_path "traj_deepswe32b_run_${RUN_ID}/deepswe_32b__r2egym__run_${RUN_ID}.json"