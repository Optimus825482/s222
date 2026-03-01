## GoalPredict Pro – Technical Architecture Document  
**Version:** 1.0 **Date:** 01 Mar 2026  

---

### 1. Recommended Technology Stack  

| Layer | Technology | Why It’s Chosen (Key Benefits) |
|-------|------------|--------------------------------|
| **Frontend** | **React 18** + **TypeScript** + **React‑Query** + **Tailwind CSS** | • Strong typing avoids runtime errors (critical for numeric predictions). <br>• React‑Query handles async fetches with built‑in caching & stale‑while‑revalidate. <br>• Tailwind gives rapid UI styling with utility‑first approach. |
| **State Management** | **Redux Toolkit** (optional) | Central store for authenticating user, current match selection, and UI notifications. |
| **Backend API** | **FastAPI 0.110** (Python 3.11) | • Asynchronous, production‑grade. <br>• Automatic OpenAPI docs (Swagger) for easy testing. <br>• Pydantic models map directly to DB schemas & request validation. |
| **Data Layer** | **SQLAlchemy (async)** + **PostgreSQL 15** (managed on **Amazon RDS**) | • ACID compliance for transactional data (predictions, user balances). <br>• Rich SQL features for complex analytics. |
| **Cache / Session Store** | **Redis 7** (managed on **AWS ElastiCache**) | Fast look‑up of auth tokens, user preferences, and prediction‑caching. |
| **ML / Model Hosting** | **scikit‑learn**, **XGBoost**, **PyMC3** (Docker‑packaged) | • Proven libraries for baseline Poisson/XGBoost models and Bayesian inference. <br>• Containerised deployment enables easy scaling and versioning. |
| **Monitoring / Logging** | **AWS CloudWatch** + **Sentry** | Automatic metrics & tracing; error alerts for critical failure paths. |
| **CI/CD** | **GitHub Actions** → **Docker Build** → **AWS ECR → ECS (Fargate)** | Zero‑downtime, reproducible builds; automatic rollback on failed health checks. |
| **Payments** | **Stripe Checkout** (PCI‑DSS‑compliant) | Subscription billing, secure card handling, webhook for plan changes. |
| **Infrastructure as Code** | **AWS CDK (Python)** | IaC ensures repeatable environments (VPC, ALB, RDS, ECS, ElastiCache). |
| **API Documentation** | **FastAPI generate‑swagger‑ui** | Interactive docs, versioning, request/response examples reachable at `/docs`. |
| **Container Registry** | **Amazon ECR** | Private, fully managed image repository. |
| **Notification Service** | **AWS SNS** + **NLP‑driven sentiment analysis on Twitter** | Real‑time alerts for s‑injury, form spikes, or market edge changes. |
| **Data Enrichment (Live Feed Agent)** | **AsyncIO** + **aiohttp** (Python) + **polyglot‑nlp** (BERT‑based) | Non‑blocking I/O for simultaneous calls to SofaScore, OpenWeather, Betfair, Twitter APIs. |

---

### 2. System Architecture (Textual Diagram)

