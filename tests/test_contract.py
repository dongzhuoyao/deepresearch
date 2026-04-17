"""Tests for frozen research-contract artifact."""
import pytest

from tao.orchestration.contract import (
    CONTRACT_LOCK_PATH,
    ContractError,
    ResearchContract,
    Signal,
    freeze_contract,
    load_contract,
    save_contract,
)
from tao.workspace import Workspace


def _ws(tmp_path):
    ws = Workspace(tmp_path, iteration_dirs=False)
    ws.init_project("test topic")
    return ws


def test_contract_requires_hypothesis_and_signals():
    with pytest.raises(ContractError):
        ResearchContract(
            version="v1", hypothesis="", success_signals=[], failure_signals=[], ablations=[],
        ).validate()


def test_contract_requires_independent_failure_signals():
    c = ResearchContract(
        version="v1",
        hypothesis="method X improves accuracy",
        success_signals=[Signal(id="s1", description="accuracy >= 0.8")],
        failure_signals=[Signal(id="f1", description="accuracy < 0.8")],
        ablations=[],
    )
    with pytest.raises(ContractError, match="independent"):
        c.validate()


def test_contract_accepts_distinct_failure_signal():
    c = ResearchContract(
        version="v1",
        hypothesis="method X improves accuracy",
        success_signals=[Signal(id="s1", description="accuracy >= 0.8 on CIFAR")],
        failure_signals=[Signal(id="f1", description="training loss diverges within 1k steps")],
        ablations=[Signal(id="a1", description="no-LoRA baseline loses >=3 acc pts")],
    )
    c.validate()  # must not raise


def test_save_load_roundtrip(tmp_path):
    ws = _ws(tmp_path)
    c = ResearchContract(
        version="v1", hypothesis="h",
        success_signals=[Signal(id="s1", description="metric goes up")],
        failure_signals=[Signal(id="f1", description="training crashes")],
        ablations=[],
    )
    save_contract(ws, c)
    loaded = load_contract(ws)
    assert loaded.hypothesis == "h"
    assert loaded.success_signals[0].id == "s1"


def test_freeze_prevents_same_version_overwrite(tmp_path):
    ws = _ws(tmp_path)
    c = ResearchContract(
        version="v1", hypothesis="h",
        success_signals=[Signal(id="s1", description="x goes up")],
        failure_signals=[Signal(id="f1", description="training crashes")],
        ablations=[],
    )
    save_contract(ws, c)
    freeze_contract(ws)
    c2 = ResearchContract(
        version="v1", hypothesis="different",
        success_signals=[Signal(id="s1", description="x goes up")],
        failure_signals=[Signal(id="f1", description="training crashes")],
        ablations=[],
    )
    with pytest.raises(ContractError, match="frozen"):
        save_contract(ws, c2)


def test_v2_allowed_after_freeze(tmp_path):
    ws = _ws(tmp_path)
    c = ResearchContract(
        version="v1", hypothesis="h",
        success_signals=[Signal(id="s1", description="x goes up")],
        failure_signals=[Signal(id="f1", description="training crashes")],
        ablations=[],
    )
    save_contract(ws, c)
    freeze_contract(ws)
    c2 = ResearchContract(
        version="v2", hypothesis="h",
        changelog="loosened metric threshold",
        success_signals=[Signal(id="s1", description="x goes up")],
        failure_signals=[Signal(id="f1", description="training crashes")],
        ablations=[],
    )
    save_contract(ws, c2)
    assert load_contract(ws).version == "v2"


def test_load_missing_raises(tmp_path):
    ws = _ws(tmp_path)
    with pytest.raises(ContractError):
        load_contract(ws)


def test_freeze_is_idempotent(tmp_path):
    ws = _ws(tmp_path)
    c = ResearchContract(
        version="v1", hypothesis="h",
        success_signals=[Signal(id="s1", description="x goes up")],
        failure_signals=[Signal(id="f1", description="training crashes")],
        ablations=[],
    )
    save_contract(ws, c)
    freeze_contract(ws)
    freeze_contract(ws)
    assert ws.file_exists(CONTRACT_LOCK_PATH)


def test_negation_detection_le_gt_pair():
    # success uses >, failure uses <= on same metric core -> mere negation
    c = ResearchContract(
        version="v1",
        hypothesis="h",
        success_signals=[Signal(id="s1", description="loss > 0.5")],
        failure_signals=[Signal(id="f1", description="loss <= 0.5")],
        ablations=[],
    )
    with pytest.raises(ContractError, match="independent"):
        c.validate()


def test_negation_detection_eq_neq_pair():
    # == and != on the same metric are also mere negations.
    c = ResearchContract(
        version="v1",
        hypothesis="h",
        success_signals=[Signal(id="s1", description="accuracy == 0.9")],
        failure_signals=[Signal(id="f1", description="accuracy != 0.9")],
        ablations=[],
    )
    with pytest.raises(ContractError, match="independent"):
        c.validate()


def test_distinct_metrics_with_equality_accepted():
    # Same-shape eq/neq but on different metrics -> NOT a negation.
    c = ResearchContract(
        version="v1",
        hypothesis="h",
        success_signals=[Signal(id="s1", description="accuracy == 0.9")],
        failure_signals=[Signal(id="f1", description="loss != 0.9")],
        ablations=[],
    )
    c.validate()  # must not raise
