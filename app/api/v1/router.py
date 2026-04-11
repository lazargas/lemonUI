from fastapi import APIRouter

from app.api.v1.endpoints import developer, project, leadership, ingestion, jobs, search, standup

api_router = APIRouter()

# ── Developer APIs ─────────────────────────────────────────────────────────
# GET  /api/v1/daily-summary?userId=
# GET  /api/v1/sprint-summary?userId=&sprintId=
# GET  /api/v1/standup-helper?userId=&sprintId=
api_router.include_router(developer.router, tags=["Developer"])

# ── Search & RAG APIs ──────────────────────────────────────────────────────
# POST /api/v1/search
# GET  /api/v1/generate-answer  (SSE streaming)
api_router.include_router(search.router, tags=["Search"])

# ── Project APIs ───────────────────────────────────────────────────────────
# GET /api/v1/projects?sprintId=
# GET /api/v1/projects/{projectId}/sprint-context?sprintId=
# GET /api/v1/projects/{projectId}/facts?sprintId=
# GET /api/v1/projects/{projectId}/timeline?sprintId=
api_router.include_router(project.router, prefix="/projects", tags=["Projects"])

# ── Leadership APIs ────────────────────────────────────────────────────────
# GET /api/v1/leadership/roadmap-summary?sprintId=
api_router.include_router(leadership.router, prefix="/leadership", tags=["Leadership"])

# ── Ingestion APIs ─────────────────────────────────────────────────────────
# POST /api/v1/ingestion/trigger
# GET  /api/v1/ingestion/status/{jobId}
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["Ingestion"])

# ── Standup Cache APIs ─────────────────────────────────────────────────────
# POST /api/v1/standup/trigger
# GET  /api/v1/standup/cached?userId=&sprintId=
api_router.include_router(standup.router, prefix="/standup", tags=["Standup"])

# ── Background Job Triggers (dev/testing) ─────────────────────────────────
# POST /api/v1/jobs/daily-summary?userId=
# POST /api/v1/jobs/sprint-summary?userId=&sprintId=
# POST /api/v1/jobs/roadmap-summary?sprintId=
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])


# ── Health ping ────────────────────────────────────────────────────────────
@api_router.get("/ping", tags=["Health"])
async def ping():
    return {"ping": "pong"}
