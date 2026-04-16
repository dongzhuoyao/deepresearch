"""Tests for the writing gate (claim -> signal tag verification)."""
from tao.orchestration.writing_gate import (
    verify_claims_against_contract, ClaimViolation,
)
from tao.orchestration.contract import ResearchContract, Signal


def _contract():
    return ResearchContract(
        version="v1", hypothesis="h",
        success_signals=[
            Signal(id="s1", description="accuracy > 80 on CIFAR"),
            Signal(id="s2", description="FLOPs reduced by 30%"),
        ],
        failure_signals=[Signal(id="f1", description="training diverges")],
        ablations=[Signal(id="a1", description="no-LoRA baseline loses 3 pts")],
    )


def test_claim_without_tag_is_violation():
    text = "We improve SOTA by 5 points on ImageNet-21k."
    vs = verify_claims_against_contract(text, _contract())
    assert any(isinstance(v, ClaimViolation) for v in vs)
    assert "no [signal:*] tag" in vs[0].reason


def test_claim_with_known_signal_passes():
    text = "Our method reaches 82% accuracy on CIFAR [signal:s1]."
    assert verify_claims_against_contract(text, _contract()) == []


def test_claim_with_unknown_signal_is_violation():
    text = "Our method outperforms baselines by 4 points [signal:s99]."
    vs = verify_claims_against_contract(text, _contract())
    assert vs and "unknown signals" in vs[0].reason


def test_non_empirical_text_has_no_claims():
    text = "We propose a method based on sparse attention. It is novel."
    assert verify_claims_against_contract(text, _contract()) == []


def test_multiple_claims_each_evaluated():
    text = (
        "Our model reaches 82% accuracy on CIFAR [signal:s1]. "
        "We also improve FLOPs [signal:s99]."
    )
    vs = verify_claims_against_contract(text, _contract())
    assert len(vs) == 1
    assert "s99" in vs[0].reason


def test_ablation_signal_id_is_accepted():
    text = "Removing LoRA loses 3 pts [signal:a1]."
    assert verify_claims_against_contract(text, _contract()) == []
