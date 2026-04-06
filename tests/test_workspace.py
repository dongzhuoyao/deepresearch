"""Tests for workspace management."""
import json
from pathlib import Path
from tao.workspace import Workspace, WorkspaceStatus
from tao.orchestration.workspace_paths import (
    resolve_active_root, ensure_workspace_dirs,
)


class TestWorkspaceStatus:
    def test_defaults(self):
        ws = WorkspaceStatus()
        assert ws.stage == "init"
        assert ws.iteration == 0
        assert ws.paused is False

    def test_roundtrip(self):
        ws = WorkspaceStatus(stage="writing_latex", iteration=3, paused=True)
        d = ws.to_dict()
        ws2 = WorkspaceStatus.from_dict(d)
        assert ws2.stage == "writing_latex"
        assert ws2.iteration == 3
        assert ws2.paused is True


class TestWorkspacePaths:
    def test_resolve_no_iteration_dirs(self, tmp_path):
        root = resolve_active_root(tmp_path, iteration_dirs=False, iteration=5)
        assert root == tmp_path

    def test_resolve_with_iteration_dirs(self, tmp_path):
        root = resolve_active_root(tmp_path, iteration_dirs=True, iteration=3)
        assert root == tmp_path / "iter_003"

    def test_resolve_iteration_zero(self, tmp_path):
        root = resolve_active_root(tmp_path, iteration_dirs=True, iteration=0)
        assert root == tmp_path  # iteration 0 = no subdir

    def test_ensure_workspace_dirs(self, tmp_path):
        ensure_workspace_dirs(tmp_path)
        assert (tmp_path / "idea").is_dir()
        assert (tmp_path / "exp" / "code").is_dir()
        assert (tmp_path / "writing" / "sections").is_dir()
        assert (tmp_path / "reflection").is_dir()
        assert (tmp_path / "logs" / "iterations").is_dir()


class TestWorkspace:
    def test_init_project(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("Testing neural scaling laws")
        assert (tmp_path / "topic.txt").read_text() == "Testing neural scaling laws"
        assert (tmp_path / "status.json").exists()
        assert (tmp_path / "idea").is_dir()

    def test_read_write_file(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        ws.write_file("idea/proposal.md", "# My Idea\nTest proposal")
        content = ws.read_file("idea/proposal.md")
        assert content == "# My Idea\nTest proposal"

    def test_read_nonexistent(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        assert ws.read_file("nonexistent.txt") is None

    def test_read_write_json(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        data = {"tasks": [{"id": "baseline", "gpu_count": 1}]}
        ws.write_json("plan/task_plan.json", data)
        loaded = ws.read_json("plan/task_plan.json")
        assert loaded["tasks"][0]["id"] == "baseline"

    def test_file_exists(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        assert ws.file_exists("topic.txt")
        assert not ws.file_exists("nonexistent.txt")

    def test_append_file(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        ws.write_file("logs/diary.md", "# Day 1\n")
        ws.append_file("logs/diary.md", "# Day 2\n")
        content = ws.read_file("logs/diary.md")
        assert "Day 1" in content
        assert "Day 2" in content

    def test_list_files(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        ws.write_file("writing/sections/intro.md", "intro")
        ws.write_file("writing/sections/method.md", "method")
        ws.write_file("writing/sections/README.txt", "ignore")
        files = ws.list_files("writing/sections", "*.md")
        assert len(files) == 2

    def test_update_stage(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        ws.update_stage("literature_search")
        status = ws.get_status()
        assert status.stage == "literature_search"
        assert status.stage_started_at is not None

    def test_update_stage_and_iteration(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        ws.update_stage_and_iteration("experiment_cycle", 2)
        status = ws.get_status()
        assert status.stage == "experiment_cycle"
        assert status.iteration == 2

    def test_iteration_dirs(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=True)
        ws.init_project("test")
        new_iter = ws.new_iteration()
        assert new_iter == 1
        assert (tmp_path / "iter_001").is_dir()
        assert (tmp_path / "current").is_symlink()

    def test_record_error(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        ws.record_error("import", "ModuleNotFoundError: torch")
        status = ws.get_status()
        assert len(status.errors) == 1
        assert status.errors[0]["category"] == "import"

    def test_clear_iteration_artifacts(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        # Write some artifacts
        ws.write_file("idea/proposal.md", "idea content")
        ws.write_file("reflection/lessons_learned.md", "lessons to keep")
        ws.write_file("reflection/action_plan.json", '{"fixes": []}')
        ws.write_file("writing/sections/intro.md", "intro to clear")
        # Clear
        ws.clear_iteration_artifacts()
        # Artifacts cleared
        assert ws.read_file("idea/proposal.md") is None
        assert ws.read_file("writing/sections/intro.md") is None
        # Preserved files kept
        assert ws.read_file("reflection/lessons_learned.md") == "lessons to keep"
        assert ws.read_file("reflection/action_plan.json") == '{"fixes": []}'
        # Dirs recreated
        assert (tmp_path / "idea").is_dir()