```mermaid
flowchart TD
    %% CLIENTS
    subgraph CLIENT[Web / Mobile Client]
        UI[User Interface]
        Auth[Auth & Billing]
    end

    %% API GATEWAY
    GW[REST API Gateway (FastAPI)]

    %% AUTH SERVICE
    AuthN[Auth Service (JWT + Stripe)]

    %% CORE SERVICES
    ML[Predict Service (Containerized Models)]
    STATE[State Service (Redis / Postgres)]
    FEED[Live Feed Agent (Async Workers)]
    BN[Betting Edge Service]

    %% INTEGRATIONS
    PG[PostgreSQL (RDS)]
    RC[Redis (ElastiCache)]
    ECS[ECS/Fargate]
    CW[CloudWatch]

    %% EXTERNAL APIs
    SFS[SofaScore API]
    OB[Opta/Betfair API]
    UND[Understat Alexa/CSV]
    TS[Transfermarkt Scraper]
    GOV[OpenWeather API]
    TW[Twitter API (v2)]

    %% Linking
    UI --> GW
    Auth --> AuthN
    GW --> ML
    GW --> FEED
    GW --> BN
    FEED --> STATE
    BN --> STATE
    STATE --> ML
    ML --> PG
    ML --> RC
    FEED --> SFS
    FEED --> OB
    FEED --> UND
    FEED --> TS
    FEED --> GOV
    FEED --> TW
    AuthN --> GW

    style CLIENT fill:#f9f,stroke:#333,stroke-width:2px
    style GW fill:#bbf,stroke:#333,stroke-width:2px
    style AuthN fill:#bbf,stroke:#333,stroke-width:2px
    style ML fill:#bfb,stroke:#333,stroke-width:2px
    style STATE fill:#ffb,stroke:#333,stroke-width:2px
    style FEED fill:#bfb,stroke:#333,stroke-width:2px
    style BN fill:#bfb,stroke:#333,stroke-width:2px
    style PG fill:#dfd,stroke:#333,stroke-width:2px
    style RC fill:#dfd,stroke:#333,stroke-width:2px
    style ECS fill:#dfd,stroke:#333,stroke-width:2px
    style CW fill:#cfc,stroke:#333,stroke-width:2px
    style SFS fill:#cce,stroke:#333,stroke-width:2px
    style OB fill:#cce,stroke:#333,stroke-width:2px
    style UND fill:#cce,stroke:#333,stroke-width:2px
    style TS fill:#cce,stroke:#333,stroke-width:2px
    style GOV fill:#cce,stroke:#333,stroke-width:2px
    style TW fill:#cce,stroke:#333,stroke-width:2px
```

**Explanation of Flow:**

1. **Client → API Gateway** – All UI requests (auth, match selection, report download) are funneled through FastAPI.  
2. **Auth Service** validates JWT and checks subscription status before forwarding the request.  
3. **Live Feed Agent** (asynchronous workers) poll external data sources every few minutes and push updates to **Redis**.  
4. **Predict Service** consumes the *state* (features, live feed data) and runs the suitable ML model (Poisson baseline, XGBoost, or ensemble).  
5. **Betting Edge Service** compares predicted probabilities with market odds fetched from Betfair, calculates edge, and stores the result.  
6. **State Service** persists user, match, prediction, and edge metadata to PostgreSQL and caches frequently accessed look‑ups in Redis.  
7. The final **report** is generated on‑the‑fly by the UI from the prediction JSON and markdown templates, then served as PDF/HTML.  

---

### 3. Database Schema  

| Table | Primary Key | Important Columns | Relationship |
|-------|-------------|-------------------|--------------|
| **users** | `id` (UUID) | `email`, `hashed_password`, `role` (enum: free/pro, enterprise), `stripe_customer_id`, `created_at`, `updated_at` | 1‑M → **subscriptions** |
| **subscriptions** | `id` (UUID) | `user_id`, `plan` (enum: free/pro/enterprise), `stripe_subscription_id`, `status`, `created_at`, `current_period_end` | FK → `users.id` |
| **matches** | `match_id` (string, e.g., `GS-FB-20260315`) | `home_team`, `away_team`, `kickoff_utc`, `league`, `status` (`upcoming|live`), `slug` | Many‑to‑many with **predictions** |
| **data_sources** | `source_id` (int) | `name`, `type` (`statsbomb|understat|transfermarkt|sofascore|openweather|twitter|betfair`), `enabled` | Used by **LiveFeedAgent** |
| **features** | `match_id`, `feature_timestamp` (PK composite) | `xg_home`, `xg_away`, `ppda_home`, `ppda_away`, `form_home`, `form_away`, `h2h_wins_home`, `h2h_wins_away`, `player_elo_avg_home`, `player_elo_avg_away`, `is_derby`, `is_cup_final`, `injury_impact_home`, `injury_impact_away`, `weather_code`, `market_implied_prob_home`, `market_implied_prob_away` | FK → `matches.match_id` |
| **predictions** | `pred_id` (UUID) | `match_id`, `user_id`, `model_version`, `pred_home_goals`, `pred_away_goals`, `probability_matrix` (JSON), `brier_score`, `confidence`, `edge_value`, `generated_at` | FK → `matches.match_id`, FK → `users.id` |
| **edge_alerts** | `alert_id` (UUID) | `pred_id`, `home_odds`, `away_odds`, `implied_home_prob`, `edge`, `recommendation` | FK → `predictions.pred_id` |
| **logs** | `log_id` (UUID) | `timestamp`, `level` (`INFO|WARN|ERROR`), `module`, `message`, `request_id` | Used for audit & Sentry correlation |

