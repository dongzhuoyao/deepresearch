"""Tests for compute backend."""
import os
import subprocess
import sys
from unittest.mock import patch, MagicMock
import pytest
from sibyl.compute.base import ComputeBackend
from sibyl.compute.runpod_backend import RunPodBackend, _find_ssh_key
from sibyl.compute import get_backend
from sibyl.config import Config


def test_backend_type():
    cfg = Config()
    backend = RunPodBackend(cfg)
    assert backend.backend_type == "runpod"


def test_project_dir():
    cfg = Config()
    backend = RunPodBackend(cfg)
    assert backend.project_dir("my_project") == "/workspace/projects/my_project"


def test_env_cmd():
    cfg = Config()
    backend = RunPodBackend(cfg)
    cmd = backend.env_cmd("my_project")
    assert "cd" in cmd
    assert "my_project" in cmd


def test_gpu_poll_script():
    cfg = Config()
    backend = RunPodBackend(cfg)
    script = backend.gpu_poll_script(
        candidate_gpu_ids=[0, 1],
        threshold_mb=2000,
        poll_interval_sec=30,
        max_polls=10,
        marker_file="/tmp/gpu_marker.json",
    )
    assert "nvidia-smi" in script
    assert "gpu_marker.json" in script
    assert "THRESHOLD=2000" in script


def test_gpu_poll_script_aggressive():
    cfg = Config()
    backend = RunPodBackend(cfg)
    script = backend.gpu_poll_script(
        candidate_gpu_ids=[0],
        threshold_mb=2000,
        poll_interval_sec=30,
        max_polls=5,
        marker_file="/tmp/m.json",
        aggressive_mode=True,
        aggressive_threshold_pct=30,
    )
    assert "AGGRESSIVE=true" in script
    assert "AGG_PCT=30" in script


def test_experiment_monitor_script():
    cfg = Config()
    backend = RunPodBackend(cfg)
    script = backend.experiment_monitor_script(
        project_dir="/workspace/projects/test",
        task_ids=["train_baseline", "train_ablation"],
        poll_interval_sec=30,
        timeout_minutes=120,
        marker_file="/tmp/monitor.json",
        workspace_path="/local/ws",
    )
    assert "train_baseline" in script
    assert "train_ablation" in script
    assert "TIMEOUT_SEC" in script
    assert "_DONE" in script
    assert ".pid" in script


def test_get_backend():
    cfg = Config()
    backend = get_backend(cfg)
    assert isinstance(backend, RunPodBackend)
    assert backend.backend_type == "runpod"


def test_create_pod_no_api_key():
    import os
    import sys
    # Clear env var BEFORE constructing the backend so __init__ sees no key
    old_env = os.environ.pop("RUNPOD_API_KEY", None)
    # Mock the runpod module so the import inside create_pod succeeds
    mock_runpod = MagicMock()
    had_runpod = "runpod" in sys.modules
    prev_mod = sys.modules.get("runpod")
    sys.modules["runpod"] = mock_runpod
    try:
        cfg = Config()
        cfg.runpod_api_key = ""
        backend = RunPodBackend(cfg)
        import pytest
        with pytest.raises(ValueError, match="RUNPOD_API_KEY"):
            backend.create_pod("test-pod")
    finally:
        if old_env is not None:
            os.environ["RUNPOD_API_KEY"] = old_env
        if had_runpod:
            sys.modules["runpod"] = prev_mod
        else:
            sys.modules.pop("runpod", None)


def test_abstract_methods():
    """Verify ComputeBackend can't be instantiated."""
    with pytest.raises(TypeError):
        ComputeBackend()


# --- SSH key detection ---

def test_find_ssh_key(tmp_path):
    """_find_ssh_key returns the first matching key."""
    _find_ssh_key.cache_clear()
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    key = ssh_dir / "id_ed25519"
    key.write_text("fake-key")
    with patch("sibyl.compute.runpod_backend.Path.home", return_value=tmp_path):
        result = _find_ssh_key()
    assert result == str(key)
    _find_ssh_key.cache_clear()


def test_find_ssh_key_fallback_rsa(tmp_path):
    """Falls back to id_rsa when ed25519 is absent."""
    _find_ssh_key.cache_clear()
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    key = ssh_dir / "id_rsa"
    key.write_text("fake-key")
    with patch("sibyl.compute.runpod_backend.Path.home", return_value=tmp_path):
        result = _find_ssh_key()
    assert result == str(key)
    _find_ssh_key.cache_clear()


