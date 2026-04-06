"""Mechanical auto-fix patterns — zero LLM cost."""
from __future__ import annotations
import subprocess
import json
from pathlib import Path
from typing import Any

# Modules that are safe to pip-install automatically
SAFE_MODULES = {
    "torch", "torchvision", "numpy", "scipy", "pandas",
    "matplotlib", "seaborn", "sklearn", "scikit-learn",
    "transformers", "datasets", "accelerate", "wandb",
    "tqdm", "pillow", "requests", "pyyaml",
}


def try_auto_fix(category: str, message: str, workspace_root: str | Path = "") -> dict:
    """Attempt a mechanical fix. Returns {fixed: bool, action: str, details: str}."""
    fixers = {
        "import": _fix_import,
        "build": _fix_import,  # often same root cause
        "config": _fix_config,
        "state": _fix_state,
    }
    fixer = fixers.get(category)
    if fixer is None:
        return {"fixed": False, "action": "none", "details": "No auto-fix for this category"}
    return fixer(message, workspace_root)


def _fix_import(message: str, workspace_root: str | Path = "") -> dict:
    """Fix missing module imports by pip-installing."""
    # Extract module name from "No module named 'xxx'" or "ModuleNotFoundError: xxx"
    module = _extract_module_name(message)
    if not module:
        return {"fixed": False, "action": "none", "details": "Could not extract module name"}

    # Safety check
    base_module = module.split(".")[0]
    if base_module not in SAFE_MODULES:
        return {
            "fixed": False,
            "action": "manual",
            "details": f"Module '{base_module}' not in safe list. Manual install needed.",
        }

    # Map common aliases
    pip_name = _module_to_pip(base_module)

    try:
        result = subprocess.run(
            ["pip", "install", pip_name],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return {"fixed": True, "action": f"pip install {pip_name}", "details": "Installed successfully"}
        return {"fixed": False, "action": f"pip install {pip_name}", "details": result.stderr[:200]}
    except Exception as e:
        return {"fixed": False, "action": "pip install", "details": str(e)}


def _fix_config(message: str, workspace_root: str | Path = "") -> dict:
    """Fix YAML/JSON syntax errors in config files."""
    if not workspace_root:
        return {"fixed": False, "action": "none", "details": "No workspace root"}

    config_file = Path(workspace_root) / "config.yaml"
    if not config_file.exists():
        return {"fixed": False, "action": "none", "details": "No config.yaml found"}

    try:
        import yaml
        content = config_file.read_text(encoding="utf-8")
        yaml.safe_load(content)
        return {"fixed": False, "action": "none", "details": "Config YAML is valid"}
    except yaml.YAMLError as e:
        # Try to fix common issues
        fixed_content = content.replace("\t", "  ")  # tabs to spaces
        try:
            yaml.safe_load(fixed_content)
            config_file.write_text(fixed_content, encoding="utf-8")
            return {"fixed": True, "action": "fix_yaml_tabs", "details": "Replaced tabs with spaces"}
        except yaml.YAMLError:
            return {"fixed": False, "action": "manual", "details": f"YAML error: {e}"}


def _fix_state(message: str, workspace_root: str | Path = "") -> dict:
    """Fix corrupted state files."""
    if not workspace_root:
        return {"fixed": False, "action": "none", "details": "No workspace root"}

    # Check for corrupted status.json
    status_file = Path(workspace_root) / "status.json"
    if status_file.exists():
        try:
            json.loads(status_file.read_text())
        except json.JSONDecodeError:
            # Reset to safe defaults
            default = {"stage": "init", "iteration": 0, "errors": [], "paused": False}
            status_file.write_text(json.dumps(default, indent=2))
            return {"fixed": True, "action": "reset_status", "details": "Reset corrupted status.json"}

    return {"fixed": False, "action": "none", "details": "No state corruption detected"}


def _extract_module_name(message: str) -> str:
    """Extract module name from error message."""
    import re
    patterns = [
        r"No module named ['\"]([^'\"]+)['\"]",
        r"ModuleNotFoundError:\s*(?:No module named\s*)?['\"]?(\w[\w.]*)",
        r"ImportError:.*cannot import.*from ['\"]([^'\"]+)['\"]",
    ]
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1)
    return ""


def _module_to_pip(module: str) -> str:
    """Map Python module names to pip package names."""
    mapping = {
        "sklearn": "scikit-learn",
        "cv2": "opencv-python",
        "PIL": "Pillow",
        "pillow": "Pillow",
        "yaml": "pyyaml",
    }
    return mapping.get(module, module)
