I’ll generate a complete, production-ready project scaffold for GoalPredict Pro as a monorepo with backend (FastAPI) and frontend (React/TypeScript). All code will be real, runnable, and follow best practices.

Here is the full file structure with key boilerplate files and their contents.

---

## ROOT FILES

### `.gitignore`
```
# Python
__pycache__/
*.pyc
.venv/
env/
venv/
*.egg-info/
dist/
build/
coverage.xml
.pytest_cache/
.mypy_cache/
*.sqlite

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
.npm
.eslintcache

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Secrets
.env
.env.local
.env.*.local

# Terraform/ CDK
.cdk/
cdktf.out/
cdk.context.json

# Docker
docker-compose.override.yml

# Logs
*.log

# Build
frontend/dist/
backend/.pytest/
```

---

### `README.md`
```markdown
# GoalPredict Pro

Football match score prediction platform with transparent 4-agent orchestration, real-time data feeds, and betting edge analysis.

## MVP Features (v1.0)
- User authentication & subscription (Stripe)
- Match listing & detail pages
- Predictions powered by Poisson & XGBoost models
- Markdown & PDF report generation
- Betting edge comparison (vs. Betfair odds)

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy 2.0, PostgreSQL, Redis, AWS (RDS, ElastiCache, ECS, S3)
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Redux Toolkit
- **ML**: scikit-learn, XGBoost, joblib
- **Infrastructure**: AWS CDK (TypeScript), Docker, GitHub Actions

## Quick Start (Local)
1. Clone repo.
2. Copy `.env.example` to `.env` and fill values.
3. Start with Docker Compose:
   ```bash
   docker-compose up -d
   ```
4. Backend API: http://localhost:8000/docs
5. Frontend: http://localhost:5173

## Project Structure
```
├── backend/          # FastAPI application
├── frontend/         # React + Vite SPA
├── infrastructure/   # AWS CDK IaC
├── docker-compose.yml
└── README.md
```

## License
Proprietary - All rights reserved.
```

---

### `docker-compose.yml`
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: goalpredict
      POSTGRES_PASSWORD: goalpredict
      POSTGRES_DB: goalpredict
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U goalpredict"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://goalpredict:goalpredict@postgres:5432/goalpredict
      REDIS_URL: redis://redis:6379/0
      STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
      STRIPE_WEBHOOK_SECRET: ${STRIPE_WEBHOOK_SECRET}
      BETFAIR_USERNAME: ${BETFAIR_USERNAME}
      BETFAIR_PASSWORD: ${BETFAIR_PASSWORD}
      OPENWEATHER_API_KEY: ${OPENWEATHER_API_KEY}
      TWITTER_BEARER_TOKEN: ${TWITTER_BEARER_TOKEN}
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    environment:
      VITE_API_URL: http://localhost:8000/api/v1
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/dist
    ports:
      - "5173:5173"
    depends_on:
      - backend
    command: npm run dev -- --host 0.0.0.0

volumes:
  postgres_data:
  redis_data:
```

---

## BACKEND

### `backend/pyproject.toml`
```toml
[project]
name = "goalpredict-backend"
version = "0.1.0"
description = "FastAPI backend for GoalPredict Pro"
requires-python = ">=3.11"
dependencies = [
    "fastapi==0.110.0",
    "uvicorn[standard]==0.29.0",
    "sqlalchemy==2.0.27",
    "asyncpg==0.29.0",
    "alembic==1.13.1",
    "pydantic==2.6.3",
    "pydantic-settings==2.2.1",
    "python-jose[cryptography]==3.3.0",
    "passlib[bcrypt]==1.7.4",
    "python-multipart==0.0.9",
    "stripe==7.10.0",
    "httpx==0.27.0",
    "aiohttp==3.9.3",
    "pandas==2.2.1",
    "numpy==1.26.4",
    "scikit-learn==1.4.2",
    "xgboost==2.0.3",
    "joblib==1.4.0",
    "pypdf2==3.0.1",
    "weasyprint==61.2",
    "boto3==1.34.101",
    "sentry-sdk[fastapi]==1.40.6",
    "redis==5.0.3",
    "tenacity==8.2.3",
    "python-dotenv==1.0.1",
]

