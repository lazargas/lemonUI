"""
Seed script — populates all DynamoDB tables for testing.

User  : bspvaish
Sprint: 0530dc38-0d6f-443c-89c7-c3b3c66698f1

Run:
    python scripts/seed_data.py
"""

import boto3
from decimal import Decimal

REGION = "us-east-1"
USER_ID   = "bspvaish"
SPRINT_ID = "0530dc38-0d6f-443c-89c7-c3b3c66698f1"
PROJECT_ID = "proj-lemon-001"
PROJECT_NAME = "Lemon Developer Intelligence API"
SIM_ID_1 = "sim-apigw-001"
SIM_ID_2 = "sim-dynamo-002"
SIM_ID_3 = "sim-search-003"

NOW       = "2026-04-10T02:00:00Z"
YESTERDAY = "2026-04-09T18:00:00Z"
TWO_DAYS  = "2026-04-08T10:00:00Z"

ddb = boto3.resource("dynamodb", region_name=REGION)


def put(table_name: str, item: dict):
    table = ddb.Table(table_name)
    # Convert floats to Decimal for DynamoDB
    item = _convert(item)
    table.put_item(Item=item)
    print(f"  ✅ {table_name}: {item.get('pk','?')} / {item.get('sk','?')}")


def _convert(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert(i) for i in obj]
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# 1. Projects
# ─────────────────────────────────────────────────────────────────────────────
print("\n📦 Seeding Projects...")
put("Projects", {
    "pk": f"PROJECT#{PROJECT_ID}",
    "sk": "METADATA",
    "entity_type": "project",
    "project_id": PROJECT_ID,
    "project_name": PROJECT_NAME,
    "roadmap_item_id": "roadmap-q2-2026",
    "roadmap_item_title": "Q2 2026 — Developer Intelligence Platform",
    "leadership_owner_user_id": "jsmith",
    "engineering_owner_user_id": USER_ID,
    "product_owner_user_id": "pmguru",
    "description": (
        "A FastAPI-based developer intelligence platform that aggregates SIM activity, "
        "generates daily/sprint summaries using Claude on Bedrock, and provides semantic "
        "search over developer activity via OpenSearch."
    ),
    "status": "IN_PROGRESS",
    "priority": "HIGH",
    "team": "DevEx",
    "program": "Developer Productivity",
    "contributors": [USER_ID, "alice", "bob"],
    "created_at": TWO_DAYS,
    "updated_at": NOW,
})


# ─────────────────────────────────────────────────────────────────────────────
# 2. SimState (3 SIMs owned by bspvaish)
# ─────────────────────────────────────────────────────────────────────────────
print("\n📦 Seeding SimState...")
put("SimState", {
    "pk": f"SIM#{SIM_ID_1}",
    "sk": "STATE",
    "entity_type": "sim_state",
    "sim_id": SIM_ID_1,
    "sprint_id": SPRINT_ID,
    "title": "Implement API Gateway → EC2 integration with nginx proxy",
    "description": (
        "Set up HTTP API Gateway to proxy requests to EC2 FastAPI app via nginx on port 80. "
        "Resolved INTEGRATION_NETWORK_FAILURE by whitelisting AWS API Gateway IP ranges."
    ),
    "status": "IN_REVIEW",
    "priority": "HIGH",
    "owner_user_id": USER_ID,
    "reporter_user_id": "jsmith",
    "labels": ["infrastructure", "api-gateway", "nginx"],
    "team": "DevEx",
    "known_comment_ids": ["cmt-001", "cmt-002"],
    "latest_comment_at": YESTERDAY,
    "latest_sim_updated_at": NOW,
    "created_at": TWO_DAYS,
    "last_seen_at": NOW,
    "version": 3,
})

put("SimState", {
    "pk": f"SIM#{SIM_ID_2}",
    "sk": "STATE",
    "entity_type": "sim_state",
    "sim_id": SIM_ID_2,
    "sprint_id": SPRINT_ID,
    "title": "Optimize DynamoDB query patterns for UserSprintContext",
    "description": (
        "Improve query performance for UserSprintContext table. "
        "Add GSI for sprint-based queries and implement pagination."
    ),
    "status": "IN_PROGRESS",
    "priority": "MEDIUM",
    "owner_user_id": USER_ID,
    "reporter_user_id": USER_ID,
    "labels": ["dynamodb", "performance", "backend"],
    "team": "DevEx",
    "known_comment_ids": ["cmt-003"],
    "latest_comment_at": YESTERDAY,
    "latest_sim_updated_at": YESTERDAY,
    "created_at": TWO_DAYS,
    "last_seen_at": YESTERDAY,
    "version": 2,
})

