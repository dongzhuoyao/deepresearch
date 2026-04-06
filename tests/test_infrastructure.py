"""Tests for paths, event logger, and error collector."""
import json
import tempfile
from pathlib import Path

from tao._paths import tao_root, system_data_dir, prompts_dir, global_config_path
from tao.event_logger import log_event, read_events
from tao.error_collector import collect_error, read_errors, clear_errors


class TestPaths:
    def test_tao_root(self):
        root = tao_root()
        assert root.is_dir()
        # Should contain the tao package
        assert (root / "tao").is_dir() or (root / "pyproject.toml").exists()

    def test_system_data_dir(self):
        d = system_data_dir()
        assert str(d).endswith(".tao")
        assert d.parent == Path.home()

    def test_prompts_dir(self):
        d = prompts_dir()
        assert d.name == "prompts"
        assert d.parent.name == "tao"

    def test_global_config_path(self):
        p = global_config_path()
        assert p.name == "config.yaml"
        assert ".tao" in str(p)


class TestEventLogger:
    def test_log_and_read(self, tmp_path):
        log_event(tmp_path, "stage_complete", {"stage": "init", "score": 8.5})
        log_event(tmp_path, "error", {"message": "timeout"})

        all_events = read_events(tmp_path)
        assert len(all_events) == 2
        assert all_events[0]["type"] == "stage_complete"
        assert all_events[0]["stage"] == "init"
        assert all_events[1]["type"] == "error"

    def test_read_filtered(self, tmp_path):
        log_event(tmp_path, "stage_complete", {"stage": "init"})
        log_event(tmp_path, "error", {"message": "fail"})
        log_event(tmp_path, "stage_complete", {"stage": "writing"})

        filtered = read_events(tmp_path, event_type="stage_complete")
        assert len(filtered) == 2

    def test_read_empty(self, tmp_path):
        events = read_events(tmp_path)
        assert events == []

    def test_creates_directory(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        log_event(nested, "test", {"x": 1})
        assert (nested / "events.jsonl").exists()


class TestErrorCollector:
    def test_collect_and_read(self, tmp_path):
        collect_error(tmp_path, "import", "ModuleNotFoundError: torch")
        collect_error(tmp_path, "config", "Invalid YAML", {"line": 42})

        errors = read_errors(tmp_path)
        assert len(errors) == 2
        assert errors[0]["category"] == "import"
        assert errors[1]["details"]["line"] == 42

    def test_read_filtered(self, tmp_path):
        collect_error(tmp_path, "import", "missing torch")
        collect_error(tmp_path, "config", "bad yaml")
        collect_error(tmp_path, "import", "missing numpy")

        import_errors = read_errors(tmp_path, category="import")
        assert len(import_errors) == 2

    def test_read_empty(self, tmp_path):
        errors = read_errors(tmp_path)
        assert errors == []

    def test_clear_errors(self, tmp_path):
        collect_error(tmp_path, "test", "error 1")
        collect_error(tmp_path, "test", "error 2")
        assert len(read_errors(tmp_path)) == 2

        clear_errors(tmp_path)
        assert len(read_errors(tmp_path)) == 0

    def test_clear_nonexistent(self, tmp_path):
        # Should not raise
        clear_errors(tmp_path)
