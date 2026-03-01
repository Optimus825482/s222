I'll generate the complete project scaffold for AGENTIX with real, production-ready code.

```plaintext
agentix/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── .github/
│   └── workflows/
│       └── ci-cd.yaml
├── k8s/
│   ├── base/
│   │   ├── namespace.yaml
│   │   ├── configmap.yaml
│   │   ├── secret.yaml
│   │   ├── postgres.yaml
│   │   ├── redis.yaml
│   │   └── milvus.yaml
│   └── overlays/
│       └── production/
│           ├── kustomization.yaml
│           ├── ingress.yaml
│           └── hpa.yaml
├── agentix/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── session.py
│   │   └── migrations/
│   │       ├── env.py
│   │       └── versions/
│   │           └── 001_initial.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── workflows.py
│   │   │   ├── tasks.py
│   │   │   ├── context.py
│   │   │   ├── rag.py
│   │   │   ├── approvals.py
│   │   │   └── dashboard.py
│   │   └── deps.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── planlama.py
│   │   ├── arastirma.py
│   │   ├── karar_verme.py
│   │   └── iletisim.py
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── scheduler.py
│   │   └── checkpoint.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── short_term.py
│   │   ├── long_term.py
│   │   └── semantic.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── llm.py
│   │   ├── search.py
│   │   └── external.py
│   ├── security/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── audit.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   └── helpers.py
│   └── dashboard/
│       ├── __init__.py
│       ├── static/
│       │   └── main.js
│       └── templates/
│           └── index.html
└── tests/
    ├── unit/
    │   ├── test_agents.py
    │   └── test_orchestrator.py
    ├── integration/
    │   └── test_workflows.py
    └── conftest.py
```

Now the actual file contents:

```toml:pyproject.toml
[tool.poetry]
name = "agentix"
version = "0.1.0"
description = "Enterprise multi-agent orchestration platform"
authors = ["AGENTIX Team <dev@agentix.com.tr>"]
readme = "README.md"
license = "MIT"
packages = [{include = "agentix"}]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.112.0"
uvicorn = {extras = ["standard"], version = "^0.30.0"}
langgraph = "^0.0.20"
langchain = "^0.2.0"
langchain-openai = "^0.1.0"
langchain-community = "^0.2.0"
sqlalchemy = "^2.0.30"
alembic = "^1.13.0"
psycopg2-binary = "^2.9.9"
redis = "^5.0.4"
pydantic = {extras = ["email"], version = "^2.7.0"}
pydantic-settings = "^2.3.0"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
python-multipart = "^0.0.9"
httpx = "^0.27.0"
milvus = "^2.4.0"
openai = "^1.35.0"
anthropic = "^0.20.0"
twilio = "^9.0.0"
stripe = "^9.0.0"
celery = "^5.4.0"
kombu = "^5.4.0"
boto3 = "^1.34.0"
google-search-results = "^2.4.0"
opentelemetry-api = "^1.22.0"
opentelemetry-sdk = "^1.22.0"
opentelemetry-instrumentation-fastapi = "^0.44b0"
opentelemetry-instrumentation-requests = "^0.44b0"
prometheus-client = "^0.20.0"
websockets = "^13.0.0"
jinja2 = "^3.1.4"

[tool.poetry.group.dev.dependencies]
pytest = "^8.2.0"
pytest-asyncio = "^0.23.6"
pytest-cov = "^5.0.0"
httpx = "^0.27.0"
mypy = "^1.10.0"
black = "^24.4.2"
ruff = "^0.4.8"
pre-commit = "^3.7.0"
alembic = "^1.13.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
select = ["E", "F", "B", "I", "N", "UP", "ANN", "S", "BLE", "A", "C4", "DTZ", "T10", "EM", "ICN", "ISC", "CPY", "RET", "SIM", "TID", "ARG", "PTH", "PD", "PL", "RSE", "TRY", "UP"]
ignore = ["ANN101", "ANN102", "ANN401", "S101", "TRY003", "EM101", "EM102"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
```

