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
from app.search.vector_store import similarity_search
from app.search.search_service import search as semantic_search
from app.llm.llm_service import generate
from app.llm.prompts import STANDUP_HELPER_PROMPT
from app.utils.logger import logger
from app.core.config import settings

# Constant semantic query used to pull relevant activity chunks for standup
_STANDUP_SEMANTIC_QUERY = (
    "recent work completed, pull requests merged, code reviews, blockers, "
    "risks, decisions made, tickets updated, sprint progress"
)


def _parse_section(llm_response: str, section_header: str) -> List[str]:
    """
    Parse a named section from the LLM response.

    Expects the format:
        SECTION_HEADER:
        - bullet one
        - bullet two

    Returns a list of bullet strings (stripped, no leading dash), max 3 items.
    Filters out "Nothing to report" bullets.
    """
    lines = llm_response.splitlines()
    in_section = False
    bullets: List[str] = []

    for line in lines:
        stripped = line.strip()
        # Detect section header (case-insensitive, with or without trailing colon)
        if stripped.upper().rstrip(":") == section_header.upper():
            in_section = True
            continue
        # Stop at the next section header
        if in_section and stripped and not stripped.startswith("-") and stripped.endswith(":"):
            break
        if in_section and stripped.startswith("-"):
            bullet = stripped.lstrip("-").strip()
            if bullet and bullet.lower() != "nothing to report":
                bullets.append(bullet)
            if len(bullets) >= 3:
                break

    return bullets


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
        Generate an LLM-powered standup update for a developer.

        Flow:
          1. Fetch UserSprintContext from DynamoDB (structured context)
          2. Run a constant semantic query against OpenSearch to get
             relevant recent activity chunks
          3. Feed both into Claude via STANDUP_HELPER_PROMPT
          4. Return the LLM-generated bullet-point standup update

        Debug logging is enabled when DEBUG=true in .env.
        """
        logger.info(
            f"[standup-helper] START user_id={user_id} sprint_id={sprint_id}"
        )

        # ── Step 1: Fetch structured context from DynamoDB ─────────────────
        if settings.DEBUG:
            logger.debug(
                f"[standup-helper] Step 1 — DynamoDB lookup "
                f"pk=USER#{user_id} sk=SPRINT#{sprint_id}"
            )

        ctx = self._context_accessor.get_context(user_id, sprint_id)

        if ctx is None:
            logger.warning(
                f"[standup-helper] No UserSprintContext found for "
                f"user_id={user_id} sprint_id={sprint_id} — returning fallback"
            )
            return StandupHelperResponse(
                user_id=user_id,
                sprint_id=sprint_id,
                suggested_talking_points=["No sprint context available yet. Run the summarization job first."],
                risks_to_mention=[],
                blockers=[],
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        if settings.DEBUG:
            logger.debug(
                f"[standup-helper] DynamoDB context loaded — "
                f"last_refreshed={ctx.last_refreshed_at} "
                f"active_sims={ctx.metrics.active_sim_count} "
                f"blockers={ctx.metrics.active_blocker_count} "
                f"risks={ctx.metrics.active_risk_count} "
                f"recent_facts={ctx.metrics.recent_fact_count}"
            )
            logger.debug(
                f"[standup-helper] Summary status={ctx.summary.overall_status!r} "
                f"focus={ctx.summary.primary_focus}"
            )
            logger.debug(
                f"[standup-helper] Talking points ({len(ctx.suggested_talking_points)}): "
                + " | ".join(f"[{i}] {tp[:80]}" for i, tp in enumerate(ctx.suggested_talking_points))
            )
            logger.debug(
                f"[standup-helper] Active SIMs ({len(ctx.active_sims)}): "
                + " | ".join(f"{s.sim_id}:{s.title[:40]}({s.status})" for s in ctx.active_sims)
            )
            logger.debug(
                f"[standup-helper] Risks ({len(ctx.risks)}): "
                + " | ".join(f"[{r.sim_id}] {r.summary[:80]}" for r in ctx.risks)
            )
            logger.debug(
                f"[standup-helper] Blockers ({len(ctx.blockers)}): "
                + " | ".join(ctx.blockers)
            )
            logger.debug(
                f"[standup-helper] Pending attention ({len(ctx.pending_attention)}): "
                + " | ".join(f"[{p.type}] {p.sim_id}: {p.summary[:60]}" for p in ctx.pending_attention)
            )
            logger.debug(
                f"[standup-helper] Recent changes ({len(ctx.recent_changes)}): "
                + " | ".join(ctx.recent_changes)
            )

        # Build the DynamoDB context block for the prompt
        dynamo_lines: List[str] = []
        dynamo_lines.append(f"Status: {ctx.summary.overall_status}")
        dynamo_lines.append(f"Focus: {', '.join(ctx.summary.primary_focus)}")
        if ctx.suggested_talking_points:
            dynamo_lines.append("Suggested talking points:")
            dynamo_lines.extend(f"  - {tp}" for tp in ctx.suggested_talking_points)
        if ctx.active_sims:
            dynamo_lines.append("Active SIMs:")
            for s in ctx.active_sims:
                progress = "; ".join(s.recent_progress) if s.recent_progress else "no recent progress"
                dynamo_lines.append(f"  - [{s.sim_id}] {s.title} (status={s.status}, priority={s.priority}): {progress}")
        if ctx.risks:
            dynamo_lines.append("Risks:")
            dynamo_lines.extend(f"  - [{r.sim_id}] {r.summary}" for r in ctx.risks)
        if ctx.blockers:
            dynamo_lines.append("Blockers:")
            dynamo_lines.extend(f"  - {b}" for b in ctx.blockers)
        if ctx.pending_attention:
            dynamo_lines.append("Pending action items (things the developer needs to act on):")
            dynamo_lines.extend(f"  - [{p.type}] {p.sim_id}: {p.summary}" for p in ctx.pending_attention)
        if ctx.recent_changes:
            dynamo_lines.append("Recent changes:")
            dynamo_lines.extend(f"  - {c}" for c in ctx.recent_changes)
        dynamo_context = "\n".join(dynamo_lines)

        # ── Step 2: Semantic search for relevant activity chunks ───────────
        if settings.DEBUG:
            logger.debug(
                f"[standup-helper] Step 2 — OpenSearch semantic search "
                f"query='{_STANDUP_SEMANTIC_QUERY[:60]}...' "
                f"user_id={user_id} sprint_id={sprint_id} k=8"
            )

        semantic_chunks: List[str] = []
        try:
            chunks = similarity_search(
                query=_STANDUP_SEMANTIC_QUERY,
                k=8,
                user_id=user_id,
                sprint_id=sprint_id,
            )
            if settings.DEBUG:
                logger.debug(
                    f"[standup-helper] OpenSearch returned {len(chunks)} chunks"
                )
            for i, chunk in enumerate(chunks):
                meta = (
                    f"[{chunk.get('chunk_type', 'unknown')} | "
                    f"{chunk.get('ticket_id', 'N/A')} | "
                    f"score={chunk.get('score', 0):.3f}]"
                )
                semantic_chunks.append(f"{meta}\n{chunk['text']}")
                if settings.DEBUG:
                    logger.debug(
                        f"[standup-helper] chunk[{i}] type={chunk.get('chunk_type')} "
                        f"score={chunk.get('score', 0):.3f} "
                        f"text={chunk['text'][:100]!r}"
                    )
        except Exception as exc:
            logger.warning(
                f"[standup-helper] OpenSearch unavailable (non-fatal): {exc}"
            )

        semantic_context = (
            "\n\n".join(semantic_chunks)
            if semantic_chunks
            else "No semantic activity chunks available."
        )

        # ── Step 3: Generate standup update via LLM ────────────────────────
        if settings.DEBUG:
            logger.debug(
                f"[standup-helper] Step 3 — Calling Bedrock LLM "
                f"dynamo_lines={len(dynamo_lines)} semantic_chunks={len(semantic_chunks)}"
            )

        prompt = STANDUP_HELPER_PROMPT.format(
            user_id=user_id,
            sprint_id=sprint_id,
            dynamo_context=dynamo_context,
            semantic_context=semantic_context,
        )

        try:
            llm_response = generate(prompt, max_tokens=600)
        except Exception as exc:
            logger.error(f"[standup-helper] LLM generation failed: {exc}")
            # Fall back to raw DynamoDB data
            return StandupHelperResponse(
                user_id=user_id,
                sprint_id=sprint_id,
                suggested_talking_points=ctx.suggested_talking_points[:3],
                risks_to_mention=[r.summary for r in ctx.risks][:3],
                blockers=ctx.blockers[:3],
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        if settings.DEBUG:
            logger.debug(
                f"[standup-helper] LLM raw response ({len(llm_response)} chars):\n{llm_response}"
            )

        # ── Step 4: Parse LLM response into structured lists ──────────────
        talking_points = _parse_section(llm_response, "TALKING_POINTS")
        risks_to_mention = _parse_section(llm_response, "RISKS")
        blockers = _parse_section(llm_response, "BLOCKERS")
        pending_items = _parse_section(llm_response, "PENDING_ITEMS")

        if settings.DEBUG:
            logger.debug(
                f"[standup-helper] Parsed — "
                f"talking_points={talking_points} "
                f"risks={risks_to_mention} "
                f"blockers={blockers} "
                f"pending_items={pending_items}"
            )

        logger.info(
            f"[standup-helper] DONE user_id={user_id} sprint_id={sprint_id} "
            f"semantic_chunks={len(semantic_chunks)} "
            f"talking_points={len(talking_points)} "
            f"risks={len(risks_to_mention)} blockers={len(blockers)} "
            f"pending_items={len(pending_items)}"
        )

        return StandupHelperResponse(
            user_id=user_id,
            sprint_id=sprint_id,
            suggested_talking_points=talking_points,
            risks_to_mention=risks_to_mention,
            blockers=blockers,
            pending_items=pending_items,
            generated_at=datetime.now(timezone.utc).isoformat(),
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
