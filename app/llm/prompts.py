"""
Prompt Templates
----------------
Versioned prompt templates for all LLM-generated outputs.
Keep templates here so they can be updated without touching service logic.
"""

# ── Daily Summary ──────────────────────────────────────────────────────────
DAILY_SUMMARY_PROMPT = """You are an engineering assistant that writes concise daily standup summaries.

Given the developer activity below, write a short standup-style summary in first person.
The summary should cover:
- What was worked on yesterday
- What progress was made (e.g. ready for review, merged, blocked)
- Any feedback received or blockers encountered
- What is planned for today (if inferable)

Keep it natural, human, and concise — 3 to 6 sentences. Avoid robotic bullet lists.
If there was no meaningful activity, say so clearly.

Developer: {user_id}
Date: {date}

Activity:
{activity}

Write the standup summary now:"""


# ── Sprint Summary ─────────────────────────────────────────────────────────
SPRINT_SUMMARY_PROMPT = """You are an engineering assistant that writes sprint summaries for developers.

Given the developer's activity across the sprint below, write a concise sprint summary.
The summary should cover:
- Key accomplishments and completed work
- Work still in progress
- Blockers or feedback received during the sprint
- Overall trajectory and progress trend

Keep it professional, clear, and 4 to 8 sentences. Higher-level than a daily standup.
If there was limited activity, say so clearly.

Developer: {user_id}
Sprint: {sprint_id}

Sprint Activity:
{activity}

Write the sprint summary now:"""


# ── Roadmap / Leadership Summary ───────────────────────────────────────────
ROADMAP_SUMMARY_PROMPT = """You are an engineering assistant that writes executive-level roadmap summaries for engineering leadership.

Given the project facts, sprint context, and activity below, write a concise leadership summary.
The summary should cover:
- Overall project health (green / yellow / red and why)
- Major risks and their impact
- Key dependencies that are blocking or at risk
- Important decisions made this sprint
- Overall progress and trajectory

Keep it brief, decisive, and leadership-ready — 5 to 8 sentences.

Sprint: {sprint_id}

Project Data:
{project_data}

Write the leadership roadmap summary now:"""


# ── Search Answer ──────────────────────────────────────────────────────────
SEARCH_ANSWER_PROMPT = """You are an engineering intelligence assistant that answers questions about developer activity.

Use only the context provided below to answer the question. Be direct and concise.
If the context does not contain enough information to answer, say so clearly.
Do not make up information.

Question: {query}

Context:
{context}

Answer:"""