**Notes:**  
* All JSON fields stored in PostgreSQL using the **JSONB** type for efficient querying.  
* Timestamps stored in **UTC** (ISO‑8601); UI converts to local time.  
* Soft‑delete (`is_deleted` flag) on **users** and **matches** for compliance.

---

### 4. API Endpoints (REST)  

| Method | Endpoint | Auth Requirement | Purpose | Sample Response |
|--------|----------|------------------|---------|-----------------|
| `POST` | `/api/v1/auth/register` | — | New account creation | `{ "user_id": "..."} ` |
| `POST` | `/api/v1/auth/login` | — | Issue JWT + refresh token | `{ "access_token": "..."} ` |
| `GET` | `/api/v1/matches` | JWT | List upcoming matches, filter by league/date/team | `{ "matches": [ { "match_id":"GS-FB-20260315", "kickoff":"2026-03-15T20:00:00Z", ... } ] }` |
| `GET` | `/api/v1/matches/{match_id}` | JWT | Retrieve match metadata | Same as above + expanded team info |
| `GET` | `/api/v1/predictions/{match_id}` | JWT | Current prediction (cached if valid) | `{ "pred_home_goals": 1.8, "pred_away_goals": 1.3, "confidence": 0.84, ... }` |
| `POST` | `/api/v1/predictions/{match_id}/run` | JWT | Manually trigger the full 4‑agent pipeline for this match | `{ "status":"completed", "report_url":"..."} ` |
| `GET` | `/api/v1/reports/{report_id}` | JWT | Download Markdown or PDF/HTML report | `{ "content_md":"# Report …", "content_pdf":"..."} ` |
| `GET` | `/api/v1/edge/{match_id}` | JWT | Retrieve betting‑edge calculation & recommendation | `{ "edge_value":0.045, "recommendation":"BET_HOME_WITH_STAKE_2%"} ` |
| `GET` | `/api/v1/health` | — | Liveness / readiness probe | `{ "status":"OK"} ` |
| `POST` | `/api/v1/subscriptions/cancel` | JWT (Pro/Enterprise) | Cancel active subscription | `{ "status":"canceled"} ` |
| `GET` | `/api/v1/metrics` | Internal (admin) | Export Prometheus‑compatible metrics (for autoscaling) | `{ "cpu": 0.23, "requests_pending":5,...} ` |

*All endpoints support OpenAPI spec generation (`/openapi.json`).*  
*Rate‑limiting middleware (100 req/min per token) is enforced. Payloads are validated with Pydantic schemas.*

---

### 5. Authentication & Authorization Strategy  

| Aspect | Detail |
|--------|--------|
| **Auth Method** | **JWT (v1.0)** – signed with RS256 using an RSA key pair stored in AWS Secrets Manager. <br>Refresh tokens stored encrypted in Redis, revoked on logout. |
| **Roles** | `free` (no payment), `pro` (single subscription), `enterprise` (B2B API). |
| **Permissions** | Middleware checks subscription status before granting access to premium endpoints (`/predictions/*/run`, `/edge/*`). |
| **Password Policy** | Minimum 8 characters, [a-zA-Z0-9] + one special, stored with Argon2id (`memory_cost=65536`, `time_cost=3`, `parallelism=2`). |
| **MFA (Future)** | SMS‑based OTP will be optional for `pro` tier as a security upgrade. |
| **Token Lifetime** | Access token 15 min; Refresh token 30 days, revoked on password change or suspicious activity. |