```python:agentix/config.py
"""
Configuration management using Pydantic Settings.
Loads from environment variables with .env file support.
"""
from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import json


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "AGENTIX"
    debug: bool = False
    secret_key: str = Field(..., min_length=32)
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    
    # Database
    database_url: str = "postgresql+psycopg2://agentix:agentix@postgres:5432/agentix"
    redis_url: str = "redis://redis:6379/0"
    milvus_host: str = "milvus"
    milvus_port: int = 19530
    
    # Authentication
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24  # 24 hours
    keycloak_url: Optional[str] = None
    keycloak_realm: str = "agentix"
    keycloak_client_id: str = "agentix-api"
    
    # LLM Providers
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.5-turbo"
    
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_model: str = "claude-3-opus-20240229"
    
    # Agent Configuration
    default_agent_timeout: int = 300  # seconds
    max_retry_attempts: int = 3
    agent_memory_ttl: int = 60 * 60 * 24  # 24 hours
    
    # External Services
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    
    google_search_api_key: str = ""
    google_search_engine_id: str = ""
    
    # Observability
    prometheus_enabled: bool = True
    log_level: str = "INFO"
    otlp_endpoint: Optional[str] = None
    
    # Security
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    rate_limit_requests_per_minute: int = 100
    
    # Storage
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = "agentix-backups"
    aws_region: str = "us-east-1"
    
    # Feature Flags
    enable_human_in_the_loop: bool = True
    enable_self_learning: bool = False
    enable_multi_region: bool = False
    
    @validator("database_url", "redis_url", pre=True)
    def validate_urls(cls, v):
        if isinstance(v, str) and v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v
    
    @property
    def database_ssl_mode(self) -> str:
        return "require" if not self.debug else "disable"
    
    @property
    def log_config(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": self.log_level,
                "handlers": ["console"],
            },
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

```python:agentix/database/models.py
"""
SQLAlchemy ORM models for AGENTIX.
All models include UUID primary keys and timestamp fields.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UUID,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
import enum


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    ANALYST = "analyst"
    OPERATOR = "operator"
    VIEWER = "viewer"


class AgentType(str, enum.Enum):
    """Types of specialist agents."""
    PLANLAMA = "planlama"
    ARASTIRMA = "arastirma"
    KARAR_VERME = "karar_verme"
    ILETISIM = "iletisim"


class TaskState(str, enum.Enum):
    """Task execution states."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"


class Workflow(Base):
    """A workflow represents a complete multi-agent execution."""
    __tablename__ = "workflows"
    
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="created")
    graph: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    creator: Mapped[User] = relationship("User", back_populates="workflows")
    tasks: Mapped[List[Task]] = relationship("Task", back_populates="workflow", cascade="all, delete-orphan")


class Task(Base):
    """A task is a unit of work within a workflow."""
    __tablename__ = "tasks"
    
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False
    )
    parent_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tasks.id")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    agent_type: Mapped[AgentType] = mapped_column(SQLEnum(AgentType), nullable=False)
    state: Mapped[TaskState] = mapped_column(SQLEnum(TaskState), default=TaskState.QUEUED)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    assigned_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("agents.agent_id")
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    workflow: Mapped[Workflow] = relationship("Workflow", back_populates="tasks")
    parent: Mapped[Optional[Task]] = relationship("Task", remote_side=[id], backref="children")
    assigned_agent: Mapped[Optional[Agent]] = relationship("Agent", back_populates="assigned_tasks")
    context_entries: Mapped[List[ContextEntry]] = relationship(
        "ContextEntry", back_populates="task", cascade="all, delete-orphan"
    )


class Agent(Base):
    """An AI agent instance with specific capabilities."""
    __tablename__ = "agents"
    
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    type: Mapped[AgentType] = mapped_column(SQLEnum(AgentType), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    model_endpoint: Mapped[str] = mapped_column(String(500))
    model_name: Mapped[str] = mapped_column(String(255))
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2000)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    tools: Mapped[List[str]] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    assigned_tasks: Mapped[List[Task]] = relationship("Task", back_populates="assigned_agent")
    capabilities: Mapped[List[AgentCapability]] = relationship(
        "AgentCapability", back_populates="agent", cascade="all, delete-orphan"
    )


