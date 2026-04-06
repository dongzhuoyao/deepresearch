"""Pipeline lifecycle — generates actions for each stage."""
from __future__ import annotations
from typing import TYPE_CHECKING

from tao.orchestration.models import Action
from tao.orchestration.state_machine import StateMachine
from tao.event_logger import log_event

if TYPE_CHECKING:
    from tao.config import Config
    from tao.workspace import Workspace


class Lifecycle:
    """Generates Action objects for pipeline stages and records results."""

    def __init__(self, workspace: "Workspace", config: "Config") -> None:
        self._ws = workspace
        self._cfg = config
        self._sm = StateMachine(workspace, config)

    def get_next_action(self) -> Action:
        """Generate the next action based on current workspace state."""
        status = self._ws.get_status()
        stage = status.stage
        iteration = status.iteration

        # Map stages to action builders
        builders = {
            "init": self._action_init,
            "literature_search": self._action_literature_search,
            "idea_debate": self._action_idea_debate,
            "planning": self._action_planning,
            "pilot_experiments": self._action_pilot_experiments,
            "idea_validation_decision": self._action_idea_validation,
            "experiment_cycle": self._action_experiment_cycle,
            "result_debate": self._action_result_debate,
            "experiment_decision": self._action_experiment_decision,
            "writing_outline": self._action_writing_outline,
            "writing_sections": self._action_writing_sections,
            "writing_integrate": self._action_writing_integrate,
            "writing_final_review": self._action_writing_final_review,
            "writing_latex": self._action_writing_latex,
            "review": self._action_review,
            "reflection": self._action_reflection,
            "quality_gate": self._action_quality_gate,
            "done": self._action_done,
        }

        builder = builders.get(stage, self._action_done)
        action = builder()
        action.stage = stage
        action.iteration = iteration
        return action

    def record_result(self, stage: str, result: str, score: float = 0.0) -> str:
        """Record stage result and advance to next stage.

        Returns the next stage name.
        """
        # Log the completion event
        log_event(
            self._ws.active_root / "logs",
            "stage_complete",
            {"stage": stage, "result": result[:200], "score": score},
        )

        # Compute next stage
        next_stage = self._sm.natural_next_stage(stage, result, score)

        # Handle iteration advancement
        status = self._ws.get_status()
        if next_stage == "literature_search" and stage == "quality_gate":
            # Starting new iteration
            self._ws.new_iteration()
            self._ws.update_stage("literature_search")
        elif next_stage == "done":
            self._ws.update_stage("done")
        else:
            self._ws.update_stage(next_stage)

        return next_stage

    # --- Action builders (one per stage) ---

    def _action_init(self) -> Action:
        return Action(
            action_type="skill",
            skills=[{"name": "tao-literature", "description": "Initialize research workspace"}],
            description="Initialize project and prepare for literature search",
            estimated_minutes=2,
        )

    def _action_literature_search(self) -> Action:
        return Action(
            action_type="skill",
            skills=[{"name": "tao-literature", "description": "Search literature on arXiv and web"}],
            description="Conduct literature survey",
            estimated_minutes=10,
        )

    def _action_idea_debate(self) -> Action:
        agents = [
            {"name": "tao-innovator", "description": "Generate novel research ideas"},
            {"name": "tao-pragmatist", "description": "Evaluate practical feasibility"},
            {"name": "tao-theoretical", "description": "Assess theoretical soundness"},
            {"name": "tao-contrarian", "description": "Challenge assumptions"},
            {"name": "tao-interdisciplinary", "description": "Cross-domain insights"},
            {"name": "tao-empiricist", "description": "Evidence-based evaluation"},
        ]
        return Action(
            action_type="team",
            team={
                "name": "idea_debate_team",
                "prompt": "Debate and refine research ideas",
                "agents": agents,
                "post_steps": [{"skill": "tao-synthesizer", "description": "Synthesize best idea"}],
            },
            description="Multi-agent idea debate and synthesis",
            estimated_minutes=15,
        )

    def _action_planning(self) -> Action:
        return Action(
            action_type="skill",
            skills=[{"name": "tao-planner", "description": "Design experiment plan with GPU tasks"}],
            description="Create experiment plan with task dependencies",
            estimated_minutes=10,
        )

    def _action_pilot_experiments(self) -> Action:
        return Action(
            action_type="bash",
            bash_command="tao experiment-status .",
            description="Launch pilot experiments on RunPod",
            estimated_minutes=30,
            experiment_monitor={"type": "pilot", "timeout_minutes": self._cfg.pilot_timeout // 60},
        )

    def _action_idea_validation(self) -> Action:
        return Action(
            action_type="skill",
            skills=[{"name": "tao-idea-validation-decision", "description": "Evaluate pilot results and decide ADVANCE/REFINE/PIVOT"}],
            description="Validate idea based on pilot results",
            estimated_minutes=5,
        )

    def _action_experiment_cycle(self) -> Action:
        return Action(
            action_type="experiment_wait",
            description="Run full experiments on RunPod and monitor",
            estimated_minutes=120,
            experiment_monitor={"type": "full", "timeout_minutes": self._cfg.experiment_timeout // 60},
        )

    def _action_result_debate(self) -> Action:
        agents = [
            {"name": "tao-innovator", "description": "Interpret results creatively"},
            {"name": "tao-pragmatist", "description": "Practical implications"},
            {"name": "tao-theoretical", "description": "Theoretical analysis"},
            {"name": "tao-contrarian", "description": "Challenge conclusions"},
            {"name": "tao-interdisciplinary", "description": "Cross-domain comparison"},
            {"name": "tao-empiricist", "description": "Statistical rigor check"},
        ]
        return Action(
            action_type="team",
            team={
                "name": "result_debate_team",
                "prompt": "Analyze and debate experiment results",
                "agents": agents,
                "post_steps": [{"skill": "tao-result-synthesizer", "description": "Synthesize result analysis"}],
            },
            description="Multi-agent result analysis and debate",
            estimated_minutes=15,
        )

    def _action_experiment_decision(self) -> Action:
        return Action(
            action_type="skill",
            skills=[{"name": "tao-supervisor-decision", "description": "Decide PROCEED or PIVOT based on results"}],
            description="Supervisor decides whether to proceed or pivot",
            estimated_minutes=5,
        )

    def _action_writing_outline(self) -> Action:
        return Action(
            action_type="skill",
            skills=[{"name": "tao-outline-writer", "description": "Create paper outline"}],
            description="Write paper outline",
            estimated_minutes=5,
        )

    def _action_writing_sections(self) -> Action:
        if self._cfg.writing_mode == "parallel":
            from tao.orchestration.constants import PAPER_SECTIONS
            agents = [
                {"name": "tao-section-writer", "description": f"Write {title} section", "args": {"section": sid}}
                for sid, title in PAPER_SECTIONS
            ]
            return Action(
                action_type="skills_parallel",
                agents=agents,
                description="Write all paper sections in parallel",
                estimated_minutes=20,
            )
        return Action(
            action_type="skill",
            skills=[{"name": "tao-sequential-writer", "description": "Write all sections sequentially"}],
            description="Write paper sections sequentially",
            estimated_minutes=30,
        )

    def _action_writing_integrate(self) -> Action:
        return Action(
            action_type="team",
            team={
                "name": "writing_review_team",
                "prompt": "Cross-critique and integrate paper sections",
                "agents": [
                    {"name": "tao-section-critic", "description": "Critique each section"},
                    {"name": "tao-editor", "description": "Edit and integrate paper"},
                ],
            },
            description="Cross-critique and integrate paper",
            estimated_minutes=15,
        )

    def _action_writing_final_review(self) -> Action:
        return Action(
            action_type="skill",
            skills=[{"name": "tao-final-critic", "description": "Score paper quality (0-10)"}],
            description="Final paper quality review",
            estimated_minutes=5,
        )

    def _action_writing_latex(self) -> Action:
        return Action(
            action_type="bash",
            bash_command="tao latex-compile .",
            description="Convert to LaTeX and compile PDF",
            estimated_minutes=5,
        )

    def _action_review(self) -> Action:
        return Action(
            action_type="team",
            team={
                "name": "review_team",
                "prompt": "Final structural and content review",
                "agents": [
                    {"name": "tao-supervisor", "description": "Supervisor review"},
                    {"name": "tao-critic", "description": "Critical review"},
                ],
            },
            description="Final paper review",
            estimated_minutes=10,
        )

    def _action_reflection(self) -> Action:
        return Action(
            action_type="skill",
            skills=[{"name": "tao-reflection", "description": "Extract lessons and create action plan"}],
            description="Reflect on iteration and extract lessons",
            estimated_minutes=5,
        )

    def _action_quality_gate(self) -> Action:
        return Action(
            action_type="done",
            description="Quality gate — deterministic decision on DONE or iterate",
            estimated_minutes=1,
        )

    def _action_done(self) -> Action:
        return Action(
            action_type="done",
            description="Pipeline complete",
            estimated_minutes=0,
        )