---

### 6. Deployment Architecture  

| Component | Cloud Service | Reason |
|-----------|---------------|--------|
| **Web/API** | **AWS Elastic Container Service (Fargate)** – 2 × autoscaling groups (one for API, one for workers) | Serverless containers; pay‑per‑use CPU/memory; integrates with ALB. |
| **Load Balancer** | **Application Load Balancer (ALB)** – TLS termination, path‑based routing to API vs worker services | Simplifies HTTPS endpoint management and health‑checks. |
| **Database** | **Amazon RDS PostgreSQL (Multi‑AZ)** | Managed backups, automated failover, read replicas for analytics. |
| **Cache** | **AWS ElastiCache (Redis)** – 2‑node cluster with replication | Low‑latency sessions and prediction caching. |
| **Object Storage** | **Amazon S3** (standard) | Store generated Markdown/PDF reports, static assets (logo, icons). |
| **Static Front‑End** | **Amazon CloudFront + S3** (served via `goalpredict.com`) | Global edge distribution, low latency loading. |
| **CI/CD** | **GitHub Actions** → **ECR** → **ECS** | Automated testing, image scanning (Trivy), deployment via CDK. |
| **Secrets Management** | **AWS Secrets Manager** | Secure storage of API keys, DB credentials, Stripe webhook secrets. |
| **Monitoring** | **CloudWatch Alarms** (CPU > 70% for 5 min, error rate > 1%) → **SNS** notifications to on‑call. |
| **Logging** | **AWS CloudWatch Logs** + **Sentry** (client‑side) | Correlation IDs propagated from API to logs for full‑traceability. |
| **Domain & TLS** | **Route 53** + **ACM** (certificate for `app.goalpredict.com`) | Automated renewal, DNS routing to ALB. |

**Scalability Tactics**

* **Horizontal Pod Autoscaling (HPA)** on CPU and custom metric (`requests_per_second`) for API pods.  
* **Read Replicas** (up to 3) for heavy analytics queries (e.g., reporting dashboards).  
* **Cache‑first strategy** – if a match’s prediction is already cached for the current day, serve it directly without re‑running the pipeline.  
* **Back‑pressure handling** – queue incoming match‑run requests in **Redis Streams**; process in batches of ≤ 10 concurrent pipelines.  

---

### 7. Third‑Party Integrations Required  

| Integration | Provider | Data Obtained | Usage |
|-------------|----------|----------------|-------|
| **SofaScore API** | Sofascore (open‑access) | Live injury reports, line‑ups, recent form, market odds | `Live Feed Agent` → real‑time updates to `features` table. |
| **Betfair API** | Betfair (commercial) | Current odds for 1X2, over/under markets | `Betting Edge Service` → calculate `edge` and recommendation. |
| **OpenWeather API** | OpenWeatherMap | Current & forecast weather at stadium (temp, humidity, precipitation) | Adjust `xg` and `ppda` coefficients based on precipitation impact. |
| **Twitter API v2** | Twitter (academic/research track) | User‑generated match‑related tweets (sentiment analysis) | NLP sentiment → `motivation_score` for `Contextual Engine`. |
| **StatsBomb Open Data** | GitHub repo | Event‑level JSON (shots, passes, xG) for historical matches | Primary dataset for training baseline Poisson & XGBoost models. |
| **Understat API / CSV** | Understat (free endpoints) | Season‑long shot‑level stats, xG values | Enrich `features` with `xG` per team and player. |
| **Transfermarkt Scraper** | Self‑hosted scraper (GitHub `dcaribou/transfermarkt-scraper`) | Player market values, injury history, contract status | Populate `injury_impact_*` fields & player‑Elo averages. |
| **Stripe** | Stripe Checkout | Subscription billing, invoice management | Payment flow for Pro/Enterprise plans. |
| **Sentry** | Sentry.io | Error tracking & client‑side performance metrics | Automatic alerts on unhandled exceptions. |