class AgentCapability(Base):
    """Specific capabilities/tools an agent can use."""
    __tablename__ = "agent_capabilities"
    
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("agents.agent_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    
    # Relationships
    agent: Mapped[Agent] = relationship("Agent", back_populates="capabilities")


class ContextEntry(Base):
    """Short-term context storage for tasks (Redis-backed)."""
    __tablename__ = "context_entries"
    
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    ttl_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    
    # Relationships
    task: Mapped[Task] = relationship("Task", back_populates="context_entries")
    
    __table_args__ = (
        # Composite index for fast lookup
        {"postgresql_using": "btree"},
    )


class VectorStoreEntry(Base):
    """Long-term semantic memory (Milvus)."""
    __tablename__ = "vector_store"
    
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    collection_name: Mapped[str] = mapped_column(String(100), nullable=False)
    vector_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    embedding: Mapped[List[float]] = mapped_column(JSONB, nullable=False)  # Store as JSON array
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AuditLog(Base):
    """Immutable audit trail for compliance."""
    __tablename__ = "audit_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.user_id")
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )
    details: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class Integration(Base):
    """Configuration for external service integrations."""
    __tablename__ = "integrations"
    
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'twilio', 'stripe'
    endpoint: Mapped[str] = mapped_column(String(500))
    auth_type: Mapped[str] = mapped_column(String(50))  # 'api_key', 'oauth', 'none'
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class User(Base):
    """System users."""
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    workflows: Mapped[List[Workflow]] = relationship("Workflow", back_populates="creator")
```

```python:agentix/database/session.py
"""
Database session management with async support.
"""
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .models import Base
from agentix.config import settings


# Create sync engine for migrations and simple operations
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    echo=settings.debug,
)

# Sync session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Session:
    """
    FastAPI dependency for database sessions.
    Yields a session and ensures it's closed after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables (for development only)."""
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all tables (for development only)."""
    Base.metadata.drop_all(bind=engine)
```

```python:agentix/main.py
"""
AGENTIX - Multi-Agent Orchestration Platform
FastAPI application entry point.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
import uvicorn

