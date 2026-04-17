# Context-Is-All-You-Need Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Apply 9 lessons from a TOP10 PhD's AI-research playbook (summarized in `context_is_all_you_need.md`) to the Tao pipeline: freeze a research contract before experiments, isolate reviewer contexts, bound review loops, prefer source over PDF, add a Gemini scout, sub-agent heavy ops, tmux-wrap remote runs, enforce contract-grounded writing claims, and add Codex as independent reviewer.

**Architecture:** All changes live under `tao/` with one new artifact (`contract.json`) and small, additive fields on existing dataclasses. State machine gains a max-review-rounds guard. `compute/runpod_backend.py::run_remote` wraps long commands in tmux. `orchestra_skills.py` gains a Gemini-CLI scout dispatcher. No new packages; Codex and Gemini are external CLIs shelled out to, matching the pattern the author's post describes.

**Tech Stack:** Python 3.11+, pytest, existing Tao dataclasses/state machine, RunPod SSH, Gemini CLI, Codex CLI. No new dependencies.

---

## Conventions

- TDD for every task: failing test → minimal impl → green → commit.
- One conceptual change per commit; use conventional-commit prefixes (`feat:`, `refactor:`, `test:`).
- All new fields on dataclasses are optional with safe defaults (no break to existing callers).
- Run `pytest tests/ -v` after each task. The full suite must stay green.

---

## Task 1: Research Contract Artifact

**Files:**
- Create: `tao/orchestration/contract.py`
- Test: `tests/test_contract.py`
- Modify: `tao/orchestration/workspace_paths.py` (add `plan/contract.json` to standard dirs)

**Step 1: Write the failing tests**

```python
# tests/test_contract.py
import pytest
from tao.orchestration.contract import (
    ResearchContract, Signal, ContractError, load_contract, save_contract, freeze_contract,
)
from tao.workspace import Workspace


def _ws(tmp_path):
    ws = Workspace(tmp_path, iteration_dirs=False)
    ws.init_project("test topic")
    return ws


def test_contract_requires_hypothesis_and_signals(tmp_path):
    with pytest.raises(ContractError):
        ResearchContract(
            version="v1", hypothesis="", success_signals=[], failure_signals=[], ablations=[],
        ).validate()


def test_contract_requires_independent_failure_signals(tmp_path):
    # Failure signal that merely negates a success signal is rejected.
    c = ResearchContract(
        version="v1",
        hypothesis="method X improves accuracy",
        success_signals=[Signal(id="s1", description="accuracy >= 0.8")],
        failure_signals=[Signal(id="f1", description="accuracy < 0.8")],
        ablations=[],
    )
    with pytest.raises(ContractError, match="independent"):
        c.validate()


def test_contract_accepts_distinct_failure_signal(tmp_path):
    c = ResearchContract(
        version="v1",
        hypothesis="method X improves accuracy",
        success_signals=[Signal(id="s1", description="accuracy >= 0.8 on CIFAR")],
        failure_signals=[Signal(id="f1", description="training loss diverges within 1k steps")],
        ablations=[Signal(id="a1", description="no-LoRA baseline loses >=3 acc pts")],
    )
    c.validate()  # does not raise


def test_save_load_roundtrip(tmp_path):
    ws = _ws(tmp_path)
    c = ResearchContract(
        version="v1",
        hypothesis="h",
        success_signals=[Signal(id="s1", description="metric goes up")],
        failure_signals=[Signal(id="f1", description="training crashes")],
        ablations=[],
    )
    save_contract(ws, c)
    loaded = load_contract(ws)
    assert loaded.hypothesis == "h"
    assert loaded.success_signals[0].id == "s1"


def test_freeze_prevents_overwrite(tmp_path):
    ws = _ws(tmp_path)
    c = ResearchContract(
        version="v1", hypothesis="h",
        success_signals=[Signal(id="s1", description="x")],
        failure_signals=[Signal(id="f1", description="y")],
        ablations=[],
    )
    save_contract(ws, c)
    freeze_contract(ws)
    c2 = ResearchContract(
        version="v1", hypothesis="h2",
        success_signals=[Signal(id="s1", description="x")],
        failure_signals=[Signal(id="f1", description="y")],
        ablations=[],
    )
    with pytest.raises(ContractError, match="frozen"):
        save_contract(ws, c2)


def test_v2_allowed_after_freeze(tmp_path):
    ws = _ws(tmp_path)
    c = ResearchContract(
        version="v1", hypothesis="h",
        success_signals=[Signal(id="s1", description="x")],
        failure_signals=[Signal(id="f1", description="y")],
        ablations=[],
    )
    save_contract(ws, c)
    freeze_contract(ws)
    c2 = ResearchContract(
        version="v2", hypothesis="h", changelog="loosened metric threshold",
        success_signals=[Signal(id="s1", description="x")],
        failure_signals=[Signal(id="f1", description="y")],
        ablations=[],
    )
    save_contract(ws, c2)
    assert load_contract(ws).version == "v2"
```

