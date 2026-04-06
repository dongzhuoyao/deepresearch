"""Abstract base class for compute backends."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tao.config import Config


class ComputeBackend(ABC):
    """Unified interface for GPU compute environments.

    Each backend encapsulates how to discover GPUs, run experiments,
    monitor task progress, and collect results. The orchestrator calls
    backend methods instead of hardcoding specific commands.
    """

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Return the backend identifier (e.g. 'runpod')."""

    @abstractmethod
    def project_dir(self, ws_name: str) -> str:
        """Return the directory where experiment artifacts live on the compute node."""

    @abstractmethod
    def env_cmd(self, project_name: str) -> str:
        """Return shell command that activates the experiment environment."""

    @abstractmethod
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
        """Generate a bash script that polls for free GPUs.

        The script must:
        1. Run nvidia-smi to check GPU memory usage
        2. Write free GPU IDs to marker_file as JSON on success
        3. Exit 0 when free GPUs are found, exit 1 on timeout
        """

    @abstractmethod
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
        """Generate a bash daemon script that monitors running experiments.

        The script must:
        1. Check DONE / PID status for each task
        2. Detect stuck processes
        3. Write wake events when tasks complete
        """

    @abstractmethod
    def create_pod(self, name: str) -> dict:
        """Create a compute pod. Returns pod info dict."""

    @abstractmethod
    def terminate_pod(self, pod_id: str) -> None:
        """Terminate a compute pod."""

    @abstractmethod
    def list_pods(self) -> list[dict]:
        """List all active pods."""

    @abstractmethod
    def stop_pod(self, pod_id: str) -> None:
        """Stop a pod (preserves volume, releases GPU)."""

    @abstractmethod
    def wait_for_ready(self, pod_id: str, timeout_sec: int = 300, poll_sec: int = 5) -> bool:
        """Block until pod is running and SSH-ready. Returns True if ready."""

    @abstractmethod
    def run_remote(self, pod_id: str, command: str, timeout_sec: int = 600) -> dict:
        """Execute a command on a pod via SSH.

        Returns dict with keys: stdout, stderr, returncode.
        """

    @abstractmethod
    def upload_code(self, pod_id: str, local_path: str, remote_path: str) -> bool:
        """Upload code/data to pod. Returns True on success."""

    @abstractmethod
    def download_results(self, pod_id: str, remote_path: str, local_path: str) -> bool:
        """Download results from pod. Returns True on success."""

    @classmethod
    @abstractmethod
    def from_config(cls, config: "Config", workspace_active_root: str = "") -> "ComputeBackend":
        """Construct backend from Config."""
