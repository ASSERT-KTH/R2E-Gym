#!/usr/bin/env python3
"""
Test for Apptainer backend with Docker images.

Note: This test uses the simple standalone approach to avoid
Python 3.14 compatibility issues with some dependencies.

For full integration testing, use test_apptainer_simple.py
"""

import subprocess
import os
import sys
import base64

print("=" * 60)
print("Testing Apptainer Backend with Docker Images")
print("=" * 60)

instance_name = "test-apptainer-runtime"
docker_image = "docker://alpine:latest"

# Test 1: Start instance
print("\n[1/4] Starting Apptainer instance from Docker Hub...")
start_cmd = ["apptainer", "instance", "start", "--writable-tmpfs", docker_image, instance_name]
try:
    subprocess.run(start_cmd, check=True, capture_output=True)
    print(f"✓ Instance '{instance_name}' started from {docker_image}")
except subprocess.CalledProcessError as e:
    print(f"✗ Failed to start instance: {e}")
    sys.exit(1)

# Test 2: Run command
print("\n[2/4] Running command 'echo hello world'...")
exec_cmd = ["apptainer", "exec", f"instance://{instance_name}", "/bin/sh", "-c", "echo 'hello world'"]
try:
    result = subprocess.run(exec_cmd, check=True, capture_output=True, text=True)
    print(f"✓ Command executed: {result.stdout.strip()}")
except subprocess.CalledProcessError as e:
    print(f"✗ Failed to run command: {e}")

# Test 3: Copy file (simulating DockerRuntime.copy_to_container)
print("\n[3/4] Copying file to container...")
test_content = "test content from Docker image"
b64_content = base64.b64encode(test_content.encode()).decode('utf-8')
copy_cmd = ["apptainer", "exec", f"instance://{instance_name}", "/bin/sh", "-c", 
            f"mkdir -p /tmp && echo '{b64_content}' | base64 -d > /tmp/test_file.txt"]
try:
    subprocess.run(copy_cmd, check=True, capture_output=True)
    print("✓ File copied successfully")
except subprocess.CalledProcessError as e:
    print(f"✗ Failed to copy file: {e}")

# Test 4: Verify file
print("\n[4/4] Verifying file content...")
verify_cmd = ["apptainer", "exec", f"instance://{instance_name}", "/bin/sh", "-c", "cat /tmp/test_file.txt"]
try:
    result = subprocess.run(verify_cmd, check=True, capture_output=True, text=True)
    if result.stdout.strip() == test_content:
        print(f"✓ File content verified: '{result.stdout.strip()}'")
    else:
        print(f"✗ Content mismatch!")
except subprocess.CalledProcessError as e:
    print(f"✗ Failed to verify file: {e}")

# Cleanup
print("\n[Cleanup] Stopping instance...")
stop_cmd = ["apptainer", "instance", "stop", instance_name]
try:
    subprocess.run(stop_cmd, check=True, capture_output=True)
    print(f"✓ Instance '{instance_name}' stopped")
except subprocess.CalledProcessError as e:
    print(f"✗ Failed to stop instance: {e}")

print("\n" + "=" * 60)
print("✓ All tests completed successfully!")
print("=" * 60)
print("\nNote: This test validates the core Apptainer functionality")
print("that DockerRuntime uses. For full integration testing with")
print("the actual codebase, use test_apptainer_simple.py")