def test_find_ssh_key_none(tmp_path):
    """Returns None when no keys exist."""
    _find_ssh_key.cache_clear()
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    with patch("sibyl.compute.runpod_backend.Path.home", return_value=tmp_path):
        result = _find_ssh_key()
    assert result is None
    _find_ssh_key.cache_clear()


# --- get_pod_ssh_info ---

def test_get_pod_ssh_info_full_ssh():
    """Full SSH mode when public IP and port 22 mapping exists."""
    cfg = Config()
    cfg.runpod_api_key = "test-key"
    backend = RunPodBackend(cfg)
    mock_pod = {
        "runtime": {
            "uptimeInSeconds": 120,
            "ports": [
                {"privatePort": 22, "publicPort": 17445, "isIpPublic": True, "ip": "213.173.108.12"},
                {"privatePort": 8888, "publicPort": 18888, "isIpPublic": True, "ip": "213.173.108.12"},
            ],
        },
    }
    mock_runpod = MagicMock()
    mock_runpod.get_pod.return_value = mock_pod
    with patch.dict(sys.modules, {"runpod": mock_runpod}):
        info = backend.get_pod_ssh_info("pod-123")
    assert info["mode"] == "full"
    assert info["host"] == "213.173.108.12"
    assert info["port"] == 17445
    assert info["username"] == "root"


def test_get_pod_ssh_info_basic_ssh():
    """Falls back to basic SSH via ssh.runpod.io when no public IP."""
    cfg = Config()
    cfg.runpod_api_key = "test-key"
    backend = RunPodBackend(cfg)
    mock_pod = {
        "runtime": {
            "uptimeInSeconds": 60,
            "ports": [],
        },
    }
    mock_runpod = MagicMock()
    mock_runpod.get_pod.return_value = mock_pod
    with patch.dict(sys.modules, {"runpod": mock_runpod}):
        info = backend.get_pod_ssh_info("pod-456")
    assert info["mode"] == "basic"
    assert info["host"] == "ssh.runpod.io"
    assert info["username"] == "pod-456"
    assert info["port"] == 22


def test_get_pod_ssh_info_no_runtime():
    """Handles pod with no runtime (not yet started)."""
    cfg = Config()
    cfg.runpod_api_key = "test-key"
    backend = RunPodBackend(cfg)
    mock_pod = {"runtime": None}
    mock_runpod = MagicMock()
    mock_runpod.get_pod.return_value = mock_pod
    with patch.dict(sys.modules, {"runpod": mock_runpod}):
        info = backend.get_pod_ssh_info("pod-789")
    assert info["mode"] == "basic"
    assert info["host"] == "ssh.runpod.io"


# --- stop_pod ---

def test_stop_pod():
    """stop_pod calls runpod.stop_pod."""
    cfg = Config()
    cfg.runpod_api_key = "test-key"
    backend = RunPodBackend(cfg)
    mock_runpod = MagicMock()
    with patch.dict(sys.modules, {"runpod": mock_runpod}):
        backend.stop_pod("pod-stop-1")
    mock_runpod.stop_pod.assert_called_once_with("pod-stop-1")


# --- wait_for_ready ---

def test_wait_for_ready_immediate():
    """Returns True immediately when pod is already running."""
    cfg = Config()
    cfg.runpod_api_key = "test-key"
    backend = RunPodBackend(cfg)
    mock_runpod = MagicMock()
    mock_runpod.get_pod.return_value = {"runtime": {"uptimeInSeconds": 30}}
    with patch.dict(sys.modules, {"runpod": mock_runpod}):
        assert backend.wait_for_ready("pod-1", timeout_sec=10, poll_sec=1) is True


def test_wait_for_ready_becomes_ready():
    """Returns True when pod becomes ready after polling."""
    cfg = Config()
    cfg.runpod_api_key = "test-key"
    backend = RunPodBackend(cfg)
    mock_runpod = MagicMock()
    mock_runpod.get_pod.side_effect = [
        {"runtime": None, "desiredStatus": "RUNNING"},
        {"runtime": {"uptimeInSeconds": 0}, "desiredStatus": "RUNNING"},
        {"runtime": {"uptimeInSeconds": 5}, "desiredStatus": "RUNNING"},
    ]
    with patch.dict(sys.modules, {"runpod": mock_runpod}), \
         patch("sibyl.compute.runpod_backend.time.sleep"):
        assert backend.wait_for_ready("pod-2", timeout_sec=300, poll_sec=1) is True