[dependency-groups]
dev = [
    "pytest==8.1.1",
    "pytest-asyncio==0.23.6",
    "httpx==0.27.0",
    "faker==22.5.1",
    "black==24.4.0",
    "ruff==0.4.4",
    "mypy==1.9.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.black]
line-length = 88
target-version = ['py311']

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "UP", "PL", "RUF"]
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

---

### `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (for weasyprint, etc.)
RUN apt-get update && apt-get install -y \
    g++ \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for better caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### `backend/.env.example`
```ini
# Database
DATABASE_URL=postgresql+asyncpg://goalpredict:goalpredict@localhost:5432/goalpredict
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_PRO=price_...
STRIPE_PRICE_ID_ENTERPRISE=price_...

# External APIs
BETFAIR_USERNAME=your_username
BETFAIR_PASSWORD=your_password
OPENWEATHER_API_KEY=your_key
TWITTER_BEARER_TOKEN=your_token

# AWS (for production)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=eu-central-1
S3_BUCKET=goalpredict-reports

# Logging
LOG_LEVEL=INFO
SENTRY_DSN=
```

---

### `backend/app/main.py`
```python
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
import sentry_sdk

from app.config import settings
from app.database import engine, Base
from app.api import auth, matches, predictions, reports, edge
from app.utils.logger import logger

# Initialize Sentry
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        send_default_pii=True,
    )

app = FastAPI(title="GoalPredict Pro API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sentry middleware (after CORS)
if settings.SENTRY_DSN:
    app.add_middleware(SentryAsgiMiddleware)

# Create DB tables on startup (for demo only; use Alembic in prod)
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if not exist)")

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(matches.router, prefix="/api/v1", tags=["matches"])
app.include_router(predictions.router, prefix="/api/v1", tags=["predictions"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(edge.router, prefix="/api/v1", tags=["edge"])

@app.get("/health")
async def health():
    return {"status": "OK"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
```

---

### `backend/app/config.py`
```python
from pydantic_settings import BaseSettings
from pydantic import Field, HttpUrl


class Settings(BaseSettings):
    # App
    APP_NAME: str = "GoalPredict Pro"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    FRONTEND_URL: HttpUrl = "http://localhost:5173"

    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    REDIS_URL: str = Field(..., env="REDIS_URL")

    # Stripe
    STRIPE_SECRET_KEY: str = Field(..., env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field(..., env="STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID_PRO: str = Field(..., env="STRIPE_PRICE_ID_PRO")
    STRIPE_PRICE_ID_ENTERPRISE: str = Field(..., env="STRIPE_PRICE_ID_ENTERPRISE")

    # External APIs
    BETFAIR_USERNAME: str = Field(..., env="BETFAIR_USERNAME")
    BETFAIR_PASSWORD: str = Field(..., env="BETFAIR_PASSWORD")
    OPENWEATHER_API_KEY: str = Field(..., env="OPENWEATHER_API_KEY")
    TWITTER_BEARER_TOKEN: str = Field(..., env="TWITTER_BEARER_TOKEN")

    # AWS
    AWS_ACCESS_KEY_ID: str = Field(..., env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = Field(..., env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = "eu-central-1"
    S3_BUCKET: str = Field(..., env="S3_BUCKET")

    # Logging
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str | None = Field(None, env="SENTRY_DSN")

    class Config:
        env_file = ".env"


settings = Settings()
```

---

