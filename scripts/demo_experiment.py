#!/usr/bin/env python3
"""
Demo Experiment Flow — End-to-end RunPod test.

1. Creates a RunPod pod (RTX 4000 Ada, cheapest with SSH)
2. Waits for pod to be ready
3. Uploads MNIST CNN training script via SSH
4. Runs experiment on pod
5. Monitors via polling (DONE marker)
6. Downloads results
7. Terminates pod

Usage:
    python scripts/demo_experiment.py
    python scripts/demo_experiment.py --gpu "NVIDIA GeForce RTX 4090" --keep-pod
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure tao is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_GPU = "NVIDIA RTX 4000 Ada Generation"
IMAGE = "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
POLL_INTERVAL = 10  # seconds between status checks
POD_READY_TIMEOUT = 300  # 5 min to wait for pod startup
EXPERIMENT_TIMEOUT = 300  # 5 min max for training


# ---------------------------------------------------------------------------
# MNIST Training Script (uploaded to pod)
# ---------------------------------------------------------------------------

TRAIN_SCRIPT = r'''#!/usr/bin/env python3
"""MNIST CNN — demo experiment for Tao pipeline validation."""
import json
import os
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

TASK_ID = os.environ.get("TASK_ID", "mnist_cnn")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "/workspace/results")
EPOCHS = 5
BATCH_SIZE = 128
LR = 0.01

os.makedirs(RESULTS_DIR, exist_ok=True)

# Write PID file
pid_file = os.path.join(RESULTS_DIR, f"{TASK_ID}.pid")
with open(pid_file, "w") as f:
    f.write(str(os.getpid()))

print(f"[{TASK_ID}] Starting MNIST CNN training on {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Data
transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))])
train_data = datasets.MNIST("/workspace/data", train=True, download=True, transform=transform)
test_data = datasets.MNIST("/workspace/data", train=False, transform=transform)
train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True, num_workers=2)
test_loader = DataLoader(test_data, batch_size=1000, num_workers=2)

# Model
class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.pool = nn.MaxPool2d(2)
        self.fc1 = nn.Linear(9216, 128)
        self.fc2 = nn.Linear(128, 10)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.25)

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        x = self.dropout(x)
        x = torch.flatten(x, 1)
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        return self.fc2(x)

model = SimpleCNN().to(device)
optimizer = optim.Adam(model.parameters(), lr=LR)
criterion = nn.CrossEntropyLoss()

start_time = time.time()

# Train
for epoch in range(1, EPOCHS + 1):
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        pred = output.argmax(dim=1)
        correct += pred.eq(target).sum().item()
        total += len(target)

    train_acc = correct / total
    avg_loss = total_loss / len(train_loader)

    # Evaluate
    model.eval()
    test_correct = 0
    test_total = 0
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            pred = output.argmax(dim=1)
            test_correct += pred.eq(target).sum().item()
            test_total += len(target)
    test_acc = test_correct / test_total

    elapsed = time.time() - start_time
    print(f"Epoch {epoch}/{EPOCHS} — loss={avg_loss:.4f} train_acc={train_acc:.4f} test_acc={test_acc:.4f} elapsed={elapsed:.1f}s")

    # Write progress file (Tao protocol)
    progress = {
        "task_id": TASK_ID,
        "epoch": epoch,
        "total_epochs": EPOCHS,
        "loss": avg_loss,
        "train_acc": train_acc,
        "test_acc": test_acc,
        "elapsed_sec": elapsed,
    }
    progress_file = os.path.join(RESULTS_DIR, f"{TASK_ID}_PROGRESS.json")
    with open(progress_file, "w") as f:
        json.dump(progress, f, indent=2)

# Save model
torch.save(model.state_dict(), os.path.join(RESULTS_DIR, "model.pt"))

# Final results
total_time = time.time() - start_time
results = {
    "task_id": TASK_ID,
    "status": "success",
    "epochs": EPOCHS,
    "final_test_acc": test_acc,
    "final_train_acc": train_acc,
    "final_loss": avg_loss,
    "total_time_sec": total_time,
    "device": str(device),
    "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
}
print(f"\n[{TASK_ID}] Training complete: test_acc={test_acc:.4f} in {total_time:.1f}s")

# Write result file
with open(os.path.join(RESULTS_DIR, f"{TASK_ID}_result.json"), "w") as f:
    json.dump(results, f, indent=2)

# Write DONE marker (Tao protocol)
with open(os.path.join(RESULTS_DIR, f"{TASK_ID}_DONE"), "w") as f:
    json.dump(results, f, indent=2)

# Clean up PID file
os.remove(pid_file)
print(f"[{TASK_ID}] DONE marker written. Experiment complete.")
'''


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def run_ssh(host: str, port: int, cmd: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run command on pod via SSH."""
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-p", str(port),
        f"root@{host}",
        cmd,
    ]
    result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def scp_to_pod(host: str, port: int, local_path: str, remote_path: str) -> bool:
    """Copy file to pod via SCP."""
    scp_cmd = [
        "scp", "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-P", str(port),
        local_path,
        f"root@{host}:{remote_path}",
    ]
    result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=120)
    return result.returncode == 0


