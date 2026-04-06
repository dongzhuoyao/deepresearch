"""Tests for configuration system."""
import os
import tempfile
import pytest
from pathlib import Path
from tao.config import Config, AgentConfig


def test_config_defaults():
    cfg = Config()
    assert cfg.compute_backend == "runpod"
    assert cfg.max_gpus == 4
    assert cfg.language == "en"
    assert cfg.research_focus == 3
    assert cfg.writing_mode == "parallel"
    assert cfg.evolution_enabled is True
    assert cfg.runpod_spot is True


def test_agent_config_defaults():
    ac = AgentConfig()
    assert ac.model == "claude-opus-4-6"
    assert ac.temperature == 0.7


def test_config_from_yaml():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("language: zh\nresearch_focus: 5\nmax_gpus: 8\nrunpod_gpu_type: 'NVIDIA H100 80GB HBM3'\n")
        f.flush()
        path = f.name
    try:
        cfg = Config.from_yaml(path)
        assert cfg.language == "zh"
        assert cfg.research_focus == 5
        assert cfg.max_gpus == 8
        assert cfg.runpod_gpu_type == "NVIDIA H100 80GB HBM3"
    finally:
        os.unlink(path)


def test_config_from_yaml_chain():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f1:
        f1.write("language: zh\nmax_gpus: 2\n")
        f1.flush()
        path1 = f1.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f2:
        f2.write("max_gpus: 8\nresearch_focus: 4\n")
        f2.flush()
        path2 = f2.name
    try:
        cfg = Config.from_yaml_chain(path1, path2)
        assert cfg.language == "zh"  # from first file
        assert cfg.max_gpus == 8     # overridden by second
        assert cfg.research_focus == 4
    finally:
        os.unlink(path1)
        os.unlink(path2)


def test_config_validation_bad_backend():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("compute_backend: local\n")
        f.flush()
        path = f.name
    try:
        with pytest.raises(ValueError, match="Only 'runpod'"):
            Config.from_yaml(path)
    finally:
        os.unlink(path)


def test_config_validation_bad_language():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("language: fr\n")
        f.flush()
        path = f.name
    try:
        with pytest.raises(ValueError, match="Invalid language"):
            Config.from_yaml(path)
    finally:
        os.unlink(path)


def test_config_validation_bad_research_focus():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("research_focus: 10\n")
        f.flush()
        path = f.name
    try:
        with pytest.raises(ValueError, match="research_focus"):
            Config.from_yaml(path)
    finally:
        os.unlink(path)


def test_config_to_yaml():
    cfg = Config()
    yaml_str = cfg.to_yaml()
    assert "runpod" in yaml_str
    assert "workspaces_dir" in yaml_str


def test_config_to_dict():
    cfg = Config()
    d = cfg.to_dict()
    assert isinstance(d, dict)
    assert d["compute_backend"] == "runpod"
    assert isinstance(d["workspaces_dir"], str)


def test_config_env_var_fallback(monkeypatch):
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key-123")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("language: en\n")
        f.flush()
        path = f.name
    try:
        cfg = Config.from_yaml(path)
        assert cfg.runpod_api_key == "test-key-123"
    finally:
        os.unlink(path)


def test_config_model_tiers_merge():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("model_tiers:\n  heavy: claude-sonnet-4-6\n")
        f.flush()
        path = f.name
    try:
        cfg = Config.from_yaml(path)
        assert cfg.model_tiers["heavy"] == "claude-sonnet-4-6"
        assert cfg.model_tiers["standard"] == "claude-opus-4-6"  # default preserved
    finally:
        os.unlink(path)
