"""Main triage pipeline: classify → retrieve → safety → respond → persist."""

from __future__ import annotations

import os
import random
import uuid
from pathlib import Path
from typing import Optional

from agent.classifier import infer_company, classify_product_area
from agent.responder import generate_response
from ticket_io.csv_reader import Ticket
from ticket_io.csv_writer import TriageResult
from retrieval.retriever import BM25Retriever
from safety.gate import pre_check, post_check
from telemetry.logger import TriageLogger
from store.persistence import RunStore


class TriagePipeline:
    """
    Orchestrates the full triage flow for a single ticket or a batch.
    Initialised once per run; BM25 indexes are built at startup and reused.
    """

    def __init__(
        self,
        data_dir: Path,
        seed: Optional[int] = None,
        verbose: bool = False,
        model: Optional[str] = None,
    ):
        if seed is not None:
            random.seed(seed)

        self.job_id = f"job_{uuid.uuid4().hex[:8]}"
        self.model = model or os.environ.get("TRIAGE_LLM_MODEL", "claude-sonnet-4-6")
        self.verbose = verbose
        self.logger = TriageLogger(job_id=self.job_id, verbose=verbose)
        self.store = RunStore()

        self.logger.info("Loading corpus BM25 index…")
        self.retriever = BM25Retriever.from_data_dir(data_dir)
        self.logger.info(f"Corpus loaded — job_id={self.job_id}")

    def process_ticket(self, ticket: Ticket) -> TriageResult:
        """Full single-ticket triage: pre-check → retrieve → LLM → post-check."""
        company = infer_company(ticket.issue, ticket.subject, ticket.company)
        self.logger.info(f"row={ticket.row_id} company={company}")

        # --- Safety pre-check ---
        pre = pre_check(ticket.issue, ticket.subject, company)

        if pre.is_invalid:
            return self._build_result(
                ticket=ticket,
                company=company,
                status="replied",
                product_area="general",
                response=(
                    "This request is outside the scope of our support capabilities. "
                    "We're unable to assist with this query."
                ),
                justification=f"Safety gate: {pre.reason}",
                request_type="invalid",
                retrieval_sources=[],
                confidence=1.0,
            )

        if pre.should_escalate:
            return self._build_result(
                ticket=ticket,
                company=company,
                status="escalated",
                product_area="general",
                response=(
                    "Your request has been escalated to a human support agent "
                    "who will contact you shortly."
                ),
                justification=f"Safety gate triggered: {pre.reason}",
                request_type="product_issue",
                retrieval_sources=[],
                confidence=1.0,
            )

        # --- Corpus retrieval ---
        query = f"{ticket.subject} {ticket.issue}"
        results = self.retriever.search(query, company, top_k=5)
        max_score = self.retriever.max_score(results)
        self.logger.debug(f"row={ticket.row_id} retrieval hits={len(results)} max_score={max_score:.3f}")

        # --- LLM response generation ---
        llm = generate_response(
            issue=ticket.issue,
            subject=ticket.subject,
            company=company,
            retrieval_results=results,
            model=self.model,
        )

        # --- Safety post-check ---
        post = post_check(
            status=llm.status,
            response=llm.response,
            justification=llm.justification,
            retrieval_max_score=max_score,
        )

        final_status = "escalated" if post.should_escalate else llm.status
        final_justification = llm.justification
        if post.should_escalate and post.reason:
            final_justification = f"{llm.justification} [Post-check: {post.reason}]"
            final_response = (
                llm.response
                if llm.status == "escalated"
                else "Your request has been escalated to a human support agent."
            )
        else:
            final_response = llm.response

        # Derive product_area from top retrieval result breadcrumbs if LLM returned "general"
        product_area = llm.product_area
        if product_area == "general" and results:
            product_area = classify_product_area(results[0].chunk.breadcrumbs, company)

        sources = [r.chunk.source_url for r in results if r.chunk.source_url]

        return self._build_result(
            ticket=ticket,
            company=company,
            status=final_status,
            product_area=product_area,
            response=final_response,
            justification=final_justification,
            request_type=llm.request_type,
            retrieval_sources=sources,
            confidence=max_score,
        )

    def _build_result(
        self,
        ticket: Ticket,
        company: str,
        status: str,
        product_area: str,
        response: str,
        justification: str,
        request_type: str,
        retrieval_sources: list[str],
        confidence: float,
    ) -> TriageResult:
        result = TriageResult(
            row_id=ticket.row_id,
            issue=ticket.issue,
            subject=ticket.subject,
            company=ticket.company,
            status=status,
            product_area=product_area,
            response=response,
            justification=justification,
            request_type=request_type,
            retrieval_sources=retrieval_sources,
            confidence=confidence,
        )
        self.store.save_result(self.job_id, result)
        self.logger.info(
            f"row={ticket.row_id} status={status} area={product_area} type={request_type}"
        )
        return result
