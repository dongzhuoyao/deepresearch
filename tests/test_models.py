"""Tests for orchestration models and constants."""
from tao.orchestration.models import Action, AgentTask
from tao.orchestration.constants import (
    PIPELINE_STAGES, PAPER_SECTIONS, CHECKPOINT_DIRS, SYNC_SKIP_STAGES,
)


def test_action_defaults():
    a = Action(action_type="skill", stage="init")
    assert a.agents is None
    assert a.skills is None
    assert a.team is None
    assert a.bash_command is None
    assert a.execution_script == ""
    assert a.estimated_minutes == 0


def test_action_with_agents():
    a = Action(
        action_type="skills_parallel",
        agents=[{"name": "lit", "prompt": "search"}],
        stage="literature_search",
        iteration=1,
    )
    assert len(a.agents) == 1
    assert a.iteration == 1


def test_agent_task():
    t = AgentTask("lit_researcher", "search for papers on X", "literature search", "/tmp/ws")
    assert t.agent_name == "lit_researcher"
    assert t.workspace_path == "/tmp/ws"


def test_pipeline_stages_order():
    assert PIPELINE_STAGES[0] == "init"
    assert PIPELINE_STAGES[-1] == "done"
    assert len(PIPELINE_STAGES) == 18
    # Key stages exist
    assert "literature_search" in PIPELINE_STAGES
    assert "idea_debate" in PIPELINE_STAGES
    assert "experiment_cycle" in PIPELINE_STAGES
    assert "writing_latex" in PIPELINE_STAGES
    assert "quality_gate" in PIPELINE_STAGES


def test_pipeline_stages_no_duplicates():
    assert len(PIPELINE_STAGES) == len(set(PIPELINE_STAGES))


def test_paper_sections():
    assert len(PAPER_SECTIONS) == 6
    ids = [s[0] for s in PAPER_SECTIONS]
    assert "intro" in ids
    assert "conclusion" in ids


def test_checkpoint_dirs():
    assert "idea_debate" in CHECKPOINT_DIRS
    assert CHECKPOINT_DIRS["writing_sections"] == "writing/sections"


def test_sync_skip_stages():
    assert "init" in SYNC_SKIP_STAGES
    assert "done" in SYNC_SKIP_STAGES
    assert "literature_search" not in SYNC_SKIP_STAGES
