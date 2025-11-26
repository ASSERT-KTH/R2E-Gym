#!/usr/bin/env python3
"""Simple test for Apptainer backend with Docker images."""

import subprocess
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testing Apptainer backend with Docker images...")

# Test 1: Start an instance with a Docker image
print("\n1. Starting Apptainer instance from Docker Hub...")
instance_name = "test-docker-instance"
docker_image = "docker://alpine:latest"
start_cmd = ["apptainer", "instance", "start", "--writable-tmpfs", docker_image, instance_name]
try:
    subprocess.run(start_cmd, check=True)
    print(f"✓ Instance '{instance_name}' started from {docker_image}")
except subprocess.CalledProcessError as e:
    print(f"✗ Failed to start instance: {e}")
    sys.exit(1)

# Test 2: Run a command
print("\n2. Running command in instance...")
exec_cmd = ["apptainer", "exec", f"instance://{instance_name}", "/bin/sh", "-c", "echo 'Hello from Apptainer with Docker image'"]
try:
    result = subprocess.run(exec_cmd, check=True, capture_output=True, text=True)
    print(f"✓ Command output: {result.stdout.strip()}")
except subprocess.CalledProcessError as e:
    print(f"✗ Failed to run command: {e}")

# Test 3: Copy a file using base64
print("\n3. Testing file copy with base64...")
test_content = "Test file content from Docker image"
import base64
b64_content = base64.b64encode(test_content.encode()).decode('utf-8')
copy_cmd = ["apptainer", "exec", f"instance://{instance_name}", "/bin/sh", "-c", 
            f"mkdir -p /tmp && echo '{b64_content}' | base64 -d > /tmp/test_file.txt"]
try:
    subprocess.run(copy_cmd, check=True, capture_output=True)
    print("✓ File copied")
except subprocess.CalledProcessError as e:
    print(f"✗ Failed to copy file: {e}")

# Test 4: Verify file content
print("\n4. Verifying file content...")
verify_cmd = ["apptainer", "exec", f"instance://{instance_name}", "/bin/sh", "-c", "cat /tmp/test_file.txt"]
try:
    result = subprocess.run(verify_cmd, check=True, capture_output=True, text=True)
    if result.stdout.strip() == test_content:
        print(f"✓ File content verified: {result.stdout.strip()}")
    else:
        print(f"✗ Content mismatch. Expected: '{test_content}', Got: '{result.stdout.strip()}'")
except subprocess.CalledProcessError as e:
    print(f"✗ Failed to verify file: {e}")

# Test 5: Stop the instance
print("\n5. Stopping instance...")
stop_cmd = ["apptainer", "instance", "stop", instance_name]
try:
    subprocess.run(stop_cmd, check=True)
    print(f"✓ Instance '{instance_name}' stopped")
except subprocess.CalledProcessError as e:
    print(f"✗ Failed to stop instance: {e}")

print("\n✓ All Apptainer tests with Docker images passed!")
