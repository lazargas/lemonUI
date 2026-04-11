"""
Search Endpoints
----------------
General-purpose search and RAG endpoints — not tied to any specific entity.
Questions can be about developers, projects, sprints, or anything in the activity data.

POST /api/v1/search           – non-streaming RAG answer (JSON)
GET  /api/v1/generate-answer  – streaming RAG answer (SSE)
"""
import json
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.schemas.developer import SearchRequest, SearchResponse
from app.services.developer_service import DeveloperService

router = APIRouter()
_svc = DeveloperService()


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Natural-language search over all activity data",
    description=(
        "Accepts a free-text question about developers, projects, sprints, or tickets "
        "and returns a natural-language answer backed by semantic retrieval over all "
        "indexed activity data. Optionally filter by userId or sprintId."
    ),
)
async def search(body: SearchRequest):
    return await _svc.search(
        query=body.query,
        user_id=body.user_id,
        sprint_id=body.sprint_id,
        limit=body.limit,
    )


@router.get(
    "/generate-answer",
    summary="Stream a RAG answer for any natural-language question (SSE)",
    description=(
        "Fetches the top-k relevant chunks from OpenSearch via semantic search across "
        "all activity data (developers, projects, sprints, tickets), then streams a "
        "Claude (Bedrock) answer token-by-token using Server-Sent Events.\n\n"
        "Connect with EventSource or `curl -N`. "
        "Each SSE event has one of these types:\n"
        "- `sources` — JSON array of retrieved context chunks (sent first)\n"
        "- `token`   — `{\"text\": \"...\"}` incremental answer chunk\n"
        "- `error`   — `{\"error\": \"...\"}` if something went wrong\n"
        "- `done`    — empty payload, signals end of stream"
    ),
    response_class=StreamingResponse,
)
async def generate_answer(
    question: str = Query(..., description="Natural-language question (about developers, projects, sprints, or tickets)"),
    userId: Optional[str] = Query(None, description="Optional: filter context to a specific developer"),
    sprintId: Optional[str] = Query(None, description="Optional: filter context to a specific sprint"),
    k: int = Query(5, ge=1, le=20, description="Number of context chunks to retrieve (default 5)"),
):
    from app.search.vector_store import similarity_search
    from app.llm.llm_service import generate_stream
    from app.llm.prompts import SEARCH_ANSWER_PROMPT

    async def event_stream() -> AsyncGenerator[str, None]:
        # ── Step 1: Retrieve relevant chunks ──────────────────────────────
        try:
            chunks = similarity_search(
                query=question,
                k=k,
                user_id=userId,
                sprint_id=sprintId,
            )
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
            return

        if not chunks:
            yield "event: error\ndata: {\"error\": \"No relevant context found for this question.\"}\n\n"
            return

        # ── Step 2: Build context string ───────────────────────────────────
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            meta = (
                f"[{i}] ({chunk.get('chunk_type', 'unknown')} | "
                f"{chunk.get('ticket_id', 'N/A')} | "
                f"{chunk.get('created_at', 'N/A')})"
            )
            context_parts.append(f"{meta}\n{chunk['text']}")
        context = "\n\n".join(context_parts)

        # ── Step 3: Emit sources before streaming starts ───────────────────
        sources_payload = json.dumps([
            {
                "text": c.get("text", "")[:200],
                "user_id": c.get("user_id"),
                "sprint_id": c.get("sprint_id"),
                "ticket_id": c.get("ticket_id"),
                "chunk_type": c.get("chunk_type"),
                "score": c.get("score"),
            }
            for c in chunks
        ])
        yield f"event: sources\ndata: {sources_payload}\n\n"

        # ── Step 4: Stream LLM answer token by token ───────────────────────
        prompt = SEARCH_ANSWER_PROMPT.format(query=question, context=context)
        try:
            async for token in generate_stream(prompt, max_tokens=1024):
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
            return

        # ── Step 5: Signal completion ──────────────────────────────────────
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
