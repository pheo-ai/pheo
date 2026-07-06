#!/usr/bin/env python3
"""PHEO platform harness for infra, kernel, persistence, and learning-loop checks.

This is intentionally outside the public happy-path examples. It is a developer/tester
tool for hardening the platform before design partners touch it.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
import venv
from dataclasses import dataclass, field
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pheo
from pheo import PendingReview


MEDICAL_RULES = """\
Task: identify breast-cancer papers that should be selected for downstream evidence review.

Select papers that are specifically about breast cancer and contain extractable clinical,
outcomes, biomarker, safety, epidemiology, or real-world evidence. Hold for judgment when
breast-cancer relevance is present but synthesis utility or extractable evidence is unclear.
Do not select generic background biology or papers without enough review context.
"""

MEDICAL_CASES = [
    (
        "P001",
        "HER2-low expression in early breast cancer",
        "Breast cancer cohort study with clinicopathological features, survival outcomes, biomarkers, and extractable subgroup evidence.",
        "select",
    ),
    (
        "P002",
        "Metastatic breast cancer treatment response markers",
        "Clinical metastatic breast cancer paper with response markers, patient outcomes, and extractable evidence.",
        "select",
    ),
    (
        "P003",
        "Breast cancer family history cohort",
        "Population cohort on family history and breast cancer risk with epidemiologic outcomes and review context.",
        "judgment",
    ),
    (
        "P004",
        "Serum trace elements in breast cancer subgroups",
        "Breast cancer subgroup study with biomarkers but limited downstream synthesis utility.",
        "judgment",
    ),
    (
        "P005",
        "Generic cell stress pathway review",
        "General molecular biology background review with only tangential breast cancer discussion and no extractable outcomes.",
        "reject",
    ),
]

FINANCE_RULES = """\
Task: review finance receipt exception notes before payment-related action.

