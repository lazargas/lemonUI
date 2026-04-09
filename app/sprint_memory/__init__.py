"""Sprint Memory — DynamoDB-backed SIM tracking and agent context system.

Tables:
    SimState           — Latest known state per SIM (diff/change detection)
    SimEvents          — Normalized event timeline (append-only history)
    UserSprintFacts    — Interpreted high-signal facts (compressed sprint memory)
    UserSprintContext   — Pre-aggregated agent-serving sprint summary
"""
