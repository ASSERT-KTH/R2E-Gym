#!/bin/bash
# Run devstral evaluation N times sequentially on local CPU (no Slurm)
# Usage: ./reproduce_devstral.sh [--runs N]

set -euo pipefail

# Defaults
NUM_RUNS=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --runs)
      NUM_RUNS="${2:?}"; shift 2;;
    *)
      echo "Unknown arg: $1" >&2
      echo "Usage: $0 [--runs N]" >&2
      exit 1;;
  esac
done

# Hyperparameters
TOKEN_LIMIT=256000
TOOL_LIMIT=500
TEMP=0.2
MAX_WORKERS=16

echo "Running $NUM_RUNS devstral run(s) sequentially"

for ((run=0; run<NUM_RUNS; run++)); do
  export RUN_ID="$run"
  EXP_NAME="devstral_agent_swebv_eval_temp_${TEMP}_run_${RUN_ID}"
  TRAJ_DIR="./traj_devstral_run_${RUN_ID}"

  echo ""
  echo "----------------------------------------"
  echo "Starting run $((run + 1))/$NUM_RUNS"
  echo "RUN_ID: $RUN_ID"
  echo "Trajectory dir: $TRAJ_DIR"
  echo "Experiment name: $EXP_NAME"
  echo "----------------------------------------"

  # Run the agent with Mistral-hosted devstral-2512
  if time uv run python src/r2egym/agenthub/run/edit.py runagent_multiple \
      --traj_dir "$TRAJ_DIR" \
      --max_workers $MAX_WORKERS \
      --start_idx 0 \
      --k 500 \
      --dataset "R2E-Gym/SWE-Bench-Verified" \
      --split "test" \
      --llm_name "mistral/devstral-2512" \
      --scaffold "r2egym" \
      --use_fn_calling False \
      --exp_name "$EXP_NAME" \
      --temperature "$TEMP" \
      --max_steps_absolute "$TOOL_LIMIT" \
      --backend "docker" \
      --max_reward_calc_time 1200 \
      --max_tokens "$TOKEN_LIMIT"; then

    # Create SWE-Bench submission file
    uv run python src/r2egym/agenthub/trajectory/create_swebench_submission.py \
      --traj_file_path "${TRAJ_DIR}/${EXP_NAME}.jsonl" \
      --output_json_path "${TRAJ_DIR}/devstral__r2egym__run_${RUN_ID}.json"

    echo "✓ Run $((run + 1))/$NUM_RUNS completed successfully"
    echo "  Trajectories saved to: ${TRAJ_DIR}/${EXP_NAME}.jsonl"
    echo "  Submission saved to:   ${TRAJ_DIR}/devstral__r2egym__run_${RUN_ID}.json"
  else
    echo "✗ Run $((run + 1))/$NUM_RUNS failed" >&2
    exit 1
  fi
done

echo ""
echo "=========================================="
echo "All $NUM_RUNS devstral run(s) completed successfully!"
echo "=========================================="