Clear only when support is present and approval is identified. Hold or escalate when PO
support is missing, approval is unclear, duplicate risk exists, vendor bank details changed,
or budget owner evidence is absent. Do not release payment-ready language without support.
"""

FINANCE_CASES = [
    (
        "FIN-1007",
        "Northstar Office Supplies",
        "Receipt has missing PO match and approval owner is unclear.",
        "escalate",
    ),
    (
        "FIN-1011",
        "Vertex Travel",
        "Receipt appears duplicate of prior reimbursement and manager approval is missing.",
        "escalate",
    ),
    (
        "FIN-1020",
        "Orion Cloud Services",
        "Budget overage has IT approval but finance budget owner support is missing.",
        "judgment",
    ),
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    elapsed_ms: int
    details: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class Harness:
    def __init__(
        self,
        project: Path,
        report: Path,
        stress: int = 1,
        review_count: int = 5,
        ui_smoke: bool = False,
        wheel_smoke: bool = False,
    ):
        self.project = project
        self.report = report
        self.stress = max(1, stress)
        self.review_count = max(1, review_count)
        self.ui_smoke = ui_smoke
        self.wheel_smoke = wheel_smoke
        self.results: list[CheckResult] = []
        self.store = None
        self.medical = None
        self.finance = None
        self.reviewed_packet_ids: list[str] = []
        self.memory_probe: dict[str, Any] = {}

    def run(self) -> int:
        checks: list[tuple[str, Callable[[], dict[str, Any]]]] = [
            ("kernel_runtime_available", self.check_kernel_runtime),
            ("go_onboarding_and_seed_data", self.check_go_onboarding),
            ("workflow_isolation", self.check_workflow_isolation),
            ("grow_branch_score_and_gate", self.check_grow_branch_score_and_gate),
            ("govern_decision_receipt_tuple_pair", self.check_govern_decision_artifacts),
            ("idempotency_and_retry_safety", self.check_idempotency_and_retry_safety),
            ("cycle2_memory_application", self.check_cycle2_memory_application),
            ("persistence_reopen", self.check_persistence_reopen),
            ("count_taxonomy_is_clear", self.check_count_taxonomy),
            ("export_pack_integrity", self.check_export_pack_integrity),
        ]
        if self.ui_smoke:
            checks.append(("ui_server_e2e_smoke", self.check_ui_server_e2e))
        if self.wheel_smoke:
            checks.append(("clean_wheel_smoke", self.check_clean_wheel_smoke))
        for name, fn in checks:
            self._run_check(name, fn)
        self._write_report()
        self._print_summary()
        return 0 if all(item.ok for item in self.results) else 1

    def _run_check(self, name: str, fn: Callable[[], dict[str, Any]]) -> None:
        start = time.perf_counter()
        try:
            details = fn()
            self.results.append(CheckResult(name, True, int((time.perf_counter() - start) * 1000), details))
        except Exception as exc:  # pragma: no cover - harness diagnostic path
            self.results.append(
                CheckResult(
                    name,
                    False,
                    int((time.perf_counter() - start) * 1000),
                    error=f"{exc}\n{traceback.format_exc()}",
                )
            )

    def check_kernel_runtime(self) -> dict[str, Any]:
        import pheo_kernels

        runtime = pheo_kernels.KernelRuntime()
        methodology = runtime.synthesize_methodology(
            {"objective": "Review outputs before release."},
            [{"title": "Policy", "text": "Escalate missing approval and unsupported claims."}],
        )
        candidates = runtime.branch_candidates(
            "This output can proceed.",
            {"approval_status": "unclear", "support": "missing"},
            methodology,
        )
        scored = runtime.score_candidates(
            candidates,
            {"approval_status": "unclear", "support": "missing"},
            ["Escalate missing approval and unsupported claims."],
            methodology,
        )
        assert methodology.get("rules"), "kernel did not synthesize rules"
        assert len(candidates) >= 1, "kernel did not branch candidates"
        assert scored and scored[0].get("scores"), "kernel did not score candidates"
        return {"kernel_file": str(getattr(pheo_kernels, "__file__", "")), "scored": len(scored)}

    def check_go_onboarding(self) -> dict[str, Any]:
        self.store = pheo.open(self.project)
        self.medical = self.store.create_store(
            "harness_medical_review",
            business_area="life_sciences",
            goal="Review scientific evidence against approved criteria before downstream use.",
        )
        self.finance = self.store.create_store(
            "harness_finance_review",
            business_area="finance",
            goal="Review finance receipt exception notes before payment-related action.",
        )
        self.store.source.add_text("Medical review rules", MEDICAL_RULES, tags=["workflow_rules"], store_id=self.medical["id"])
        for case_id, title, text, target in MEDICAL_CASES:
            self.store.source.add_text(
                f"{case_id} {title}",
                text,
                tags=["harness_medical", case_id, f"target_{target}"],
                store_id=self.medical["id"],
            )
        self.store.source.add_text("Finance review rules", FINANCE_RULES, tags=["workflow_rules"], store_id=self.finance["id"])
        for case_id, vendor, text, target in FINANCE_CASES:
            self.store.source.add_text(
                f"{case_id} {vendor}",
                text,
                tags=["harness_finance", case_id, f"target_{target}"],
                store_id=self.finance["id"],
            )
        for workflow in (self.medical, self.finance):
            self.store.build_methodology(workflow["id"])
            self.store.review_methodology(workflow["id"], actor="harness")
            self.store.approve_methodology(workflow["id"], actor="harness")
            methodology = self.store.methodology(workflow["id"])
            assert methodology and methodology["status"] == "approved", f"{workflow['name']} methodology not approved"
            assert methodology.get("review_pairs"), f"{workflow['name']} has no onboarding review pairs"
        return {
            "medical_sources": len(self.store.corpus(self.medical["id"], active_only=True)),
            "finance_sources": len(self.store.corpus(self.finance["id"], active_only=True)),
            "medical_seed_pairs": len(self.store.methodology(self.medical["id"]).get("review_pairs") or []),
            "finance_seed_pairs": len(self.store.methodology(self.finance["id"]).get("review_pairs") or []),
        }

    def check_workflow_isolation(self) -> dict[str, Any]:
        medical_store = self.store.preference_store(self.medical["id"])
        finance_store = self.store.preference_store(self.finance["id"])
        medical_titles = {item["title"] for item in medical_store["corpus"]}
        finance_titles = {item["title"] for item in finance_store["corpus"]}
        assert not (medical_titles & finance_titles), "corpus title leakage across workflows"
        assert not finance_store["review_packets"], "finance workflow should not inherit medical review packets"
        assert not [item for item in finance_store["decisions"] if str(item.get("provenance", "")).startswith("human")], (
            "finance workflow inherited human decisions"
        )
        return {
            "medical_corpus": len(medical_titles),
            "finance_corpus": len(finance_titles),
            "shared_titles": sorted(medical_titles & finance_titles),
        }

    def check_grow_branch_score_and_gate(self) -> dict[str, Any]:
        point = self.store.review_point.create(
            "harness_medical_review",
            description=self.medical["objective"],
            dimensions=["criteria fit", "evidence support", "review action"],
            store_id=self.medical["id"],
        )
        packets = []
        for iteration in range(self.stress):
            for case_id, title, text, target in MEDICAL_CASES:
                candidates = [
                    {"generator": "harness_medical", "output": f"Include {case_id}: {title}\n\nEvidence: {text}"},
                    {"generator": "harness_medical", "output": f"Hold {case_id} for judgment.\n\nEvidence: {text}"},
                    {"generator": "harness_medical", "output": f"Do not select {case_id} unless extractable evidence is confirmed.\n\nEvidence: {text}"},
                ]
                packet = self.store.observe.output(
                    point["name"],
                    output=candidates[0]["output"],
                    context={"case_id": case_id, "target_bucket": target, "iteration": iteration},
                    source={"connector": "harness_medical", "case_id": case_id, "cycle_id": "cycle_1"},
                    candidates=candidates,
                    mode="explicit_capture",
                )
                packets.append(packet)
                assert packet.status == "pending_review", "raw output was not gated for review"
                assert packet.recommended and packet.recommended.get("scores"), "candidate was not scored"
                try:
                    packet.require_released()
                    raise AssertionError("require_released did not block pending packet")
                except PendingReview:
                    pass
        return {"packets": len(packets), "stress_multiplier": self.stress}

    def check_govern_decision_artifacts(self) -> dict[str, Any]:
        packets = self.store.preference_store(self.medical["id"])["review_packets"]
        assert packets, "no packets available for decision capture"
        pending = [item for item in packets if item["status"] == "pending_review"]
        assert pending, "no pending packets available for decision capture"
        reviewed_results = []
        for index, packet in enumerate(pending[: self.review_count]):
            payload = self.store._review_packet_payload(packet["id"])
            recommended = payload["recommended"]
            full_task = payload.get("run", {}).get("task") or {}
            context = full_task.get("context") or {}
            target_bucket = context.get("target_bucket") or ""
            if index == 0 or target_bucket == "select":
                action = "edit" if index == 0 or index % 2 == 0 else "approve"
                corrected = (
                    "Select this paper for evidence review because breast-cancer relevance and extractable evidence are present."
                    if action == "edit"
                    else ""
                )
                reason = "Reviewer confirmed disease fit and extractable evidence."
            elif target_bucket == "reject":
                action = "reject"
                corrected = ""
                reason = "Reviewer kept this out because it is background-only or lacks extractable evidence."
            else:
                action = "escalate"
                corrected = ""
                reason = "Reviewer needs expert judgment because criteria fit is uncertain."
            reviewed = self.store.review(
                packet["id"],
                selected_index=recommended["index"],
                action=action,
                corrected_output=corrected,
                reason=reason,
                author_id=f"harness-reviewer-{index}@example.com",
            )
            assert reviewed["tuple"]["reason"], "preference tuple reason missing"
            assert reviewed["receipt"], "release receipt missing"
            reviewed_results.append(reviewed)
            self.reviewed_packet_ids.append(packet["id"])
            if index == 0:
                self.memory_probe = {
                    "context": context,
                    "output": corrected or (recommended.get("output") or ""),
                    "reason": reason,
                }
        assert any(item["decision"]["provenance"] == "human_correction" for item in reviewed_results), "human correction provenance missing"
        after = self.store.preference_store(self.medical["id"])
        human_decisions = [item for item in after["decisions"] if str(item.get("provenance", "")).startswith("human")]
        human_pairs = [item for item in after["preference_pairs"] if str(item.get("provenance", "")).startswith("human")]
        assert len(human_decisions) >= len(reviewed_results), "human decisions not stored"
        assert len(human_pairs) >= len(reviewed_results), "human preference pairs not stored"
        return {"reviewed_packets": len(reviewed_results), "human_decisions": len(human_decisions), "human_pairs": len(human_pairs)}

    def check_idempotency_and_retry_safety(self) -> dict[str, Any]:
        assert self.reviewed_packet_ids, "no reviewed packet available for idempotency check"
        packet_id = self.reviewed_packet_ids[0]
        before = self.store.preference_store(self.medical["id"])
        replay = self.store.review(
            packet_id,
            selected_index=0,
            action="approve",
            reason="Accidental retry should not create a new decision.",
            author_id="retry@example.com",
        )
        after = self.store.preference_store(self.medical["id"])
        assert len(before["decisions"]) == len(after["decisions"]), "retry created duplicate decision rows"
        assert len(before["preference_tuples"]) == len(after["preference_tuples"]), "retry created duplicate tuple rows"
        assert len(before["preference_pairs"]) == len(after["preference_pairs"]), "retry created duplicate preference pairs"
        assert len(before["release_receipts"]) == len(after["release_receipts"]), "retry created duplicate release receipts"
        assert replay.get("packet", {}).get("status") == "reviewed", "retry did not return reviewed packet"
        return {
            "packet_id": packet_id,
            "decision_rows": len(after["decisions"]),
            "pair_rows": len(after["preference_pairs"]),
            "receipt_rows": len(after["release_receipts"]),
        }

    def check_cycle2_memory_application(self) -> dict[str, Any]:
        memory = self.store.memory(self.medical["id"])
        assert memory.get("entries"), "judgment memory did not compile from human decision"
        probe_context = dict(self.memory_probe.get("context") or {})
        probe_output = self.memory_probe.get("output") or "Select this paper because reviewer confirmed disease fit and extractable evidence."
        packet = self.store.observe.output(
            "harness_medical_review",
            output=probe_output,
            context=probe_context,
            source={"connector": "harness_medical", "cycle_id": "cycle_2", "case_id": "P099"},
            candidates=[
                {"generator": "harness_medical", "output": probe_output},
                {"generator": "harness_medical", "output": "Hold P099 for judgment until disease fit and extractable evidence are confirmed."},
                {"generator": "harness_medical", "output": "Exclude P099 as background only."},
            ],
            mode="explicit_capture",
            memory=memory,
        )
        signals = [(candidate.get("scores") or {}).get("judgment_memory") or {} for candidate in packet.candidates]
        applied = [signal for signal in signals if signal.get("applied")]
        assert applied, "cycle 2 did not apply judgment memory"
        return {
            "memory_entries": len(memory["entries"]),
            "applied": len(applied),
            "best_signal": applied[0].get("suggestion"),
            "similarity": applied[0].get("similarity"),
        }

    def check_persistence_reopen(self) -> dict[str, Any]:
        reopened = pheo.open(self.project)
        workflow = reopened.get_workflow(self.medical["id"])
        store = reopened.preference_store(workflow["id"])
        human_decisions = [item for item in store["decisions"] if str(item.get("provenance", "")).startswith("human")]
        assert human_decisions, "human decisions did not persist after reopen"
        assert store["review_packets"], "review packets did not persist after reopen"
        assert reopened.memory(workflow["id"]).get("entries"), "memory did not recompile after reopen"
        return {
            "workflow": workflow["name"],
            "packets": len(store["review_packets"]),
            "human_decisions": len(human_decisions),
        }

    def check_count_taxonomy(self) -> dict[str, Any]:
        store = self.store.preference_store(self.medical["id"])
        decisions = store["decisions"]
        pairs = store["preference_pairs"]
        human_decisions = [item for item in decisions if str(item.get("provenance", "")).startswith("human")]
        seed_decisions = [item for item in decisions if not str(item.get("provenance", "")).startswith("human")]
        human_pairs = [item for item in pairs if str(item.get("provenance", "")).startswith("human")]
        seed_pairs = [item for item in pairs if not str(item.get("provenance", "")).startswith("human")]
        assert len(decisions) == len(human_decisions) + len(seed_decisions), "decision taxonomy does not add up"
        assert len(pairs) == len(human_pairs) + len(seed_pairs), "preference-pair taxonomy does not add up"
        assert human_decisions, "human decision count is zero"
        assert seed_decisions, "seed decision count is zero"
        return {
            "all_decisions": len(decisions),
            "human_decisions": len(human_decisions),
            "seed_decisions": len(seed_decisions),
            "all_pairs": len(pairs),
            "human_pairs": len(human_pairs),
            "seed_pairs": len(seed_pairs),
        }

    def check_export_pack_integrity(self) -> dict[str, Any]:
        pack = self.store.memory_pack(self.medical["id"], organic_only=True)
        artifacts = pack["artifacts"]
        assert artifacts["release_receipts"], "organic export missing release receipts"
        assert artifacts["preference_tuples"], "organic export missing preference tuples"
        assert artifacts["preference_pairs"], "organic export missing preference pairs"
        assert artifacts["judgment_memory"].get("entries"), "organic export missing judgment memory"
        assert pack["workflow_graph"].get("schema"), "workflow graph missing schema"
        return {
            "receipts": len(artifacts["release_receipts"]),
            "tuples": len(artifacts["preference_tuples"]),
            "pairs": len(artifacts["preference_pairs"]),
            "memory_entries": len(artifacts["judgment_memory"]["entries"]),
        }

    def check_ui_server_e2e(self) -> dict[str, Any]:
        from pheo.api import create_handler

        server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(str(self.project)))
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{port}"
        try:
            home = _http_get(f"{base}/")
            assert "PHEO Go" in home and "PHEO Grow" in home and "Decisions" in home, "home UI missing flow labels"
            workflows = _http_json(f"{base}/v1/workflows")
            assert workflows.get("workflows"), "UI API did not return workflows"
            packet_id = self.reviewed_packet_ids[0]
            review_html = _http_get(f"{base}/review/{packet_id}")
            assert "Review decision" in review_html and "Quality radar" in review_html, "review UI did not render"
            payload = _http_json(f"{base}/v1/workflows/{self.medical['id']}/preference-store")
            assert payload.get("review_packets"), "preference-store API missing packets"
            return {
                "port": port,
                "workflows": len(workflows.get("workflows") or []),
                "packets": len(payload.get("review_packets") or []),
            }
        finally:
            server.shutdown()
            server.server_close()

    def check_clean_wheel_smoke(self) -> dict[str, Any]:
        root = ROOT
        work = Path(tempfile.mkdtemp(prefix="pheo-wheel-smoke-"))
        wheel_dir = work / "wheels"
        wheel_dir.mkdir(parents=True, exist_ok=True)
        build_venv = work / "build-venv"
        venv.EnvBuilder(with_pip=True).create(build_venv)
        build_python = _venv_python(build_venv)
        _run([str(build_python), "-m", "pip", "install", "setuptools>=68", "wheel"], cwd=work)
        _run(
            [str(build_python), "-m", "pip", "wheel", str(root), "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheel_dir)],
            cwd=root,
        )
        wheels = sorted(wheel_dir.glob("pheo-*.whl"))
        assert wheels, "wheel build did not create a pheo wheel"
        venv_dir = work / "venv"
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        python = _venv_python(venv_dir)
        _run([str(python), "-m", "pip", "install", str(wheels[-1])], cwd=work)
        cli = _run([str(python), "-m", "pheo.cli", "--cli"], cwd=work)
        assert "PHEO Go" in cli.stdout and "PHEO Grow" in cli.stdout, "installed CLI did not print PHEO guide"
        smoke = _run(
            [
                str(python),
                "-c",
                (
                    "import tempfile, pheo, pheo_kernels; "
                    "r=pheo_kernels.KernelRuntime(); "
                    "m=r.synthesize_methodology({'objective':'Review outputs'}, [{'title':'Policy','text':'Escalate missing support.'}]); "
                    "assert m['rules']; "
                    "s=pheo.open(tempfile.mkdtemp()); "
                    "w=s.create_store('smoke', business_area='finance'); "
                    "s.source.add_text('Policy','Escalate missing support.', store_id=w['id']); "
                    "s.review_methodology(w['id']); s.approve_methodology(w['id']); "
                    "print('INSTALLED_WHEEL_SMOKE_OK')"
                ),
            ],
            cwd=work,
        )
        assert "INSTALLED_WHEEL_SMOKE_OK" in smoke.stdout, "installed wheel smoke failed"
        return {"wheel": wheels[-1].name, "workdir": str(work)}

    def _write_report(self) -> None:
        self.report.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "pheo.platform_harness.v1",
            "project": str(self.project),
            "stress": self.stress,
            "ok": all(item.ok for item in self.results),
            "results": [item.__dict__ for item in self.results],
        }
        self.report.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _print_summary(self) -> None:
        print("\nPHEO platform harness")
        print(f"Project: {self.project}")
        print(f"Report:  {self.report}")
        print("")
        for item in self.results:
            status = "PASS" if item.ok else "FAIL"
            print(f"{status:4} {item.name:<36} {item.elapsed_ms:>5} ms")
            if not item.ok:
                print(item.error)
        print("")
        print("Result:", "PASS" if all(item.ok for item in self.results) else "FAIL")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PHEO platform hardening harness.")
    parser.add_argument("--project", default="", help="Project directory. Defaults to a temporary harness project.")
    parser.add_argument("--report", default="", help="JSON report path. Defaults to <project>/platform-harness-report.json.")
    parser.add_argument("--reset", action="store_true", help="Delete the project directory before running.")
    parser.add_argument("--stress", type=int, default=1, help="Repeat observed case batches N times.")
    parser.add_argument("--review-count", type=int, default=5, help="Number of pending packets to review during Govern.")
    parser.add_argument("--ui-smoke", action="store_true", help="Start the local UI server and verify the browser-facing paths.")
    parser.add_argument("--wheel-smoke", action="store_true", help="Build/install the wheel in a fresh venv and run clean-package checks.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = Path(args.project) if args.project else Path(tempfile.mkdtemp(prefix="pheo-platform-harness-"))
    if args.reset and project.exists():
        shutil.rmtree(project)
    project.mkdir(parents=True, exist_ok=True)
    report = Path(args.report) if args.report else project / "platform-harness-report.json"
    return Harness(
        project,
        report,
        stress=args.stress,
        review_count=args.review_count,
        ui_smoke=args.ui_smoke,
        wheel_smoke=args.wheel_smoke,
    ).run()


def _http_get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.read().decode("utf-8")


def _http_json(url: str) -> dict[str, Any]:
    return json.loads(_http_get(url))


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            f"  {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


if __name__ == "__main__":
    raise SystemExit(main())
