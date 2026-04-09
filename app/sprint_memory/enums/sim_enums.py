from enum import Enum


class SimEventType(str, Enum):
    SIM_CREATED = "sim_created"
    SIM_STATUS_CHANGED = "sim_status_changed"
    SIM_OWNER_CHANGED = "sim_owner_changed"
    SIM_DESCRIPTION_UPDATED = "sim_description_updated"
    SIM_PRIORITY_CHANGED = "sim_priority_changed"
    SIM_CLOSED = "sim_closed"
    COMMENT_ADDED = "comment_added"


class FactType(str, Enum):
    PROGRESS = "progress"
    BLOCKER = "blocker"
    RISK = "risk"
    DECISION = "decision"
    ACTION_ITEM = "action_item"
    OPEN_QUESTION = "open_question"
    STATUS_CHANGE = "status_change"


class SimStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SimPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActorType(str, Enum):
    OWNER = "owner"
    REPORTER = "reporter"
    COMMENTER = "commenter"


class ProjectFactType(str, Enum):
    PROGRESS = "progress"
    BLOCKER = "blocker"
    RISK = "risk"
    DECISION = "decision"
    DEPENDENCY = "dependency"
    OWNERSHIP_GAP = "ownership_gap"
    OPEN_QUESTION = "open_question"
    STATUS_CHANGE = "status_change"


class ProjectHealth(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class CompletionConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class MappingType(str, Enum):
    EXPLICIT = "explicit"
    LABEL = "label"
    KEYWORD = "keyword"
    AI = "ai"
