import os
import glob
import json
from fire import Fire
from r2egym.agenthub.trajectory.trajectory import Trajectory
from r2egym.agenthub.trajectory.create_swebench_submission import create_swebench_submission_from_trajectory

def aggregate_and_convert(traj_dir: str = "./traj", output_path: str = "swebench_submission.json", pattern: str = "*.jsonl"):
    """
    Aggregates trajectory files from a directory and creates a single SWE-bench submission file.
    
    Args:
        traj_dir: Directory containing the trajectory .jsonl files.
        output_path: Path where the final aggregated JSON submission file will be saved.
        pattern: Glob pattern to match files in traj_dir (default: *.jsonl).
    """
    # Expand paths
    traj_dir = os.path.expanduser(traj_dir)
    output_path = os.path.expanduser(output_path)
    
    files = glob.glob(os.path.join(traj_dir, pattern))
    files.sort() # Ensure deterministic order
    
    if not files:
        print(f"No files found in {traj_dir} matching {pattern}")
        return

    print(f"Found {len(files)} trajectory files in {traj_dir}")
    
    submission_entries = []
    total_trajectories = 0
    
    for file_path in files:
        print(f"Processing {os.path.basename(file_path)}...")
        try:
            with open(file_path, "r") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        trajectory = Trajectory.load_from_model_dump_json(line)
                        # Create submission entry for this trajectory
                        entry = create_swebench_submission_from_trajectory(trajectory)
                        submission_entries.append(entry)
                        total_trajectories += 1
                    except Exception as e:
                        print(f"Error processing file {os.path.basename(file_path)} line {line_num}: {e}")
        except Exception as e:
             print(f"Error reading file {file_path}: {e}")

    print(f"Total trajectories processed: {total_trajectories}")
    
    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(submission_entries, f, indent=2)
    
    print(f"Submission file written to {output_path}")

if __name__ == "__main__":
    Fire(aggregate_and_convert)

