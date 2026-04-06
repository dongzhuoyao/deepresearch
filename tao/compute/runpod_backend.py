"""RunPod compute backend — create/manage GPU pods for experiments."""
from __future__ import annotations
import os
import subprocess
import json
import time
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from tao.compute.base import ComputeBackend

if TYPE_CHECKING:
    from tao.config import Config

_SSH_KEY_CANDIDATES = ["id_ed25519", "id_rsa", "id_ecdsa"]


@lru_cache(maxsize=1)
def _find_ssh_key() -> str | None:
    """Auto-detect the first available SSH private key in ~/.ssh/."""
    ssh_dir = Path.home() / ".ssh"
    for name in _SSH_KEY_CANDIDATES:
        key_path = ssh_dir / name
        if key_path.is_file():
            return str(key_path)
    return None


class RunPodBackend(ComputeBackend):
    """Execute experiments on RunPod GPU pods.

    Manages full pod lifecycle: create, SSH into, run experiments,
    monitor, collect results, terminate.
    """

    def __init__(self, config: "Config") -> None:
        self._config = config
        self._api_key = config.runpod_api_key or os.environ.get("RUNPOD_API_KEY", "")
        self._ssh_key: str | None = _find_ssh_key()

    def _runpod(self) -> ModuleType:
        """Import runpod and set the API key. Centralizes the repeated boilerplate."""
        try:
            import runpod
        except ImportError:
            raise RuntimeError("runpod package not installed. Run: pip install runpod")
        runpod.api_key = self._api_key
        return runpod

    @property
    def backend_type(self) -> str:
        return "runpod"

    def project_dir(self, ws_name: str) -> str:
        return f"{self._config.runpod_volume_mount}/projects/{ws_name}"

    def env_cmd(self, project_name: str) -> str:
        return f"cd {self.project_dir(project_name)} &&"

    def create_pod(self, name: str) -> dict:
        """Create a RunPod GPU pod via the RunPod API."""
        runpod = self._runpod()
        if not self._api_key:
            raise ValueError("RUNPOD_API_KEY not set. Set it in config or environment.")

        kwargs = {
            "name": name,
            "image_name": self._config.runpod_image,
            "gpu_type_id": self._config.runpod_gpu_type,
            "gpu_count": self._config.runpod_gpu_count,
            "volume_in_gb": self._config.runpod_disk_gb,
            "volume_mount_path": self._config.runpod_volume_mount,
            "cloud_type": self._config.runpod_cloud_type,
        }
        if self._config.runpod_volume_id:
            kwargs["network_volume_id"] = self._config.runpod_volume_id
        if self._config.runpod_template_id:
            kwargs["template_id"] = self._config.runpod_template_id

        pod = runpod.create_pod(**kwargs)
        return pod

    def terminate_pod(self, pod_id: str) -> None:
        """Terminate a RunPod pod."""
        self._runpod().terminate_pod(pod_id)

    def list_pods(self) -> list[dict]:
        """List all active RunPod pods."""
        return self._runpod().get_pods()

    def get_pod_ssh_info(self, pod_id: str) -> dict:
        """Get SSH connection info for a pod.

        Returns dict with keys: host, port, username, ssh_key, mode.

        RunPod has two SSH modes:
        - "full": public IP + mapped port (supports SCP/SFTP/rsync)
        - "basic": proxied via ssh.runpod.io (no SCP/SFTP)
        """
        pod = self._runpod().get_pod(pod_id)
        runtime = pod.get("runtime") or {}
        ports = runtime.get("ports") or []

        # Try full SSH first: look for public IP + TCP port mapped to 22
        public_ip = None
        ssh_port = None
        for p in ports:
            if p.get("privatePort") == 22 and p.get("isIpPublic"):
                public_ip = p.get("ip")
                ssh_port = p.get("publicPort")
                break

        if public_ip and ssh_port:
            return {
                "host": public_ip,
                "port": ssh_port,
                "username": "root",
                "ssh_key": self._ssh_key,
                "mode": "full",
            }

        # Fallback: basic SSH via RunPod proxy
        return {
            "host": "ssh.runpod.io",
            "port": 22,
            "username": pod_id,
            "ssh_key": self._ssh_key,
            "mode": "basic",
        }

    def _ssh_cmd_prefix(self, ssh_info: dict) -> list[str]:
        """Build the ssh/rsync -e prefix from SSH info."""
        parts = ["ssh", "-o", "StrictHostKeyChecking=no"]
        if ssh_info.get("ssh_key"):
            parts += ["-i", ssh_info["ssh_key"]]
        if ssh_info["port"] != 22:
            parts += ["-p", str(ssh_info["port"])]
        return parts

    def _ssh_target(self, ssh_info: dict) -> str:
        """Return user@host string."""
        return f"{ssh_info['username']}@{ssh_info['host']}"

    def stop_pod(self, pod_id: str) -> None:
        """Stop a RunPod pod (preserves volume, releases GPU)."""
        self._runpod().stop_pod(pod_id)

    def wait_for_ready(self, pod_id: str, timeout_sec: int = 300, poll_sec: int = 5) -> bool:
        """Block until pod is running and has a runtime. Returns True if ready."""
        runpod = self._runpod()
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            pod = runpod.get_pod(pod_id)
            runtime = pod.get("runtime") or {}
            if runtime.get("uptimeInSeconds", 0) > 0:
                return True
            status = pod.get("desiredStatus", "")
            if status in ("EXITED", "TERMINATED", "ERROR"):
                return False
            time.sleep(poll_sec)
        return False

    def run_remote(self, pod_id: str, command: str, timeout_sec: int = 600) -> dict:
        """Execute a command on a pod via SSH.

        Returns dict with keys: stdout, stderr, returncode.
        """
        ssh_info = self.get_pod_ssh_info(pod_id)
        ssh_prefix = self._ssh_cmd_prefix(ssh_info)
        cmd = ssh_prefix + [self._ssh_target(ssh_info), command]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_sec,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Command timed out", "returncode": -1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": -1}

    def upload_code(self, pod_id: str, local_path: str, remote_path: str) -> bool:
        """Upload code to pod via rsync over SSH."""
        try:
            ssh_info = self.get_pod_ssh_info(pod_id)
            if ssh_info["mode"] == "basic":
                # Basic SSH doesn't support rsync; fall back to tar+ssh
                return self._upload_via_tar(ssh_info, local_path, remote_path)
            ssh_e = " ".join(self._ssh_cmd_prefix(ssh_info))
            cmd = [
                "rsync", "-avz", "--progress",
                "-e", ssh_e,
                f"{local_path}/",
                f"{self._ssh_target(ssh_info)}:{remote_path}/",
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            return result.returncode == 0
        except Exception:
            return False

    def _upload_via_tar(self, ssh_info: dict, local_path: str, remote_path: str) -> bool:
        """Upload via tar pipe over basic SSH (no rsync support)."""
        try:
            ssh_prefix = self._ssh_cmd_prefix(ssh_info)
            tar_cmd = ["tar", "-czf", "-", "-C", local_path, "."]
            ssh_cmd = ssh_prefix + [
                self._ssh_target(ssh_info),
                f"mkdir -p {remote_path} && tar -xzf - -C {remote_path}",
            ]
            tar_proc = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE)
            ssh_proc = subprocess.Popen(
                ssh_cmd, stdin=tar_proc.stdout, capture_output=True,
            )
            tar_proc.stdout.close()
            ssh_proc.communicate(timeout=300)
            return ssh_proc.returncode == 0
        except Exception:
            return False

    def download_results(self, pod_id: str, remote_path: str, local_path: str) -> bool:
        """Download results from pod via rsync."""
        try:
            ssh_info = self.get_pod_ssh_info(pod_id)
            if ssh_info["mode"] == "basic":
                return self._download_via_tar(ssh_info, remote_path, local_path)
            ssh_e = " ".join(self._ssh_cmd_prefix(ssh_info))
            cmd = [
                "rsync", "-avz", "--progress",
                "-e", ssh_e,
                f"{self._ssh_target(ssh_info)}:{remote_path}/",
                f"{local_path}/",
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=600)
            return result.returncode == 0
        except Exception:
            return False

    def _download_via_tar(self, ssh_info: dict, remote_path: str, local_path: str) -> bool:
        """Download via tar pipe over basic SSH."""
        try:
            ssh_prefix = self._ssh_cmd_prefix(ssh_info)
            ssh_cmd = ssh_prefix + [
                self._ssh_target(ssh_info),
                f"tar -czf - -C {remote_path} .",
            ]
            os.makedirs(local_path, exist_ok=True)
            tar_cmd = ["tar", "-xzf", "-", "-C", local_path]
            ssh_proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE)
            tar_proc = subprocess.Popen(tar_cmd, stdin=ssh_proc.stdout, capture_output=True)
            ssh_proc.stdout.close()
            tar_proc.communicate(timeout=600)
            return tar_proc.returncode == 0
        except Exception:
            return False

    def gpu_poll_script(
        self,
        candidate_gpu_ids: list[int],
        threshold_mb: int,
        poll_interval_sec: int,
        max_polls: int,
        marker_file: str,
        aggressive_mode: bool = False,
        aggressive_threshold_pct: int = 25,
    ) -> str:
        """Generate GPU polling script for RunPod pods.

        RunPod pods have dedicated GPUs, so they're typically always free.
        This script confirms GPU availability and writes the marker.
        """
        gpu_ids_str = ",".join(str(g) for g in candidate_gpu_ids) if candidate_gpu_ids else ""
        return f'''#!/bin/bash
set -e
MARKER="{marker_file}"
THRESHOLD={threshold_mb}
INTERVAL={poll_interval_sec}
MAX_POLLS={max_polls}
AGGRESSIVE={str(aggressive_mode).lower()}
AGG_PCT={aggressive_threshold_pct}
CANDIDATE_GPUS="{gpu_ids_str}"
poll=0

while true; do
    FREE_GPUS=""
    while IFS=',' read -r idx mem_used mem_total; do
        idx=$(echo "$idx" | xargs)
        mem_used=$(echo "$mem_used" | xargs)
        mem_total=$(echo "$mem_total" | xargs)

        # Skip if not in candidate list (if specified)
        if [ -n "$CANDIDATE_GPUS" ]; then
            echo "$CANDIDATE_GPUS" | grep -qw "$idx" || continue
        fi

        if [ "$mem_used" -lt "$THRESHOLD" ]; then
            FREE_GPUS="$FREE_GPUS$idx,"
        elif [ "$AGGRESSIVE" = "true" ] && [ "$mem_total" -gt 0 ]; then
            pct=$((mem_used * 100 / mem_total))
            if [ "$pct" -lt "$AGG_PCT" ]; then
                FREE_GPUS="$FREE_GPUS$idx,"
            fi
        fi
    done < <(nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader,nounits)

    # Remove trailing comma
    FREE_GPUS="${{FREE_GPUS%,}}"

    if [ -n "$FREE_GPUS" ]; then
        echo "{{\\"gpu_ids\\": [$FREE_GPUS]}}" > "$MARKER"
        echo "Found free GPUs: $FREE_GPUS"
        exit 0
    fi

    poll=$((poll + 1))
    [ "$MAX_POLLS" -gt 0 ] && [ "$poll" -ge "$MAX_POLLS" ] && echo "Timeout" && exit 1
    echo "Poll $poll: no free GPUs, waiting ${{INTERVAL}}s..."
    sleep "$INTERVAL"
done
'''

    def experiment_monitor_script(
        self,
        project_dir: str,
        task_ids: list[str],
        poll_interval_sec: int,
        timeout_minutes: int,
        marker_file: str,
        workspace_path: str,
        heartbeat_polls: int = 5,
        task_gpu_map: dict[str, list[int]] | None = None,
    ) -> str:
        """Generate experiment monitoring daemon script for RunPod pods."""
        task_ids_str = " ".join(f'"{t}"' for t in task_ids)
        return f'''#!/bin/bash
set -e
PROJECT_DIR="{project_dir}"
MARKER="{marker_file}"
INTERVAL={poll_interval_sec}
TIMEOUT_SEC=$((60 * {timeout_minutes}))
TASK_IDS=({task_ids_str})
HEARTBEAT_INTERVAL=$(({heartbeat_polls} * {poll_interval_sec}))
START=$(date +%s)
heartbeat_counter=0

echo "Experiment monitor started: ${{#TASK_IDS[@]}} tasks, timeout={timeout_minutes}m"

while true; do
    ALL_DONE=true
    COMPLETED=0
    RUNNING=0
    DEAD=0

    for tid in "${{TASK_IDS[@]}}"; do
        if [ -f "$PROJECT_DIR/${{tid}}_DONE" ]; then
            COMPLETED=$((COMPLETED + 1))
            continue
        fi
        ALL_DONE=false

        if [ -f "$PROJECT_DIR/${{tid}}.pid" ]; then
            PID=$(cat "$PROJECT_DIR/${{tid}}.pid")
            if kill -0 "$PID" 2>/dev/null; then
                RUNNING=$((RUNNING + 1))
                # Check progress file
                if [ -f "$PROJECT_DIR/${{tid}}_PROGRESS.json" ]; then
                    echo "PROGRESS:$tid:$(cat "$PROJECT_DIR/${{tid}}_PROGRESS.json")"
                fi
            else
                DEAD=$((DEAD + 1))
                echo "DEAD:$tid:$PID" >> "$MARKER"
            fi
        else
            echo "UNKNOWN:$tid (no PID file)"
        fi
    done

    echo "Status: completed=$COMPLETED running=$RUNNING dead=$DEAD"

    if $ALL_DONE; then
        echo "ALL_DONE" >> "$MARKER"
        echo "All ${{#TASK_IDS[@]}} tasks completed."
        exit 0
    fi

    # Timeout check
    NOW=$(date +%s)
    ELAPSED=$((NOW - START))
    if [ "$ELAPSED" -ge "$TIMEOUT_SEC" ]; then
        echo "TIMEOUT after ${{TIMEOUT_SEC}}s" >> "$MARKER"
        exit 1
    fi

    # Heartbeat
    heartbeat_counter=$((heartbeat_counter + 1))
    if [ "$heartbeat_counter" -ge "{heartbeat_polls}" ]; then
        echo "HEARTBEAT:elapsed=${{ELAPSED}}s/${{TIMEOUT_SEC}}s completed=$COMPLETED running=$RUNNING"
        heartbeat_counter=0
    fi

    sleep "$INTERVAL"
done
'''

    @classmethod
    def from_config(cls, config: "Config", workspace_active_root: str = "") -> "RunPodBackend":
        return cls(config=config)