*All integration clients are written as **async** wrappers (`aiohttp`), respect rate limits and exponential back‑off.*

---

### 8. Scalability & Performance Considerations  

| Concern | Mitigation Strategy |
|---------|----------------------|
| **High Match‑Day Traffic Spike (e.g., derby weekend)** | *Load‑based scaling*: HPA spikes Pods; pre‑warm cache entries for upcoming matches; use **Redis Cluster** with sharding to avoid bottlenecks. |
| **Model Inference Latency** | *Model serving*: Deploy XGBoost & Bayesian models in **TorchServe** or **FastAPI‑compatible containers**; use **ONNX** export for inference optimization; warm‑up pods before peak hours. |
| **Large Report Generation** | *Lazy generation*: Reports built from cached prediction objects; async PDF rendering off‑loaded to a worker queue (Celery‑like) and stored in S3 for later retrieval. |
| **Data Consistency** | *Transactional boundaries*: Use PostgreSQL `SERIALIZABLE` isolation for prediction persistence; version `model_version` column to avoid stale model mismatches. |
| **External API Rate Limits** | *Circuit Breaker* pattern in async workers; fallback to cached data if provider unreachable; exponential back‑off and retries up to 5 attempts. |
| **Data Retention** | Store raw event data for 2 years in **S3 Glacier**; delete from PostgreSQL after 12 months; keep indexed summary tables for active period. |
| **Cost Control** | Auto‑scale down idle worker containers to **0**; schedule nightly batch jobs for model retraining (cron in ECS) using spot instances to reduce compute spend. |
| **Disaster Recovery** | Multi‑AZ RDS replication; daily snapshots of EFS (for static assets); Route53 health checks redirect traffic to secondary region if primary fails. |

---

## 9. Development Roadmap (High‑Level)

| Milestone | Target Release | Core Deliverables |
|-----------|----------------|-------------------|
| **MVP (v1.0)** | June 2026 | • User auth & subscription flow <br>• Match listing & detail pages <br>• Data ingestion from StatsBomb & Understat <br>• Basic XGBoost + Poisson pipeline <br>• Markdown report download |
| **Live Features (v2.0)** | Dec 2026 | • Async Live Feed Agent (SofaScore, Weather, Twitter) <br>• Betting‑Edge dashboard <br>• Real‑time UI updates <br>• Payment integration (Stripe) |
| **Enterprise Tier (v3.0)** | Jun 2027 | • Public REST API (OpenAPI) <br>• Mobile app (React Native) <br>• Multi‑league support (Premier, La Liga…) <br>• Simulation engine & 3‑D visualisation <br>• Role‑based access control for corporate clients |

---

### 10. Summary  

The architecture outlined above provides a **producer‑ready, production‑grade foundation** for GoalPredict Pro:

* **Clear separation** of concerns (API, async agents, ML, data store).  
* **Modern, type‑safe stack** that aligns with the team’s existing Python expertise while leveraging cloud‑native scalability.  
* **Integrations** that supply the live, contextual data needed for the 4‑agent orchestration model.  
* **Robust security and payment handling**, enabling a sustainable subscription business.  
* **Scalable deployment** patterns that can absorb sudden traffic bursts typical of high‑profile derbies.  

With this blueprint, the engineering team can commence detailed design, component prototyping, and CI/CD pipeline setup, moving swiftly toward a beta launch in June 2026.  

---  

*Prepared by the GoalPredict Pro Technical Architecture Working Group – 01 Mar 2026*