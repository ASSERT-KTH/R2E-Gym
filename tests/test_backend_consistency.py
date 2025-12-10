
import pytest
import os
import sys
from datasets import load_dataset
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from r2egym.agenthub.environment.env import RepoEnv, EnvArgs
# from r2egym.agenthub.action.action import Action
# from r2egym.agenthub.runtime.docker import DockerRuntime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_swebench_sample():
    """Load a single sample from SWE-Bench Verified."""
    try:
        ds = load_dataset("R2E-Gym/SWE-Bench-Verified", split="test", streaming=True)
        # Get the first example
        return next(iter(ds))
    except Exception as e:
        pytest.skip(f"Failed to load SWE-Bench Verified dataset: {e}")

@pytest.fixture(scope="module")
def swebench_sample():
    return get_swebench_sample()

def run_actions_on_backend(sample, backend, actions, tool_paths=None):
    """Run a sequence of actions on a specific backend and return observations."""
    env_args = EnvArgs(ds=sample)
    
    # Initialize environment
    try:
        env = RepoEnv(args=env_args, logger=logger, backend=backend)
    except Exception as e:
        pytest.fail(f"Failed to initialize {backend} environment: {e}")

    # Add tools if provided
    if tool_paths:
        # Resolve paths relative to project root
        project_root = os.path.join(os.path.dirname(__file__), '..')
        resolved_tool_paths = [os.path.join(project_root, p) for p in tool_paths]
        env.add_commands(resolved_tool_paths)

    observations = []
    
    try:
        for action_cmd in actions:
            # Use runtime directly to bypass allowed commands check for raw bash commands
            # BUT for tool commands, we want to run them as if the agent did it, 
            # or just run them via runtime if they are available in PATH or via python
            
            # Since we added commands via env.add_commands, they should be in /usr/local/bin
            # and executable. So we can just run them as bash commands.
            
            output, exit_code = env.runtime.run(action_cmd)
            observations.append(output)
            
            # If we created a file, cat it to verify content
            if "echo" in action_cmd and ">" in action_cmd:
                filename = action_cmd.split(">")[-1].strip()
                output_check, _ = env.runtime.run(f"cat {filename}")
                observations.append(output_check)
                
    finally:
        env.close()
        
    return observations

def test_swebench_consistency(swebench_sample):
    """
    Test consistency between Docker and Apptainer backends on a SWE-Bench Verified sample.
    """
    # Check if docker and apptainer are available
    import shutil
    if not shutil.which("docker"):
        pytest.skip("Docker not installed")
    if not shutil.which("apptainer"):
        pytest.skip("Apptainer not installed")

    # Define tools to load
    tool_paths = [
        "src/r2egym/agenthub/tools/r2egym/file_editor.py",
        "src/r2egym/agenthub/tools/search.py",
        "src/r2egym/agenthub/tools/r2egym/execute_bash.py",
        "src/r2egym/agenthub/tools/finish.py"
    ]

    # Define a set of actions to perform
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    test_file = f"/tmp/test_file_editor_{unique_id}.txt"
    
    actions = [
        # Basic Bash
        "pwd",
        "ls -la",
        "echo 'Hello form R2E-Gym' > /tmp/test_consistency.txt",
        "env | grep PATH",
        "python3 --version",
        
        # Tool: execute_bash
        "execute_bash --cmd 'echo \"Hello from execute_bash\"'",
        
        # Tool: file_editor
        f"file_editor create --path {test_file} --file_text 'Line 1\nLine 2\nLine 3'",
        f"file_editor view --path {test_file}",
        f"file_editor str_replace --path {test_file} --old_str 'Line 2' --new_str 'Line 2 Modified'",
        f"file_editor insert --path {test_file} --insert_line 3 --new_str 'Line 4 Inserted'",
        f"file_editor undo_edit --path {test_file}",
        
        # Tool: search
        f"search --search_term 'Line' --path {test_file}",
        
        # Tool: finish
        "finish submit --result 'Test complete'"
    ]

    # Run on Docker
    logger.info("Running on Docker backend...")
    docker_obs = run_actions_on_backend(swebench_sample, "docker", actions, tool_paths)
    
    # Run on Apptainer
    logger.info("Running on Apptainer backend...")
    apptainer_obs = run_actions_on_backend(swebench_sample, "apptainer", actions, tool_paths)

    # Compare results
    assert len(docker_obs) == len(apptainer_obs), "Number of observations differs"
    
    # Mapping of expected output substrings for validation
    # Since indices can shift due to extra observations (e.g. from echo), we check by content content
    
    for i, (d_obs, a_obs) in enumerate(zip(docker_obs, apptainer_obs)):
        logger.info(f"Observation {i}:")
        logger.info(f"Docker Output:\n{d_obs.strip()}")
        logger.info(f"Apptainer Output:\n{a_obs.strip()}")
        logger.info("-" * 20)
        
        # General consistency check
        # We can't strict assert equality because of PIDs, timestamps, temp paths etc.
        # But for specific tool outputs, we should see key phrases.
        
        # 1. Created file content (via echo)
        if "Hello form R2E-Gym" in d_obs:
            assert d_obs.strip() == a_obs.strip()
            
        # 2. execute_bash output
        if "Hello from execute_bash" in d_obs and "STDOUT" in d_obs:
            assert "Hello from execute_bash" in a_obs
            
        # 3. file_editor create output
        if f"File created at {test_file}" in d_obs:
             assert f"File created at {test_file}" in a_obs

        # 4. file_editor view output
        if f"running `cat -n` on {test_file}" in d_obs:
             assert "Line 1" in a_obs
             assert "Line 2" in a_obs

        # 5. file_editor str_replace output
        if "has been edited" in d_obs and "Line 2 Modified" in d_obs:
            assert "Line 2 Modified" in a_obs
            
        # 6. file_editor insert output
        if "Line 4 Inserted" in d_obs:
            assert "Line 4 Inserted" in a_obs
            
        # 7. file_editor undo_edit output
        if "undone successfully" in d_obs:
            assert "undone successfully" in a_obs

        # 8. search output
        if "Matches for" in d_obs and test_file in d_obs:
            assert "Line 1" in a_obs

        # 9. finish output
        if "<<<Finished>>>" in d_obs:
            assert "<<<Finished>>>" in a_obs

    logger.info("Consistency test passed!")

