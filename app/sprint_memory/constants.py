# DynamoDB table names — User layer
SIM_STATE_TABLE = "SimState"
SIM_EVENTS_TABLE = "SimEvents"
USER_SPRINT_FACTS_TABLE = "UserSprintFacts"
USER_SPRINT_CONTEXT_TABLE = "UserSprintContext"

# DynamoDB table names — Project layer
PROJECTS_TABLE = "Projects"
PROJECT_MAPPINGS_TABLE = "ProjectMappings"
PROJECT_FACTS_TABLE = "ProjectFacts"
PROJECT_SPRINT_CONTEXT_TABLE = "ProjectSprintContext"

# Key prefixes
SIM_PREFIX = "SIM#"
USER_PREFIX = "USER#"
SPRINT_PREFIX = "SPRINT#"
PROJECT_PREFIX = "PROJECT#"
EVT_PREFIX = "EVT#"
FACT_PREFIX = "FACT#"

# Fixed sort keys
SIM_STATE_SK = "STATE"
PROJECT_METADATA_SK = "METADATA"

# GSI names
GSI1_NAME = "gsi1pk-gsi1sk-index"
GSI2_NAME = "gsi2pk-gsi2sk-index"