def scp_from_pod(host: str, port: int, remote_path: str, local_path: str) -> bool:
    """Copy file from pod via SCP."""
    scp_cmd = [
        "scp", "-r",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-P", str(port),
        f"root@{host}:{remote_path}",
        local_path,
    ]
    result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=120)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def create_pod(gpu_type: str) -> dict:
    """Step 1: Create RunPod pod."""
    import runpod
    runpod.api_key = os.environ["RUNPOD_API_KEY"]

    log(f"Creating pod with {gpu_type}...")
    pod = runpod.create_pod(
        name="tao-demo-mnist",
        image_name=IMAGE,
        gpu_type_id=gpu_type,
        gpu_count=1,
        container_disk_in_gb=20,
        volume_in_gb=0,
        cloud_type="ALL",
        start_ssh=True,
        support_public_ip=True,
        ports="22/tcp",  # explicitly request SSH TCP port
    )
    pod_id = pod["id"]
    log(f"Pod created: {pod_id}")
    return pod


def wait_for_ready(pod_id: str) -> dict:
    """Step 2: Wait for pod to be RUNNING with SSH available."""
    import runpod
    runpod.api_key = os.environ["RUNPOD_API_KEY"]

    log("Waiting for pod to be ready...")
    start = time.time()
    while time.time() - start < POD_READY_TIMEOUT:
        pod = runpod.get_pod(pod_id)
        status = pod.get("desiredStatus", "unknown")
        runtime = pod.get("runtime")

        if status == "RUNNING" and runtime:
            # Extract SSH info from runtime ports
            # RunPod exposes SSH as: privatePort=22, type=tcp, isIpPublic=true
            ports = runtime.get("ports", [])
            ssh_port = None
            ssh_host = None
            for p in ports:
                if p.get("privatePort") == 22 and p.get("type") == "tcp":
                    ssh_host = p.get("ip")
                    ssh_port = p.get("publicPort")
                    break

            if ssh_host and ssh_port:
                log(f"Pod RUNNING — SSH at {ssh_host}:{ssh_port}")
                # Give sshd time to start
                time.sleep(10)
                # Retry SSH connection a few times
                for attempt in range(3):
                    try:
                        rc, out, err = run_ssh(ssh_host, ssh_port, "echo ok", timeout=20)
                        if rc == 0 and "ok" in out:
                            log("SSH connection verified")
                            return {"pod": pod, "ssh_host": ssh_host, "ssh_port": ssh_port}
                    except Exception:
                        pass
                    log(f"SSH attempt {attempt+1}/3 failed, retrying in 10s...")
                    time.sleep(10)

        elapsed = int(time.time() - start)
        log(f"  status={status}, elapsed={elapsed}s...")
        time.sleep(10)

    raise TimeoutError(f"Pod not ready after {POD_READY_TIMEOUT}s")