**Step 2: Run tests to verify failure**

```
pytest tests/test_contract.py -v
```
Expected: ImportError / module not found.

**Step 3: Implement `tao/orchestration/contract.py`**

```python
"""Research contract — frozen hypothesis/signals artifact.

Written at end of `planning`; locked once `pilot_experiments` starts.
Downstream stages (experiment_decision, result_debate, writing_sections) read it
to judge claims against pre-registered signals rather than post-hoc narratives.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tao.workspace import Workspace


CONTRACT_PATH = "plan/contract.json"
CONTRACT_LOCK_PATH = "plan/contract.lock"


class ContractError(Exception):
    """Raised on invalid contract content or illegal mutation."""


@dataclass
class Signal:
    id: str
    description: str


@dataclass
class ResearchContract:
    version: str
    hypothesis: str
    success_signals: list[Signal]
    failure_signals: list[Signal]
    ablations: list[Signal]
    changelog: str = ""

    def validate(self) -> None:
        if not self.hypothesis.strip():
            raise ContractError("hypothesis required")
        if not self.success_signals:
            raise ContractError("at least one success_signal required")
        if not self.failure_signals:
            raise ContractError("at least one failure_signal required")
        # Independence check: a failure signal that is just a negation
        # of a success signal ("accuracy >= X" vs "accuracy < X") is rejected.
        for fs in self.failure_signals:
            for ss in self.success_signals:
                if _is_mere_negation(ss.description, fs.description):
                    raise ContractError(
                        f"failure signal {fs.id} is not independent of success signal {ss.id}"
                    )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ResearchContract":
        return cls(
            version=data["version"],
            hypothesis=data["hypothesis"],
            success_signals=[Signal(**s) for s in data.get("success_signals", [])],
            failure_signals=[Signal(**s) for s in data.get("failure_signals", [])],
            ablations=[Signal(**s) for s in data.get("ablations", [])],
            changelog=data.get("changelog", ""),
        )


def _is_mere_negation(a: str, b: str) -> bool:
    """Detect obvious negations like '>= X' vs '< X' on the same metric."""
    a, b = a.strip().lower(), b.strip().lower()
    for pos, neg in [(">=", "<"), (">", "<="), ("<=", ">"), ("<", ">=")]:
        if pos in a and neg in b:
            core_a = a.split(pos, 1)[0].strip()
            core_b = b.split(neg, 1)[0].strip()
            if core_a and core_a == core_b:
                return True
    return False


def save_contract(ws: "Workspace", contract: ResearchContract) -> Path:
    contract.validate()
    if ws.file_exists(CONTRACT_LOCK_PATH):
        existing = load_contract(ws)
        if contract.version == existing.version:
            raise ContractError(
                "contract is frozen — bump version (e.g. v2) with changelog to modify"
            )
    return ws.write_json(CONTRACT_PATH, contract.to_dict())


def load_contract(ws: "Workspace") -> ResearchContract:
    data = ws.read_json(CONTRACT_PATH)
    if data is None:
        raise ContractError(f"no contract at {CONTRACT_PATH}")
    return ResearchContract.from_dict(data)


def freeze_contract(ws: "Workspace") -> None:
    ws.write_file(CONTRACT_LOCK_PATH, "frozen")
```

**Step 4: Update `workspace_paths.py`** — no new dir needed, `plan/` already exists. Skip.

**Step 5: Run tests to verify pass**
```
pytest tests/test_contract.py -v
```
Expected: all green.

**Step 6: Commit**
```
git add tao/orchestration/contract.py tests/test_contract.py
git commit -m "feat: add frozen research-contract artifact (hypothesis + independent signals)"
```

---

## Task 2: Wire Contract into Planning → Freeze on Pilot

