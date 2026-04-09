"""
Developer Service
-----------------
Handles daily summary, sprint summary, and search logic.

NOTE: DB repository calls are stubbed with TODO markers.
      Wire in the actual DynamoDB repository once the DB layer is ready.
"""
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.developer import (
    DailySummaryResponse,
    SearchResponse,
    SprintSummaryResponse,
)
from app.search.search_service import search as semantic_search
from app.utils.logger import logger


class DeveloperService:

    # ── Daily Summary ──────────────────────────────────────────────────────

    async def get_daily_summary(self, user_id: str) -> DailySummaryResponse:
        """
        Fetch the most recently precomputed daily summary for a developer.
        Falls back to a placeholder when no summary exists yet.
        """
        logger.info(f"Fetching daily summary for user_id={user_id}")

        # TODO: replace with actual DynamoDB fetch
        # record = await daily_summary_repo.get_latest(user_id)
        record: Optional[Dict[str, Any]] = None

        if record is None:
            return DailySummaryResponse(
                user_id=user_id,
                date=str(date.today()),
                summary=(
                    "No daily summary has been generated yet for this developer. "
                    "The ingestion and summarization jobs may not have run yet."
                ),
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        return DailySummaryResponse(**record)

    # ── Sprint Summary ─────────────────────────────────────────────────────

    async def get_sprint_summary(
        self, user_id: str, sprint_id: str
    ) -> SprintSummaryResponse:
        """
        Fetch the precomputed sprint summary for a developer and sprint.
        """
        logger.info(
            f"Fetching sprint summary for user_id={user_id} sprint_id={sprint_id}"
        )

        # TODO: replace with actual DynamoDB fetch
        # record = await sprint_summary_repo.get(user_id, sprint_id)
        record: Optional[Dict[str, Any]] = None

        if record is None:
            return SprintSummaryResponse(
                user_id=user_id,
                sprint_id=sprint_id,
                summary=(
                    f"No sprint summary has been generated yet for sprint {sprint_id}. "
                    "The summarization job may not have run yet."
                ),
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        return SprintSummaryResponse(**record)

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
          1. Retrieve structured context from DynamoDB (exact matches).
          2. Retrieve semantic context from vector store (fuzzy matches).
          3. Send combined context + query to LLM.
          4. Return the LLM answer with source references.
        """
        logger.info(
            f"Search query='{query}' user_id={user_id} sprint_id={sprint_id}"
        )

        # TODO: Step 1 – structured retrieval (wire in DynamoDB repo when ready)
        # structured_ctx = await activity_repo.search_structured(
        #     user_id=user_id, sprint_id=sprint_id, query=query, limit=limit
        # )

        # Step 2 & 3 – semantic retrieval + LLM answer (fully wired)
        result = semantic_search(
            query=query,
            user_id=user_id,
            sprint_id=sprint_id,
            k=limit,
        )

        return SearchResponse(
            query=result["query"],
            answer=result["answer"],
            sources=result["sources"],
        )
