# GoalPredict Pro — Implementation Plan (MVP)

**Total estimated effort: 280 hours (≈ 7 weeks @ 40 h/week)**  
**Team: 1 Full‑stack dev, 1 ML engineer, 0.5 DevOps, 0.5 QA**

---

## SPRINT 1 — Foundation & Core Backend (Weeks 1‑2) — 100 h

### Infrastructure & Project Setup
- [ ] **Initialize repo & tooling** (8 h) — monorepo with `frontend/` and `backend/`, ESLint/Prettier, commit conventions.  
  Dependencies: None
- [ ] **AWS CDK IaC** (16 h) — define VPC, ECS cluster, RDS (PostgreSQL), ElastiCache (Redis), S3, CloudFront, ALB, Secrets Manager.  
  Dependencies: None
- [ ] **CI/CD pipeline** (12 h) — GitHub Actions: lint → test → Docker build → push to ECR → ECS deployment (staging).  
  Dependencies: Repo setup, CDK

### Database & Authentication
- [ ] **PostgreSQL schema migration** (8 h) — SQLAlchemy models + Alembic migrations for `users`, `subscriptions`, `matches`, `features`, `predictions`, `edge_alerts`, `logs`.  
  Dependencies: CDK (RDS provisioned)
- [ ] **JWT auth service** (12 h) — FastAPI endpoints `/auth/register`, `/auth/login`; Argon2id password hashing; Redis token storage.  
  Dependencies: DB models
- [ ] **Stripe subscription webhook** (10 h) — handle `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`; update `subscriptions` table.  
  Dependencies: Stripe account, auth service

### Data Ingestion (StatsBomb + Understat)
- [ ] **StatsBomb open‑data loader** (12 h) — script to download latest JSON from GitHub, parse events, shots, lineups; store into `features` table.  
  Dependencies: DB
- [ ] **Understat scraper** (10 h) — async scraper for team/player xG data; enrich `features` with `xg_home`, `xg_away`.  
  Dependencies: DB
- [ ] **Match metadata ingestion** (8 h) — schedule daily job to populate `matches` table from fixture APIs (e.g., football‑data.org).  
  Dependencies: DB

---

## SPRINT 2 — Prediction Pipeline & Frontend Integration (Weeks 3‑4) — 110 h

### ML Pipeline Development
- [ ] **Baseline Poisson model** (16 h) — train on StatsBomb historical data; export with `joblib`; create inference endpoint `/predictions/{match_id}`.  
  Dependencies: Data ingestion, features table
- [ ] **XGBoost ensemble** (20 h) — feature engineering (form, H2H, PPDA, player Elo approx.); train; evaluate against Poisson; package as Docker container.  
  Dependencies: Poisson model, features
- [ ] **Model registry & versioning** (8 h) — store model artifacts in S3; track `model_version` in `predictions` table.  
  Dependencies: XGBoost model

### API & State Management
- [ ] **Predict service integration** (12 h) — FastAPI endpoint triggers pipeline: fetch features → run model → store prediction → return JSON.  
  Dependencies: Poisson, XGBoost, features
- [ ] **Caching layer** (8 h) — Redis cache for prediction results (TTL=24 h); avoid recompute.  
  Dependencies: Predict service
- [ ] **Betfair odds fetcher** (10 h) — async worker to pull market odds; store `market_implied_prob_*` in `features`.  
  Dependencies: Redis, Betfair API credentials

### Frontend (React/TypeScript)
- [ ] **Project scaffolding** (8 h) — Vite + React + TypeScript + Tailwind; routing (React Router); Redux Toolkit store.  
  Dependencies: None
- [ ] **Auth UI** (10 h) — login/register pages; JWT storage (httpOnly cookie); protected routes.  
  Dependencies: Backend auth endpoints
- [ ] **Match listing page** (12 h) — fetch `/api/v1/matches` with filters; display cards; pagination.  
  Dependencies: Match ingestion, API
- [ ] **Match detail & prediction display** (16 h) — fetch prediction; show score, probability matrix, confidence, xG diff, form, H2H.  
  Dependencies: Predict service, caching

---

## SPRINT 3 — Polish, Testing & Deployment (Weeks 5‑6) — 70 h

### Report Generation & Edge Analysis
- [ ] **Markdown report generator** (12 h) — template with agent pipeline steps, metrics, risk factors; endpoint `/reports/{report_id}`.  
  Dependencies: Prediction JSON
- [ ] **PDF rendering** (10 h) — headless Chrome (puppeteer) or WeasyPrint; store PDF in S3; return signed URL.  
  Dependencies: Markdown generator
- [ ] **Betting Edge endpoint** (8 h) — compute `edge = model_prob - implied_prob`; recommendation logic; store in `edge_alerts`.  
  Dependencies: Betfair odds, prediction

### Testing & QA
- [ ] **Unit tests (backend)** (12 h) — Pytest for auth, predict, ingestion, edge (≥ 80% coverage).  
  Dependencies: Core services
- [ ] **Integration tests** (10 h) — FastAPI TestClient for API flows; PostgreSQL test container; Redis mock.  
  Dependencies: Unit tests
- [ ] **E2E tests (frontend)** (8 h) — Cypress for auth, match listing, prediction view, report download.  
  Dependencies: Frontend pages

### Deployment & Documentation
- [ ] **Production CDK deployment** (8 h) — finalize stacks, domain (Route53), ACM cert, ALB listeners, auto‑scaling policies.  
  Dependencies: All services passing tests
- [ ] **Staging environment** (4 h) — separate stack for QA; run smoke tests.  
  Dependencies: Prod CDK
- [ ] **Monitoring & alerts** (6 h) — CloudWatch dashboards (CPU, latency, error rate); Sentry DSN; SNS alerts.  
  Dependencies: Prod deployment
- [ ] **User documentation** (6 h) — README, API docs (OpenAPI), user guide (PDF/HTML).  
  Dependencies: Final UI/UX

---

## DEPENDENCY GRAPH (Simplified)

```
Infrastructure (CDK) → DB (RDS) & Redis → Auth & Stripe → Data ingestion → Features → ML models → Predict service → Frontend → Reports & Edge → Testing → Deployment
```

---

## NOTES & ASSUMPTIONS

1. **Data sources**: StatsBomb open‑data is freely downloadable; Understat scraping may need rate‑limit handling; Betfair requires commercial API access (assume credentials available).  
2. **ML models**: Poisson and XGBoost are sufficient for MVP; Bayesian (PyMC3) deferred to v2.  
3. **Time estimates** include buffer for unexpected issues (e.g., API changes, model tuning).  
4. **Parallelization**: DevOps can start CDK while backend sets up DB; frontend can mock API endpoints until backend ready.  
5. **No mobile app** in MVP; responsive web only.  
6. **No live feed agent** in MVP; only daily batch updates.  

---

## TOTAL HOURS BY SPRINT

- Sprint 1: 100 h  
- Sprint 2: 110 h  
- Sprint 3: 70 h  
- **Total: 280 h**

With a team of 2 FTEs (dev + ML) + part‑time DevOps/QA, this fits within a 6‑week timeline at ~47 h/week per person. Adjust sprint lengths (1‑2 weeks) based on team capacity.