put("SimState", {
    "pk": f"SIM#{SIM_ID_3}",
    "sk": "STATE",
    "entity_type": "sim_state",
    "sim_id": SIM_ID_3,
    "sprint_id": SPRINT_ID,
    "title": "Integrate OpenSearch semantic search with Bedrock embeddings",
    "description": (
        "Wire up OpenSearch Serverless with Amazon Titan embedding model for semantic search. "
        "Index developer activity events and enable natural language queries."
    ),
    "status": "OPEN",
    "priority": "MEDIUM",
    "owner_user_id": USER_ID,
    "reporter_user_id": "alice",
    "labels": ["opensearch", "bedrock", "search", "embeddings"],
    "team": "DevEx",
    "known_comment_ids": [],
    "latest_comment_at": None,
    "latest_sim_updated_at": TWO_DAYS,
    "created_at": TWO_DAYS,
    "last_seen_at": TWO_DAYS,
    "version": 1,
})


# ─────────────────────────────────────────────────────────────────────────────
# 3. ProjectMappings (SIM → Project)
# ─────────────────────────────────────────────────────────────────────────────
print("\n📦 Seeding ProjectMappings...")
for sim_id, sim_title in [
    (SIM_ID_1, "Implement API Gateway → EC2 integration with nginx proxy"),
    (SIM_ID_2, "Optimize DynamoDB query patterns for UserSprintContext"),
    (SIM_ID_3, "Integrate OpenSearch semantic search with Bedrock embeddings"),
]:
    put("ProjectMappings", {
        "pk": f"SIM#{sim_id}",
        "sk": f"PROJECT#{PROJECT_ID}",
        "entity_type": "project_mapping",
        "sim_id": sim_id,
        "project_id": PROJECT_ID,
        "mapping_type": "explicit",
        "mapping_source": "manual",
        "mapping_confidence": 1.0,
        "sim_title": sim_title,
        "project_name": PROJECT_NAME,
        "gsi1pk": f"PROJECT#{PROJECT_ID}",
        "gsi1sk": f"SIM#{sim_id}",
        "created_at": TWO_DAYS,
        "updated_at": NOW,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 4. SimEvents (activity events for bspvaish)
# ─────────────────────────────────────────────────────────────────────────────
print("\n📦 Seeding SimEvents...")
events = [
    {
        "pk": f"USER#{USER_ID}",
        "sk": f"EVT#{NOW}#{SIM_ID_1}#PR_MERGED#evt-001",
        "entity_type": "sim_event",
        "event_id": "evt-001",
        "source": "sim",
        "user_id": USER_ID,
        "sprint_id": SPRINT_ID,
        "sim_id": SIM_ID_1,
        "sim_title": "Implement API Gateway → EC2 integration with nginx proxy",
        "event_type": "PR_MERGED",
        "event_time": NOW,
        "actor_user_id": USER_ID,
        "actor_type": "developer",
        "content": {
            "pr_title": "fix: update nginx.conf to proxy port 80 → FastAPI:8000",
            "pr_url": "https://github.com/lazargas/lemonUI/pull/42",
            "description": "Fixed nginx configuration to proxy all HTTP requests to FastAPI instead of redirecting to HTTPS. This resolves the API Gateway INTEGRATION_NETWORK_FAILURE.",
        },
        "metadata": {"branch": "fix/nginx-proxy", "files_changed": 2},
        "gsi1pk": f"SIM#{SIM_ID_1}",
        "gsi1sk": f"EVT#{NOW}",
        "gsi2pk": f"SPRINT#{SPRINT_ID}",
        "gsi2sk": f"EVT#{NOW}",
        "created_at": NOW,
    },
    {
        "pk": f"USER#{USER_ID}",
        "sk": f"EVT#{YESTERDAY}#{SIM_ID_1}#BLOCKER_RESOLVED#evt-002",
        "entity_type": "sim_event",
        "event_id": "evt-002",
        "source": "sim",
        "user_id": USER_ID,
        "sprint_id": SPRINT_ID,
        "sim_id": SIM_ID_1,
        "sim_title": "Implement API Gateway → EC2 integration with nginx proxy",
        "event_type": "BLOCKER_RESOLVED",
        "event_time": YESTERDAY,
        "actor_user_id": USER_ID,
        "actor_type": "developer",
        "content": {
            "blocker": "API Gateway INTEGRATION_NETWORK_FAILURE — EC2 security group blocking API Gateway IPs",
            "resolution": "Whitelisted all 16 AWS API Gateway IP ranges for us-east-1 on port 80 in EC2 security group",
        },
        "metadata": {},
        "gsi1pk": f"SIM#{SIM_ID_1}",
        "gsi1sk": f"EVT#{YESTERDAY}",
        "gsi2pk": f"SPRINT#{SPRINT_ID}",
        "gsi2sk": f"EVT#{YESTERDAY}",
        "created_at": YESTERDAY,
    },
    {
        "pk": f"USER#{USER_ID}",
        "sk": f"EVT#{YESTERDAY}#{SIM_ID_2}#CODE_REVIEW#evt-003",
        "entity_type": "sim_event",
        "event_id": "evt-003",
        "source": "sim",
        "user_id": USER_ID,
        "sprint_id": SPRINT_ID,
        "sim_id": SIM_ID_2,
        "sim_title": "Optimize DynamoDB query patterns for UserSprintContext",
        "event_type": "CODE_REVIEW",
        "event_time": YESTERDAY,
        "actor_user_id": "alice",
        "actor_type": "reviewer",
        "content": {
            "pr_title": "feat: add GSI for sprint-based UserSprintContext queries",
            "review_status": "APPROVED",
            "comments": "LGTM — good use of begins_with for sprint prefix queries",
        },
        "metadata": {},
        "gsi1pk": f"SIM#{SIM_ID_2}",
        "gsi1sk": f"EVT#{YESTERDAY}",
        "gsi2pk": f"SPRINT#{SPRINT_ID}",
        "gsi2sk": f"EVT#{YESTERDAY}",
        "created_at": YESTERDAY,
    },
    {
        "pk": f"USER#{USER_ID}",
        "sk": f"EVT#{TWO_DAYS}#{SIM_ID_3}#DESIGN_DOC_UPDATED#evt-004",
        "entity_type": "sim_event",
        "event_id": "evt-004",
        "source": "sim",
        "user_id": USER_ID,
        "sprint_id": SPRINT_ID,
        "sim_id": SIM_ID_3,
        "sim_title": "Integrate OpenSearch semantic search with Bedrock embeddings",
        "event_type": "DESIGN_DOC_UPDATED",
        "event_time": TWO_DAYS,
        "actor_user_id": USER_ID,
        "actor_type": "developer",
        "content": {
            "doc_title": "OpenSearch + Bedrock Embeddings Architecture",
            "summary": "Finalized embedding pipeline: SimEvents → Titan embed-text-v2 → OpenSearch Serverless AOSS collection",
        },
        "metadata": {},
        "gsi1pk": f"SIM#{SIM_ID_3}",
        "gsi1sk": f"EVT#{TWO_DAYS}",
        "gsi2pk": f"SPRINT#{SPRINT_ID}",
        "gsi2sk": f"EVT#{TWO_DAYS}",
        "created_at": TWO_DAYS,
    },
]
for evt in events:
    put("SimEvents", evt)


# ─────────────────────────────────────────────────────────────────────────────
# 5. UserSprintFacts
# ─────────────────────────────────────────────────────────────────────────────
print("\n📦 Seeding UserSprintFacts...")
facts = [
    {
        "pk": f"USER#{USER_ID}",
        "sk": f"FACT#{NOW}#fact-001",
        "entity_type": "sprint_fact",
        "fact_id": "fact-001",
        "user_id": USER_ID,
        "sprint_id": SPRINT_ID,
        "sim_id": SIM_ID_1,
        "sim_title": "Implement API Gateway → EC2 integration with nginx proxy",
        "fact_type": "ACHIEVEMENT",
        "fact_time": NOW,
        "summary": (
            "bspvaish resolved the API Gateway INTEGRATION_NETWORK_FAILURE blocker by "
            "whitelisting 16 AWS API Gateway IP ranges in the EC2 security group and "
            "fixing nginx.conf to proxy port 80 directly to FastAPI instead of redirecting to HTTPS."
        ),
        "details": {
            "impact": "HIGH",
            "sims_unblocked": [SIM_ID_1],
            "pr_merged": "fix/nginx-proxy",
        },
        "evidence_event_ids": ["evt-001", "evt-002"],
        "confidence_score": 0.95,
        "importance_score": 0.9,
        "is_active": True,
        "gsi1pk": f"SPRINT#{SPRINT_ID}",
        "gsi1sk": f"FACT#{NOW}#fact-001",
        "gsi2pk": f"SIM#{SIM_ID_1}",
        "gsi2sk": f"FACT#{NOW}#fact-001",
        "created_at": NOW,
        "updated_at": NOW,
    },
    {
        "pk": f"USER#{USER_ID}",
        "sk": f"FACT#{YESTERDAY}#fact-002",
        "entity_type": "sprint_fact",
        "fact_id": "fact-002",
        "user_id": USER_ID,
        "sprint_id": SPRINT_ID,
        "sim_id": SIM_ID_2,
        "sim_title": "Optimize DynamoDB query patterns for UserSprintContext",
        "fact_type": "PROGRESS",
        "fact_time": YESTERDAY,
        "summary": (
            "bspvaish completed DynamoDB GSI design for UserSprintContext table. "
            "PR approved by alice. Implements begins_with query pattern for sprint-based lookups, "
            "reducing scan operations by ~80%."
        ),
        "details": {
            "pr_status": "APPROVED",
            "reviewer": "alice",
            "performance_improvement": "~80% reduction in scan operations",
        },
        "evidence_event_ids": ["evt-003"],
        "confidence_score": 0.9,
        "importance_score": 0.75,
        "is_active": True,
        "gsi1pk": f"SPRINT#{SPRINT_ID}",
        "gsi1sk": f"FACT#{YESTERDAY}#fact-002",
        "gsi2pk": f"SIM#{SIM_ID_2}",
        "gsi2sk": f"FACT#{YESTERDAY}#fact-002",
        "created_at": YESTERDAY,
        "updated_at": YESTERDAY,
    },
    {
        "pk": f"USER#{USER_ID}",
        "sk": f"FACT#{TWO_DAYS}#fact-003",
        "entity_type": "sprint_fact",
        "fact_id": "fact-003",
        "user_id": USER_ID,
        "sprint_id": SPRINT_ID,
        "sim_id": SIM_ID_3,
        "sim_title": "Integrate OpenSearch semantic search with Bedrock embeddings",
        "fact_type": "RISK",
        "fact_time": TWO_DAYS,
        "summary": (
            "OpenSearch Serverless AOSS collection indexing latency may affect search quality "
            "for real-time developer activity queries. Embedding pipeline not yet tested at scale."
        ),
        "details": {
            "risk_level": "MEDIUM",
            "mitigation": "Add async indexing with retry logic; test with 1000 events before sprint end",
        },
        "evidence_event_ids": ["evt-004"],
        "confidence_score": 0.8,
        "importance_score": 0.7,
        "is_active": True,
        "gsi1pk": f"SPRINT#{SPRINT_ID}",
        "gsi1sk": f"FACT#{TWO_DAYS}#fact-003",
        "gsi2pk": f"SIM#{SIM_ID_3}",
        "gsi2sk": f"FACT#{TWO_DAYS}#fact-003",
        "created_at": TWO_DAYS,
        "updated_at": TWO_DAYS,
    },
]
for fact in facts:
    put("UserSprintFacts", fact)


# ─────────────────────────────────────────────────────────────────────────────
# 6. UserSprintContext  ← powers /daily-summary and /sprint-summary
# ─────────────────────────────────────────────────────────────────────────────
print("\n📦 Seeding UserSprintContext...")
put("UserSprintContext", {
    "pk": f"USER#{USER_ID}",
    "sk": f"SPRINT#{SPRINT_ID}",
    "entity_type": "user_sprint_context",
    "user_id": USER_ID,
    "sprint_id": SPRINT_ID,
    "last_refreshed_at": NOW,
    "summary": {
        "primary_focus": [
            "API Gateway → EC2 integration",
            "DynamoDB query optimization",
            "OpenSearch semantic search architecture",
        ],
        "overall_status": "ON_TRACK",
    },
    "active_sims": [
        {
            "sim_id": SIM_ID_1,
            "title": "Implement API Gateway → EC2 integration with nginx proxy",
            "status": "IN_REVIEW",
            "priority": "HIGH",
            "recent_progress": [
                "Fixed nginx.conf to proxy port 80 → FastAPI:8000",
                "Whitelisted 16 AWS API Gateway IP ranges in EC2 security group",
                "PR merged: fix/nginx-proxy",
            ],
            "last_updated_at": NOW,
        },
        {
            "sim_id": SIM_ID_2,
            "title": "Optimize DynamoDB query patterns for UserSprintContext",
            "status": "IN_PROGRESS",
            "priority": "MEDIUM",
            "recent_progress": [
                "GSI design completed and approved by alice",
                "begins_with query pattern reduces scan ops by ~80%",
            ],
            "last_updated_at": YESTERDAY,
        },
        {
            "sim_id": SIM_ID_3,
            "title": "Integrate OpenSearch semantic search with Bedrock embeddings",
            "status": "OPEN",
            "priority": "MEDIUM",
            "recent_progress": [
                "Architecture doc finalized: Titan embed-text-v2 → AOSS",
            ],
            "last_updated_at": TWO_DAYS,
        },
    ],
    "recent_changes": [
        "Merged PR: fix nginx proxy configuration (port 80 → FastAPI:8000)",
        "Resolved API Gateway INTEGRATION_NETWORK_FAILURE blocker",
        "DynamoDB GSI PR approved by alice",
        "OpenSearch embedding architecture finalized",
    ],
    "pending_attention": [
        {
            "type": "REVIEW_NEEDED",
            "sim_id": SIM_ID_2,
            "summary": "DynamoDB GSI PR approved — ready to merge and deploy",
        },
    ],
    "suggested_talking_points": [
        "API Gateway is now fully connected to EC2 via nginx proxy on port 80",
        "Resolved INTEGRATION_NETWORK_FAILURE by whitelisting AWS API Gateway IP ranges",
        "DynamoDB query optimization PR approved — ~80% reduction in scan operations",
        "OpenSearch semantic search architecture finalized, implementation starting next",
        "3 active SIMs in sprint, all on track",
    ],
    "risks": [
        {
            "sim_id": SIM_ID_3,
            "summary": "OpenSearch indexing latency may affect real-time search quality — needs load testing",
        },
    ],
    "blockers": [],
    "metrics": {
        "active_sim_count": 3,
        "active_blocker_count": 0,
        "active_risk_count": 1,
        "recent_fact_count": 3,
    },
    "created_at": TWO_DAYS,
    "updated_at": NOW,
})


# ─────────────────────────────────────────────────────────────────────────────
# 7. ProjectFacts
# ─────────────────────────────────────────────────────────────────────────────
print("\n📦 Seeding ProjectFacts...")
put("ProjectFacts", {
    "pk": f"PROJECT#{PROJECT_ID}",
    "sk": f"FACT#{NOW}#pfact-001",
    "entity_type": "project_fact",
    "fact_id": "pfact-001",
    "project_id": PROJECT_ID,
    "project_name": PROJECT_NAME,
    "sprint_id": SPRINT_ID,
    "fact_type": "MILESTONE",
    "fact_time": NOW,
    "summary": (
        "Lemon API is now fully accessible via AWS API Gateway HTTPS endpoint. "
        "End-to-end flow: Client → HTTPS → API Gateway → HTTP:80 → nginx → FastAPI:8000 → DynamoDB/Bedrock. "
        "All infrastructure deployed via CDK."
    ),
    "details": {
        "api_gateway_url": "https://id0318digk.execute-api.us-east-1.amazonaws.com",
        "ec2_instance": "i-0c98f7b176b6725e3",
        "milestone": "Infrastructure complete",
    },
    "source_sim_ids": [SIM_ID_1],
    "source_user_ids": [USER_ID],
    "evidence_event_ids": ["evt-001", "evt-002"],
    "confidence_score": 0.95,
    "importance_score": 0.95,
    "is_active": True,
    "gsi1pk": f"SPRINT#{SPRINT_ID}",
    "gsi1sk": f"FACT#{NOW}#pfact-001",
    "created_at": NOW,
    "updated_at": NOW,
})

put("ProjectFacts", {
    "pk": f"PROJECT#{PROJECT_ID}",
    "sk": f"FACT#{YESTERDAY}#pfact-002",
    "entity_type": "project_fact",
    "fact_id": "pfact-002",
    "project_id": PROJECT_ID,
    "project_name": PROJECT_NAME,
    "sprint_id": SPRINT_ID,
    "fact_type": "RISK",
    "fact_time": YESTERDAY,
    "summary": (
        "OpenSearch Serverless AOSS collection not yet load-tested. "
        "Semantic search quality for developer activity queries is unverified at scale. "
        "Risk: search feature may not be production-ready by sprint end."
    ),
    "details": {
        "risk_level": "MEDIUM",
        "owner": USER_ID,
        "mitigation": "Schedule load test with 1000 events before sprint end",
    },
    "source_sim_ids": [SIM_ID_3],
    "source_user_ids": [USER_ID],
    "evidence_event_ids": ["evt-004"],
    "confidence_score": 0.8,
    "importance_score": 0.7,
    "is_active": True,
    "gsi1pk": f"SPRINT#{SPRINT_ID}",
    "gsi1sk": f"FACT#{YESTERDAY}#pfact-002",
    "created_at": YESTERDAY,
    "updated_at": YESTERDAY,
})


# ─────────────────────────────────────────────────────────────────────────────
# 8. ProjectSprintContext  ← powers /leadership/roadmap
# ─────────────────────────────────────────────────────────────────────────────
print("\n📦 Seeding ProjectSprintContext...")
put("ProjectSprintContext", {
    "pk": f"PROJECT#{PROJECT_ID}",
    "sk": f"SPRINT#{SPRINT_ID}",
    "entity_type": "project_sprint_context",
    "project_id": PROJECT_ID,
    "project_name": PROJECT_NAME,
    "sprint_id": SPRINT_ID,
    "last_refreshed_at": NOW,
    "summary": {
        "overall_status": "Infrastructure complete, feature development in progress",
        "health": "GREEN",
        "completion_confidence": "HIGH",
    },
    "active_users": [
        {"user_id": USER_ID, "role": "engineering_owner", "focus_area": "API Gateway, DynamoDB, OpenSearch"},
        {"user_id": "alice", "role": "contributor", "focus_area": "Code review, DynamoDB"},
        {"user_id": "bob", "role": "contributor", "focus_area": "Frontend integration"},
    ],
    "active_sims": [
        {
            "sim_id": SIM_ID_1,
            "title": "Implement API Gateway → EC2 integration with nginx proxy",
            "status": "IN_REVIEW",
            "owner_user_id": USER_ID,
            "last_updated_at": NOW,
        },
        {
            "sim_id": SIM_ID_2,
            "title": "Optimize DynamoDB query patterns for UserSprintContext",
            "status": "IN_PROGRESS",
            "owner_user_id": USER_ID,
            "last_updated_at": YESTERDAY,
        },
        {
            "sim_id": SIM_ID_3,
            "title": "Integrate OpenSearch semantic search with Bedrock embeddings",
            "status": "OPEN",
            "owner_user_id": USER_ID,
            "last_updated_at": TWO_DAYS,
        },
    ],
    "recent_changes": [
        "API Gateway fully connected to EC2 — HTTPS endpoint live",
        "nginx proxy configuration fixed (port 80 → FastAPI:8000)",
        "DynamoDB GSI optimization approved, ready to deploy",
        "OpenSearch embedding architecture finalized",
    ],
    "risks": [
        {
            "summary": "OpenSearch semantic search not load-tested — may not be production-ready by sprint end",
            "severity": "MEDIUM",
        },
    ],
    "blockers": [],
    "dependencies": [
        {"summary": "OpenSearch AOSS collection must be indexed before search feature can be tested"},
    ],
    "leadership_summary": {
        "one_liner": "Lemon API infrastructure is complete and live; 3 features in active development, all on track.",
        "what_changed": [
            "API Gateway HTTPS endpoint is now live and routing to EC2",
            "Resolved infrastructure blocker: nginx proxy + security group configuration",
            "DynamoDB query optimization approved — 80% performance improvement",
        ],
        "needs_attention": [
            "OpenSearch semantic search needs load testing before sprint end",
        ],
    },
    "metrics": {
        "active_sim_count": 3,
        "active_user_count": 3,
        "active_risk_count": 1,
        "active_blocker_count": 0,
    },
    "created_at": TWO_DAYS,
    "updated_at": NOW,
})


print("\n✅ All seed data written successfully!")
print(f"\nTest these endpoints:")
print(f"  GET  /api/v1/developer/{USER_ID}/daily-summary")
print(f"  GET  /api/v1/developer/{USER_ID}/sprint/{SPRINT_ID}/summary")
print(f"  GET  /api/v1/leadership/roadmap/{SPRINT_ID}")
print(f"  POST /api/v1/search  body: {{\"query\": \"what is bspvaish working on?\", \"user_id\": \"{USER_ID}\", \"sprint_id\": \"{SPRINT_ID}\"}}")
