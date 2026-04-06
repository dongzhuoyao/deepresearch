"""Tests for the main orchestrator."""
import json
from pathlib import Path
from tao.orchestrate import (
    FarsOrchestrator, cli_next, cli_record, cli_status,
    cli_init, cli_init_from_spec, _topic_to_name,
)
from tao.config import Config


class TestFarsOrchestrator:
    def test_init_project(self, tmp_path):
        orch = FarsOrchestrator(tmp_path / "ws", Config())
        path = orch.init_project("Neural scaling laws")
        assert Path(path).exists()
        assert (Path(path) / "topic.txt").read_text() == "Neural scaling laws"

    def test_get_next_action(self, tmp_path):
        orch = FarsOrchestrator(tmp_path / "ws", Config())
        orch.init_project("test")
        action = orch.get_next_action()
        assert action["stage"] == "init"
        assert action["action_type"] == "skill"
        assert "execution_script" in action

    def test_record_result(self, tmp_path):
        orch = FarsOrchestrator(tmp_path / "ws", Config())
        orch.init_project("test")
        next_stage = orch.record_result("init", "done")
        assert next_stage == "literature_search"

    def test_get_status(self, tmp_path):
        orch = FarsOrchestrator(tmp_path / "ws", Config())
        orch.init_project("test")
        status = orch.get_status()
        assert status["stage"] == "init"
        assert status["iteration"] == 0

    def test_is_done(self, tmp_path):
        orch = FarsOrchestrator(tmp_path / "ws", Config())
        orch.init_project("test")
        assert orch.is_done() is False
        orch.workspace.update_stage("done")
        assert orch.is_done() is True

    def test_full_pipeline_forward(self, tmp_path):
        """Test advancing through several stages."""
        orch = FarsOrchestrator(tmp_path / "ws", Config())
        orch.init_project("test")

        stages_visited = ["init"]
        for _ in range(5):
            next_s = orch.record_result(stages_visited[-1], "completed", 8.0)
            stages_visited.append(next_s)

        assert "literature_search" in stages_visited
        assert "idea_debate" in stages_visited


class TestCliInterface:
    def test_cli_next(self, tmp_path):
        ws = tmp_path / "ws"
        orch = FarsOrchestrator(ws, Config())
        orch.init_project("test")
        result = cli_next(str(ws))
        data = json.loads(result)
        assert data["stage"] == "init"

    def test_cli_record(self, tmp_path):
        ws = tmp_path / "ws"
        orch = FarsOrchestrator(ws, Config())
        orch.init_project("test")
        result = cli_record(str(ws), "init", "done", 0)
        data = json.loads(result)
        assert data["next_stage"] == "literature_search"

    def test_cli_status(self, tmp_path):
        ws = tmp_path / "ws"
        orch = FarsOrchestrator(ws, Config())
        orch.init_project("test")
        result = cli_status(str(ws))
        data = json.loads(result)
        assert "stage" in data

    def test_cli_init(self, tmp_path):
        path = cli_init("Neural scaling laws", workspace_dir=str(tmp_path))
        assert Path(path).exists()
        assert (Path(path) / "topic.txt").exists()

    def test_cli_init_from_spec(self, tmp_path):
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# My Research\nStudy neural nets")
        path = cli_init_from_spec(str(spec_file), workspace_dir=str(tmp_path))
        assert Path(path).exists()
        ws = Path(path)
        assert (ws / "spec.md").exists()
        assert (ws / "topic.txt").exists()


class TestHelpers:
    def test_topic_to_name(self):
        name = _topic_to_name("Neural Scaling Laws for LLMs")
        assert "neural" in name
        assert "scaling" in name
        assert len(name) < 70

    def test_topic_to_name_special_chars(self):
        name = _topic_to_name("What's the best model? (GPT-5)")
        assert "/" not in name
        assert "?" not in name