**Files:**
- Modify: `tao/orchestration/simple_actions.py::build_planning` (prompt hint)
- Modify: `tao/orchestration/lifecycle.py::record_result` (freeze on `planning → pilot_experiments`)
- Test: `tests/test_lifecycle.py` (add freeze test)

**Step 1: Failing test**

```python
# append to tests/test_lifecycle.py
from tao.orchestration.contract import ResearchContract, Signal, save_contract, CONTRACT_LOCK_PATH


def test_contract_freezes_when_planning_completes(tmp_path):
    from tao.config import Config
    from tao.workspace import Workspace
    from tao.orchestration.lifecycle import Lifecycle

    ws = Workspace(tmp_path, iteration_dirs=False)
    ws.init_project("t")
    ws.update_stage("planning")
    save_contract(ws, ResearchContract(
        version="v1", hypothesis="h",
        success_signals=[Signal(id="s1", description="metric improves")],
        failure_signals=[Signal(id="f1", description="training crashes")],
        ablations=[],
    ))
    lc = Lifecycle(ws, Config())
    lc.record_result("planning", "done")
    assert ws.file_exists(CONTRACT_LOCK_PATH)
```

**Step 2: Run** → fails (no freeze logic yet).

**Step 3: Implement** — in `lifecycle.py::record_result`, after computing `next_stage`:

```python
if stage == "planning" and next_stage == "pilot_experiments":
    from tao.orchestration.contract import freeze_contract
    try:
        freeze_contract(self._ws)
    except Exception as e:
        log_event(self._ws.active_root / "logs", "contract_freeze_failed",
                  {"error": str(e)})
```

**Step 4: Update `build_planning` description** to prompt contract authoring:
```python
skills=[{"name": "tao-planner", "description": "Design experiment plan WITH research contract (hypothesis, success/failure signals, ablations) written to plan/contract.json"}],
```

**Step 5: Run full test suite**
```
pytest tests/ -v
```

**Step 6: Commit**
```
git commit -am "feat: freeze research contract at planning → pilot transition"
```

---

## Task 3: Reviewer Context Isolation

**Files:**
- Modify: `tao/orchestration/models.py` (add `context_isolation` field)
- Modify: `tao/orchestration/team_actions.py` (propagate field)
- Test: `tests/test_action_builders.py`

**Step 1: Failing test**

```python
# tests/test_action_builders.py — add
from tao.orchestration.team_actions import build_idea_debate
from tao.config import Config

def test_idea_debate_uses_context_isolation_by_default():
    action = build_idea_debate(Config())
    assert action.team["context_isolation"] is True
    # Each reviewer should see only the baseline paper + its own candidate.
    assert action.team["isolation_inputs"] == ["baseline_paper", "candidate"]
```

**Step 2: Run** → fails.

**Step 3: Implement** — in `team_actions.py`:

```python
def build_idea_debate(config: "Config") -> Action:
    return Action(
        action_type="team",
        team={
            "name": "idea_debate_team",
            "prompt": "...",
            "agents": IDEA_DEBATE_AGENTS,
            "rounds": config.debate_rounds,
            "context_isolation": True,
            "isolation_inputs": ["baseline_paper", "candidate"],
            "post_steps": [{"skill": "tao-synthesizer", "description": "..."}],
        },
        description="Multi-agent idea debate and synthesis",
        estimated_minutes=15,
    )
```

Repeat for `build_result_debate` with `isolation_inputs=["contract", "experiment_record"]`.

**Step 4: Action-dispatcher read-through** — scan `tao/orchestration/action_dispatcher.py` and update the prompt rendering to, when `context_isolation=True`, build per-agent prompts that include only the listed inputs. (Keep changes minimal; if the dispatcher is already prompt-string based, add a filtering step.)

**Step 5: Run tests**
```
pytest tests/test_action_builders.py tests/test_state_machine.py -v
```

**Step 6: Commit**
```
git commit -am "feat: context isolation flag on review team actions"
```

---

## Task 4: Max-Review-Rounds Guard in State Machine

**Files:**
- Modify: `tao/config.py` (add `max_review_rounds: int = 3`)
- Modify: `tao/orchestration/state_machine.py` (enforce cap on `idea_debate`/`result_debate` revisits)
- Test: `tests/test_state_machine.py`

**Step 1: Failing test**