def test_wait_for_ready_terminated():
    """Returns False when pod status is TERMINATED."""
    cfg = Config()
    cfg.runpod_api_key = "test-key"
    backend = RunPodBackend(cfg)
    mock_runpod = MagicMock()
    mock_runpod.get_pod.return_value = {"runtime": None, "desiredStatus": "TERMINATED"}
    with patch.dict(sys.modules, {"runpod": mock_runpod}):
        assert backend.wait_for_ready("pod-3", timeout_sec=10, poll_sec=1) is False


def test_wait_for_ready_timeout():
    """Returns False on timeout."""
    cfg = Config()
    cfg.runpod_api_key = "test-key"
    backend = RunPodBackend(cfg)
    mock_runpod = MagicMock()
    mock_runpod.get_pod.return_value = {"runtime": None, "desiredStatus": "RUNNING"}
    with patch.dict(sys.modules, {"runpod": mock_runpod}), \
         patch("sibyl.compute.runpod_backend.time.sleep"), \
         patch("sibyl.compute.runpod_backend.time.time", side_effect=[0, 0, 999]):
        assert backend.wait_for_ready("pod-4", timeout_sec=10, poll_sec=1) is False


# --- run_remote ---

def test_run_remote_success():
    """run_remote returns stdout/stderr/returncode on success."""
    cfg = Config()
    cfg.runpod_api_key = "test-key"
    backend = RunPodBackend(cfg)
    backend._ssh_key = "/home/user/.ssh/id_ed25519"
    mock_ssh_info = {
        "host": "1.2.3.4", "port": 17445, "username": "root",
        "ssh_key": "/home/user/.ssh/id_ed25519", "mode": "full",
    }
    mock_result = MagicMock()
    mock_result.stdout = "GPU 0: A100\n"
    mock_result.stderr = ""
    mock_result.returncode = 0
    with patch.object(backend, "get_pod_ssh_info", return_value=mock_ssh_info), \
         patch("sibyl.compute.runpod_backend.subprocess.run", return_value=mock_result) as mock_run:
        result = backend.run_remote("pod-1", "nvidia-smi")
    assert result["stdout"] == "GPU 0: A100\n"
    assert result["returncode"] == 0
    # Verify SSH command was constructed correctly
    call_args = mock_run.call_args[0][0]
    assert "ssh" in call_args[0]
    assert "-i" in call_args
    assert "root@1.2.3.4" in call_args
    assert "nvidia-smi" in call_args


def test_run_remote_timeout():
    """run_remote returns error dict on timeout."""
    cfg = Config()
    cfg.runpod_api_key = "test-key"
    backend = RunPodBackend(cfg)
    mock_ssh_info = {
        "host": "ssh.runpod.io", "port": 22, "username": "pod-1",
        "ssh_key": None, "mode": "basic",
    }
    with patch.object(backend, "get_pod_ssh_info", return_value=mock_ssh_info), \
         patch("sibyl.compute.runpod_backend.subprocess.run",
               side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=600)):
        result = backend.run_remote("pod-1", "long-running-cmd")
    assert result["returncode"] == -1
    assert "timed out" in result["stderr"]


# --- _ssh_cmd_prefix ---

def test_ssh_cmd_prefix_full():
    """SSH prefix includes key and port for full mode."""
    cfg = Config()
    backend = RunPodBackend(cfg)
    info = {"host": "1.2.3.4", "port": 17445, "username": "root",
            "ssh_key": "/home/.ssh/id_ed25519", "mode": "full"}
    prefix = backend._ssh_cmd_prefix(info)
    assert "-i" in prefix
    assert "/home/.ssh/id_ed25519" in prefix
    assert "-p" in prefix
    assert "17445" in prefix


def test_ssh_cmd_prefix_basic_no_key():
    """SSH prefix omits key and port when defaults."""
    cfg = Config()
    backend = RunPodBackend(cfg)
    info = {"host": "ssh.runpod.io", "port": 22, "username": "pod-1",
            "ssh_key": None, "mode": "basic"}
    prefix = backend._ssh_cmd_prefix(info)
    assert "-i" not in prefix
    assert "-p" not in prefix