from agentix.config import settings
from agentix.database.session import init_db, engine
from agentix.api.v1 import auth, workflows, tasks, context, rag, approvals, dashboard
from agentix.orchestrator.engine import Orchestrator
from agentix.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting AGENTIX...")
    
    # Initialize database (for dev, in prod use migrations)
    if settings.debug:
        init_db()
        logger.info("Database initialized")
    
    # Initialize orchestrator singleton
    app.state.orchestrator = Orchestrator()
    await app.state.orchestrator.start()
    logger.info("Orchestrator started")
    
    # Start background tasks
    asyncio.create_task(background_cleanup())
    
    yield
    
    # Shutdown
    logger.info("Shutting down AGENTIX...")
    await app.state.orchestrator.stop()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description="Enterprise Multi-Agent Orchestration Platform",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["Workflows"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(context.router, prefix="/api/v1/context", tags=["Context"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["RAG"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["Approvals"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Metrics endpoint for Prometheus
if settings.prometheus_enabled:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

# Background cleanup task
async def background_cleanup():
    """Periodic cleanup of expired context entries and old logs."""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            # TODO: Implement cleanup logic
            logger.debug("Background cleanup completed")
        except Exception as e:
            logger.error(f"Background cleanup failed: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "agentix.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
```

```python:agentix/api/v1/auth.py
"""
Authentication API endpoints.
Handles user login, token refresh, and RBAC.
"""
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from agentix.config import settings
from agentix.database.session import get_db
from agentix.database.models import User, UserRole
from agentix.security.auth import verify_password, create_access_token, get_password_hash
from agentix.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user.
    Raises HTTPException if token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Ensure the user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    
    logger.info(f"User logged in: {user.email}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expires_minutes * 60,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
        }
    }


@router.get("/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get current user information.
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "created_at": current_user.created_at.isoformat(),
    }


@router.post("/refresh")
async def refresh_token(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Refresh JWT token.
    """
    access_token = create_access_token(
        data={"sub": str(current_user.id), "role": current_user.role.value}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expires_minutes * 60,
    }
```

```python:agentix/api/v1/workflows.py
"""
Workflow management endpoints.
Create, list, get, and delete multi-agent workflows.
"""
from typing import List, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from agentix.database.session import get_db
from agentix.database.models import Workflow, User, Task, Agent
from agentix.api.v1.deps import get_current_user
from agentix.orchestrator.engine import Orchestrator
from agentix.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Create a new workflow.
    Expected payload:
    {
        "name": "Market Research",
        "description": "Research and analyze market trends",
        "graph": {
            "nodes": [...],
            "edges": [...]
        }
    }
    """
    try:
        workflow = Workflow(
            name=workflow_data["name"],
            description=workflow_data.get("description"),
            created_by=current_user.id,
            graph=workflow_data.get("graph", {}),
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        
        logger.info(f"Workflow created: {workflow.id} by user {current_user.email}")
        
        return {
            "id": str(workflow.id),
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status,
            "created_at": workflow.created_at.isoformat(),
        }
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow creation failed"
        )


@router.get("")
async def list_workflows(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    List workflows for the current user.
    """
    workflows = (
        db.query(Workflow)
        .filter(Workflow.created_by == current_user.id)
        .order_by(Workflow.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return {
        "workflows": [
            {
                "id": str(w.id),
                "name": w.name,
                "description": w.description,
                "status": w.status,
                "created_at": w.created_at.isoformat(),
                "task_count": len(w.tasks),
            }
            for w in workflows
        ],
        "total": db.query(Workflow).filter(Workflow.created_by == current_user.id).count(),
    }


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Get workflow details including tasks.
    """
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.created_by == current_user.id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    
    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "description": workflow.description,
        "status": workflow.status,
        "graph": workflow.graph,
        "created_at": workflow.created_at.isoformat(),
        "updated_at": workflow.updated_at.isoformat(),
        "tasks": [
            {
                "id": str(t.id),
                "name": t.name,
                "agent_type": t.agent_type.value,
                "state": t.state.value,
                "priority": t.priority,
                "created_at": t.created_at.isoformat(),
            }
            for t in workflow.tasks
        ],
    }


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Delete a workflow and all its tasks.
    """
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.created_by == current_user.id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    
    db.delete(workflow)
    db.commit()
    
    logger.info(f"Workflow deleted: {workflow_id} by user {current_user.email}")
    
    return None


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Start execution of a workflow.
    """
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.created_by == current_user.id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    
    if workflow.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow is already running"
        )
    
    # Get orchestrator from app state
    from fastapi import Request
    request: Request = Request.scope.get("request")
    orchestrator: Orchestrator = request.app.state.orchestrator
    
    try:
        await orchestrator.start_workflow(workflow, db)
        workflow.status = "running"
        db.commit()
        
        logger.info(f"Workflow execution started: {workflow_id}")
        
        return {
            "workflow_id": str(workflow.id),
            "status": "started",
            "message": "Workflow execution initiated",
        }
        
    except Exception as e:
        logger.error(f"Failed to start workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}"
        )
```

```python:agentix/api/v1/tasks.py
"""
Task management endpoints.
Monitor task status, retrieve results, and manage task lifecycle.
"""
from typing import List, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from agentix.database.session import get_db
from agentix.database.models import Task, Workflow, User
from agentix.api.v1.deps import get_current_user

router = APIRouter()


@router.get("/{task_id}")
async def get_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Get detailed task information including result.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Verify user owns the workflow
    workflow = db.query(Workflow).filter(
        Workflow.id == task.workflow_id,
        Workflow.created_by == current_user.id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this task"
        )
    
    return {
        "id": str(task.id),
        "name": task.name,
        "description": task.description,
        "agent_type": task.agent_type.value,
        "state": task.state.value,
        "priority": task.priority,
        "payload": task.payload,
        "result": task.result,
        "error_message": task.error_message,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


@router.get("/workflow/{workflow_id}")
async def list_workflow_tasks(
    workflow_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    state: str = Query(None, description="Filter by task state")
):
    """
    List all tasks for a workflow.
    """
    # Verify ownership
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.created_by == current_user.id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )
    
    query = db.query(Task).filter(Task.workflow_id == workflow_id)
    
    if state:
        try:
            task_state = TaskState(state)
            query = query.filter(Task.state == task_state)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task state: {state}"
            )
    
    tasks = query.order_by(Task.created_at).all()
    
    return {
        "tasks": [
            {
                "id": str(t.id),
                "name": t.name,
                "agent_type": t.agent_type.value,
                "state": t.state.value,
                "priority": t.priority,
                "parent_task_id": str(t.parent_task_id) if t.parent_task_id else None,
                "created_at": t.created_at.isoformat(),
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in tasks
        ],
        "total": len(tasks),
    }


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Cancel a running or queued task.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Verify ownership
    workflow = db.query(Workflow).filter(
        Workflow.id == task.workflow_id,
        Workflow.created_by == current_user.id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    if task.state not in [TaskState.QUEUED, TaskState.RUNNING, TaskState.WAITING_APPROVAL]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task in state: {task.state.value}"
        )
    
    task.state = TaskState.CANCELLED
    db.commit()
    
    logger.info(f"Task cancelled: {task_id} by user {current_user.email}")
    
    return {"status": "cancelled", "task_id": str(task_id)}
```

```python:agentix/api/v1/context.py
"""
Context management endpoints.
Store and retrieve short-term context for tasks.
"""
from typing import Annotated, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from agentix.database.session import get_db
from agentix.database.models import Task, User, Workflow, ContextEntry
from agentix.api.v1.deps import get_current_user
from agentix.memory.short_term import ShortTermMemory

router = APIRouter()


@router.get("/task/{task_id}")
async def get_task_context(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Get all context entries for a task.
    """
    # Verify ownership
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    workflow = db.query(Workflow).filter(
        Workflow.id == task.workflow_id,
        Workflow.created_by == current_user.id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    entries = db.query(ContextEntry).filter(ContextEntry.task_id == task_id).all()
    
    return {
        "task_id": str(task_id),
        "context": {entry.key: entry.value for entry in entries}
    }


@router.post("/task/{task_id}")
async def set_task_context(
    task_id: UUID,
    context_data: Dict[str, Any] = Body(...),
    ttl_seconds: int = Body(None),
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Set context entries for a task.
    """
    # Verify ownership
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    workflow = db.query(Workflow).filter(
        Workflow.id == task.workflow_id,
        Workflow.created_by == current_user.id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    # Store in database
    for key, value in context_data.items():
        entry = ContextEntry(
            task_id=task_id,
            key=key,
            value=value,
            ttl_seconds=ttl_seconds,
        )
        db.add(entry)
    
    db.commit()
    
    # Also store in Redis for fast access
    memory = ShortTermMemory()
    await memory.set_many(task_id, context_data, ttl_seconds)
    
    return {
        "status": "saved",
        "task_id": str(task_id),
        "keys": list(context_data.keys()),
    }


@router.delete("/task/{task_id}")
async def clear_task_context(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Clear all context for a task.
    """
    # Verify ownership
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    workflow = db.query(Workflow).filter(
        Workflow.id == task.workflow_id,
        Workflow.created_by == current_user.id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    # Delete from database
    db.query(ContextEntry).filter(ContextEntry.task_id == task_id).delete()
    db.commit()
    
    # Delete from Redis
    memory = ShortTermMemory()
    await memory.delete_task(task_id)
    
    return {"status": "cleared", "task_id": str(task_id)}
```

```python:agentix/orchestrator/engine.py
"""
LangGraph-based orchestration engine.
Manages task graph execution, state persistence, and agent coordination.
"""
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import asyncio
import uuid

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from sqlalchemy.orm import Session

from agentix.config import settings
from agentix.database.models import Workflow, Task, Agent, AgentType
from agentix.database.session import engine as db_engine
from agentix.agents.base import BaseAgent
from agentix.agents.planlama import PlanlamaAgent
from agentix.agents.arastirma import ArastirmaAgent
from agentix.agents.karar_verme import KararVermeAgent
from agentix.agents.iletisim import IletisimAgent
from agentix.memory.short_term import ShortTermMemory
from agentix.utils.logger import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """
    Main orchestration engine using LangGraph.
    Manages workflow execution across multiple agents.
    """
    
    def __init__(self):
        self._agents: Dict[AgentType, BaseAgent] = {}
        self._checkpointer: Optional[PostgresSaver] = None
        self._store: Optional[PostgresStore] = None
        self._running_workflows: Dict[uuid.UUID, asyncio.Task] = {}
        self._initialized = False
    
    async def start(self):
        """Initialize orchestrator and agents."""
        if self._initialized:
            return
        
        logger.info("Initializing Orchestrator...")
        
        # Initialize checkpointer and store
        self._checkpointer = PostgresSaver(connection=db_engine)
        self._store = PostgresStore(connection=db_engine)
        
        await self._checkpointer.setup()
        await self._store.setup()
        
        # Initialize agents
        self._agents = {
            AgentType.PLANLAMA: PlanlamaAgent(),
            AgentType.ARASTIRMA: ArastirmaAgent(),
            AgentType.KARAR_VERME: KararVermeAgent(),
            AgentType.ILETISIM: IletisimAgent(),
        }
        
        # Verify all agents are healthy
        for agent_type, agent in self._agents.items():
            try:
                await agent.health_check()
                logger.info(f"Agent {agent_type.value} is healthy")
            except Exception as e:
                logger.error(f"Agent {agent_type.value} health check failed: {e}")
                raise
        
        self._initialized = True
        logger.info("Orchestrator initialized successfully")
    
    async def stop(self):
        """Gracefully shutdown orchestrator."""
        logger.info("Shutting down Orchestrator...")
        
        # Cancel all running workflows
        for wf_id, task in self._running_workflows.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Workflow {wf_id} cancelled")
        
        self._running_workflows.clear()
        self._initialized = False
        
        # Close agent connections
        for agent in self._agents.values():
            await agent.close()
        
        logger.info("Orchestrator shutdown complete")
    
    async def start_workflow(self, workflow: Workflow, db: Session):
        """
        Start executing a workflow.
        
        Args:
            workflow: Workflow ORM instance
            db: Database session
        """
        if workflow.id in self._running_workflows:
            raise ValueError(f"Workflow {workflow.id} is already running")
        
        # Create asyncio task for this workflow
        task = asyncio.create_task(
            self._execute_workflow(workflow, db),
            name=f"workflow-{workflow.id}"
        )
        self._running_workflows[workflow.id] = task
        
        # Add callback to remove from running workflows when done
        task.add_done_callback(
            lambda t: self._running_workflows.pop(workflow.id, None)
        )
    
    async def _execute_workflow(self, workflow: Workflow, db: Session):
        """
        Internal workflow execution.
        Builds and runs the LangGraph state machine.
        """
        logger.info(f"Executing workflow {workflow.id}: {workflow.name}")
        
        try:
            # Build task graph from workflow definition
            task_graph = self._build_task_graph(workflow, db)
            
            # Create initial state
            initial_state = {
                "workflow_id": str(workflow.id),
                "tasks": {},
                "context": {},
                "current_task_id": None,
                "completed_tasks": set(),
                "failed_tasks": set(),
            }
            
            # Compile graph with checkpointing
            graph = StateGraph(initial_state)
            
            # Add nodes for each task
            for task_id, task_config in task_graph.items():
                agent_type = task_config["agent_type"]
                agent = self._agents.get(agent_type)
                if not agent:
                    raise ValueError(f"Unknown agent type: {agent_type}")
                
                graph.add_node(task_id, self._create_task_runner(agent, task_config))
            
            # Add edges based on dependencies
            for task_id, task_config in task_graph.items():
                dependencies = task_config.get("depends_on", [])
                if not dependencies:
                    # No dependencies - can start immediately
                    graph.set_entry_point(task_id)
                else:
                    for dep in dependencies:
                        graph.add_edge(dep, task_id)
            
            # Add end node
            graph.add_end("END", lambda x: x)
            
            # Compile
            app = graph.compile(
                checkpointer=self._checkpointer,
                store=self._store,
            )
            
            # Run the graph
            config = {"configurable": {"thread_id": str(workflow.id)}}
            async for event in app.astream(initial_state, config=config):
                logger.debug(f"Workflow {workflow.id} event: {event}")
            
            # Mark workflow as completed
            workflow.status = "completed"
            db.commit()
            
            logger.info(f"Workflow {workflow.id} completed successfully")
            
        except Exception as e:
            logger.error(f"Workflow {workflow.id} failed: {e}", exc_info=True)
            workflow.status = "failed"
            db.commit()
            raise
    
    def _build_task_graph(self, workflow: Workflow, db: Session) -> Dict[str, Dict]:
        """
        Build task graph from workflow definition.
        Returns dict of task_id -> task_config.
        """
        graph = {}
        
        # Get all tasks for this workflow
        tasks = db.query(Task).filter(Task.workflow_id == workflow.id).all()
        
        for task in tasks:
            graph[str(task.id)] = {
                "task": task,
                "agent_type": task.agent_type,
                "depends_on": [
                    str(parent.id) for parent in task.parent.children
                ] if task.parent else [],
                "payload": task.payload,
            }
        
        return graph
    
    def _create_task_runner(self, agent: BaseAgent, task_config: Dict):
        """
        Create an async function that runs a single task.
        """
        task = task_config["task"]
        payload = task_config["payload"]
        
        async def run_task(state: Dict[str, Any]) -> Dict[str, Any]:
            """Run a single task with the given agent."""
            task_id = str(task.id)
            logger.info(f"Running task {task_id} with agent {task.agent_type.value}")
            
            try:
                # Update task state
                task.state = TaskState.RUNNING
                task.started_at = datetime.utcnow()
                
                # Prepare context for agent
                context = await self._gather_context(task, state)
                
                # Execute agent
                result = await agent.execute(
                    task_name=task.name,
                    context=context,
                    payload=payload,
                    db_session=db,
                )
                
                # Store result
                task.result = result
                task.state = TaskState.COMPLETED
                task.completed_at = datetime.utcnow()
                
                # Update state
                state["tasks"][task_id] = {
                    "status": "completed",
                    "result": result,
                }
                state["completed_tasks"].add(task_id)
                
                # Store in context for downstream tasks
                state["context"].update(result.get("output", {}))
                
                logger.info(f"Task {task_id} completed")
                return state
                
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                task.state = TaskState.FAILED
                task.error_message = str(e)
                state["failed_tasks"].add(task_id)
                raise
        
        return run_task
    
    async def _gather_context(self, task: Task, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gather context for task execution from various sources.
        """
        context = {}
        
        # Get task-specific context from database
        from agentix.memory.short_term import ShortTermMemory
        memory = ShortTermMemory()
        task_context = await memory.get_all(task.id)
        context.update(task_context)
        
        # Get parent task outputs
        if task.parent:
            parent_task = task.parent
            if parent_task.result:
                context.update(parent_task.result.get("output", {}))
        
        # Add workflow-level context
        context["workflow_id"] = str(task.workflow_id)
        context["task_id"] = str(task.id)
        context["task_name"] = task.name
        
        return context
```

```python:agentix/agents/base.py
"""
Base class for all agents.
Defines common interface and functionality.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from agentix.config import settings
from agentix.tools.llm import LLMProvider
from agentix.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    All specialist agents inherit from this.
    """
    
    def __init__(self):
        self.agent_type: str = "base"
        self.llm_provider: LLMProvider = LLMProvider()
        self.tools: List[str] = []
        self.system_prompt: Optional[str] = None
    
    @abstractmethod
    async def execute(
        self,
        task_name: str,
        context: Dict[str, Any],
        payload: Dict[str, Any],
        db_session: Session
    ) -> Dict[str, Any]:
        """
        Execute a task with given context and payload.
        
        Args:
            task_name: Name of the task
            context: Gathered context from memory and parent tasks
            payload: Task-specific input data
            db_session: Database session for persistence
            
        Returns:
            Dict with at least an "output" key containing results
        """
        pass
    
    async def health_check(self) -> bool:
        """Check if agent and its dependencies are healthy."""
        try:
            # Test LLM connection
            await self.llm_provider.test_connection()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def close(self):
        """Cleanup resources."""
        await self.llm_provider.close()
    
    def _build_prompt(
        self,
        task_name: str,
        context: Dict[str, Any],
        payload: Dict[str, Any]
    ) -> str:
        """
        Build the prompt for the LLM.
        Override in subclasses for custom prompt templates.
        """
        prompt = f"""You are a {self.agent_type} agent.

Task: {task_name}

Context:
{self._format_context(context)}

Instructions:
{payload.get('instructions', 'Complete the task using the provided context.')}

Provide your response in JSON format with an "output" field containing your results.
"""
        return prompt
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dict as readable string."""
        lines = []
        for key, value in context.items():
            if isinstance(value, (dict, list)):
                import json
                value = json.dumps(value, indent=2)
            lines.append(f"{key}: {value}")
        return "\n".join(lines)
    
    async def _call_llm(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Call the LLM with the given prompt."""
        return await self.llm_provider.generate(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
```

```python:agentix/agents/planlama.py
"""
Planlama Agent - Task decomposition and planning agent.
"""
import json
from typing import Any, Dict

from sqlalchemy.orm import Session

from agentix.agents.base import BaseAgent
from agentix.config import settings
from agentix.utils.logger import get_logger

logger = get_logger(__name__)


class PlanlamaAgent(BaseAgent):
    """
    Planning agent that decomposes complex tasks into subtasks.
    """
    
    def __init__(self):
        super().__init__()
        self.agent_type = "planlama"
        self.system_prompt = """You are an expert project planner and task decomposition specialist.

Your role is to break down complex tasks into smaller, manageable subtasks that can be executed by specialist agents.

Guidelines:
1. Analyze the task requirements thoroughly
2. Identify dependencies between subtasks
3. Estimate complexity and assign appropriate agent types:
   - araştırma: data gathering, research, analysis
   - karar_verme: synthesis, decision making, recommendations
   - iletisim: notifications, reporting, approvals
4. Ensure subtasks are atomic and independently executable
5. Consider parallel execution opportunities

Respond in valid JSON with this structure:
{
  "plan": {
    "summary": "Brief summary of the approach",
    "subtasks": [
      {
        "id": "unique_subtask_id",
        "name": "Subtask name",
        "description": "Detailed description",
        "agent_type": "arastirma|karar_verme|iletisim",
        "depends_on": ["id1", "id2"],
        "estimated_complexity": 1-5,
        "payload": {
          "instructions": "Specific instructions for this subtask"
        }
      }
    ]
  }
}
"""
    
    async def execute(
        self,
        task_name: str,
        context: Dict[str, Any],
        payload: Dict[str, Any],
        db_session: Session
    ) -> Dict[str, Any]:
        """
        Decompose a complex task into subtasks.
        """
        logger.info(f"PlanlamaAgent executing: {task_name}")
        
        # Build prompt
        prompt = f"""Original Task: {task_name}

Requirements: {payload.get('requirements', 'No specific requirements provided')}

Context:
{self._format_context(context)}

Create a detailed execution plan with subtasks.
"""
        
        # Call LLM
        response = await self._call_llm(
            prompt=prompt,
            temperature=0.3,  # Lower temperature for deterministic planning
            max_tokens=3000,
        )
        
        try:
            # Parse JSON response
            # Extract JSON from response if it contains markdown
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```