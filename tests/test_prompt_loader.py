"""Tests for prompt loader and context builder."""
from tao.orchestration.prompt_loader import (
    load_prompt, load_shared_prompt, compile_prompt, compile_team_prompt,
    _research_focus_directive,
)
from tao.orchestration.context_builder import (
    build_context, gather_workspace_context,
)
from tao.orchestra_skills import scan_skills, format_skills_index, build_skills_section
from tao.workspace import Workspace
from tao.config import Config


class TestPromptLoader:
    def test_load_existing_prompt(self):
        prompt = load_prompt("innovator")
        assert "You are" in prompt

    def test_load_nonexistent_prompt(self):
        prompt = load_prompt("nonexistent_agent_xyz")
        assert "nonexistent_agent_xyz" in prompt

    def test_load_shared_common(self):
        common = load_shared_prompt("_common")
        assert len(common) > 0

    def test_compile_prompt(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("Neural scaling laws")
        cfg = Config()
        prompt = compile_prompt("innovator", ws, cfg)
        assert "You are" in prompt
        assert "Neural scaling laws" in prompt

    def test_compile_with_overlay(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        ws.write_file(".tao/project/overlays/innovator.md", "## Lessons\n- Focus on efficiency")
        cfg = Config()
        prompt = compile_prompt("innovator", ws, cfg)
        assert "Focus on efficiency" in prompt

    def test_compile_with_memory(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        ws.write_file(".tao/project/memory.md", "Prior work showed X works best")
        cfg = Config()
        prompt = compile_prompt("innovator", ws, cfg)
        assert "Prior work showed X works best" in prompt

    def test_research_focus_directives(self):
        assert "Explore" in _research_focus_directive(1)
        assert "Balanced" in _research_focus_directive(3)
        assert "Deep Focus" in _research_focus_directive(5)

    def test_compile_team_prompt(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        cfg = Config()
        agents = [
            {"name": "innovator", "description": "Ideas"},
            {"name": "critic", "description": "Critique"},
        ]
        prompt = compile_team_prompt("debate", agents, ws, cfg)
        assert "innovator" in prompt
        assert "critic" in prompt

    def test_experiment_protocol_injected(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test")
        cfg = Config()
        prompt = compile_prompt("experimenter", ws, cfg)
        assert "VRAM" in prompt or "PID" in prompt or "experiment" in prompt.lower()


class TestContextBuilder:
    def test_build_context_basic(self):
        sections = [
            {"label": "Topic", "content": "Neural nets", "priority": 1},
            {"label": "Lit", "content": "Paper A, Paper B", "priority": 5},
        ]
        ctx = build_context(None, sections)
        assert "Neural nets" in ctx
        assert "Paper A" in ctx

    def test_build_context_truncation(self):
        sections = [
            {"label": "A", "content": "x" * 1000, "priority": 1},
            {"label": "B", "content": "y" * 1000, "priority": 2},
        ]
        ctx = build_context(None, sections, max_chars=500)
        assert "x" in ctx
        # B may be truncated or omitted

    def test_gather_workspace_context(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test topic")
        ws.write_file("idea/proposal.md", "# Great Idea")
        sections = gather_workspace_context(ws)
        assert len(sections) >= 2
        assert sections[0]["priority"] == 1  # topic is highest


class TestOrchestraSkills:
    def test_scan_empty(self, tmp_path):
        skills = scan_skills(str(tmp_path / "nonexistent"))
        assert skills == []

    def test_scan_skills(self, tmp_path):
        (tmp_path / "skill_a.md").write_text("# Fast Matrix Multiply\nDetails...")
        (tmp_path / "skill_b.md").write_text("# GPU Profiling\nMore details...")
        (tmp_path / "not_a_skill.txt").write_text("ignore me")
        skills = scan_skills(str(tmp_path))
        assert len(skills) == 2
        assert skills[0]["name"] == "skill_a"

    def test_format_index(self):
        skills = [{"name": "a", "description": "Do A"}, {"name": "b", "description": "Do B"}]
        idx = format_skills_index(skills)
        assert "Do A" in idx
        assert "Do B" in idx

    def test_format_empty(self):
        assert format_skills_index([]) == ""

    def test_build_skills_section(self, tmp_path):
        (tmp_path / "test.md").write_text("# My Skill\nDetails")
        section = build_skills_section(str(tmp_path))
        assert "My Skill" in section
