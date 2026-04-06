"""Tests for dashboard and WebUI modules."""
import json
from pathlib import Path
from tao.orchestration.dashboard_data import get_dashboard_data, list_all_projects
from tao.webui.control_api import pause_project, resume_project, stop_project
from tao.webui.monitor_api import get_experiment_status
from tao.webui.session_registry import SessionRegistry
from tao.workspace import Workspace


class TestDashboardData:
    def test_get_dashboard_data(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        data = get_dashboard_data(tmp_path)
        assert data["status"]["stage"] == "init"
        assert data["has_paper"] is False

    def test_list_all_projects(self, tmp_path):
        for name in ["proj_a", "proj_b"]:
            ws = Workspace(tmp_path / name, iteration_dirs=False)
            ws.init_project(f"topic {name}")
        projects = list_all_projects(tmp_path)
        assert len(projects) == 2

    def test_list_empty(self, tmp_path):
        projects = list_all_projects(tmp_path / "nope")
        assert projects == []


class TestControlApi:
    def test_pause_resume(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        result = pause_project(tmp_path)
        assert result["success"] is True
        status = json.loads((tmp_path / "status.json").read_text())
        assert status["paused"] is True

        result = resume_project(tmp_path)
        assert result["success"] is True
        status = json.loads((tmp_path / "status.json").read_text())
        assert status["paused"] is False

    def test_stop(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        result = stop_project(tmp_path)
        assert result["success"] is True

    def test_pause_no_status(self, tmp_path):
        result = pause_project(tmp_path)
        assert result["success"] is False


class TestMonitorApi:
    def test_experiment_status(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        status = get_experiment_status(tmp_path)
        assert "progress" in status
        assert "state" in status


class TestSessionRegistry:
    def test_register_and_get(self, tmp_path):
        reg = SessionRegistry(tmp_path / "sessions")
        reg.register("my_project", "session-123")
        session = reg.get_session("my_project")
        assert session["session_id"] == "session-123"

    def test_unregister(self, tmp_path):
        reg = SessionRegistry(tmp_path / "sessions")
        reg.register("proj", "sess-1")
        reg.unregister("proj")
        assert reg.get_session("proj") is None

    def test_list_active(self, tmp_path):
        reg = SessionRegistry(tmp_path / "sessions")
        reg.register("a", "s1")
        reg.register("b", "s2")
        active = reg.list_active()
        assert len(active) == 2

    def test_get_nonexistent(self, tmp_path):
        reg = SessionRegistry(tmp_path / "sessions")
        assert reg.get_session("nope") is None
