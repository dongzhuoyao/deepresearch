"""WebUI Flask application with WebSocket support."""
from __future__ import annotations
import json
from pathlib import Path

try:
    from flask import Flask, jsonify, request, send_from_directory
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

from tao.gpu_scheduler import load_task_plan, load_gpu_progress, get_progress_summary
from tao.orchestration.dashboard_data import get_dashboard_data, list_all_projects

_WEBUI_DIR = Path(__file__).parent

_SKIP_DIRS = {"__pycache__", ".git", ".venv", "node_modules"}


def _build_tree(root: Path, current: Path, max_depth: int, depth: int = 0) -> list[dict]:
    """Recursively build a directory tree, returning sorted entries.

    Hidden directories (starting with '.') and __pycache__ are skipped.
    Directories are listed first, then files, both alphabetically.
    """
    if depth >= max_depth:
        return []

    entries: list[dict] = []
    try:
        children = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return []

    for child in children:
        if child.name.startswith(".") or child.name in _SKIP_DIRS:
            continue
        rel = str(child.relative_to(root))
        if child.is_dir():
            entries.append({
                "name": child.name,
                "type": "dir",
                "path": rel,
                "children": _build_tree(root, child, max_depth, depth + 1),
            })
        elif child.is_file():
            entries.append({
                "name": child.name,
                "type": "file",
                "path": rel,
                "children": [],
            })
    return entries


def create_webui_app(workspaces_dir: str = "workspace") -> "Flask":
    """Create the WebUI Flask application."""
    if not HAS_FLASK:
        raise RuntimeError("Flask not installed")

    app = Flask(__name__)
    app.config["WORKSPACES_DIR"] = workspaces_dir

    @app.route("/")
    def index():
        return send_from_directory(str(_WEBUI_DIR), "dashboard.html")

    @app.route("/api/projects")
    def api_projects():
        return jsonify(list_all_projects(workspaces_dir))

    @app.route("/api/project/<name>/dashboard")
    def api_project_dashboard(name: str):
        ws_path = Path(workspaces_dir) / name
        if not ws_path.exists():
            return jsonify({"error": "not found"}), 404
        return jsonify(get_dashboard_data(ws_path))

    @app.route("/api/project/<name>/tree")
    def api_project_tree(name: str):
        ws_path = (Path(workspaces_dir) / name).resolve()
        base = Path(workspaces_dir).resolve()
        # Guard against path traversal
        if not str(ws_path).startswith(str(base) + "/") and ws_path != base:
            return jsonify({"error": "invalid project name"}), 400
        if not ws_path.is_dir():
            return jsonify({"error": "not found"}), 404
        tree = _build_tree(ws_path, ws_path, max_depth=3)
        return jsonify(tree)

    @app.route("/api/project/<name>/experiments")
    def api_project_experiments(name: str):
        ws_path = Path(workspaces_dir) / name
        if not ws_path.exists():
            return jsonify({"error": "not found"}), 404
        summary = get_progress_summary(ws_path)
        plan = load_task_plan(ws_path)
        summary["tasks"] = plan.get("tasks", [])
        return jsonify(summary)

    @app.route("/api/project/<name>/files/<path:filepath>")
    def api_project_file(name: str, filepath: str):
        ws_path = Path(workspaces_dir) / name
        full_path = ws_path / filepath
        if not full_path.exists():
            return jsonify({"error": "file not found"}), 404
        if full_path.suffix in (".json", ".jsonl"):
            return jsonify(json.loads(full_path.read_text()))
        return full_path.read_text(encoding="utf-8")

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "webui"})

    return app
