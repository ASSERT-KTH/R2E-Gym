#!/usr/bin/env python3
"""Simple test for Apptainer backend with Docker images."""

import base64
import subprocess
import pytest

@pytest.fixture(scope="module")
def apptainer_instance():
    """Fixture to start and stop an Apptainer instance for testing."""
    instance_name = "test-docker-instance"
    docker_image = "docker://alpine:latest"
    
    # Start instance
    start_cmd = ["apptainer", "instance", "start", "--writable-tmpfs", docker_image, instance_name]
    try:
        subprocess.run(start_cmd, check=True, capture_output=True)
        print(f"✓ Instance '{instance_name}' started from {docker_image}")
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to start instance: {e}")
    
    yield instance_name
    
    # Stop instance (teardown)
    stop_cmd = ["apptainer", "instance", "stop", instance_name]
    try:
        subprocess.run(stop_cmd, check=True, capture_output=True)
        print(f"✓ Instance '{instance_name}' stopped")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to stop instance: {e}")


def test_start_instance(apptainer_instance):
    """Test that the instance was started successfully."""
    # The fixture handles starting, so we just verify it exists
    assert apptainer_instance == "test-docker-instance"


def test_run_command(apptainer_instance):
    """Test running a command in the Apptainer instance."""
    exec_cmd = [
        "apptainer", "exec", "--pwd", "/", f"instance://{apptainer_instance}", 
        "/bin/sh", "-c", "echo 'Hello from Apptainer with Docker image'"
    ]
    result = subprocess.run(exec_cmd, check=True, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Hello from Apptainer with Docker image" in result.stdout
    print(f"✓ Command output: {result.stdout.strip()}")


def test_copy_file_base64(apptainer_instance):
    """Test copying a file using base64 encoding."""
    test_content = "Test file content from Docker image"
    b64_content = base64.b64encode(test_content.encode()).decode('utf-8')
    copy_cmd = [
        "apptainer", "exec", "--pwd", "/", f"instance://{apptainer_instance}", "/bin/sh", "-c",
        f"mkdir -p /tmp && echo '{b64_content}' | base64 -d > /tmp/test_file.txt"
    ]
    result = subprocess.run(copy_cmd, check=True, capture_output=True, text=True)
    assert result.returncode == 0
    print("✓ File copied")


def test_verify_file_content(apptainer_instance):
    """Test verifying the copied file content."""
    test_content = "Test file content from Docker image"
    verify_cmd = [
        "apptainer", "exec", "--pwd", "/", f"instance://{apptainer_instance}", 
        "/bin/sh", "-c", "cat /tmp/test_file.txt"
    ]
    result = subprocess.run(verify_cmd, check=True, capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == test_content
    print(f"✓ File content verified: {result.stdout.strip()}")
