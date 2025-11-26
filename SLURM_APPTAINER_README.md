# Running R2E-Gym on SLURM with Apptainer Backend

This guide explains how to run R2E-Gym on the Berzelius SLURM cluster using the Apptainer backend for test containers.

## Overview

- **R2E-Gym**: Installed directly in `/proj` directory (more space)
- **Test containers**: Spawned using Apptainer backend
- **Direct installation**: No container images needed for R2E-Gym itself

## Setup Instructions

### 1. Set Up Project Directory

```bash
# SSH to Berzelius
ssh x_andaf@berzelius.nsc.liu.se

# Create project directory (replace with your username)
export PROJ_DIR="/proj/berzelius-2024-336/x_andaf"
mkdir -p $PROJ_DIR/r2e-gym
cd $PROJ_DIR/r2e-gym

# Clone or transfer R2E-Gym
git clone <your-repo-url> .
# OR: scp -r /local/path/to/R2E-Gym x_andaf@berzelius.nsc.liu.se:$PROJ_DIR/r2e-gym/
```

### 2. Configure Environment Variables

Create a setup script to configure paths for the larger `/proj` storage:

```bash
# Create environment setup script
cat > setup_env.sh << 'EOF'
#!/bin/bash
# R2E-Gym Environment Setup for Berzelius

# Set project directory (adjust username as needed)
export PROJ_DIR="/proj/berzelius-2024-336/x_andaf"
export R2E_DIR="$PROJ_DIR/r2e-gym"

# Configure UV to use /proj for cache and installations
export UV_CACHE_DIR="$PROJ_DIR/.cache/uv"
export UV_PYTHON_INSTALL_DIR="$PROJ_DIR/.local/share/uv/python"

# Configure Apptainer to use /proj for cache
export APPTAINER_CACHEDIR="$PROJ_DIR/.apptainer/cache"
export APPTAINER_TMPDIR="$PROJ_DIR/.apptainer/tmp"

# Configure pip cache (if needed)
export PIP_CACHE_DIR="$PROJ_DIR/.cache/pip"

# Add local bin to PATH
export PATH="$HOME/.local/bin:$PATH"

# Create necessary directories
mkdir -p $UV_CACHE_DIR
mkdir -p $UV_PYTHON_INSTALL_DIR
mkdir -p $APPTAINER_CACHEDIR
mkdir -p $APPTAINER_TMPDIR
mkdir -p $PIP_CACHE_DIR

echo "Environment configured:"
echo "  R2E-Gym: $R2E_DIR"
echo "  UV Cache: $UV_CACHE_DIR"
echo "  Apptainer Cache: $APPTAINER_CACHEDIR"
EOF

chmod +x setup_env.sh
```

### 3. Install Dependencies

```bash
# Load environment
source setup_env.sh

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# Create virtual environment in /proj
cd $R2E_DIR
uv venv .venv
source .venv/bin/activate

# Install R2E-Gym and dependencies
uv sync && uv pip install -e .
```

### 4. Verify Installation

```bash
# Test Apptainer backend
python test_apptainer_simple.py

# Should see:
# ✓ Instance started from docker://alpine:latest
# ✓ Command executed
# ✓ File copied
# ✓ File content verified
# ✓ Instance stopped
```

### 5. Submit Job

```bash
cd $R2E_DIR
sbatch run_r2egym_slurm.sh
```

## Storage Usage

With this setup, large files are stored in `/proj` where you have ~14.6 TiB:

```
/proj/berzelius-2024-336/x_andaf/
├── r2e-gym/                    # R2E-Gym code and venv
│   ├── .venv/                  # Python virtual environment (~2-3 GB)
│   ├── traj/                   # Trajectory outputs
│   └── logs/                   # Job logs
├── .cache/
│   ├── uv/                     # UV package cache
│   └── pip/                    # Pip cache
└── .apptainer/
    ├── cache/                  # Docker images cache (can be large)
    └── tmp/                    # Temporary files
```

Your `/home` directory stays under quota with only:
- `~/.local/bin/uv` - UV binary (~50 MB)
- Small config files

## Monitoring

Check storage usage:
```bash
# Check /proj usage
du -sh /proj/berzelius-2024-336/x_andaf/*

# Check job status
squeue -u x_andaf

# View job output
tail -f logs/r2egym_<jobid>.out
```

## Troubleshooting

### "No space left on device"

If you see this error, check which directory is full:
```bash
# Check quotas
berzelius-quota

# Clean caches if needed
rm -rf $PROJ_DIR/.cache/uv/*
rm -rf $PROJ_DIR/.apptainer/cache/*
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