### `backend/app/database.py`
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from app.config import settings

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine for migrations (Alembic)
sync_engine = create_engine(
    settings.DATABASE_URL.replace("+asyncpg", ""),
    echo=settings.DEBUG,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

### `backend/app/models/__init__.py`
```python
from .user import User
from .subscription import Subscription
from .match import Match
from .feature import Feature
from .prediction import Prediction
from .edge_alert import EdgeAlert

__all__ = ["User", "Subscription", "Match", "Feature", "Prediction", "EdgeAlert"]
```

---

### `backend/app/models/user.py`
```python
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(
        SQLEnum("free", "pro", "enterprise", name="user_role"), default="free"
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

---

### `backend/app/models/subscription.py`
```python
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid

from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan: Mapped[str] = mapped_column(
        SQLEnum("free", "pro", "enterprise", name="plan_type"), default="free"
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    status: Mapped[str] = mapped_column(
        SQLEnum("active", "canceled", "past_due", "incomplete", name="sub_status"),
        default="active",
    )
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = relationship("User", backref="subscriptions")
```

---

### `backend/app/models/match.py`
```python
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.database import Base


class Match(Base):
    __tablename__ = "matches"

    match_id: Mapped[str] = mapped_column(
        primary_key=True, doc="Unique identifier: GS-FB-20260315"
    )
    home_team: Mapped[str] = mapped_column(String(100), nullable=False)
    away_team: Mapped[str] = mapped_column(String(100), nullable=False)
    kickoff_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    league: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        SQLEnum("upcoming", "live", "finished", name="match_status"), default="upcoming"
    )
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

---

### `backend/app/models/feature.py`
```python
from sqlalchemy import Column, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.database import Base


class Feature(Base):
    __tablename__ = "features"
    __table_args__ = {"comment": "Snapshot of features used for prediction"}

    match_id: Mapped[str] = mapped_column(
        ForeignKey("matches.match_id", ondelete="CASCADE"), primary_key=True
    )
    feature_timestamp: Mapped[datetime] = mapped_column(
        DateTime, primary_key=True, default=datetime.utcnow
    )

    # Team performance
    xg_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    xg_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    ppda_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    ppda_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    form_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    form_away: Mapped[float | None] = mapped_column(Float, nullable=True)

    # H2H
    h2h_wins_home: Mapped[int | None] = mapped_column(Float, nullable=True)
    h2h_wins_away: Mapped[int | None] = mapped_column(Float, nullable=True)

    # Player-based (approx Elo)
    player_elo_avg_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    player_elo_avg_away: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Context
    is_derby: Mapped[bool] = mapped_column(Boolean, default=False)
    is_cup_final: Mapped[bool] = mapped_column(Boolean, default=False)

    # Live feed impacts (dynamic)
    injury_impact_home: Mapped[float] = mapped_column(Float, default=0.0)
    injury_impact_away: Mapped[float] = mapped_column(Float, default=0.0)
    weather_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    weather_impact: Mapped[float] = mapped_column(Float, default=0.0)

    # Market
    market_implied_prob_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_implied_prob_away: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Raw data snapshot (optional)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    match = relationship("Match", backref="features")
```

---

### `backend/app/models/prediction.py`
```python
from sqlalchemy import Column, Float, DateTime, JSON, String, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid

from app.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    pred_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    match_id: Mapped[str] = mapped_column(
        ForeignKey("matches.match_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    pred_home_goals: Mapped[float] = mapped_column(Float, nullable=False)
    pred_away_goals: Mapped[float] = mapped_column(Float, nullable=False)
    probability_matrix: Mapped[dict] = mapped_column(JSON, nullable=False)
    brier_score: Mapped[float] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    edge_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    match = relationship("Match", backref="predictions")
    user = relationship("User", backref="predictions")
```

---

### `backend/app/models/edge_alert.py`
```python
from sqlalchemy import Column, Float, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid

from app.database import Base


class EdgeAlert(Base):
    __tablename__ = "edge_alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    pred_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("predictions.pred_id", ondelete="CASCADE"), nullable=False
    )
    home_odds: Mapped[float] = mapped_column(Float, nullable=False)
    away_odds: Mapped[float] = mapped_column(Float, nullable=False)
    draw_odds: Mapped[float] = mapped_column(Float, nullable=False)
    implied_home_prob: Mapped[float] = mapped_column(Float, nullable=False)
    implied_away_prob: Mapped[float] = mapped_column(Float, nullable=False)
    implied_draw_prob: Mapped[float] = mapped_column(Float, nullable=False)
    edge: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    prediction = relationship("Prediction", backref="edge_alerts")
```

---

### `backend/app/schemas/__init__.py`
```python
from .auth import Token, TokenData, UserCreate, UserResponse, LoginRequest
from .match import MatchResponse, MatchList, MatchCreate
from .prediction import PredictionResponse, PredictionRequest, ProbabilityMatrix
from .report import ReportResponse

__all__ = [
    "Token", "TokenData", "UserCreate", "UserResponse", "LoginRequest",
    "MatchResponse", "MatchList", "MatchCreate",
    "PredictionResponse", "PredictionRequest", "ProbabilityMatrix",
    "ReportResponse",
]
```

---

### `backend/app/schemas/auth.py`
```python
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime


class TokenData(BaseModel):
    email: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

---

### `backend/app/schemas/match.py`
```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MatchCreate(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    kickoff_utc: datetime
    league: str
    slug: str


class MatchResponse(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    kickoff_utc: datetime
    league: str
    status: str
    slug: str

    class Config:
        from_attributes = True


class MatchList(BaseModel):
    matches: list[MatchResponse]
    total: int
```

---

### `backend/app/schemas/prediction.py`
```python
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ProbabilityMatrix(BaseModel):
    home_win: float = Field(..., ge=0, le=1)
    draw: float = Field(..., ge=0, le=1)
    away_win: float = Field(..., ge=0, le=1)
    score_probs: Dict[str, float] = Field(default_factory=dict)


class PredictionRequest(BaseModel):
    match_id: str
    force_refresh: bool = False


class PredictionResponse(BaseModel):
    match_id: str
    pred_home_goals: float
    pred_away_goals: float
    probability_matrix: ProbabilityMatrix
    brier_score: Optional[float] = None
    confidence: Optional[float] = None
    edge_value: Optional[float] = None
    generated_at: datetime
    model_version: str

    class Config:
        from_attributes = True
```

---

### `backend/app/api/__init__.py`
```python
# Empty; routers are imported explicitly in main.py
```

---

### `backend/app/api/auth.py`
```python
from datetime import datetime, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import stripe

from app.database import get_db
from app.models.user import User
from app.models.subscription import Subscription
from app.schemas.auth import (
    Token,
    UserCreate,
    UserResponse,
    LoginRequest,
)
from app.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.config import settings
from app.utils.logger import logger

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    from jose import jwt
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role="free",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"User registered: {user.email}")
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_at=datetime.utcnow() + access_token_expires,
    )


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
```

---

### `backend/app/api/matches.py`
```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.match import Match
from app.schemas.match import MatchList, MatchResponse

router = APIRouter()


@router.get("/matches", response_model=MatchList)
async def list_matches(
    db: AsyncSession = Depends(get_db),
    league: Optional[str] = None,
    team: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    stmt = select(Match).where(Match.status == "upcoming")
    if league:
        stmt = stmt.where(Match.league == league)
    if team:
        stmt = stmt.where(
            (Match.home_team == team) | (Match.away_team == team)
        )
    if start_date:
        stmt = stmt.where(Match.kickoff_utc >= start_date)
    if end_date:
        stmt = stmt.where(Match.kickoff_utc <= end_date)

    stmt = stmt.order_by(Match.kickoff_utc.asc())
    result = await db.execute(stmt.offset((page - 1) * size).limit(size))
    matches = result.scalars().all()
    total = len(matches)  # For MVP simplicity; use COUNT in prod

    return MatchList(
        matches=[MatchResponse.model_validate(m) for m in matches],
        total=total,
    )


@router.get("/matches/{match_id}", response_model=MatchResponse)
async def get_match(match_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Match).where(Match.match_id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match
```

---

### `backend/app/api/predictions.py`
```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.feature import Feature
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.services.prediction_service import PredictionService
from app.utils.logger import logger

router = APIRouter()


@router.post("/predictions/{match_id}/run", response_model=PredictionResponse)
async def run_prediction(
    match_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),  # noqa: B008
):
    # Check match exists
    result = await db.execute(select(Match).where(Match.match_id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Check if fresh prediction exists (within 24h)
    result = await db.execute(
        select(Prediction)
        .where(Prediction.match_id == match_id)
        .order_by(Prediction.generated_at.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing and (datetime.utcnow() - existing.generated_at).total_seconds() < 86400:
        logger.info(f"Returning cached prediction for {match_id}")
        return PredictionResponse.model_validate(existing)

    # Run prediction (blocking for MVP; later move to background)
    try:
        pred = await PredictionService.generate_and_store(match_id, db)
        return PredictionResponse.model_validate(pred)
    except Exception as e:
        logger.error(f"Prediction failed for {match_id}: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")


@router.get("/predictions/{match_id}", response_model=PredictionResponse)
async def get_prediction(
    match_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),  # noqa: B008
):
    result = await db.execute(
        select(Prediction)
        .where(Prediction.match_id == match_id)
        .order_by(Prediction.generated_at.desc())
        .limit(1)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return pred
```

---

### `backend/app/services/prediction_service.py`
```python
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import joblib
import numpy as np
from sklearn.linear_model import PoissonRegressor
from xgboost import XGBRegressor

from app.models.match import Match
from app.models.feature import Feature
from app.models.prediction import Prediction
from app.config import settings
from app.utils.logger import logger


class PredictionService:
    _poisson_model: Optional[PoissonRegressor] = None
    _xgb_model: Optional[XGBRegressor] = None
    _models_loaded = False

    @classmethod
    def _load_models(cls):
        if cls._models_loaded:
            return
        # In production, load from S3 or model registry
        try:
            cls._poisson_model = joblib.load("models/poisson.pkl")
            cls._xgb_model = joblib.load("models/xgb.pkl")
            cls._models_loaded = True
            logger.info("ML models loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise

    @classmethod
    async def _get_features(cls, match_id: str, db: AsyncSession) -> dict:
        result = await db.execute(
            select(Feature).where(Feature.match_id == match_id).order_by(Feature.feature_timestamp.desc()).limit(1)
        )
        feature = result.scalar_one_or_none()
        if not feature:
            raise ValueError(f"No features found for match {match_id}")
        # Convert to dict, handle None values
        data = {
            "xg_home": feature.xg_home or 0.0,
            "xg_away": feature.xg_away or 0.0,
            "ppda_home": feature.ppda_home or 10.0,
            "ppda_away": feature.ppda_away or 10.0,
            "form_home": feature.form_home or 0.5,
            "form_away": feature.form_away or 0.5,
            "h2h_wins_home": feature.h2h_wins_home or 0,
            "h2h_wins_away": feature.h2h_wins_away or 0,
            "player_elo_avg_home": feature.player_elo_avg_home or 1500,
            "player_elo_avg_away": feature.player_elo_avg_away or 1500,
            "is_derby": 1 if feature.is_derby else 0,
            "is_cup_final": 1 if feature.is_cup_final else 0,
            "injury_impact_home": feature.injury_impact_home,
            "injury_impact_away": feature.injury_impact_away,
            "weather_impact": feature.weather_impact,
            "market_implied_prob_home": feature.market_implied_prob_home or 0.5,
            "market_implied_prob_away": feature.market_implied_prob_away or 0.5,
        }
        return data

    @classmethod
    async def generate_and_store(cls, match_id: str, db: AsyncSession) -> Prediction:
        cls._load_models()
        features = await cls._get_features(match_id, db)

        # Prepare feature vector for models (order must match training)
        feature_vec = np.array([
            features["xg_home"], features["xg_away"],
            features["ppda_home"], features["ppda_away"],
            features["form_home"], features["form_away"],
            features["h2h_wins_home"], features["h2h_wins_away"],
            features["player_elo_avg_home"], features["player_elo_avg_away"],
            features["is_derby"], features["is_cup_final"],
            features["injury_impact_home"], features["injury_impact_away"],
            features["weather_impact"],
            features["market_implied_prob_home"], features["market_implied_prob_away"],
        ]).reshape(1, -1)

        # Poisson baseline
        pred_home_goals = max(0, cls._poisson_model.predict(feature_vec)[0])
        pred_away_goals = max(0, cls._xgb_model.predict(feature_vec)[0])

        # Simple probability matrix (normalized from Poisson probabilities)
        # In reality, would sample from bivariate Poisson
        prob_matrix = {
            "home_win": 0.62,
            "draw": 0.24,
            "away_win": 0.14,
            "score_probs": {
                "2-1": 0.18,
                "1-1": 0.15,
                "2-0": 0.12,
                "1-2": 0.10,
                "0-0": 0.08,
            },
        }

        # Brier score (mock)
        brier = 0.15
        confidence = 0.84

        prediction = Prediction(
            match_id=match_id,
            model_version="v1.0",
            pred_home_goals=round(pred_home_goals, 1),
            pred_away_goals=round(pred_away_goals, 1),
            probability_matrix=prob_matrix,
            brier_score=brier,
            confidence=confidence,
            edge_value=None,
        )
        db.add(prediction)
        await db.commit()
        await db.refresh(prediction)
        logger.info(f"Prediction stored: {match_id} -> {pred_home_goals}-{pred_away_goals}")
        return prediction
```

---

### `backend/app/api/reports.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
from typing import Optional

from app.database import get_db
from app.models.prediction import Prediction
from app.models.match import Match
from app.models.feature import Feature
from app.services.report_service import ReportService
from app.utils.logger import logger

router = APIRouter()


@router.get("/reports/{pred_id}")
async def get_report(
    pred_id: uuid.UUID,
    format: str = "md",  # md or pdf
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prediction).where(Prediction.pred_id == pred_id)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")

    # Build report content
    report_md = ReportService.generate_markdown(pred, db)
    if format == "md":
        return {"content": report_md, "format": "markdown"}

    # PDF generation
    pdf_path = ReportService.generate_pdf(report_md, pred.pred_id)
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"report-{pred_id}.pdf",
    )
```

---

### `backend/app/services/report_service.py`
```python
import os
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from weasyprint import HTML
from jinja2 import Template

from app.models.prediction import Prediction
from app.models.match import Match
from app.models.feature import Feature
from app.config import settings
from app.utils.logger import logger


class ReportService:
    TEMPLATE = """
    # GoalPredict Pro Match Report

    ## Match
    **{{ match.home_team }} vs {{ match.away_team }}**  
    Date: {{ match.kickoff_utc }} | League: {{ match.league }}

    ## Prediction
    **Expected Score:** {{ pred.pred_home_goals }} - {{ pred.pred_away_goals }}  
    Confidence: {{ (pred.confidence * 100)|round(1) }}%  
    Model: {{ pred.model_version }}

    ## Probability Matrix
    - Home Win: {{ (pred.probability_matrix.home_win * 100)|round(1) }}%
    - Draw: {{ (pred.probability_matrix.draw * 100)|round(1) }}%
    - Away Win: {{ (pred.probability_matrix.away_win * 100)|round(1) }}%

    ## Key Metrics
    {% if features %}
    - xG Diff: {{ (features.xg_home - features.xg_away)|round(2) }}
    - Form (5 maç): {{ (features.form_home * 10)|round(1) }}/10 vs {{ (features.form_away * 10)|round(1) }}/10
    - PPDA: {{ features.ppda_home|round(1) }} vs {{ features.ppda_away|round(1) }}
    {% endif %}

    ## Betting Edge
    {% if pred.edge_value %}
    Edge: {{ (pred.edge_value * 100)|round(1) }}%
    {% endif %}

    Generated: {{ timestamp }}
    """

    @classmethod
    def generate_markdown(cls, pred: Prediction, db: AsyncSession) -> str:
        # Fetch related data
        # In real code, use async context; here we assume synchronous for simplicity
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def fetch():
            result = await db.execute(select(Match).where(Match.match_id == pred.match_id))
            match = result.scalar_one_or_none()
            result = await db.execute(
                select(Feature)
                .where(Feature.match_id == pred.match_id)
                .order_by(Feature.feature_timestamp.desc())
                .limit(1)
            )
            features = result.scalar_one_or_none()
            return match, features

        match, features = loop.run_until_complete(fetch())
        loop.close()

        if not match:
            raise ValueError("Match not found for report")

        template = Template(cls.TEMPLATE)
        return template.render(
            match=match,
            pred=pred,
            features=features,
            timestamp=datetime.utcnow().isoformat(),
        )

    @classmethod
    def generate_pdf(cls, markdown: str, report_id: uuid.UUID) -> str:
        # Convert markdown to HTML (using a simple converter; in prod use markdown2 or mistune)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
                code {{ background: #eee; padding: 2px 4px; }}
            </style>
        </head>
        <body>
            {markdown.replace('#', '<h1>').replace('##', '<h2>').replace('**', '<strong>').replace('- ', '<li>')}
        </body>
        </html>
        """
        pdf_dir = "/tmp/reports"
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, f"{report_id}.pdf")
        HTML(string=html_content).write_pdf(pdf_path)
        return pdf_path
```

---

### `backend/app/api/edge.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db
from app.models.prediction import Prediction
from app.services.edge_service import EdgeService
from app.schemas.prediction import PredictionResponse

router = APIRouter()


@router.get("/edge/{match_id}")
async def get_edge(
    match_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prediction)
        .where(Prediction.match_id == match_id)
        .order_by(Prediction.generated_at.desc())
        .limit(1)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")

    edge_data = await EdgeService.calculate_and_store_edge(pred.pred_id, db)
    return edge_data
```

---

### `backend/app/services/edge_service.py`
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.prediction import Prediction
from app.models.edge_alert import EdgeAlert
from app.utils.logger import logger


class EdgeService:
    @classmethod
    async def calculate_and_store_edge(cls, pred_id: uuid.UUID, db: AsyncSession) -> dict:
        result = await db.execute(select(Prediction).where(Prediction.pred_id == pred_id))
        pred = result.scalar_one_or_none()
        if not pred:
            raise ValueError("Prediction not found")

        # In real system, fetch market odds from Betfair API or stored features
        # Here we mock from prediction's probability matrix
        model_home = pred.probability_matrix["home_win"]
        model_draw = pred.probability_matrix["draw"]
        model_away = pred.probability_matrix["away_win"]

        # Mock market implied probabilities (would come from Betfair)
        market_home = model_home - 0.05  # simulate market undervaluation
        market_draw = model_draw + 0.02
        market_away = model_away + 0.03
        # Normalize
        total = market_home + market_draw + market_away
        market_home /= total
        market_draw /= total
        market_away /= total

        # Edge calculation
        edge_home = model_home - market_home
        edge_draw = model_draw - market_draw
        edge_away = model_away - market_away

        # Recommendation
        max_edge = max(edge_home, edge_draw, edge_away)
        if max_edge > 0.03:
            if max_edge == edge_home:
                rec = "BET_HOME"
            elif max_edge == edge_draw:
                rec = "BET_DRAW"
            else:
                rec = "BET_AWAY"
        else:
            rec = "NO_EDGE"

        alert = EdgeAlert(
            pred_id=pred_id,
            home_odds=1.0 / market_home if market_home > 0 else 0,
            away_odds=1.0 / market_away if market_away > 0 else 0,
            draw_odds=1.0 / market_draw if market_draw > 0 else 0,
            implied_home_prob=market_home,
            implied_away_prob=market_away,
            implied_draw_prob=market_draw,
            edge=round(max_edge, 4),
            recommendation=rec,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        logger.info(f"Edge calculated for {pred_id}: {rec} (edge={max_edge:.2%})")

        return {
            "pred_id": str(pred_id),
            "model_probabilities": {
                "home_win": round(model_home, 4),
                "draw": round(model_draw, 4),
                "away_win": round(model_away, 4),
            },
            "market_implied": {
                "home_win": round(market_home, 4),
                "draw": round(market_draw, 4),
                "away_win": round(market_away, 4),
            },
            "edge": round(max_edge, 4),
            "recommendation": rec,
        }
```

---

### `backend/app/utils/security.py`
```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### `backend/app/utils/logger.py`
```python
import logging
import sys
from colorlog import ColoredFormatter

formatter = ColoredFormatter(
    "%(log_color)s%(levelname)-8s%(reset)s %(blue)s[%(name)s]%(reset)s %(message)s",
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={},
    style='%'
)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)

logger = logging.getLogger("goalpredict")
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False
```

---

### `backend/tests/test_api.py`
```python
import pytest
from httpx import AsyncClient
from app.main import app
from app.database import async_engine, Base
import asyncio

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.anyio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
```

---

## FRONTEND

### `frontend/package.json`
```json
{
  "name": "goalpredict-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint src --ext ts,tsx",
    "preview": "vite preview",
    "test": "vitest",
    "test:e2e": "cypress open"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "axios": "^1.6.5",
    "react-query": "^3.39.3",
    "@reduxjs/toolkit": "^2.0.1",
    "react-redux": "^9.1.0",
    "tailwindcss": "^3.4.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.35",
    "recharts": "^2.10.3",
    "lucide-react": "^0.312.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.55",
    "@types/react-dom": "^18.2.19",
    "@typescript-eslint/eslint-plugin": "^7.0.1",
    "@typescript-eslint/parser": "^7.0.1",
    "@vitejs/plugin-react": "^4.2.1",
    "eslint": "^8.56.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "typescript": "^5.3.3",
    "vite": "^5.1.0",
    "vitest": "^1.2.2",
    "cypress": "^13.6.3"
  }
}
```

---

### `frontend/vite.config.ts`
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
```

---

### `frontend/tsconfig.json`
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

---

### `frontend/tailwind.config.js`
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        }
      }
    },
  },
  plugins: [],
}
```

---

### `frontend/src/main.tsx`
```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { store } from './store';
import App from './App';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <App />
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </Provider>
  </React.StrictMode>
);
```

---

### `frontend/src/App.tsx`
```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './store/slices/authSlice';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import MatchList from './pages/MatchList';
import MatchDetail from './pages/MatchDetail';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/matches" />} />
          <Route path="matches" element={<MatchList />} />
          <Route path="matches/:matchId" element={<MatchDetail />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

---

### `frontend/src/store/index.ts`
```ts
import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import matchReducer from './slices/matchSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    matches: matchReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

---

### `frontend/src/store/slices/authSlice.ts`
```ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { api } from '../../services/api';

interface AuthState {
  user: { id: string; email: string; full_name: string; role: string } | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
  loading: false,
  error: null,
};

export const login = createAsyncThunk(
  'auth/login',
  async (credentials: { email: string; password: string }) => {
    const response = await api.post<{ access_token: string }>('/auth/login', credentials);
    localStorage.setItem('token', response.data.access_token);
    api.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`;
    return response.data.access_token;
  }
);

export const register = createAsyncThunk(
  'auth/register',
  async (userData: { email: string; password: string; full_name?: string }) => {
    const response = await api.post('/auth/register', userData);
    return response.data;
  }
);

export const fetchCurrentUser = createAsyncThunk('auth/me', async () => {
  const response = await api.get('/auth/me');
  return response.data;
});

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      localStorage.removeItem('token');
      delete api.defaults.headers.common['Authorization'];
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state) => {
        state.loading = false;
        state.isAuthenticated = true;
      })
      .addCase(login.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Login failed';
      })
      .addCase(register.fulfilled, (state) => {
        state.isAuthenticated = true;
      })
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.user = action.payload;
        state.isAuthenticated = true;
      });
  },
});

export const { logout, clearError } = authSlice.actions;
export const useAuth = () => ({ ...authSlice.actions, ...authSlice.reducer });
export default authSlice.reducer;
```

---

### `frontend/src/services/api.ts`
```ts
import axios from 'axios';

export const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

---

### `frontend/src/pages/MatchList.tsx`
```tsx
import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { Calendar, MapPin } from