```python
def test_idea_validation_respects_max_review_rounds(tmp_path):
    sm = _make_sm(tmp_path, idea_validation_rounds=10, max_review_rounds=2)
    ws = sm._ws
    from tao.event_logger import log_event
    for _ in range(2):
        log_event(ws.active_root / "logs", "stage_complete",
                  {"stage": "idea_validation_decision"})
    # Two prior revisits already; a 3rd PIVOT must be capped.
    next_stage = sm.natural_next_stage(
        "idea_validation_decision", result="DECISION: PIVOT"
    )
    assert next_stage == "experiment_cycle"  # forced forward
```

**Step 2: Run** → fails.

**Step 3: Implement** — add `max_review_rounds` to `Config`, and in `state_machine.py` replace:

```python
if rounds_used < self._cfg.idea_validation_rounds:
```
with
```python
if (rounds_used < self._cfg.idea_validation_rounds
        and rounds_used < self._cfg.max_review_rounds):
```

Do the same for `experiment_decision`.

**Step 4: Run** → green.

**Step 5: Commit**
```
git commit -am "feat: enforce max_review_rounds cap on debate revisits"
```

---

## Task 5: Prefer Source-Over-PDF in Literature Search

**Files:**
- Create: `tao/paper_source.py` (small helper: arxiv e-print → markdown fallback)
- Test: `tests/test_paper_source.py`
- Modify: `tao/orchestration/simple_actions.py::build_literature_search` description

**Step 1: Failing tests**

```python
# tests/test_paper_source.py
from tao.paper_source import prefer_source_url, is_pdf_url

def test_prefer_arxiv_eprint_over_pdf():
    url = prefer_source_url("https://arxiv.org/pdf/2401.12345v2")
    assert url == "https://arxiv.org/e-print/2401.12345v2"

def test_unknown_domain_falls_through():
    assert prefer_source_url("https://example.com/paper.pdf") == "https://example.com/paper.pdf"

def test_is_pdf_url():
    assert is_pdf_url("https://foo/bar.pdf")
    assert not is_pdf_url("https://foo/bar.html")
```

**Step 2: Run** → fails.

**Step 3: Implement**

```python
# tao/paper_source.py
"""Helpers for preferring LaTeX/Markdown sources over rendered PDFs.

Rationale: PDFs get skimmed by LLMs — feeding the raw source lets agents
read by section (abstract/method) instead of drowning in 30+ pages.
"""
from __future__ import annotations
import re

_ARXIV_PDF = re.compile(r"https?://arxiv\.org/pdf/([\w\.\-/]+?)(?:\.pdf)?$")


def is_pdf_url(url: str) -> bool:
    return url.lower().endswith(".pdf") or "/pdf/" in url.lower()


def prefer_source_url(url: str) -> str:
    """Map well-known PDF URLs to source-form URLs when possible."""
    m = _ARXIV_PDF.match(url)
    if m:
        return f"https://arxiv.org/e-print/{m.group(1)}"
    return url
```

**Step 4: Update literature-search action description** (prompt-level hint only):

```python
skills=[{"name": "tao-literature",
         "description": "Search literature; prefer LaTeX source / HF-Papers markdown over PDF (use tao.paper_source.prefer_source_url)"}],
```

**Step 5: Run tests + commit**

```
pytest tests/test_paper_source.py -v
git add tao/paper_source.py tests/test_paper_source.py tao/orchestration/simple_actions.py
git commit -m "feat: prefer arxiv e-print / markdown source over PDF for lit search"
```

---

## Task 6: Gemini Scout Agent

**Files:**
- Create: `tao/scouts/__init__.py`
- Create: `tao/scouts/gemini.py`
- Test: `tests/test_gemini_scout.py`
- Modify: `tao/config.py` (add `lit_search_scout: str = "gemini"`, `gemini_cli_bin: str = "gemini"`)

**Step 1: Failing tests**

```python
# tests/test_gemini_scout.py
from unittest.mock import patch
from tao.scouts.gemini import GeminiScout, ScoutQuery


def test_scout_builds_multiangle_queries():
    q = ScoutQuery(topic="efficient fine-tuning", constraints=["has code", "top venue"])
    q2 = q.expand()
    # A scout query must fan out into multiple angles.
    assert len(q2) >= 3


def test_scout_invokes_cli_and_parses_json():
    scout = GeminiScout(bin_path="gemini")
    fake_stdout = '{"papers":[{"title":"X","url":"https://arxiv.org/abs/1"}]}'
    with patch("subprocess.run") as run:
        run.return_value.stdout = fake_stdout
        run.return_value.returncode = 0
        papers = scout.search("efficient fine-tuning", constraints=["has code"])
    assert papers and papers[0]["title"] == "X"


def test_scout_returns_empty_on_cli_missing(tmp_path):
    scout = GeminiScout(bin_path="/no/such/bin")
    assert scout.search("topic") == []
```

