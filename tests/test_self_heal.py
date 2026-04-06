"""Tests for auto-fix and self-healing."""
from tao.auto_fix import try_auto_fix, _extract_module_name, _module_to_pip
from tao.self_heal import SelfHealRouter, SKILL_ROUTE_TABLE, CATEGORY_PRIORITY
from tao.error_collector import collect_error


class TestAutoFix:
    def test_extract_module_no_module_named(self):
        assert _extract_module_name("No module named 'torch'") == "torch"

    def test_extract_module_error(self):
        assert _extract_module_name("ModuleNotFoundError: No module named 'numpy'") == "numpy"

    def test_extract_module_no_match(self):
        assert _extract_module_name("SyntaxError: invalid syntax") == ""

    def test_module_to_pip(self):
        assert _module_to_pip("sklearn") == "scikit-learn"
        assert _module_to_pip("PIL") == "Pillow"
        assert _module_to_pip("torch") == "torch"

    def test_auto_fix_unknown_category(self):
        result = try_auto_fix("unknown_cat", "some error")
        assert result["fixed"] is False

    def test_auto_fix_unsafe_module(self):
        result = try_auto_fix("import", "No module named 'malicious_pkg'")
        assert result["fixed"] is False
        assert "not in safe list" in result["details"]

    def test_auto_fix_config_no_workspace(self):
        result = try_auto_fix("config", "YAML error")
        assert result["fixed"] is False

    def test_auto_fix_state_no_workspace(self):
        result = try_auto_fix("state", "corrupted state")
        assert result["fixed"] is False

    def test_auto_fix_state_corrupted(self, tmp_path):
        # Write corrupted status.json
        (tmp_path / "status.json").write_text("{bad json", encoding="utf-8")
        result = try_auto_fix("state", "JSONDecodeError", str(tmp_path))
        assert result["fixed"] is True
        assert result["action"] == "reset_status"


class TestSelfHealRouter:
    def test_scan_empty(self, tmp_path):
        router = SelfHealRouter(tmp_path)
        errors = router.scan_errors()
        assert errors == []

    def test_scan_and_fix(self, tmp_path):
        collect_error(tmp_path / "logs", "state", "corrupted status")
        # Write corrupted status.json in workspace
        (tmp_path / "status.json").write_text("{bad", encoding="utf-8")

        router = SelfHealRouter(tmp_path)
        errors = router.scan_errors()
        assert len(errors) == 1

        result = router.attempt_fix(errors[0]["key"])
        assert result["fixed"] is True

    def test_circuit_breaker(self, tmp_path):
        collect_error(tmp_path / "logs", "import", "No module named 'nonexistent_pkg'")
        router = SelfHealRouter(tmp_path, max_attempts=2)
        errors = router.scan_errors()
        key = errors[0]["key"]

        # Attempt 1 & 2
        router.attempt_fix(key)
        router.attempt_fix(key)

        # Attempt 3 — breaker trips
        result = router.attempt_fix(key)
        assert result["action"] == "breaker"

    def test_get_repair_skills(self):
        router = SelfHealRouter("/tmp")
        assert router.get_repair_skills("import") == ["python-patterns", "tdd-workflow"]
        assert router.get_repair_skills("prompt") is None

    def test_summary(self, tmp_path):
        collect_error(tmp_path / "logs", "config", "bad yaml")
        router = SelfHealRouter(tmp_path)
        router.scan_errors()
        summary = router.get_summary()
        assert summary["total"] == 1
        assert summary["active"] == 1

    def test_reset(self, tmp_path):
        collect_error(tmp_path / "logs", "import", "missing torch")
        router = SelfHealRouter(tmp_path)
        router.scan_errors()
        router.reset()
        assert router.get_summary()["total"] == 0

    def test_priority_sorting(self):
        assert CATEGORY_PRIORITY.index("import") < CATEGORY_PRIORITY.index("config")
        assert CATEGORY_PRIORITY.index("build") < CATEGORY_PRIORITY.index("prompt")

    def test_dedup(self, tmp_path):
        collect_error(tmp_path / "logs", "import", "No module named 'torch'")
        collect_error(tmp_path / "logs", "import", "No module named 'torch'")
        router = SelfHealRouter(tmp_path)
        errors = router.scan_errors()
        assert len(errors) == 1  # deduped
