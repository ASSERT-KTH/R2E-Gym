#!/bin/bash
#SBATCH --job-name=crrl-swe-nano
#SBATCH --output=logs/reproduce_deepswe_%A_%a.out
#SBATCH --error=logs/reproduce_deepswe_%A_%a.err
#SBATCH --nodes=1
#SBATCH --gpus 1
#SBATCH --time=06:00:00
#SBATCH -C "fat"
#SBATCH --array=0-49

set -euo pipefail

# Use common Apptainer runtime config (requires CRRL_WORKDIR in env)
source /proj/berzelius-2024-336/users/x_andaf/CodeRepairRL/scripts/appt_common.sh

# Defaults
BASE_MODEL="Qwen/Qwen3-32B"
SCAFFOLD="deepswe"
OUTPUT_BASE_DIR="swe_bench/results_apptainer"
SUBSET="verified"
SPLIT="test"
SLICE=""
PORT=8000
SIF="/proj/berzelius-2024-336/users/x_andaf/CodeRepairRL/benchmarks/benchmark_container.sif"
WANDB_API_KEY=""
START_SERVER=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-model)
      BASE_MODEL="${2:?}"; shift 2;;
    --output-dir)
      OUTPUT_BASE_DIR="${2:?}"; shift 2;;
    --subset)
      SUBSET="${2:?}"; shift 2;;
    --split)
      SPLIT="${2:?}"; shift 2;;
    *)
      echo "Unknown arg: $1"; exit 1;;
  esac
done

# Derive slice and per-task settings when running as a SLURM array
TASK_ID=${SLURM_ARRAY_TASK_ID:-0}
SHARD_SIZE=10

# Auto-compute slice if not explicitly provided
if [[ -z "$SLICE" ]]; then
  START=$(( TASK_ID * SHARD_SIZE ))
  END=$(( START + SHARD_SIZE ))
  SLICE="${START}:${END}"
fi

# Offset port to avoid conflicts if multiple tasks land on the same node
if [[ $START_SERVER -eq 1 ]]; then
  PORT=$(( PORT + TASK_ID ))
fi

ENDPOINT="http://localhost:${PORT}/v1"

MODEL_NAME="$BASE_MODEL"

# Build a descriptive run tag: <scaffold>-<model_tag>
sanitize_tag() {
  local s="$1"
  s="${s//\//__}"
  s="${s// /_}"
  s=$(printf '%s' "$s" | sed -E 's/[^A-Za-z0-9._-]+/_/g; s/_+/_/g; s/^_+|_+$//g')
  printf '%s' "$s"
}

MODEL_TAG=$(sanitize_tag "$MODEL_NAME")

RUN_TAG="${SCAFFOLD}-${MODEL_TAG}"
OUTPUT_DIR="${OUTPUT_BASE_DIR}/${RUN_TAG}/shard_${TASK_ID}"

mkdir -p "$(dirname "logs/.keep")" "$OUTPUT_DIR"

wait_for_vllm() {
  local url="$1"; local -i tries=180
  while (( tries-- > 0 )); do
    code=$(curl -s -o /dev/null -w "%{http_code}" "$url/models" || true)
    if [[ "$code" == "200" ]]; then return 0; fi
    sleep 10
  done
  return 1
}

# Minimal parser selection based on base model and optional chat template
RP=""; TP=""; CT=""
case "${BASE_MODEL,,}" in
  *qwen*)     RP="--reasoning-parser qwen3"; TP="--tool-call-parser hermes";;
  *nemotron*) TP="--tool-call-parser llama3_json"; CT="--chat-template src/chat_templates/tool_chat_template_llama3.1_json.jinja";;
  *llama*)    TP="--tool-call-parser llama3_json"; CT="--chat-template src/chat_templates/tool_chat_template_llama3.1_json.jinja";;
  *mistral*)  TP="--tool-call-parser mistral"; CT="--chat-template src/chat_templates/tool_chat_template_mistral.jinja";;
  *)          TP="--tool-call-parser hermes";;
esac

VLLM_PID=""
if [[ $START_SERVER -eq 1 ]]; then
  echo "Starting vLLM server on port $PORT for base model '$BASE_MODEL'..."
  CMD=(apptainer exec $APPT_COMMON --env VLLM_ALLOW_LONG_MAX_MODEL_LEN=1 "$SIF" vllm serve "$BASE_MODEL" \
    --port "$PORT" \
    --enable-auto-tool-choice \
    # --tensor-parallel-size 8 \
    # --max-model-len 65536 \
    --max-model-len 50000 \
    --enable_prefix_caching \
    --rope-scaling '{"rope_type":"yarn","factor":1.52,"original_max_position_embeddings":32768}' \
    --gpu-memory-utilization 0.94 \
    $CT \
    $RP $TP)

  # Start server in background and capture PID
  "${CMD[@]}" > "logs/vllm_${SLURM_JOB_ID:-$$}.log" 2>&1 &
  VLLM_PID=$!
  trap 'if [[ -n "$VLLM_PID" ]]; then kill "$VLLM_PID" 2>/dev/null || true; fi' EXIT

  echo "Waiting for vLLM to become ready at $ENDPOINT ..."
  if ! wait_for_vllm "$ENDPOINT"; then
    echo "vLLM did not become ready in time" >&2
    exit 1
  fi
fi

export TEMP=1
export EXP_NAME="${MODEL_TAG}__32b_agent_swe_${SUBSET}_${SPLIT}_${SLICE}_eval"
export LLM_BASE_URL="$ENDPOINT"
uv run time python src/r2egym/agenthub/run/edit.py runagent_multiple \
    --traj_dir "./traj" \
    --max_workers $SHARD_SIZE \
    --start_idx $START \
    --k $SHARD_SIZE \
    --dataset "R2E-Gym/SWE-Bench-Verified" \
    --split "test" \
    --llm_name "hosted_vllm/Qwen/Qwen3-32B" \
    --scaffold "r2egym" \
    --use_fn_calling False \
    --exp_name "$EXP_NAME" \
    --temperature "$TEMP" \
    --max_steps_absolute 100 \
    --backend "apptainer" \
    --max_reward_calc_time 1200 \
    --max_tokens 50000