**Step 2: Run** → fails.

**Step 3: Implement**

```python
# tao/scouts/__init__.py  (empty)

# tao/scouts/gemini.py
"""Gemini CLI scout — literature discovery via an external `gemini` binary.

Rationale (from `context_is_all_you_need.md`): Gemini has the widest search
coverage; using it as a scout keeps the main Claude session out of web results
and preserves context. The scout returns structured paper records; the main
orchestrator decides what to read in full.
"""
from __future__ import annotations
import json
import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class ScoutQuery:
    topic: str
    constraints: list[str] = field(default_factory=list)

    def expand(self) -> list[str]:
        """Fan out into multi-angle queries: methods / empirical / surveys."""
        angles = [
            f"{self.topic} — recent methods (top venues, code available)",
            f"{self.topic} — empirical comparisons and benchmarks",
            f"{self.topic} — surveys and taxonomy",
        ]
        if self.constraints:
            suffix = " [" + ", ".join(self.constraints) + "]"
            angles = [a + suffix for a in angles]
        return angles


class GeminiScout:
    def __init__(self, bin_path: str = "gemini", timeout_sec: int = 180) -> None:
        self._bin = bin_path
        self._timeout = timeout_sec

    def available(self) -> bool:
        return shutil.which(self._bin) is not None

    def search(self, topic: str, constraints: list[str] | None = None) -> list[dict]:
        if not self.available():
            return []
        query = ScoutQuery(topic=topic, constraints=constraints or [])
        prompt = (
            "Return strict JSON {\"papers\":[{\"title\":..,\"url\":..,\"venue\":..,\"has_code\":..}]}. "
            "Search angles:\n" + "\n".join(f"- {a}" for a in query.expand())
        )
        try:
            result = subprocess.run(
                [self._bin, "-p", prompt],
                capture_output=True, text=True, timeout=self._timeout,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
        if result.returncode != 0:
            return []
        try:
            data = json.loads(result.stdout.strip())
            return data.get("papers", [])
        except json.JSONDecodeError:
            return []
```

**Step 4: Run tests + commit**

```
pytest tests/test_gemini_scout.py -v
git add tao/scouts/ tests/test_gemini_scout.py tao/config.py
git commit -m "feat: add Gemini-CLI literature scout (multi-angle search, JSON output)"
```

---

## Task 7: Sub-Agent Wrapping for Heavy Ops (pip/download/reproduce)

**Files:**
- Modify: `tao/auto_fix.py` — pip-install path must emit a sub-agent Action, not exec inline
- Test: `tests/test_self_heal.py` (reuse existing harness)

**Step 1: Failing test**

```python
# tests/test_self_heal.py — append
def test_pip_install_routed_to_subagent(tmp_path):
    from tao.auto_fix import plan_pip_install
    action = plan_pip_install(package="numpy", workspace_root=tmp_path)
    assert action.action_type == "agents_parallel"
    # Must be out-of-band so stdout/stderr never lands in main session context.
    assert action.description.startswith("subagent:")
```

**Step 2: Run** → fails.

**Step 3: Implement** `plan_pip_install` in `auto_fix.py`:

```python
def plan_pip_install(package: str, workspace_root) -> Action:
    """Emit an agents_parallel Action so the main session never sees pip chatter."""
    return Action(
        action_type="agents_parallel",
        agents=[{
            "agent_name": "tao-installer",
            "description": f"subagent: pip install {package}",
            "prompt": f"Run `pip install {package}` and report only final status.",
            "workspace_path": str(workspace_root),
        }],
        description=f"subagent: install {package}",
        estimated_minutes=5,
    )
```

Replace any in-line `subprocess.run(["pip", "install", ...])` call sites with a call to this. (Audit `auto_fix.py`.)

**Step 4: Run tests**
```
pytest tests/test_self_heal.py -v
```

**Step 5: Commit**
```
git commit -am "refactor: route pip installs through sub-agent to prevent context pollution"
```

---

## Task 8: tmux-Wrap Remote Execution