def upload_and_run(ssh_host: str, ssh_port: int) -> None:
    """Step 3+4: Upload training script and run it."""
    # Write training script to temp file
    tmp_script = "/tmp/tao_mnist_train.py"
    with open(tmp_script, "w") as f:
        f.write(TRAIN_SCRIPT)

    # Upload
    log("Uploading training script...")
    run_ssh(ssh_host, ssh_port, "mkdir -p /workspace/results")
    ok = scp_to_pod(ssh_host, ssh_port, tmp_script, "/workspace/train.py")
    if not ok:
        raise RuntimeError("Failed to upload training script")
    log("Script uploaded to /workspace/train.py")

    # Launch experiment: write a launcher script, then execute it.
    # This avoids SSH hanging on backgrounded processes.
    log("Launching experiment...")
    launcher = (
        '#!/bin/bash\n'
        'cd /workspace\n'
        'export TASK_ID=mnist_cnn\n'
        'export RESULTS_DIR=/workspace/results\n'
        'python train.py > /workspace/results/train.log 2>&1\n'
    )
    # Write launcher script
    run_ssh(ssh_host, ssh_port,
            f"cat > /workspace/launch.sh << 'LAUNCHER_EOF'\n{launcher}LAUNCHER_EOF\nchmod +x /workspace/launch.sh",
            timeout=15)

    # Use ssh -f -n to fork SSH into background, run the script via nohup+setsid
    launch_cmd = [
        "ssh", "-f", "-n",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-p", str(ssh_port),
        f"root@{ssh_host}",
        "setsid nohup /workspace/launch.sh </dev/null >/dev/null 2>&1 &",
    ]
    result = subprocess.run(launch_cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to launch: {result.stderr}")

    # Verify it started (wait a moment for PID file)
    time.sleep(3)
    rc, out, _ = run_ssh(ssh_host, ssh_port,
                         "test -f /workspace/results/mnist_cnn.pid && echo RUNNING || echo STARTING",
                         timeout=15)
    log(f"Experiment status: {out.strip()}")


def monitor_experiment(ssh_host: str, ssh_port: int) -> dict:
    """Step 5: Monitor via DONE marker polling."""
    log(f"Monitoring experiment (poll every {POLL_INTERVAL}s, timeout {EXPERIMENT_TIMEOUT}s)...")
    start = time.time()

    while time.time() - start < EXPERIMENT_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        elapsed = int(time.time() - start)

        # Check DONE marker
        rc, out, _ = run_ssh(
            ssh_host, ssh_port,
            "cat /workspace/results/mnist_cnn_DONE 2>/dev/null || echo NOT_DONE",
            timeout=15,
        )
        if rc == 0 and "NOT_DONE" not in out and out.strip():
            try:
                result = json.loads(out.strip())
                log(f"DONE! test_acc={result['final_test_acc']:.4f} in {result['total_time_sec']:.1f}s")
                return result
            except json.JSONDecodeError:
                pass

        # Check progress
        rc, out, _ = run_ssh(
            ssh_host, ssh_port,
            "cat /workspace/results/mnist_cnn_PROGRESS.json 2>/dev/null || echo NO_PROGRESS",
            timeout=15,
        )
        if rc == 0 and "NO_PROGRESS" not in out:
            try:
                prog = json.loads(out.strip())
                epoch = prog.get("epoch", "?")
                total = prog.get("total_epochs", "?")
                acc = prog.get("test_acc", 0)
                log(f"  [{elapsed}s] epoch {epoch}/{total} test_acc={acc:.4f}")
            except json.JSONDecodeError:
                log(f"  [{elapsed}s] running...")
        else:
            log(f"  [{elapsed}s] waiting for first epoch...")

        # Check if process died
        rc, out, _ = run_ssh(
            ssh_host, ssh_port,
            "cat /workspace/results/mnist_cnn.pid 2>/dev/null && echo PID_EXISTS || echo NO_PID",
            timeout=15,
        )
        if "NO_PID" in out:
            # PID gone + no DONE = check for error
            rc2, log_tail, _ = run_ssh(
                ssh_host, ssh_port,
                "tail -20 /workspace/results/train.log 2>/dev/null || echo NO_LOG",
                timeout=15,
            )
            if "NO_LOG" not in log_tail and "Error" in log_tail:
                raise RuntimeError(f"Experiment crashed:\n{log_tail}")

    raise TimeoutError(f"Experiment did not complete within {EXPERIMENT_TIMEOUT}s")


def collect_results(ssh_host: str, ssh_port: int, local_dir: str) -> None:
    """Step 6: Download results from pod (JSON files only, skip large model weights)."""
    log(f"Downloading results to {local_dir}/...")
    os.makedirs(local_dir, exist_ok=True)

    # Download only the small result files (skip model.pt which can be huge)
    files_to_download = [
        "mnist_cnn_DONE",
        "mnist_cnn_result.json",
        "mnist_cnn_PROGRESS.json",
        "train.log",
    ]
    for fname in files_to_download:
        ok = scp_from_pod(ssh_host, ssh_port, f"/workspace/results/{fname}", f"{local_dir}/{fname}")
        if ok:
            size = Path(f"{local_dir}/{fname}").stat().st_size
            log(f"  {fname} ({size} bytes)")
        else:
            log(f"  {fname} — skipped (not found or failed)")


def terminate_pod(pod_id: str) -> None:
    """Step 7: Terminate the pod."""
    import runpod
    runpod.api_key = os.environ["RUNPOD_API_KEY"]
    log(f"Terminating pod {pod_id}...")
    runpod.terminate_pod(pod_id)
    log("Pod terminated")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tao Demo Experiment — MNIST CNN on RunPod")
    parser.add_argument("--gpu", default=DEFAULT_GPU, help=f"GPU type (default: {DEFAULT_GPU})")
    parser.add_argument("--keep-pod", action="store_true", help="Don't terminate pod after experiment")
    parser.add_argument("--output-dir", default="workspaces/demo_results", help="Local results directory")
    args = parser.parse_args()

    if not os.environ.get("RUNPOD_API_KEY"):
        print("ERROR: RUNPOD_API_KEY not set. Run: source ~/.zshrc")
        sys.exit(1)

    pod_id = None
    try:
        # 1. Create pod
        pod = create_pod(args.gpu)
        pod_id = pod["id"]

        # 2. Wait for ready
        info = wait_for_ready(pod_id)
        ssh_host = info["ssh_host"]
        ssh_port = info["ssh_port"]

        # 3+4. Upload and run
        upload_and_run(ssh_host, ssh_port)

        # 5. Monitor
        result = monitor_experiment(ssh_host, ssh_port)

        # 6. Collect results
        collect_results(ssh_host, ssh_port, args.output_dir)

        # Summary
        print("\n" + "=" * 60)
        print("EXPERIMENT COMPLETE")
        print("=" * 60)
        print(f"  GPU:       {result.get('gpu_name', 'unknown')}")
        print(f"  Test Acc:  {result['final_test_acc']:.4f}")
        print(f"  Train Acc: {result['final_train_acc']:.4f}")
        print(f"  Loss:      {result['final_loss']:.4f}")
        print(f"  Time:      {result['total_time_sec']:.1f}s")
        print(f"  Results:   {args.output_dir}/")
        print("=" * 60)

    except KeyboardInterrupt:
        log("Interrupted by user")
    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if pod_id and not args.keep_pod:
            try:
                terminate_pod(pod_id)
            except Exception as e:
                log(f"WARNING: Failed to terminate pod {pod_id}: {e}")
                log(f"  Manually terminate at: https://www.runpod.io/console/pods")
        elif pod_id:
            log(f"Pod {pod_id} left running (--keep-pod). Terminate manually when done.")


if __name__ == "__main__":
    main()
