"""LaTeX pipeline — Markdown to LaTeX conversion and PDF compilation."""
from __future__ import annotations
import subprocess
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tao.workspace import Workspace

NEURIPS_PREAMBLE = r"""\documentclass{article}
\usepackage[preprint]{neurips_2024}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\usepackage{url}
\usepackage{booktabs}
\usepackage{amsfonts}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{microtype}
\usepackage{xcolor}
"""


def markdown_to_latex(markdown: str, title: str = "", authors: str = "") -> str:
    """Convert a markdown paper to LaTeX."""
    lines = []
    lines.append(NEURIPS_PREAMBLE)

    if title:
        lines.append(f"\\title{{{_escape_latex(title)}}}")
    if authors:
        lines.append(f"\\author{{{_escape_latex(authors)}}}")

    lines.append("\\begin{document}")
    if title:
        lines.append("\\maketitle")

    # Convert markdown body
    body = _convert_body(markdown)
    lines.append(body)

    lines.append("\\end{document}")
    return "\n".join(lines)


def compile_pdf(
    workspace_root: str | Path,
    latex_content: str | None = None,
) -> dict:
    """Compile LaTeX to PDF.

    Returns {success: bool, pdf_path: str, log: str}.
    """
    root = Path(workspace_root)
    latex_dir = root / "writing" / "latex"
    latex_dir.mkdir(parents=True, exist_ok=True)

    # Read or use provided content
    tex_file = latex_dir / "paper.tex"
    if latex_content:
        tex_file.write_text(latex_content, encoding="utf-8")
    elif not tex_file.exists():
        # Try converting from paper.md
        paper_md = root / "writing" / "paper.md"
        if paper_md.exists():
            md_content = paper_md.read_text(encoding="utf-8")
            latex_content = markdown_to_latex(md_content)
            tex_file.write_text(latex_content, encoding="utf-8")
        else:
            return {"success": False, "pdf_path": "", "log": "No paper.tex or paper.md found"}

    # Compile with pdflatex (2 passes for references)
    pdf_path = latex_dir / "paper.pdf"
    log_output = ""

    for _ in range(2):
        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(latex_dir), str(tex_file)],
                capture_output=True, text=True, timeout=60, cwd=str(latex_dir),
            )
            log_output = result.stdout + result.stderr
        except FileNotFoundError:
            return {"success": False, "pdf_path": "", "log": "pdflatex not found. Install TeX Live."}
        except subprocess.TimeoutExpired:
            return {"success": False, "pdf_path": "", "log": "pdflatex timed out after 60s"}

    success = pdf_path.exists()
    return {
        "success": success,
        "pdf_path": str(pdf_path) if success else "",
        "log": log_output[-500:] if log_output else "",
    }


def _convert_body(markdown: str) -> str:
    """Convert markdown body to LaTeX."""
    text = markdown

    # Headers
    text = re.sub(r'^# (.+)$', r'\\section{\1}', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'\\subsection{\1}', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'\\subsubsection{\1}', text, flags=re.MULTILINE)

    # Bold and italic
    text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
    text = re.sub(r'\*(.+?)\*', r'\\textit{\1}', text)

    # Inline code
    text = re.sub(r'`([^`]+)`', r'\\texttt{\1}', text)

    # Simple bullet lists
    text = re.sub(r'^- (.+)$', r'\\item \1', text, flags=re.MULTILINE)

    # Escape special characters (after conversions)
    # Only escape % and & that aren't already part of LaTeX commands
    text = text.replace('%', '\\%')
    text = text.replace('&', '\\&')

    return text


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    chars = {'&': '\\&', '%': '\\%', '$': '\\$', '#': '\\#', '_': '\\_',
             '{': '\\{', '}': '\\}', '~': '\\textasciitilde{}', '^': '\\textasciicircum{}'}
    for char, replacement in chars.items():
        text = text.replace(char, replacement)
    return text