**Files:**
- Modify: `tao/compute/runpod_backend.py::run_remote` (add `use_tmux: bool = False` + `session_name`)
- Modify: `tao/experiment_launcher.py` (pass `use_tmux=True` for long jobs)
- Test: `tests/test_compute_backend.py`

**Step 1: Failing test**

```python
# tests/test_compute_backend.py — append
from unittest.mock import patch, MagicMock
from tao.compute.runpod_backend import RunPodBackend
from tao.config import Config


def test_run_remote_wraps_in_tmux_when_requested():
    be = RunPodBackend(Config())
    with patch.object(be, "get_pod_ssh_info", return_value={
            "mode": "basic", "host": "x", "port": 22, "user": "u"}), \
         patch.object(be, "_run_remote_via_script") as via:
        via.return_value = {"stdout": "", "stderr": "", "returncode": 0}
        be.run_remote("pod1", "python train.py", use_tmux=True, session_name="train1")
        sent = via.call_args[0][1]
        assert "tmux new-session -d -s train1" in sent
        assert "python train.py" in sent
```

**Step 2: Run** → fails (signature mismatch).

**Step 3: Implement** — modify `run_remote`:

```python
def run_remote(
    self, pod_id: str, command: str, timeout_sec: int = 600,
    use_tmux: bool = False, session_name: str = "tao",
) -> dict:
    if use_tmux:
        # SSH disconnect would otherwise kill the job; tmux survives.
        esc = command.replace("'", "'\"'\"'")
        command = (
            f"tmux kill-session -t {session_name} 2>/dev/null; "
            f"tmux new-session -d -s {session_name} '{esc}; echo __TAO_EXIT__=$?' && "
            f"tmux pipe-pane -t {session_name} 'cat >/tmp/{session_name}.log' && "
            f"while tmux has-session -t {session_name} 2>/dev/null; do sleep 5; done; "
            f"cat /tmp/{session_name}.log"
        )
    # ... rest unchanged
```

Update `experiment_launcher.py` call sites that launch training / eval to pass `use_tmux=True`.

**Step 4: Run full suite**
```
pytest tests/test_compute_backend.py -v
```

**Step 5: Commit**
```
git commit -am "feat: tmux-wrap long remote commands so SSH disconnect never kills jobs"
```

---

## Task 9: Contract-Driven Writing Gate + Codex Reviewer

**Files:**
- Create: `tao/orchestration/writing_gate.py`
- Test: `tests/test_writing_gate.py`
- Modify: `tao/orchestration/writing_artifacts.py` (invoke gate after `writing_sections`)

**Step 1: Failing tests**

```python
# tests/test_writing_gate.py
from tao.orchestration.writing_gate import verify_claims_against_contract, ClaimViolation
from tao.orchestration.contract import ResearchContract, Signal


def _contract():
    return ResearchContract(
        version="v1", hypothesis="h",
        success_signals=[Signal(id="s1", description="accuracy > 80 on CIFAR")],
        failure_signals=[Signal(id="f1", description="training diverges")],
        ablations=[],
    )


def test_claim_without_signal_is_violation():
    text = "We improve SOTA by 5 points on ImageNet-21k."  # no s1, no f1
    violations = verify_claims_against_contract(text, _contract())
    assert any(isinstance(v, ClaimViolation) for v in violations)


def test_claim_backed_by_signal_passes():
    text = "Our method reaches 82% accuracy on CIFAR [signal:s1]."
    assert verify_claims_against_contract(text, _contract()) == []
```

**Step 2: Run** → fails.

**Step 3: Implement**

```python
# tao/orchestration/writing_gate.py
"""Writing gate — every empirical claim must cite a contract signal.

Scans paper text for numbered results / comparative claims and flags any that
don't reference a [signal:sX] tag. Downstream of writing_sections, before
writing_integrate. Complements `latex_linter.py` (structural checks).
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from tao.orchestration.contract import ResearchContract


@dataclass
class ClaimViolation:
    claim: str
    reason: str


_CLAIM = re.compile(
    r"[^.\n]*?(?:improve|outperform|SOTA|\d+(?:\.\d+)?\s*%|\+\d+(?:\.\d+)?)[^.\n]*\.",
    re.IGNORECASE,
)
_SIGNAL_TAG = re.compile(r"\[signal:([a-zA-Z0-9_\-]+)\]")


def verify_claims_against_contract(
    text: str, contract: ResearchContract
) -> list[ClaimViolation]:
    ids = {s.id for s in contract.success_signals + contract.failure_signals + contract.ablations}
    violations: list[ClaimViolation] = []
    for match in _CLAIM.finditer(text):
        sentence = match.group(0).strip()
        tags = _SIGNAL_TAG.findall(sentence)
        if not tags:
            violations.append(ClaimViolation(claim=sentence, reason="no [signal:*] tag"))
            continue
        unknown = [t for t in tags if t not in ids]
        if unknown:
            violations.append(ClaimViolation(
                claim=sentence, reason=f"unknown signals: {unknown}"))
    return violations
```

