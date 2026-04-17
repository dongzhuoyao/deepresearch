"""Tests for lifecycle and action dispatcher."""
from tao.orchestration.lifecycle import Lifecycle
from tao.orchestration.action_dispatcher import render_execution_script
from tao.orchestration.models import Action
from tao.workspace import Workspace
from tao.config import Config


def _make_lifecycle(tmp_path, **overrides) -> Lifecycle:
    cfg = Config()
    for k, v in overrides.items():
        setattr(cfg, k, v)
    ws = Workspace(tmp_path, iteration_dirs=False)
    ws.init_project("test")
    return Lifecycle(ws, cfg)


class TestLifecycle:
    def test_get_next_action_init(self, tmp_path):
        lc = _make_lifecycle(tmp_path)
        action = lc.get_next_action()
        assert action.stage == "init"
        assert action.action_type == "skill"

    def test_get_next_action_literature(self, tmp_path):
        lc = _make_lifecycle(tmp_path)
        lc._ws.update_stage("literature_search")
        action = lc.get_next_action()
        assert action.stage == "literature_search"
        assert action.action_type == "skill"

    def test_get_next_action_idea_debate(self, tmp_path):
        lc = _make_lifecycle(tmp_path)
        lc._ws.update_stage("idea_debate")
        action = lc.get_next_action()
        assert action.action_type == "team"
        assert action.team is not None
        assert len(action.team["agents"]) == 6

    def test_get_next_action_writing_parallel(self, tmp_path):
        lc = _make_lifecycle(tmp_path, writing_mode="parallel")
        lc._ws.update_stage("writing_sections")
        action = lc.get_next_action()
        assert action.action_type == "skills_parallel"
        assert len(action.agents) == 6  # one section writer per PAPER_SECTIONS entry

    def test_get_next_action_writing_sequential(self, tmp_path):
        lc = _make_lifecycle(tmp_path, writing_mode="sequential")
        lc._ws.update_stage("writing_sections")
        action = lc.get_next_action()
        assert action.action_type == "skill"

    def test_get_next_action_writing_assets(self, tmp_path):
        # Always sequential regardless of writing_mode
        for mode in ("parallel", "sequential"):
            lc = _make_lifecycle(tmp_path, writing_mode=mode)
            lc._ws.update_stage("writing_assets")
            action = lc.get_next_action()
            assert action.action_type == "skill"
            assert len(action.skills) == 1

    def test_get_next_action_writing_teaser(self, tmp_path):
        lc = _make_lifecycle(tmp_path)
        lc._ws.update_stage("writing_teaser")
        action = lc.get_next_action()
        assert action.action_type == "skill"
        assert "teaser" in action.skills[0]["name"].lower()

    def test_get_next_action_done(self, tmp_path):
        lc = _make_lifecycle(tmp_path)
        lc._ws.update_stage("done")
        action = lc.get_next_action()
        assert action.action_type == "done"

    def test_record_result_advances(self, tmp_path):
        lc = _make_lifecycle(tmp_path)
        next_stage = lc.record_result("init", "initialized", 0)
        assert next_stage == "literature_search"
        status = lc._ws.get_status()
        assert status.stage == "literature_search"

    def test_record_result_quality_gate_loop(self, tmp_path):
        lc = _make_lifecycle(tmp_path, max_iterations=10)
        lc._ws.update_stage_and_iteration("quality_gate", 1)
        next_stage = lc.record_result("quality_gate", "needs improvement", 5.0)
        assert next_stage == "literature_search"

    def test_record_result_done(self, tmp_path):
        lc = _make_lifecycle(tmp_path, max_iterations=3)
        lc._ws.update_stage_and_iteration("quality_gate", 3)
        next_stage = lc.record_result("quality_gate", "done", 8.0)
        assert next_stage == "done"


class TestActionDispatcher:
    def test_render_skill(self):
        action = Action(
            action_type="skill",
            skills=[{"name": "tao-literature", "description": "Search papers"}],
            stage="literature_search",
            iteration=1,
        )
        script = render_execution_script(action)
        assert "tao-literature" in script
        assert "literature_search" in script
        assert action.execution_script == script

    def test_render_team(self):
        action = Action(
            action_type="team",
            team={
                "name": "debate_team",
                "prompt": "Debate ideas",
                "agents": [
                    {"name": "innovator", "description": "Ideas"},
                    {"name": "critic", "description": "Critique"},
                ],
                "post_steps": [{"skill": "synthesizer", "description": "Synthesize"}],
            },
            stage="idea_debate",
            iteration=2,
        )
        script = render_execution_script(action)
        assert "debate_team" in script
        assert "innovator" in script
        assert "synthesizer" in script

    def test_render_bash(self):
        action = Action(
            action_type="bash",
            bash_command="tao latex-compile .",
            stage="writing_latex",
        )
        script = render_execution_script(action)
        assert "tao latex-compile" in script

    def test_render_skills_parallel(self):
        action = Action(
            action_type="skills_parallel",
            agents=[
                {"name": "writer-1", "description": "Write intro"},
                {"name": "writer-2", "description": "Write method"},
            ],
            stage="writing_sections",
        )
        script = render_execution_script(action)
        assert "writer-1" in script
        assert "writer-2" in script
        assert "parallel" in script.lower()

    def test_render_done(self):
        action = Action(action_type="done", stage="done")
        script = render_execution_script(action)
        assert "complete" in script.lower() or "done" in script.lower()

    def test_render_experiment_wait(self):
        action = Action(
            action_type="experiment_wait",
            stage="experiment_cycle",
            experiment_monitor={"type": "full", "timeout_minutes": 120},
        )
        script = render_execution_script(action)
        assert "monitor" in script.lower()
        assert "120" in script

    def test_render_bash_experiment_run(self):
        action = Action(
            action_type="bash",
            bash_command="tao experiment-run . pilot",
            stage="pilot_experiments",
        )
        script = render_execution_script(action)
        assert "experiment-run" in script


def test_contract_freezes_on_planning_to_pilot(tmp_path):
    from tao.config import Config
    from tao.workspace import Workspace
    from tao.orchestration.lifecycle import Lifecycle
    from tao.orchestration.contract import (
        ResearchContract, Signal, save_contract, CONTRACT_LOCK_PATH,
    )

    ws = Workspace(tmp_path, iteration_dirs=False)
    ws.init_project("t")
    ws.update_stage("planning")
    save_contract(ws, ResearchContract(
        version="v1", hypothesis="h",
        success_signals=[Signal(id="s1", description="metric goes up")],
        failure_signals=[Signal(id="f1", description="training crashes")],
        ablations=[],
    ))
    lc = Lifecycle(ws, Config())
    lc.record_result("planning", "done")
    assert ws.file_exists(CONTRACT_LOCK_PATH)


def test_contract_freeze_missing_contract_is_safe(tmp_path):
    # No contract saved — lifecycle must not crash.
    from tao.config import Config
    from tao.workspace import Workspace
    from tao.orchestration.lifecycle import Lifecycle

    ws = Workspace(tmp_path, iteration_dirs=False)
    ws.init_project("t")
    ws.update_stage("planning")
    lc = Lifecycle(ws, Config())
    lc.record_result("planning", "done")  # must not raise
