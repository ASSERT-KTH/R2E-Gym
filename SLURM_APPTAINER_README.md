# Running R2E-Gym on SLURM with Apptainer backend

This guide explains how to run R2E-Gym on a SLURM cluster using the Apptainer backend for test containers.

## Setup Instructions

### 1. Install Dependencies

```bash
uv sync
```

### 2. Verify Installation

```bash
pytest tests/test_apptainer.py
```

### 3. Submit Job

```bash
cd $R2E_DIR
sbatch run_r2egym_slurm.sh
```

### Apptainer cache grows too large

Apptainer caches Docker images. Clean old images:
```bash
# List cached images
apptainer cache list

# Clean cache
apptainer cache clean
```

### Virtual environment issues

If dependencies fail to install:
```bash
# Remove and recreate venv
cd $R2E_DIR
rm -rf .venv
uv venv .venv
source .venv/bin/activate
uv sync && uv pip install -e .
```

## Interactive Testing

For testing before submitting jobs:

```bash
# Request interactive node
srun --pty --cpus-per-task=8 --mem=32G --time=2:00:00 bash

# Load environment
source /proj/berzelius-2024-336/x_andaf/r2e-gym/setup_env.sh
source $R2E_DIR/.venv/bin/activate

# Run small test
cd $R2E_DIR
python src/r2egym/agenthub/run/edit.py runagent_multiple \
    --backend "apptainer" \
    --max_workers 4 \
    --k 5 \
    --dataset "R2E-Gym/SWE-Bench-Verified" \
    # ... other parameters
```

## Notes

- First run will be slower as Docker images are pulled and cached
- Subsequent runs use cached images from `$APPTAINER_CACHEDIR`
- All large data stays in `/proj` to avoid quota issues
- The setup script can be sourced in your `~/.bashrc` for convenience

## Quick Reference

```bash
# Setup (one time)
source setup_env.sh
uv venv .venv && source .venv/bin/activate
uv sync && uv pip install -e .

# Run job
sbatch run_r2egym_slurm.sh

# Check status
squeue -u x_andaf
tail -f logs/r2egym_*.out
```
