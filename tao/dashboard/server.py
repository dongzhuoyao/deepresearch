"""Simple dashboard server serving workspace data."""
from __future__ import annotations
import json
from pathlib import Path

try:
    from flask import Flask, jsonify, request
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

from tao.orchestration.dashboard_data import get_dashboard_data, list_all_projects


def create_app(workspaces_dir: str = "workspaces") -> "Flask":
    """Create Flask dashboard app."""
    if not HAS_FLASK:
        raise RuntimeError("Flask not installed. Run: pip install flask")

    app = Flask(__name__)

    @app.route("/api/projects")
    def api_projects():
        projects = list_all_projects(workspaces_dir)
        return jsonify(projects)

    @app.route("/api/dashboard/<project_name>")
    def api_dashboard(project_name: str):
        ws_path = Path(workspaces_dir) / project_name
        if not ws_path.exists():
            return jsonify({"error": "Project not found"}), 404
        data = get_dashboard_data(ws_path)
        return jsonify(data)

    @app.route("/api/health")
    def api_health():
        return jsonify({"status": "ok"})

    return app


def run_dashboard(workspaces_dir: str = "workspaces", port: int = 3000):
    """Run the dashboard server."""
    app = create_app(workspaces_dir)
    app.run(host="0.0.0.0", port=port)