**Step 4: Hook into `writing_artifacts.py`** — add a post_step to `build_writing_sections` (or inline in the writing_integrate builder) that reads every `writing/sections/*.md`, runs `verify_claims_against_contract`, and writes `writing/critique/claim_violations.json`. If violations exist, `state_machine.py` returns to `writing_sections` (bounded by `max_review_rounds` from Task 4).

**Step 5: Codex reviewer** — add a third agent to `build_review` in `team_actions.py`:

```python
agents = [
    {"name": "tao-supervisor", "description": "Supervisor structural review"},
    {"name": "tao-critic", "description": "Critical content review"},
    {"name": "tao-codex-reviewer", "description": "Codex/GPT-5 independent review; isolated context (contract + one section at a time)"},
]
```

Add `context_isolation=True` and `isolation_inputs=["contract", "section"]` on the `review` team.

**Step 6: Run tests**
```
pytest tests/test_writing_gate.py tests/test_action_builders.py -v
```

**Step 7: Commit**
```
git commit -am "feat: contract-grounded writing gate + Codex independent reviewer"
```

---

## Final: Full Regression

**Step 1:** Run the whole suite.
```
pytest tests/ -v
```
Expected: all tests green, including the new ~20 tests.

**Step 2:** Demo dry-run to ensure no import regressions.
```
python -m tao.demo
```
Expected: 20 stages traverse with no exceptions.

**Step 3:** Commit anything untracked from earlier tasks; open PR with body linking back to `context_is_all_you_need.md`.

---

## Verification Checklist (before marking complete)

- [ ] `plan/contract.json` + `plan/contract.lock` get created by the planning stage in `python -m tao.demo`.
- [ ] Attempting to overwrite a v1 contract raises `ContractError`; a v2 with changelog succeeds.
- [ ] `tests/test_state_machine.py::test_idea_validation_respects_max_review_rounds` green.
- [ ] `Action.team["context_isolation"]` = `True` for idea_debate, result_debate, review.
- [ ] `prefer_source_url("https://arxiv.org/pdf/2401.12345")` = e-print URL.
- [ ] `GeminiScout.available()` returns False cleanly when `gemini` CLI missing (no crash).
- [ ] `plan_pip_install` returns `agents_parallel` Action, never runs `pip` in-band.
- [ ] Long `run_remote` commands contain `tmux new-session -d -s`.
- [ ] Writing gate flags untagged empirical claims; tagged claims pass.
- [ ] Full `pytest tests/ -v` passes in < 10s.

---

## Deferred work (not yet wired)

The following items from this plan are intentionally *not* implemented yet
and have no pipeline consumer. Tracking here so they aren't lost.

- **Writing-gate state-machine loop-back.** `tao.orchestration.writing_gate.
  verify_claims_against_contract` ships as a library. It is not yet invoked
  by any stage, and a failed verification does not yet route back to
  `writing_sections`. Wiring it up requires: (a) a second-phase action that
  runs the gate after `writing_sections` completes (not a sibling agent in
  `skills_parallel` — see commit `d595b20` for why), (b) a state-machine
  branch that returns to `writing_sections` when violations exist, and (c)
  bounding that loop with `max_review_rounds`. Deferred because the correct
  second-phase action shape depends on how the orchestrator consumes it.

- **plan_pip_install wire-up.** `tao.auto_fix.plan_pip_install` exists as an
  Action planner but no caller dispatches it. The inline `pip install` path
  in `_fix_import` still runs in-band via `subprocess.run` because the
  self-heal circuit contract is synchronous. A future change should route
  self-heal through an async sub-agent so installs don't pollute the main
  orchestrator context.

- **Gemini scout wire-up.** `tao.scouts.gemini.GeminiScout` exists; no
  orchestrator path invokes it yet. `literature_search` still runs through
  the `tao-literature` skill only.
