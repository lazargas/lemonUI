from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "FastAPI App"
    PROJECT_DESCRIPTION: str = "A FastAPI backbone application"
    VERSION: str = "0.1.0"

    # API
    API_V1_STR: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCOUNT_ID: str = "375243950000"
    AWS_ENDPOINT_URL: Optional[str] = None   # set to http://localhost:8000 for local DynamoDB

    # DynamoDB
    DYNAMO_TABLE_PREFIX: str = "lemon"

    # Bedrock (LLM)
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    BEDROCK_EMBEDDING_MODEL_ID: str = "amazon.titan-embed-text-v2:0"

    # OpenSearch Serverless
    OPENSEARCH_ENDPOINT: str = ""   # e.g. https://xxxx.us-east-1.aoss.amazonaws.com
    OPENSEARCH_COLLECTION_NAME: str = "lemon-activity"
    OPENSEARCH_INDEX: str = "activity-embeddings"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"   # silently ignore unknown env vars (e.g. EC2_*, API_GATEWAY_URL)


settings = Settings()
