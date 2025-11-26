#!/bin/bash
#SBATCH --job-name=r2e-gym-deepswe
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=48
#SBATCH --time=24:00:00
#SBATCH --mem=128G
#SBATCH --output=logs/r2egym_%j.out
#SBATCH --error=logs/r2egym_%j.err

# Configure project directory (adjust username as needed)
export PROJ_DIR="/proj/berzelius-2024-336/users/x_andaf"
export R2E_DIR="$PROJ_DIR/r2e-gym"

# Configure cache directories to use /proj (more space)
export UV_CACHE_DIR="$PROJ_DIR/.cache/uv"
export APPTAINER_CACHEDIR="$PROJ_DIR/.apptainer/cache"
export APPTAINER_TMPDIR="$PROJ_DIR/.apptainer/tmp"
export PIP_CACHE_DIR="$PROJ_DIR/.cache/pip"

# Create necessary directories
mkdir -p $R2E_DIR/logs
mkdir -p $R2E_DIR/traj
mkdir -p $APPTAINER_CACHEDIR
mkdir -p $APPTAINER_TMPDIR

# Activate virtual environment
source $R2E_DIR/.venv/bin/activate

# Set experiment variables
export TEMP=1
export EXP_NAME="deepswe_32b_agent_swebv_eval_temp_1_run_1"

# Change to R2E-Gym directory
cd $R2E_DIR

# Run R2E-Gym with Apptainer backend
python src/r2egym/agenthub/run/edit.py runagent_multiple \
    --traj_dir "./traj" \
    --max_workers 48 \
    --start_idx 0 \
    --k 500 \
    --dataset "R2E-Gym/SWE-Bench-Verified" \
    --split "test" \
    --llm_name "openai/agentica-org/DeepSWE-Preview" \
    --scaffold "r2egym" \
    --use_fn_calling False \
    --exp_name "$EXP_NAME" \
    --temperature "$TEMP" \
    --max_steps_absolute 100 \
    --backend "apptainer" \
    --condense_history False \
    --max_reward_calc_time 1200 \
    --max_tokens 65536
