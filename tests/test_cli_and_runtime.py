"""Tests for CLI, runtime assets, and LaTeX pipeline."""
import json
from pathlib import Path
from sibyl.runtime_assets import setup_workspace_assets, update_gitignore
from sibyl.latex_pipeline import markdown_to_latex, _escape_latex, _convert_body
from sibyl.lark_sync import sync_to_lark, is_sync_enabled
from sibyl.lark_markdown_converter import markdown_to_lark_blocks
from sibyl.orchestration.cli_core import resolve_workspace, find_workspaces
from sibyl.config import Config
from sibyl.workspace import Workspace


class TestRuntimeAssets:
    def test_setup_workspace_assets(self, tmp_path):
        ws = Workspace(tmp_path, iteration_dirs=False)
        ws.init_project("test topic")
        setup_workspace_assets(tmp_path, Config())
        assert (tmp_path / "CLAUDE.md").exists()
        assert (tmp_path / ".claude").is_dir()
        assert (tmp_path / ".sibyl" / "project" / "overlays").is_dir()
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "test topic" in content

    def test_update_gitignore(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n")
        update_gitignore(tmp_path)
        content = (tmp_path / ".gitignore").read_text()
        assert "*.pyc" in content
        assert "*.log" in content


class TestLatexPipeline:
    def test_escape_latex(self):
        assert _escape_latex("a & b") == "a \\& b"
        assert _escape_latex("100%") == "100\\%"

    def test_convert_body(self):
        md = "# Introduction\nThis is **bold** and *italic*."
        latex = _convert_body(md)
        assert "\\section{Introduction}" in latex
        assert "\\textbf{bold}" in latex

    def test_markdown_to_latex(self):
        md = "# Intro\nHello world"
        latex = markdown_to_latex(md, title="My Paper", authors="Author A")
        assert "\\title{My Paper}" in latex
        assert "\\begin{document}" in latex
        assert "\\maketitle" in latex

    def test_compile_pdf_no_file(self, tmp_path):
        from sibyl.latex_pipeline import compile_pdf
        result = compile_pdf(tmp_path)
        assert result["success"] is False


class TestLarkSync:
    def test_sync_skip_stage(self, tmp_path):
        result = sync_to_lark(tmp_path, "init", "content")
        assert result["synced"] is False

    def test_sync_normal_stage(self, tmp_path):
        result = sync_to_lark(tmp_path, "literature_search", "papers found")
        assert result["synced"] is True

    def test_is_sync_enabled(self):
        assert is_sync_enabled(None) is False
        assert is_sync_enabled({"lark_enabled": True}) is True
        assert is_sync_enabled({"lark_enabled": False}) is False


class TestLarkConverter:
    def test_basic_conversion(self):
        md = "# Title\n## Subtitle\n- Item 1\nPlain text"
        blocks = markdown_to_lark_blocks(md)
        assert blocks[0]["type"] == "heading1"
        assert blocks[1]["type"] == "heading2"
        assert blocks[2]["type"] == "bullet"
        assert blocks[3]["type"] == "text"


class TestCliCore:
    def test_resolve_workspace(self, tmp_path):
        path = resolve_workspace(str(tmp_path))
        assert path == tmp_path

    def test_resolve_nonexistent(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            resolve_workspace("/nonexistent/path/xyz")

    def test_find_workspaces(self, tmp_path):
        # Create fake workspaces
        (tmp_path / "proj_a").mkdir()
        (tmp_path / "proj_a" / "status.json").write_text("{}")
        (tmp_path / "proj_b").mkdir()
        (tmp_path / "proj_b" / "status.json").write_text("{}")
        workspaces = find_workspaces(str(tmp_path))
        assert len(workspaces) == 2

    def test_find_workspaces_empty(self, tmp_path):
        workspaces = find_workspaces(str(tmp_path / "nonexistent"))
        assert workspaces == []
