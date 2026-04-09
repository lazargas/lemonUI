"""
Developer Service
-----------------
Handles daily summary, sprint summary, and search logic.

DynamoDB reads are wired to the sprint_memory persistence layer.
The search flow uses OpenSearch (semantic) + DynamoDB (structured context).
"""
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.developer import (
    DailySummaryResponse,
    PendingAttentionItem,
    PendingAttentionResponse,
    SearchResponse,
    SprintSummaryResponse,
    StandupHelperResponse,
)
from app.sprint_memory.persistence.user_sprint_context_accessor import UserSprintContextAccessor
from app.sprint_memory.persistence.user_sprint_facts_accessor import UserSprintFactsAccessor
from app.search.search_service import search as semantic_search
from app.utils.logger import logger


class DeveloperService:

    def __init__(self) -> None:
        self._context_accessor = UserSprintContextAccessor()
        self._facts_accessor = UserSprintFactsAccessor()

    # ── Daily Summary ──────────────────────────────────────────────────────

    async def get_daily_summary(self, user_id: str) -> DailySummaryResponse:
        """
        Fetch the most recently precomputed daily summary for a developer.

        We look up the UserSprintContext for the user and return the
        sprint summary / talking points as the daily summary.
        Falls back to a placeholder when no context exists yet.
        """
        logger.info(f"Fetching daily summary for user_id={user_id}")

        # Query the most recent sprint context for this user
        # (scan by pk, take the first result sorted descending by sk)
        from boto3.dynamodb.conditions import Key
        from app.sprint_memory.constants import USER_PREFIX, SPRINT_PREFIX

        pk = f"{USER_PREFIX}{user_id}"
        resp = self._context_accessor.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(SPRINT_PREFIX),
            ScanIndexForward=False,
            Limit=1,
        )

        items = resp.get("Items", [])
        if not items:
            return DailySummaryResponse(
                user_id=user_id,
                date=str(date.today()),
                summary=(
                    "No daily summary has been generated yet for this developer. "
                    "The ingestion and summarization jobs may not have run yet."
                ),
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        from app.sprint_memory.models.user_sprint_context import UserSprintContextItem
        ctx = UserSprintContextItem(**items[0])

        # Build a standup-style summary from the context
        parts: List[str] = []
        if ctx.summary.primary_focus:
            parts.append("Focus: " + ", ".join(ctx.summary.primary_focus))
        if ctx.summary.overall_status:
            parts.append(f"Status: {ctx.summary.overall_status}")
        if ctx.suggested_talking_points:
            parts.append("Talking points: " + "; ".join(ctx.suggested_talking_points[:3]))
        if ctx.blockers:
            parts.append("Blockers: " + "; ".join(ctx.blockers[:3]))

        summary = " | ".join(parts) if parts else (
            f"Sprint context available for user {user_id} sprint {ctx.sprint_id}."
        )

        return DailySummaryResponse(
            user_id=user_id,
            date=str(date.today()),
            summary=summary,
            generated_at=ctx.last_refreshed_at,
        )

    # ── Sprint Summary ─────────────────────────────────────────────────────

    async def get_sprint_summary(
        self, user_id: str, sprint_id: str
    ) -> SprintSummaryResponse:
        """
        Fetch the precomputed sprint summary for a developer and sprint.
        Uses UserSprintContext as the source of truth.
        """
        logger.info(
            f"Fetching sprint summary for user_id={user_id} sprint_id={sprint_id}"
        )

        ctx = self._context_accessor.get_context(user_id, sprint_id)

        if ctx is None:
            return SprintSummaryResponse(
                user_id=user_id,
                sprint_id=sprint_id,
                summary=(
                    f"No sprint summary has been generated yet for sprint {sprint_id}. "
                    "The summarization job may not have run yet."
                ),
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        # Build a sprint summary from the context
        parts: List[str] = []
        if ctx.summary.primary_focus:
            parts.append("Primary focus: " + ", ".join(ctx.summary.primary_focus))
        if ctx.summary.overall_status:
            parts.append(f"Overall status: {ctx.summary.overall_status}")
        if ctx.metrics.active_sim_count:
            parts.append(f"Active SIMs: {ctx.metrics.active_sim_count}")
        if ctx.metrics.active_blocker_count:
            parts.append(f"Blockers: {ctx.metrics.active_blocker_count}")
        if ctx.recent_changes:
            parts.append("Recent changes: " + "; ".join(ctx.recent_changes[:3]))

        summary = " | ".join(parts) if parts else (
            f"Sprint context available for user {user_id} sprint {sprint_id}."
        )

        return SprintSummaryResponse(
            user_id=user_id,
            sprint_id=sprint_id,
            summary=summary,
            generated_at=ctx.last_refreshed_at,
        )

    # ── Search ─────────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        sprint_id: Optional[str] = None,
        limit: int = 5,
    ) -> SearchResponse:
        """
        Perform a natural-language search over developer activity.

        Flow:
          1. Retrieve structured context from DynamoDB (sprint facts).
          2. Retrieve semantic context from OpenSearch (vector search).
          3. Send combined context + query to LLM (Claude on Bedrock).
          4. Return the LLM answer with source references.
        """
        logger.info(
            f"Search query='{query}' user_id={user_id} sprint_id={sprint_id}"
        )

        # Step 1 – structured retrieval from DynamoDB
        structured_snippets: List[str] = []
        if user_id and sprint_id:
            try:
                facts = self._facts_accessor.query_by_sprint(sprint_id=sprint_id, limit=20)
                user_facts = [f for f in facts if f.user_id == user_id]
                for f in user_facts[:5]:
                    structured_snippets.append(
                        f"[{f.fact_type}] {f.summary}"
                    )
            except Exception as exc:
                logger.warning(f"Structured DynamoDB retrieval failed (non-fatal): {exc}")

        # Step 2 & 3 – semantic retrieval + LLM answer (non-fatal if OpenSearch is down)
        try:
            result = semantic_search(
                query=query,
                user_id=user_id,
                sprint_id=sprint_id,
                k=limit,
            )
            semantic_answer = result["answer"]
            sources = result["sources"]
        except Exception as exc:
            logger.error(f"Semantic search failed (non-fatal): {exc}")
            semantic_answer = (
                "Semantic search is temporarily unavailable. "
                "Showing structured context only."
            )
            sources = []

        # Prepend structured context to the answer if available
        if structured_snippets:
            structured_block = "\n".join(structured_snippets)
            answer = f"[Structured context]\n{structured_block}\n\n{semantic_answer}"
        else:
            answer = semantic_answer

        return SearchResponse(
            query=query,
            answer=answer,
            sources=sources,
        )

    # ── Standup Helper ─────────────────────────────────────────────────────

    async def get_standup_helper(
        self, user_id: str, sprint_id: str
    ) -> StandupHelperResponse:
        """
        Return structured standup talking points, risks, and blockers
        directly from the precomputed UserSprintContext.
        """
        logger.info(
            f"Fetching standup helper for user_id={user_id} sprint_id={sprint_id}"
        )

        ctx = self._context_accessor.get_context(user_id, sprint_id)

        if ctx is None:
            return StandupHelperResponse(
                user_id=user_id,
                sprint_id=sprint_id,
                suggested_talking_points=[
                    "No sprint context available yet. Run the summarization job first."
                ],
                risks_to_mention=[],
                blockers=[],
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        risks_to_mention = [r.summary for r in ctx.risks] if ctx.risks else []

        return StandupHelperResponse(
            user_id=user_id,
            sprint_id=sprint_id,
            suggested_talking_points=ctx.suggested_talking_points,
            risks_to_mention=risks_to_mention,
            blockers=ctx.blockers,
            generated_at=ctx.last_refreshed_at,
        )

    # ── Pending Attention ──────────────────────────────────────────────────

    async def get_pending_attention(
        self, user_id: str, sprint_id: str
    ) -> PendingAttentionResponse:
        """
        Return items that need the developer's attention this sprint,
        sourced from the precomputed UserSprintContext.
        """
        logger.info(
            f"Fetching pending attention for user_id={user_id} sprint_id={sprint_id}"
        )

        ctx = self._context_accessor.get_context(user_id, sprint_id)

        if ctx is None:
            return PendingAttentionResponse(
                user_id=user_id,
                sprint_id=sprint_id,
                items=[],
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        items = [
            PendingAttentionItem(
                type=p.type,
                sim_id=p.sim_id,
                summary=p.summary,
            )
            for p in ctx.pending_attention
        ]

        return PendingAttentionResponse(
            user_id=user_id,
            sprint_id=sprint_id,
            items=items,
            generated_at=ctx.last_refreshed_at,
        )
