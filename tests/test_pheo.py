import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pheo
from pheo import PendingReview
from pheo.api import create_handler
from pheo.core.endpoint import chat_completions_url, safe_endpoint
from pheo.integrations.langchain import PheoReviewUnavailable, pheo_review_node, with_pheo_review
from pheo.openapi import OPENAPI_SPEC
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class PheoTest(unittest.TestCase):
    def _ap_review_store(self, tempdir):
        store = pheo.open(tempdir)
        workflow = store.create_store(
            "ap_invoice_exception_review",
            business_area="finance",
            description="Review AP invoice exception summaries.",
        )
        store.source.add_text("AP policy", "Human review is required before AP exception output is released.")
        store.review_methodology(workflow["id"])
        store.approve_methodology(workflow["id"])
        store.review_point.create("ap_exception_review", description="Review AP exception summaries.")
        return store, workflow

    def test_bundled_kernel_runtime_imports(self):
        import pheo_kernels

        runtime = pheo_kernels.KernelRuntime()
        self.assertTrue(hasattr(runtime, "synthesize_methodology"))
        self.assertTrue(hasattr(runtime, "branch_candidates"))
        self.assertTrue(hasattr(runtime, "score_candidates"))
        self.assertTrue(str(pheo_kernels.__file__).endswith("pheo_kernels/__init__.py"))

    def test_checked_in_openapi_spec_matches_runtime_spec(self):
        root = Path(__file__).resolve().parents[1]
        checked_in = json.loads((root / "openapi.json").read_text(encoding="utf-8"))
        self.assertEqual(checked_in, OPENAPI_SPEC)
        self.assertIn("/v1/stores/{store}/review-points/{point}/observations", checked_in["paths"])
        self.assertIn("/v1/review-packets/{packet}/reviews", checked_in["paths"])

    def test_langchain_adapter_wraps_existing_runnable(self):
        class ExistingRunnable:
            def invoke(self, payload, **kwargs):
                return {
                    "final_answer": f"Invoice {payload['invoice_id']} can proceed.",
                    "run_id": f"lc-{payload['invoice_id']}",
                }

        with tempfile.TemporaryDirectory() as tempdir:
            store, _workflow = self._ap_review_store(tempdir)

            reviewed_chain = with_pheo_review(
                ExistingRunnable(),
                store=store,
                review_point="ap_exception_review",
                output_key="final_answer",
                cycle_id="cycle_1",
            )
            result = reviewed_chain.invoke({"invoice_id": "AP-1007", "approval_status": "unclear"})

            self.assertEqual(result.raw["run_id"], "lc-AP-1007")
            self.assertEqual(result.status, "pending_review")
            self.assertIn("/review/", result.review_url)
            with self.assertRaises(PendingReview):
                result.require_released()

            store.review(
                result.outcome.id,
                selected_index=result.outcome.recommended["index"],
                action="edit",
                corrected_output="Invoice AP-1007 should be escalated until approval is clear.",
                reason="Approval status was unclear.",
                author_id="controller@example.com",
            )
            self.assertIn("escalated", result.require_released())

    def test_langchain_adapter_handles_structured_async_and_callable_memory(self):
        class StructuredRunnable:
            async def ainvoke(self, payload, **kwargs):
                return {
                    "structured_response": {
                        "invoice_id": payload["invoice_id"],
                        "decision": "hold",
                        "reason": "approval status is unclear",
                    },
                    "run_id": f"async-{payload['invoice_id']}",
                }

        with tempfile.TemporaryDirectory() as tempdir:
            store, _workflow = self._ap_review_store(tempdir)
            memory_calls = []

            def memory():
                memory_calls.append("called")
                return {"entries": []}

            reviewed_chain = with_pheo_review(
                StructuredRunnable(),
                store=store,
                review_point="ap_exception_review",
                cycle_id="cycle_2",
                memory=memory,
            )
            result = asyncio.run(reviewed_chain.ainvoke({"invoice_id": "AP-1042", "approval_status": "unclear"}))

            self.assertEqual(memory_calls, ["called"])
            self.assertIn("approval status is unclear", result.outcome.observed_output)
            source = result.outcome.get("observation")["source"]
            self.assertEqual(source["connector"], "langchain")
            self.assertEqual(source["trace_id"], "async-AP-1042")

    def test_langchain_adapter_flattens_content_blocks(self):
        class Message:
            content_blocks = [{"type": "text", "text": "Readable hold text"}, {"type": "text", "text": "Second line"}]

        class ExistingRunnable:
            def invoke(self, payload, **kwargs):
                return {"messages": [Message()], "run_id": "lc-content-blocks"}

        with tempfile.TemporaryDirectory() as tempdir:
            store, _workflow = self._ap_review_store(tempdir)
            result = with_pheo_review(
                ExistingRunnable(),
                store=store,
                review_point="ap_exception_review",
            ).invoke({"invoice_id": "AP-1043"})

            self.assertEqual(result.outcome.observed_output, "Readable hold text\nSecond line")

    def test_langchain_adapter_fails_closed_when_review_observe_fails(self):
        class ExistingRunnable:
            def invoke(self, payload, **kwargs):
                return {"final_answer": "Invoice AP-1044 can proceed.", "run_id": "lc-observe-down"}

        with tempfile.TemporaryDirectory() as tempdir:
            store, _workflow = self._ap_review_store(tempdir)
            reviewed = with_pheo_review(ExistingRunnable(), store=store, review_point="ap_exception_review")
            with patch.object(store.observe, "output", side_effect=RuntimeError("store unavailable")):
                result = reviewed.invoke({"invoice_id": "AP-1044"})

            self.assertEqual(result.raw["run_id"], "lc-observe-down")
            self.assertEqual(result.status, "review_unavailable")
            self.assertEqual(result.review_url, "")
            with self.assertRaises(PheoReviewUnavailable):
                result.require_released()

    def test_langchain_adapter_stream_has_clear_error(self):
        class ExistingRunnable:
            def invoke(self, payload, **kwargs):
                return {"final_answer": "Invoice AP-1045 can proceed."}

        with tempfile.TemporaryDirectory() as tempdir:
            store, _workflow = self._ap_review_store(tempdir)
            reviewed = with_pheo_review(ExistingRunnable(), store=store, review_point="ap_exception_review")
            with self.assertRaisesRegex(NotImplementedError, "Streaming is not supported"):
                reviewed.stream({"invoice_id": "AP-1045"})

    def test_langgraph_review_node_is_idempotent_and_uses_slim_context(self):
        with tempfile.TemporaryDirectory() as tempdir:
            store, workflow = self._ap_review_store(tempdir)
            node = pheo_review_node(
                store=store,
                review_point="ap_exception_review",
                output_key="final_answer",
                cycle_id="cycle_1",
            )

            state = {
                "invoice_id": "AP-2001",
                "vendor": "Northstar Office Supplies",
                "final_answer": "Invoice AP-2001 can proceed even though approval is unclear.",
                "internal_tool_trace": {"sql": "select * from secret_table"},
                "messages": [{"role": "assistant", "content": "internal chatter"}],
            }
            update = node(state)
            resumed_update = node({**state, **update})

            self.assertIn("pheo_review", update)
            self.assertIn("/review/", update["pheo_review"]["review_url"])
            self.assertEqual(update["pheo_review"]["outcome_id"], resumed_update["pheo_review"]["outcome_id"])
            self.assertEqual(len(store.preference_store(workflow["id"])["review_packets"]), 1)
            self.assertNotIn("released_output", update)

            payload = store._review_packet_payload(update["pheo_review"]["outcome_id"])
            context = payload["observation"]["context"]
            self.assertEqual(context["invoice_id"], "AP-2001")
            self.assertEqual(context["vendor"], "Northstar Office Supplies")
            self.assertNotIn("internal_tool_trace", context)
            self.assertNotIn("messages", context)

            store.review(
                update["pheo_review"]["outcome_id"],
                selected_index=payload["recommended"]["index"],
                action="edit",
                corrected_output="Invoice AP-2001 should be held until approval is clear.",
                reason="Approval was unclear.",
                author_id="controller@example.com",
            )
            released_update = node({**state, **update})
            self.assertIn("released_output", released_update)
            self.assertIn("held until approval", released_update["released_output"])

    def test_review_point_observe_review_exports_graph(self):
        with tempfile.TemporaryDirectory() as tempdir:
            store = pheo.open(tempdir)
            workflow = store.create_store(
                "finance_review",
                business_area="finance",
                description="Review AI-assisted variance explanations before close packet use.",
            )
            store.source.add_text(
                "Controller rule",
                "Do not accept vague seasonality explanations. Require source support, owner note, and escalation when support is missing.",
            )
            store.review_methodology(workflow["id"], actor="controller@example.com", note="Rules reviewed for test.")
            approved_methodology = store.approve_methodology(workflow["id"], actor="controller@example.com", note="Rules approved for test review.")
            self.assertEqual(approved_methodology["approved_by"], "controller@example.com")
            self.assertTrue(approved_methodology["approved_at"])
            events = store.preference_store(workflow["id"])["methodology_events"]
            self.assertEqual([event["event_type"] for event in events], ["approved", "reviewed", "drafted"])
            self.assertEqual(events[0]["actor"], "controller@example.com")
            self.assertEqual(
                events[-1]["metadata"]["goal_snapshot"],
                "Review AI-assisted variance explanations before close packet use.",
            )
            connection = store.connection.add_endpoint(
                "finance_agent_endpoint",
                "https://openrouter.ai/api/v1",
                model="openai/gpt-4o-mini",
            )
            point = store.review_point.create(
                "variance_explanation_review",
                description="Review variance explanations before they enter the close packet.",
                dimensions=["evidence grounding", "business logic", "escalation risk", "clarity"],
                connection=connection["name"],
            )
            store.review_channel.email(point["name"], "controller@example.com")

            with patch.dict(
                os.environ,
                {
                    "PHEO_SMTP_HOST": "",
                    "PHEO_SMTP_USERNAME": "",
                    "PHEO_SMTP_PASSWORD": "",
                    "PHEO_EMAIL_FROM": "",
                },
                clear=False,
            ):
                packet = store.observe(
                    point["name"],
                    output="Revenue declined due to seasonality.",
                    context={"account": "Revenue", "variance": "-12%", "period": "May 2026"},
                    source={"connector": "unit_test_agent", "trace_id": "trace-1"},
                )
            self.assertEqual(packet["review_point"]["name"], "variance_explanation_review")
            self.assertGreaterEqual(len(packet["candidates"]), 3)
            self.assertTrue(packet["recommended"])
            self.assertEqual(packet["review_url"], f"/review/{packet['packet']['id']}")
            self.assertEqual(packet["packet"]["delivery"]["notifications"]["email"]["status"], "not_configured")

            decision = store.review(
                packet["packet"]["id"],
                selected_index=packet["recommended"]["index"],
                reason="Best because it avoids unsupported seasonality and asks for review.",
            )
            self.assertEqual(decision["packet"]["status"], "reviewed")

            out = Path(tempdir) / "pack"
            pack = store.export.memory_pack(out)
            self.assertTrue((out / "workflow.graph.json").exists())
            self.assertTrue((out / "observations.jsonl").exists())
            self.assertEqual(len(pack["artifacts"]["connections"]), 1)
            self.assertEqual(len(pack["artifacts"]["review_points"]), 1)
            self.assertEqual(len(pack["artifacts"]["observations"]), 1)
            self.assertTrue(any(node["type"] == "connection" for node in pack["workflow_graph"]["nodes"]))
            self.assertTrue(any(edge["type"] == "feeds_review_point" for edge in pack["workflow_graph"]["edges"]))
            self.assertTrue(any(node["type"] == "review_point" for node in pack["workflow_graph"]["nodes"]))

    def test_review_email_uses_smtp_configuration(self):
        class FakeSMTP:
            instances = []

            def __init__(self, host, port, timeout=30):
                self.host = host
                self.port = port
                self.timeout = timeout
                self.started_tls = False
                self.login_args = None
                self.messages = []
                self.__class__.instances.append(self)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def starttls(self, context=None):
                self.started_tls = True

            def login(self, username, password):
                self.login_args = (username, password)

            def send_message(self, message):
                self.messages.append(message)

        with tempfile.TemporaryDirectory() as tempdir:
            env = {
                "PHEO_SMTP_HOST": "smtp.zoho.eu",
                "PHEO_SMTP_PORT": "587",
                "PHEO_SMTP_SECURITY": "tls",
                "PHEO_SMTP_USERNAME": "reviews@example.com",
                "PHEO_SMTP_PASSWORD": "secret",
                "PHEO_EMAIL_FROM": "reviews@example.com",
                "PHEO_REVIEW_BASE_URL": "http://127.0.0.1:8787",
            }
            with patch.dict(os.environ, env, clear=False), patch("pheo.core.notifications.smtplib.SMTP", FakeSMTP):
                store = pheo.open(tempdir)
                workflow = store.create_store("coaching_review", business_area="coaching")
                store.source.add_text("Rule", "Preserve agency and require human review.")
                store.review_methodology(workflow["id"])
                store.approve_methodology(workflow["id"])
                point = store.review_point.create("coaching_review_point", description="Review coaching outputs.")
                store.review_channel.email(point["name"], "reviewer@example.com", subject="Review ready")

                packet = store.observe(point["name"], "Pause and ask the client what outcome they want.")

            self.assertEqual(packet["packet"]["delivery"]["notifications"]["email"]["status"], "sent")
            self.assertEqual(len(FakeSMTP.instances), 1)
            smtp = FakeSMTP.instances[0]
            self.assertEqual((smtp.host, smtp.port), ("smtp.zoho.eu", 587))
            self.assertTrue(smtp.started_tls)
            self.assertEqual(smtp.login_args, ("reviews@example.com", "secret"))
            self.assertIn("http://127.0.0.1:8787/review/", smtp.messages[0].get_content())

    def test_review_notification_adapters_use_customer_channels(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"{}"

        requests = []

        def fake_urlopen(request, timeout=30):
            requests.append(
                {
                    "url": request.full_url,
                    "headers": dict(request.header_items()),
                    "body": json.loads(request.data.decode("utf-8")),
                }
            )
            return FakeResponse()

        with tempfile.TemporaryDirectory() as tempdir:
            env = {
                "PHEO_REVIEW_WEBHOOK_URL": "https://hooks.example/review",
                "PHEO_SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/test",
                "PHEO_TELEGRAM_BOT_TOKEN": "telegram-token",
            }
            with patch.dict(os.environ, env, clear=False), patch("pheo.core.notifications.request.urlopen", fake_urlopen):
                store = pheo.open(tempdir)
                workflow = store.create_store("support_review", business_area="support")
                store.source.add_text("Rule", "Require human review before sending support replies.")
                store.review_methodology(workflow["id"])
                store.approve_methodology(workflow["id"])
                point = store.review_point.create("support_reply_review", description="Review support replies.")
                store.review_channel.webhook(point["name"], url_env="PHEO_REVIEW_WEBHOOK_URL")
                store.review_channel.slack(point["name"])
                store.review_channel.telegram(point["name"], chat_id="12345")

                packet = store.observe(point["name"], "Promise an immediate refund without checking policy.")

            notifications = packet["packet"]["delivery"]["notifications"]
            self.assertEqual(notifications["webhook"]["status"], "sent")
            self.assertEqual(notifications["slack"]["status"], "sent")
            self.assertEqual(notifications["telegram"]["status"], "sent")
            self.assertEqual(len(requests), 3)
            self.assertTrue(any(item["url"] == "https://hooks.example/review" for item in requests))
            self.assertTrue(any(item["url"] == "https://hooks.slack.com/services/test" for item in requests))
            self.assertTrue(any(item["url"].startswith("https://api.telegram.org/bot") for item in requests))

    def test_observe_requires_approved_review_rules(self):
        with tempfile.TemporaryDirectory() as tempdir:
            store = pheo.open(tempdir)
            workflow = store.create_store("support_review", business_area="support")
            store.source.add_text("Support rule", "Human review is required before customer-facing claims.")
            store.review_point.create("support_reply_review", description="Review support replies before send.")

            with self.assertRaisesRegex(ValueError, "Approve review rules"):
                store.observe("support_reply_review", "Promise an immediate refund without checking policy.")

            store.review_methodology(workflow["id"])
            store.approve_methodology(workflow["id"])
            packet = store.observe("support_reply_review", "Ask for order evidence before promising a refund.")
            self.assertEqual(packet["status"], "pending_review")

    def test_methodology_review_gate_blocks_scoring_until_approved(self):
        with tempfile.TemporaryDirectory() as tempdir:
            store = pheo.open(tempdir)
            workflow = store.create_store("finance_review", business_area="finance")
            store.source.add_text("Controller rule", "Require evidence before close commentary is used.")
            review = store.review_methodology(workflow["id"])
            self.assertEqual(review["gate"]["status"], "draft")
            self.assertFalse(review["gate"]["approved"])
            self.assertEqual(review["human_review"]["goal"], "")
            self.assertIn("No review goal/protocol", review["human_review"]["goal_warning"])

            run = store.run_candidates(
                workflow["id"],
                {"goal": "Review variance explanation"},
                [{"output": "Revenue declined due to seasonality."}],
            )
            with self.assertRaisesRegex(ValueError, "Approve review rules"):
                store.score_run(run["id"])

            rejected = store.reject_methodology(workflow["id"], actor="controller@example.com", note="Rules are too vague.")
            self.assertEqual(rejected["status"], "rejected")
            with self.assertRaisesRegex(ValueError, "draft status"):
                store.approve_methodology(workflow["id"], actor="controller@example.com")

            store.update_methodology(
                workflow["id"],
                rules=["Require evidence and owner context before close commentary is used."],
                avoid=["Do not accept vague seasonality explanations."],
                actor="controller@example.com",
            )
            store.approve_methodology(workflow["id"], actor="controller@example.com")
            scored = store.score_run(run["id"])
            self.assertTrue(scored["candidates"][0]["scores"])

    def test_methodology_approval_is_idempotent_and_edits_return_to_draft(self):
        with tempfile.TemporaryDirectory() as tempdir:
            store = pheo.open(tempdir)
            workflow = store.create_store("support_review", business_area="support")
            store.source.add_text("Support rule", "Human review is required before customer-facing claims.")
            store.review_point.create("support_reply_review", description="Review support replies before send.")
            store.build_methodology(workflow["id"])

            with self.assertRaisesRegex(ValueError, "pheo methodology review --workflow support_review --format human"):
                store.approve_methodology(workflow["id"], actor="lead@example.com")
            store.review_methodology(workflow["id"], actor="lead@example.com")
            first = store.approve_methodology(workflow["id"], actor="lead@example.com")
            after_first = store.preference_store(workflow["id"])
            second = store.approve_methodology(workflow["id"], actor="lead@example.com")
            after_second = store.preference_store(workflow["id"])

            self.assertEqual(first["id"], second["id"])
            self.assertEqual(len(after_first["preference_pairs"]), len(after_second["preference_pairs"]))
            self.assertEqual(len(after_first["decisions"]), len(after_second["decisions"]))

            edited = store.update_methodology(
                workflow["id"],
                summary="Review customer-facing support replies before use.",
                rules=["Require policy support before promising refunds."],
                avoid=["Do not promise refunds without checking policy."],
                actor="lead@example.com",
            )
            self.assertEqual(edited["status"], "draft")
            with self.assertRaisesRegex(ValueError, "Approve review rules"):
                store.observe("support_reply_review", "Promise a refund immediately.")

    def test_hybrid_classical_kernels_build_and_score_without_llm(self):
        with tempfile.TemporaryDirectory() as tempdir:
            store = pheo.open(tempdir)
            workflow = store.create_store(
                "finance_close_review",
                business_area="finance",
                description="Review AI-assisted variance explanations before close packet use.",
            )
            store.source.add_text(
                "Close policy",
                (
                    "Variance explanations must cite source support and owner notes. "
                    "Unsupported seasonality explanations should be escalated. "
                    "Reviewers should separate business logic from speculation before approval."
                ),
            )
            methodology = store.build_methodology(workflow["id"])
            self.assertTrue(any("Ground outputs" in rule or "Variance explanations" in rule for rule in methodology["rules"]))
            self.assertGreaterEqual(len(methodology["review_pairs"]), 25)
            store.review_methodology(workflow["id"])
            store.approve_methodology(workflow["id"])
            store.review_point.create("variance_review", description="Review close variance explanation.")

            packet = store.observe("variance_review", "Revenue fell because of seasonality and should be accepted.")
            run = packet["run"]
            self.assertEqual(len(run["candidates"]), 3)
            self.assertEqual(
                sorted(candidate["generator"] for candidate in run["candidates"]),
                ["observed_output", "pheo", "pheo"],
            )
            self.assertEqual(sum(1 for candidate in run["candidates"] if candidate["recommended"]), 1)
            self.assertTrue(all("mean_score" in candidate["scores"] for candidate in run["candidates"]))
            self.assertTrue(all(candidate["scores"].get("explanation", {}).get("summary") for candidate in run["candidates"]))
            self.assertTrue(all(candidate["scores"]["explanation"].get("drivers") for candidate in run["candidates"]))
            self.assertTrue(any(driver.get("linked_rule") for candidate in run["candidates"] for driver in candidate["scores"]["explanation"]["drivers"]))
            prepared_candidates = [candidate for candidate in run["candidates"] if candidate["generator"] == "pheo"]
            for candidate in prepared_candidates:
                self.assertNotIn("Methodology signal", candidate["output"])
                self.assertNotIn("Keep close to", candidate["output"])

    def test_human_edit_creates_pairs_against_all_original_candidates(self):
        with tempfile.TemporaryDirectory() as tempdir:
            store = pheo.open(tempdir)
            workflow = store.create_store("clinical_review", business_area="healthcare")
            store.source.add_text("Clinical rule", "Human review is required before clinical summaries are trusted.")
            store.review_methodology(workflow["id"])
            store.approve_methodology(workflow["id"])
            store.review_point.create("clinical_output_review", description="Review clinical summary before use.")
            packet = store.observe("clinical_output_review", "The summary is final and ready for use without review.")

            before_pairs = len(store.preference_store(workflow["id"])["preference_pairs"])
            result = store.review(
                packet["packet"]["id"],
                selected_index=packet["recommended"]["index"],
                action="edit",
                corrected_output="Corrected summary: keep it as a draft, cite evidence, and require human approval.",
                reason="Human corrected the review boundary.",
                author_id="clinician@example.com",
            )
            after = store.preference_store(workflow["id"])
            new_pairs = [pair for pair in after["preference_pairs"] if pair["provenance"] == "human_correction"]
            self.assertEqual(len(new_pairs), len(packet["run"]["candidates"]))
            self.assertEqual(len(after["preference_pairs"]), before_pairs + len(packet["run"]["candidates"]))
            self.assertEqual(result["decision"]["provenance"], "human_correction")

    def test_decorator_wraps_existing_agent_output(self):
        with tempfile.TemporaryDirectory() as tempdir:
            store = pheo.open(tempdir)
            workflow = store.create_store("support_review", business_area="support")
            store.source.add_text("Support rule", "Human review is required before customer-facing claims.")
            store.review_methodology(workflow["id"])
            store.approve_methodology(workflow["id"])
            store.review_point.create("support_reply_review", description="Review support replies before send.")

            @store.review_point("support_reply_review")
            def draft_reply(ticket):
                return f"We can resolve {ticket['issue']} immediately without review."

            packet = draft_reply({"issue": "billing dispute"})
            self.assertEqual(packet["status"], "pending_review")
            self.assertEqual(packet["observation"]["source"]["connector"], "python_decorator")
            self.assertEqual(packet.observed_output, "We can resolve billing dispute immediately without review.")
            self.assertTrue(packet.recommended_output)
            with self.assertRaises(PendingReview):
                packet.require_released()

    def test_sdk_end_to_end_exports_memory_pack(self):
        with tempfile.TemporaryDirectory() as tempdir:
            factory = pheo.Pheo.open(tempdir)
            workflow = factory.workflow(
                "clinical_evidence_review",
                domain="life_sciences",
                objective="Review generated summaries against expert methodology",
            )
            corpus = factory.attach_corpus(
                workflow["id"],
                [
                    pheo.Text(
                        "Expert operating rule",
                        "Separate source-backed evidence from interpretation. Human experts approve conclusions before use.",
                        tags=["methodology"],
                    )
                ],
            )
            self.assertEqual(len(corpus), 1)

            methodology = factory.build_methodology(workflow["id"])
            self.assertGreaterEqual(len(methodology["review_pairs"]), 25)
            factory.review_methodology(workflow["id"])
            approved = factory.approve_methodology(workflow["id"])
            self.assertEqual(approved["status"], "approved")
            self.assertEqual(approved["approved_by"], "human")

            run = factory.run_candidates(
                workflow["id"],
                {"goal": "Summarize clinical trial risks with grounded caveats"},
                [
                    {"output": "The summary separates protocol evidence from interpretation and asks for expert approval.", "generator": "agent_a"},
                    {"output": "The summary is final and can be deployed without human review.", "generator": "agent_b"},
                    {"output": "The summary lists risks, caveats the evidence, and preserves provenance.", "generator": "agent_c"},
                ],
            )
            scored = factory.score_run(run["id"])
            self.assertTrue(all(candidate["scores"] for candidate in scored["candidates"]))

            decision = factory.capture_decision(run["id"], selected_index=0, reason="Most grounded and reviewable")
            self.assertEqual(decision["decision"]["action"], "approve")

            pack_dir = Path(tempdir) / "pack"
            pack = factory.export_memory_pack(workflow["id"], pack_dir)
            self.assertTrue((pack_dir / "memory_pack.json").exists())
            self.assertTrue((pack_dir / "preference_pairs.jsonl").exists())
            self.assertFalse((pack_dir / "preferences.jsonl").exists())
            self.assertTrue((pack_dir / "methodology_events.jsonl").exists())
            self.assertGreaterEqual(len(pack["artifacts"]["preference_pairs"]), 2)
            self.assertGreater(pack["memory_summary"]["bootstrap_pairs"], 0)
            self.assertIn("candidate_quality", pack["artifacts"])
            self.assertEqual(pack["artifacts"]["methodology_events"][0]["event_type"], "approved")
            self.assertGreaterEqual([event["event_type"] for event in pack["artifacts"]["methodology_events"]].count("drafted"), 1)
            organic_pack = factory.memory_pack(workflow["id"], organic_only=True)
            self.assertTrue(organic_pack["export_filter"]["organic_only"])
            self.assertTrue(organic_pack["artifacts"]["preference_pairs"])
            self.assertEqual(organic_pack["memory_summary"]["bootstrap_pairs"], 0)
            self.assertTrue(all(key.startswith("human") for key in organic_pack["memory_summary"]["pair_counts_by_provenance"]))

    def test_attach_corpus_skips_methodology_rebuild_when_approved(self):
        with tempfile.TemporaryDirectory() as tempdir:
            factory = pheo.Pheo.open(tempdir)
            workflow = factory.workflow("finance_receipt_review", domain="finance")
            factory.attach_corpus(workflow["id"], [pheo.Text("Policy", "Human review required.")])
            factory.build_methodology(workflow["id"])
            factory.review_methodology(workflow["id"])
            approved = factory.approve_methodology(workflow["id"])
            approved_id = approved["id"]
            factory.attach_corpus(workflow["id"], [pheo.Text("Extra", "More corpus without rebuilding rules.")])
            current = factory.methodology(workflow["id"])
            self.assertEqual(current["id"], approved_id)
            self.assertEqual(current["status"], "approved")

    def test_attach_corpus_can_force_methodology_rebuild(self):
        with tempfile.TemporaryDirectory() as tempdir:
            factory = pheo.Pheo.open(tempdir)
            workflow = factory.workflow("finance_receipt_review", domain="finance")
            factory.attach_corpus(workflow["id"], [pheo.Text("Policy", "Human review required.")])
            factory.build_methodology(workflow["id"])
            factory.review_methodology(workflow["id"])
            approved = factory.approve_methodology(workflow["id"])
            factory.attach_corpus(
                workflow["id"],
                [pheo.Text("Extra", "More corpus with rebuild.")],
                rebuild_methodology=True,
            )
            current = factory.methodology(workflow["id"])
            self.assertNotEqual(current["id"], approved["id"])
            self.assertEqual(current["status"], "draft")

    def test_force_new_workflow_creates_distinct_records(self):
        with tempfile.TemporaryDirectory() as tempdir:
            factory = pheo.Pheo.open(tempdir)
            first = factory.workflow("finance_receipt_review", domain="finance", force_new=False)
            second = factory.workflow("finance_receipt_review", domain="finance", force_new=False)
            self.assertEqual(first["id"], second["id"])
            third = factory.workflow("finance_receipt_review", domain="finance", force_new=True)
            self.assertNotEqual(third["id"], first["id"])
            self.assertNotEqual(third["name"], first["name"])

    def test_deactivating_corpus_preserves_decision_memory(self):
        with tempfile.TemporaryDirectory() as tempdir:
            factory = pheo.Pheo.open(tempdir)
            workflow = factory.workflow("legal_review", domain="legal")
            item = factory.attach_corpus(workflow["id"], [pheo.Text("Policy", "Human review is required.")])[0]
            factory.build_methodology(workflow["id"])
            factory.review_methodology(workflow["id"])
            factory.approve_methodology(workflow["id"])
            run = factory.run_candidates(
                workflow["id"],
                {"goal": "Draft a review note"},
                ["Draft for human review.", "Autonomously final answer."],
            )
            factory.score_run(run["id"])
            factory.capture_decision(run["id"], 0, reason="Review boundary preserved")

            factory.deactivate_corpus(item["id"])
            store = factory.preference_store(workflow["id"])
            self.assertFalse(store["corpus"][0]["active"])
            self.assertTrue(any(decision["provenance"] == "human_triage" for decision in store["decisions"]))
            self.assertGreaterEqual(len(store["preference_pairs"]), 1)

    def test_cli_commands_work_end_to_end(self):
        with tempfile.TemporaryDirectory() as tempdir:
            project = str(Path(tempdir) / "project")
            task_path = Path(tempdir) / "task.json"
            candidates_path = Path(tempdir) / "candidates.json"
            task_path.write_text(json.dumps({"goal": "Summarize trial risks"}), encoding="utf-8")
            candidates_path.write_text(
                json.dumps(
                    [
                        {"output": "Ground evidence and ask for expert review.", "generator": "agent_a"},
                        {"output": "Make a final claim without review.", "generator": "agent_b"},
                    ]
                ),
                encoding="utf-8",
            )

            self._cli(project, "init")
            store_output = self._cli(
                project,
                "store",
                "create",
                "--name",
                "clinical_review",
                "--business-area",
                "healthcare",
                "--goal",
                "Review clinical summaries against source evidence before use.",
            )
            self.assertEqual(
                json.loads(store_output)["store"]["objective"],
                "Review clinical summaries against source evidence before use.",
            )
            self._cli(project, "corpus", "add", "--workflow", "clinical_review", "Separate evidence from interpretation.")
            self._cli(project, "methodology", "build", "--workflow", "clinical_review")
            review_output = self._cli(project, "methodology", "review", "--workflow", "clinical_review", "--format", "human")
            self.assertIn("Review goal / protocol", review_output)
            self.assertIn("Review clinical summaries against source evidence before use.", review_output)
            self.assertIn("Must do", review_output)
            self.assertIn("Approve with", review_output)
            self._cli(project, "methodology", "approve", "--workflow", "clinical_review")
            run_output = self._cli(
                project,
                "run",
                "create",
                "--workflow",
                "clinical_review",
                "--task",
                str(task_path),
                "--candidates",
                str(candidates_path),
            )
            run_id = json.loads(run_output)["run"]["id"]
            self._cli(project, "run", "score", run_id)
            self._cli(project, "decision", "capture", "--run", run_id, "--selected", "0", "--reason", "Best review boundary")
            preferences = self._cli(project, "export", "preferences", "--workflow", "clinical_review")
            self.assertIn('"chosen"', preferences)
            for line in preferences.splitlines():
                json.loads(line)

    def test_cli_review_point_flow(self):
        with tempfile.TemporaryDirectory() as tempdir:
            project = str(Path(tempdir) / "project")
            graph_path = Path(tempdir) / "workflow.graph.json"
            self._cli(project, "init")
            self._cli(project, "store", "create", "--name", "finance_review", "--business-area", "finance")
            self._cli(
                project,
                "connection",
                "add",
                "--store",
                "finance_review",
                "--name",
                "openrouter",
                "--type",
                "openai-compatible-endpoint",
                "--endpoint-url",
                "https://openrouter.ai/api/v1",
                "--model",
                "openai/gpt-4o-mini",
            )
            self._cli(
                project,
                "source",
                "add",
                "--store",
                "finance_review",
                "Do not accept unsupported seasonality explanations. Escalate when support is missing.",
            )
            self._cli(project, "methodology", "review", "--workflow", "finance_review")
            self._cli(project, "methodology", "approve", "--workflow", "finance_review")
            self._cli(
                project,
                "review-point",
                "add",
                "--store",
                "finance_review",
                "--name",
                "variance_review",
                "--description",
                "Review variance explanations before close packet use.",
                "--dimension",
                "evidence grounding",
                "--dimension",
                "escalation risk",
                "--connection",
                "openrouter",
            )
            packet_payload = json.loads(
                self._cli(
                    project,
                    "observe",
                    "output",
                    "--review-point",
                    "variance_review",
                    "--context",
                    "Controller asks whether the explanation is supported.",
                    "--source",
                    "manual-agent-output",
                    "--output",
                    "Revenue declined due to seasonality.",
                )
            )
            self.assertEqual(packet_payload["observation"]["context"]["note"], "Controller asks whether the explanation is supported.")
            self.assertEqual(packet_payload["observation"]["source"]["name"], "manual-agent-output")
            packet_id = packet_payload["packet"]["id"]
            selected = packet_payload["recommended"]["index"]
            self._cli(
                project,
                "review",
                packet_id,
                "--selected",
                str(selected),
                "--reason",
                "Best review boundary",
            )
            self._cli(project, "export", "graph", "--store", "finance_review", "--out", str(graph_path))
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            self.assertTrue(any(node["type"] == "connection" for node in graph["nodes"]))
            self.assertTrue(any(edge["type"] == "feeds_review_point" for edge in graph["edges"]))
            self.assertTrue(any(node["type"] == "review_point" for node in graph["nodes"]))

    def test_project_registry_drives_cli_hierarchy(self):
        with tempfile.TemporaryDirectory() as tempdir:
            home = Path(tempdir) / "pheo-home"
            finance_project = Path(tempdir) / "finance-project"
            legal_project = Path(tempdir) / "legal-project"
            env = {**os.environ, "PHEO_HOME": str(home)}

            created = self._run_cli(
                "project",
                "create",
                "finance-pilot",
                "--path",
                str(finance_project),
                env=env,
            )
            self.assertEqual(json.loads(created)["project"]["name"], "finance-pilot")

            self._run_cli("store", "create", "--name", "finance_review", "--business-area", "finance", env=env)
            self._run_cli("store", "create", "--name", "fpna_review", "--business-area", "finance", env=env)
            stores = json.loads(self._run_cli("store", "list", env=env))["stores"]
            self.assertEqual(sorted(item["name"] for item in stores), ["finance_review", "fpna_review"])

            self._run_cli("project", "create", "legal-pilot", "--path", str(legal_project), env=env)
            self._run_cli("store", "create", "--name", "contract_review", "--business-area", "legal", env=env)
            self._run_cli("store", "create", "--name", "policy_review", "--business-area", "legal", env=env)
            current = json.loads(self._run_cli("project", "current", env=env))["project"]
            self.assertEqual(current["name"], "legal-pilot")

            self._run_cli("project", "use", "finance-pilot", env=env)
            stores = json.loads(self._run_cli("store", "list", env=env))["stores"]
            self.assertEqual(sorted(item["name"] for item in stores), ["finance_review", "fpna_review"])

            self._run_cli("project", "use", "legal-pilot", env=env)
            stores = json.loads(self._run_cli("store", "list", env=env))["stores"]
            self.assertEqual(sorted(item["name"] for item in stores), ["contract_review", "policy_review"])

            projects = json.loads(self._run_cli("project", "list", env=env))["projects"]
            self.assertEqual({item["name"] for item in projects}, {"finance-pilot", "legal-pilot"})
            self.assertTrue(any(item["name"] == "legal-pilot" and item["current"] for item in projects))

    def test_rest_api_mirrors_sdk_behavior(self):
        with tempfile.TemporaryDirectory() as tempdir:
            server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(tempdir))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.shutdown)
            self.addCleanup(server.server_close)
            base = f"http://127.0.0.1:{server.server_address[1]}"

            spec = self._get(base + "/openapi.json")
            self.assertEqual(spec["openapi"], "3.1.0")
            self.assertIn("/v1/workflows/{workflow}/memory-pack", spec["paths"])

            workflow = self._post(
                base + "/v1/workflows",
                {"name": "research_review", "goal": "Validate included evidence before downstream synthesis."},
            )["workflow"]
            self.assertEqual(self._get(base + f"/v1/workflows/{workflow['id']}")["workflow"]["name"], "research_review")
            self.assertEqual(
                self._get(base + f"/v1/workflows/{workflow['id']}")["workflow"]["objective"],
                "Validate included evidence before downstream synthesis.",
            )
            self._post(
                base + f"/v1/workflows/{workflow['id']}/corpus",
                {"items": [{"source_type": "text", "title": "Rule", "text": "Use source grounded evidence."}]},
            )
            self._post(base + f"/v1/workflows/{workflow['id']}/methodology/build", {})
            self._get(base + f"/v1/workflows/{workflow['id']}/methodology")
            self._post(base + f"/v1/workflows/{workflow['id']}/methodology/approve", {})
            run = self._post(
                base + f"/v1/workflows/{workflow['id']}/runs",
                {
                    "task": {"goal": "Review evidence"},
                    "candidates": [
                        {"output": "Use source grounded evidence and human review."},
                        {"output": "Invent a confident answer."},
                    ],
                },
            )["run"]
            scored = self._post(base + f"/v1/runs/{run['id']}/score", {})["run"]
            self.assertTrue(scored["candidates"][0]["scores"])
            self._post(base + f"/v1/runs/{run['id']}/decisions", {"selected_index": 0, "reason": "Grounded"})
            pack = self._get(base + f"/v1/workflows/{workflow['id']}/memory-pack")
            self.assertGreaterEqual(len(pack["artifacts"]["preference_pairs"]), 1)

    def test_rest_review_point_observation_flow(self):
        with tempfile.TemporaryDirectory() as tempdir:
            server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(tempdir))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.shutdown)
            self.addCleanup(server.server_close)
            base = f"http://127.0.0.1:{server.server_address[1]}"

            store = self._post(base + "/v1/stores", {"name": "finance_review", "business_area": "finance"})["store"]
            self._post(
                base + f"/v1/stores/{store['id']}/sources",
                {"sources": [{"source_type": "text", "title": "Rule", "text": "Escalate unsupported explanations."}]},
            )
            self._get(base + f"/v1/workflows/{store['id']}/methodology")
            self._post(base + f"/v1/workflows/{store['id']}/methodology/approve", {})
            connection = self._post(
                base + f"/v1/stores/{store['id']}/connections",
                {
                    "name": "openrouter",
                    "connector_type": "openai-compatible-endpoint",
                    "endpoint_url": "https://openrouter.ai/api/v1",
                    "model": "openai/gpt-4o-mini",
                },
            )["connection"]
            point = self._post(
                base + f"/v1/stores/{store['id']}/review-points",
                {"name": "variance_review", "description": "Review variance explanations.", "connection": connection["name"]},
            )["review_point"]
            packet = self._post(
                base + f"/v1/stores/{store['id']}/review-points/{point['name']}/observations",
                {"output": "Revenue declined due to seasonality.", "context": {"variance": "-12%"}},
            )
            self.assertEqual(packet["status"], "pending_review")
            selected = packet["recommended"]["index"]
            reviewed = self._post(
                base + f"/v1/review-packets/{packet['packet']['id']}/reviews",
                {"selected_index": selected, "reason": "Most controlled option."},
            )
            self.assertEqual(reviewed["packet"]["status"], "reviewed")
            pack = self._get(base + f"/v1/stores/{store['id']}/memory-pack")
            self.assertEqual(len(pack["artifacts"]["connections"]), 1)
            self.assertEqual(len(pack["artifacts"]["observations"]), 1)

    def test_rest_project_registry_switches_active_project(self):
        with tempfile.TemporaryDirectory() as tempdir:
            home = Path(tempdir) / "pheo-home"
            with patch.dict(os.environ, {"PHEO_HOME": str(home)}, clear=False):
                first_project = str(Path(tempdir) / "first")
                second_project = str(Path(tempdir) / "second")
                server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(first_project))
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                self.addCleanup(server.shutdown)
                self.addCleanup(server.server_close)
                base = f"http://127.0.0.1:{server.server_address[1]}"

                projects = self._get(base + "/v1/projects")
                self.assertEqual(projects["current_project"]["path"], str(Path(first_project).resolve()))
                self._post(base + "/v1/stores", {"name": "first_store"})
                self.assertEqual(len(self._get(base + "/v1/stores")["stores"]), 1)

                self._post(base + "/v1/projects", {"name": "second-pilot", "path": second_project})
                self.assertEqual(self._get(base + "/v1/stores")["stores"], [])
                self._post(base + "/v1/stores", {"name": "second_store"})

                self._post(base + "/v1/projects/current", {"ref": str(first_project)})
                stores = self._get(base + "/v1/stores")["stores"]
                self.assertEqual([item["name"] for item in stores], ["first_store"])

    def test_observe_endpoint_uses_review_point_connection(self):
        class EndpointHandler(BaseHTTPRequestHandler):
            requests = []

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                self.__class__.requests.append(payload)
                body = json.dumps({"choices": [{"message": {"content": "Ask the client to pause, identify the goal, and draft a reviewable response."}}]})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))

            def log_message(self, format, *args):
                return

        with tempfile.TemporaryDirectory() as tempdir:
            server = ThreadingHTTPServer(("127.0.0.1", 0), EndpointHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.shutdown)
            self.addCleanup(server.server_close)

            store = pheo.open(tempdir)
            workflow = store.create_store("coaching_review", business_area="coaching")
            store.source.add_text("Review rule", "Responses should preserve client agency and avoid overclaiming.")
            store.review_methodology(workflow["id"])
            store.approve_methodology(workflow["id"])
            store.connection.add_endpoint(
                "local_endpoint",
                f"http://127.0.0.1:{server.server_address[1]}/v1",
                model="local/test-model",
            )
            store.review_point.create(
                "coaching_response_review",
                description="Review coaching responses before reuse.",
                dimensions=["agency", "boundaries", "grounding"],
                connection="local_endpoint",
            )

            packet = store.observe_endpoint(
                "coaching_response_review",
                api_key="test-key",
                prompt="Draft a coaching response for a workplace conflict.",
            )

            self.assertEqual(EndpointHandler.requests[0]["model"], "local/test-model")
            self.assertEqual(packet["observation"]["source"]["model"], "local/test-model")
            self.assertGreaterEqual(len(packet["candidates"]), 3)

    def test_mcp_path_covers_methodology_gate_and_review_capture(self):
        from pheo.mcp import call_tool

        with tempfile.TemporaryDirectory() as tempdir:
            store = pheo.open(tempdir)
            created = call_tool(
                store,
                "pheo_create_store",
                {"name": "finance_review", "business_area": "finance", "goal": "Review finance outputs before release."},
            )["store"]
            call_tool(
                store,
                "pheo_add_source",
                {
                    "store": created["id"],
                    "title": "Controller rule",
                    "text": "Require source support and escalation for unsupported finance explanations.",
                },
            )
            methodology = call_tool(store, "pheo_review_methodology", {"store": created["id"]})
            self.assertEqual(methodology["gate"]["status"], "draft")
            self.assertFalse(methodology["gate"]["approved"])
            self.assertEqual(methodology["human_review"]["goal"], "Review finance outputs before release.")

            call_tool(
                store,
                "pheo_approve_methodology",
                {"store": created["id"], "actor": "controller@example.com", "note": "Rules reviewed."},
            )
            call_tool(
                store,
                "pheo_create_review_point",
                {
                    "store": created["id"],
                    "name": "variance_review",
                    "description": "Review variance explanations.",
                    "dimensions": ["evidence grounding", "clarity"],
                },
            )
            packet = call_tool(
                store,
                "pheo_observe_output",
                {
                    "review_point": "variance_review",
                    "output": "Revenue declined due to seasonality.",
                    "context": {"variance": "-12%"},
                },
            )
            self.assertEqual(packet["status"], "pending_review")
            reviewed = call_tool(
                store,
                "pheo_capture_review",
                {
                    "packet_id": packet["packet"]["id"],
                    "selected_index": packet["recommended"]["index"],
                    "action": "approve",
                    "reason": "Most reviewable option.",
                    "author_id": "controller@example.com",
                },
            )
            self.assertEqual(reviewed["packet"]["status"], "reviewed")

    def test_mcp_observe_endpoint_path(self):
        from pheo.mcp import call_tool

        class EndpointHandler(BaseHTTPRequestHandler):
            requests = []

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                self.__class__.requests.append(payload)
                body = json.dumps({"choices": [{"message": {"content": "Draft with source support and ask for human review before use."}}]})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))

            def log_message(self, format, *args):
                return

        with tempfile.TemporaryDirectory() as tempdir:
            server = ThreadingHTTPServer(("127.0.0.1", 0), EndpointHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.shutdown)
            self.addCleanup(server.server_close)

            store = pheo.open(tempdir)
            created = call_tool(store, "pheo_create_store", {"name": "endpoint_review", "business_area": "support"})["store"]
            call_tool(store, "pheo_add_source", {"store": created["id"], "title": "Rule", "text": "Require human review and source support."})
            call_tool(store, "pheo_review_methodology", {"store": created["id"]})
            call_tool(store, "pheo_approve_methodology", {"store": created["id"]})
            call_tool(
                store,
                "pheo_add_endpoint_connection",
                {
                    "store": created["id"],
                    "name": "local_endpoint",
                    "endpoint_url": f"http://127.0.0.1:{server.server_address[1]}/v1",
                    "model": "local/test-model",
                    "api_key_env": "PHEO_TEST_ENDPOINT_KEY",
                },
            )
            call_tool(
                store,
                "pheo_create_review_point",
                {
                    "store": created["id"],
                    "name": "answer_quality",
                    "description": "Review endpoint answers.",
                    "dimensions": ["source grounding", "review boundary"],
                },
            )
            with patch.dict(os.environ, {"PHEO_TEST_ENDPOINT_KEY": "test-key"}, clear=False):
                packet = call_tool(
                    store,
                    "pheo_observe_endpoint",
                    {
                        "review_point": "answer_quality",
                        "connection": "local_endpoint",
                        "prompt": "Draft a support answer.",
                        "context": {"ticket": "billing"},
                    },
                )

            self.assertEqual(EndpointHandler.requests[0]["model"], "local/test-model")
            self.assertEqual(packet["status"], "pending_review")
            self.assertEqual(packet["observation"]["source"]["connector"], "mcp_endpoint")
            self.assertEqual(packet["observation"]["source"]["model"], "local/test-model")

    def test_observe_namespace_returns_governed_outcome_and_released_output(self):
        with tempfile.TemporaryDirectory() as tempdir:
            store = pheo.open(tempdir)
            workflow = store.create_store("finance_review", business_area="finance")
            store.source.add_text("Rule", "Require evidence and human approval before using close commentary.")
            store.review_methodology(workflow["id"])
            store.approve_methodology(workflow["id"])
            store.review_point.create("variance_review", description="Review variance explanations before use.")

            outcome = store.observe.output(
                "variance_review",
                "Revenue declined because of seasonality.",
                context={"account": "Revenue"},
                source={"connector": "unit_test_agent"},
            )

            self.assertEqual(outcome.status, "pending_review")
            self.assertEqual(outcome.observed_output, "Revenue declined because of seasonality.")
            self.assertTrue(outcome.review_url.startswith("/review/"))
            self.assertGreaterEqual(len(outcome.candidates), 3)
            self.assertTrue(outcome.candidates[0].scores)
            self.assertTrue(outcome.candidates[0].scores.explanation.summary)
            self.assertTrue(outcome.recommended_output)
            self.assertIsNone(outcome.released_output)
            with self.assertRaisesRegex(PendingReview, "human release is required"):
                outcome.require_released()

            store.review(
                outcome.id,
                selected_index=outcome.recommended["index"],
                action="edit",
                corrected_output="Revenue declined 12%; ask the business owner for support before close packet use.",
                reason="Human correction added the control point.",
                author_id="controller@example.com",
            )

            self.assertIn("business owner", outcome.require_released())
            self.assertEqual(outcome.decision["author_id"], "controller@example.com")

    def test_preference_factory_receipts_manifest_and_memory_apply(self):
        with tempfile.TemporaryDirectory() as tempdir:
            store = pheo.open(tempdir)
            workflow = store.create_store(
                "ap_invoice_exception_review",
                business_area="finance",
                goal="Review AP invoice exceptions before payment-related action.",
            )
            store.source.add_text(
                "AP policy",
                "Escalate invoices with missing PO, unclear approver, possible duplicate, or changed bank details.",
            )
            store.review_methodology(workflow["id"], actor="controller@example.com")
            store.approve_methodology(workflow["id"], actor="controller@example.com")
            store.review_point.create("ap_exception_review", description="Review AP exception notes.")

            first = store.observe.output(
                "ap_exception_review",
                "Invoice AP-1007 can proceed.",
                context={"invoice_id": "AP-1007", "vendor": "Northstar", "issue": "missing PO and unclear approver"},
                source={"connector": "unit_test_agent", "cycle_id": "cycle_1", "case_id": "AP-1007"},
            )
            snapshot = first["run"]["task"]["pheo_snapshot"]
            self.assertEqual(snapshot["methodology_status"], "approved")
            self.assertTrue(snapshot["methodology_hash"].startswith("sha256:"))
            reviewed = store.review(
                first.id,
                selected_index=first.recommended["index"],
                action="edit",
                corrected_output="Invoice AP-1007 should be escalated because PO support is missing and the approver is unclear.",
                reason="Escalate missing PO and unclear approver before payment.",
                author_id="controller@example.com",
            )
            self.assertTrue(reviewed["receipt"])
            self.assertEqual(reviewed["receipt"]["released_output"], reviewed["decision"]["chosen_output"])

            memory = store.memory(workflow["id"])
            self.assertEqual(len(memory["entries"]), 1)
            second = store.observe.output(
                "ap_exception_review",
                "Invoice AP-1249 can proceed.",
                context={"invoice_id": "AP-1249", "vendor": "Northstar", "issue": "possible duplicate and missing PO"},
                source={"connector": "unit_test_agent", "cycle_id": "cycle_2", "case_id": "AP-1249"},
                memory=memory,
            )
            memory_scores = second.recommended["scores"]["judgment_memory"]
            self.assertTrue(memory_scores["applied"])
            self.assertIn("Escalate missing PO", memory_scores["prior_reason"])
            with self.assertRaises(PendingReview):
                second.require_released()

            pack = store.memory_pack(workflow["id"], organic_only=True)
            self.assertEqual(len(pack["artifacts"]["release_receipts"]), 1)
            self.assertEqual(len(pack["artifacts"]["preference_tuples"]), 1)
            self.assertEqual(len(pack["artifacts"]["review_examples"]), 1)
            self.assertEqual(len(pack["artifacts"]["sft_jsonl"]), 1)
            self.assertGreaterEqual(len(pack["artifacts"]["dpo_jsonl"]), 1)
            self.assertEqual(pack["artifacts"]["training_manifest"]["counts"]["released_examples"], 1)
            self.assertEqual(pack["artifacts"]["training_manifest"]["memory_richness"]["reasoned_tuple_count"], 1)
            self.assertGreaterEqual(pack["artifacts"]["cycle_diff"]["after_stats"]["memory_match_cases"], 1)
            self.assertIn("note", pack["artifacts"]["cycle_diff"])

            stale = store.training_manifest(
                workflow["id"],
                filters={"methodology_scope": "explicit", "methodology_hashes": ["sha256:not-current"]},
            )
            self.assertEqual(stale["counts"]["tuples_included"], 0)
            self.assertIn("methodology_not_selected", stale["excluded_tuples"][0]["reasons"])

    def test_trace_imports_normalize_common_observability_shapes(self):
        with tempfile.TemporaryDirectory() as tempdir:
            factory = pheo.Pheo.open(tempdir)
            workflow = factory.workflow("invoice_exception_review", domain="finance")
            factory.attach_corpus(workflow["id"], [pheo.Text("Policy", "Human approval is required before payment.")])
            factory.build_methodology(workflow["id"])
            factory.review_methodology(workflow["id"])
            factory.approve_methodology(workflow["id"])

            langsmith_runs = factory.import_traces(
                workflow["id"],
                "langsmith",
                {
                    "runs": [
                        {
                            "id": "ls-1",
                            "name": "invoice_agent",
                            "inputs": {"prompt": "Review invoice exception"},
                            "outputs": {"output": "Approve only after matching the invoice to policy and approval limits."},
                        }
                    ]
                },
            )
            self.assertEqual(len(langsmith_runs), 1)
            self.assertTrue(langsmith_runs[0]["candidates"][0]["scores"])

            weave_runs = factory.import_traces(
                workflow["id"],
                "weave",
                {
                    "calls": [
                        {
                            "id": "weave-1",
                            "op_name": "invoice_review",
                            "inputs": {"query": "Check payment exception"},
                            "output": {"text": "Hold payment until the exception has a documented reviewer."},
                        }
                    ]
                },
            )
            self.assertEqual(len(weave_runs), 1)

            otel_runs = factory.import_traces(
                workflow["id"],
                "opentelemetry",
                {
                    "resourceSpans": [
                        {
                            "scopeSpans": [
                                {
                                    "spans": [
                                        {
                                            "spanId": "otel-1",
                                            "name": "llm.chat",
                                            "attributes": [
                                                {"key": "gen_ai.request.model", "value": {"stringValue": "openrouter/auto"}},
                                                {"key": "gen_ai.response.output", "value": {"stringValue": "Escalate to finance reviewer before approval."}},
                                            ],
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
            )
            self.assertEqual(len(otel_runs), 1)

            llama_runs = factory.import_traces(
                workflow["id"],
                "llamaindex",
                [{"event": {"response_text": "Answer with source-backed caveats and reviewer approval."}}],
            )
            self.assertEqual(len(llama_runs), 1)
            vllm_runs = factory.import_traces(
                workflow["id"],
                "vllm",
                [{"model": "local/vllm", "choices": [{"message": {"content": "Ask for evidence before using the answer."}}]}],
            )
            self.assertEqual(len(vllm_runs), 1)
            hf_runs = factory.import_traces(
                workflow["id"],
                "huggingface",
                [{"generated_text": "Keep the answer reviewable and grounded in policy."}],
            )
            self.assertEqual(len(hf_runs), 1)

            root = Path(__file__).resolve().parents[1]
            langgraph_fixture = json.loads((root / "examples/traces/langgraph-langsmith-run.json").read_text())
            langgraph_runs = factory.import_traces(workflow["id"], "langsmith", langgraph_fixture)
            self.assertEqual(len(langgraph_runs), 1)
            self.assertIn("human reviewer", langgraph_runs[0]["candidates"][0]["output"])

            weave_fixture = json.loads((root / "examples/traces/weave-call.json").read_text())
            weave_fixture_runs = factory.import_traces(workflow["id"], "weave", weave_fixture)
            self.assertEqual(len(weave_fixture_runs), 1)
            self.assertIn("documented approver", weave_fixture_runs[0]["candidates"][0]["output"])

            noveum_fixture = json.loads((root / "examples/traces/noveum-trace.json").read_text())
            noveum_runs = factory.import_traces(workflow["id"], "noveum", noveum_fixture)
            self.assertEqual(len(noveum_runs), 1)
            self.assertIn("approval support is missing", noveum_runs[0]["candidates"][0]["output"])
            self.assertEqual(noveum_runs[0]["candidates"][0]["generator"], "openai/gpt-4o-mini")

            factory.connection.add_langchain(store_id=workflow["id"], workspace="local")
            factory.connection.add_weave(store_id=workflow["id"], workspace="local")
            factory.connection.add_noveum(store_id=workflow["id"], workspace="local")
            factory.connection.add_vllm(store_id=workflow["id"], endpoint_url="http://localhost:8000/v1", model="local/vllm")
            connection_types = {item["connector_type"] for item in factory.connections(workflow["id"])}
            self.assertIn("langchain", connection_types)
            self.assertIn("weave", connection_types)
            self.assertIn("noveum", connection_types)
            self.assertIn("vllm", connection_types)

            store = factory.preference_store(workflow["id"])
            trace_runs = [run for run in store["runs"] if run["mode"].startswith("trace:")]
            self.assertEqual(len(trace_runs), 9)
            self.assertTrue(all(run["status"] == "scored" for run in trace_runs))

    def test_finance_example_batch_script_seeds_review_queue(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tempdir:
            store = pheo.open(tempdir)
            workflow = store.create_store(
                "ap_invoice_exception_review",
                business_area="finance",
                goal="Prepare AP invoice exception summaries for human review before any payment-related action is approved.",
            )
            store.source.add(str(root / "examples/finance_exception/ap-policy.md"), store_id=workflow["id"])
            store.review_methodology(workflow["id"], actor="reviewer@example.com")
            store.approve_methodology(workflow["id"], actor="reviewer@example.com")
            store.review_point.create(
                "ap_exception_review",
                description="Review AP invoice exception summaries before clearing or payment-related action.",
                dimensions=["evidence support", "approval clarity", "exception risk", "next step"],
                store_id=workflow["id"],
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "examples/finance_exception/observe_cases.py"),
                    "--project",
                    tempdir,
                ],
                check=True,
                text=True,
                capture_output=True,
                env={**os.environ, "PYTHONPATH": str(root)},
            )

            self.assertIn("Observed 25 cases", result.stdout)
            self.assertIn("pheo start --store ap_invoice_exception_review", result.stdout)
            self.assertEqual(len(store.store.list_review_packets(workflow["id"])), 25)

    def test_code_agent_demo_creates_review_memory_and_cycle_2_signal(self):
        from pheo.examples.code_agent.run_demo import run_demo

        with tempfile.TemporaryDirectory() as tempdir:
            project = Path(tempdir) / "project"
            out = Path(tempdir) / "pack"
            result = run_demo(project, out, reset=True)

            self.assertTrue((out / "memory_pack.json").exists())
            self.assertTrue((out / "release_receipts.jsonl").exists())
            self.assertTrue((out / "preference_tuples.jsonl").exists())
            self.assertTrue(result["memory_signal"].get("applied"))
            self.assertIn("tests", result["memory_signal"].get("prior_reason", ""))
            artifacts = result["pack"]["artifacts"]
            organic_receipts = [
                item
                for item in artifacts["release_receipts"]
                if not item.get("backfilled") and item.get("reviewer_action") == "reject"
            ]
            self.assertEqual(len(organic_receipts), 1)
            organic_tuples = [item for item in artifacts["preference_tuples"] if item.get("provenance") == "human_triage"]
            self.assertGreaterEqual(len(organic_tuples), 1)
            self.assertGreaterEqual(len(artifacts["judgment_memory"].get("entries") or []), 1)

    def test_code_agent_demo_cli_runs_from_package(self):
        with tempfile.TemporaryDirectory() as tempdir:
            result = self._run_cli(
                "demo",
                "code-agent",
                "--project",
                str(Path(tempdir) / "project"),
                "--out",
                str(Path(tempdir) / "pack"),
                "--reset",
            )

            self.assertIn("PHEO Grow: coding-agent attachment", result)
            self.assertIn("Release blocked until human review", result)
            self.assertIn("Cycle 2 observed with judgment memory applied", result)
            self.assertIn("Export: receipts=", result)

    def test_agent_docs_are_current_and_plain_language(self):
        root = Path(__file__).resolve().parents[1]
        agents = (root / "docs/agents.md").read_text()
        self.assertFalse((root / "CLAUDE.md").exists())
        self.assertIn("Use Pheo to add a human review and learning loop to this existing workflow.", agents)
        self.assertIn("Read AGENTS.md. Add Pheo review and export to [WORKFLOW].", agents)
        self.assertIn('--goal "Prepare AP invoice exception summaries for human review before any payment-related action is approved."', agents)
        self.assertNotIn('description="Review AI-assisted variance explanations before close packet use."', agents)
        self.assertIn("LangGraph, or LangSmith trace export: use `pheo observe traces --source-type langsmith`", agents)
        self.assertIn("W&B Weave export: use `pheo observe traces --source-type weave` or `wandb-weave`", agents)
        self.assertIn("Noveum trace export: use `pheo observe traces --source-type noveum`", agents)
        self.assertIn("patterns/", agents)
        self.assertIn("examples/finance_exception/", agents)

        public_paths = (
            "README.md",
            "docs/agents.md",
            "docs/spec.md",
            "docs/glossary.md",
            "docs/api.md",
            "docs/mcp.md",
            "docs/getting-started.md",
            "docs/deployment.md",
            "patterns/wrap-python-function.md",
            "patterns/openai-compatible-endpoint.md",
            "patterns/import-traces.md",
            "patterns/mcp-agent-checklist.md",
            "patterns/coding-agent-grow.md",
            "examples/finance_exception/README.md",
            "examples/code_agent/README.md",
            "llms.txt",
        )
        public_docs = "\n".join((root / path).read_text() for path in public_paths)
        for phrase in (
            "kernel runtime boundary",
            "runtime boundary",
            "open-core review-memory layer",
            "private kernel",
            "kernel internals",
            "kernel wheel",
            "zen_tools",
            "coaching-style",
            "consultant.md",
        ):
            self.assertNotIn(phrase, public_docs)
        self.assertIn("--description \"Review AP invoice exception summaries", public_docs)
        self.assertIn("Attach PHEO Grow To Coding Agents", public_docs)
        self.assertIn("Read docs/agents.md. Add Pheo review and export to the existing workflow.", (root / "llms.txt").read_text())
        self.assertTrue((root / "examples/finance_exception/observe_cases.py").exists())
        self.assertTrue((root / "examples/code_agent/run_demo.py").exists())

        cases = [
            json.loads(line)
            for line in (root / "examples/finance_exception/invoice_cases.jsonl").read_text().splitlines()
            if line.strip()
        ]
        self.assertEqual(len(cases), 25)
        self.assertTrue(all({"invoice_id", "vendor", "approval_status", "suggested_action"} <= set(case) for case in cases))

    def test_endpoint_url_helpers(self):
        self.assertEqual(chat_completions_url("https://openrouter.ai/api/v1"), "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(chat_completions_url("https://host.example/chat/completions"), "https://host.example/chat/completions")
        self.assertEqual(safe_endpoint("https://openrouter.ai/api/v1"), "https://openrouter.ai")

    def _cli(self, project, *args):
        env = {**os.environ, "PHEO_HOME": str(Path(project).parent / "pheo-home")}
        return self._run_cli("--project", project, *args, env=env)

    def _run_cli(self, *args, env=None):
        result = subprocess.run(
            [sys.executable, "-m", "pheo.cli", *args],
            check=True,
            text=True,
            capture_output=True,
            env=env,
        )
        return result.stdout

    def _post(self, url, payload):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get(self, url):
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
