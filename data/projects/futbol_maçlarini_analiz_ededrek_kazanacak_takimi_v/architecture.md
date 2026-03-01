**Idea‑to‑Project: Phase 3 – Technical Architecture**  
*Prepared for FutVision AI (football‑match prediction & betting‑assist platform)*  

---

## 1. Recommended Tech‑Stack (with justification)

| Layer | Technology | Why this choice? (trade‑offs) |
|-------|------------|-------------------------------|
| **Frontend (Mobile & Web)** | • React + TypeScript (Web)  <br>• React‑Native (iOS/Android) | Mature ecosystem, component reuse, strong TS support → predictable build pipelines and easier hand‑off between web & mobile teams. |
| **State Management** | Redux Toolkit (Web) / Recoil (React‑Native) | Minimal boilerplate, time‑travel debugging, works seamlessly with server‑side rendering for SEO‑friendly pages. |
| **Backend Core Services** | • Go (Golang) – micro‑services (API‑gateway, data‑ingestion, prediction orchestrator) <br>• Python (FastAPI) – ML & LLM inference services | **Go**: compiled, low‑latency, excellent concurrency (goroutines) → ideal for high‑throughput API‑gateway & orchestration. <br>**Python**: rich ML & NLP libraries (PyTorch, TensorFlow, Transformers) → easiest integration with existing models and rapid prototyping of LLM prompts. |
| **API Protocol** | REST + OpenAPI 3.0 (versioned) + optional GraphQL for internal dashboards | REST is universally supported, easy to cache & version. GraphQL added later only where the UI needs flexible queries (e.g., admin console). |
| **Messaging / Event Bus** | Kafka (or Pulsar) for async events (match‑result events, model‑outputs, notification triggers) | Guarantees at‑least‑once delivery, replayability for audit/re‑training, and decouples services. For MVP low volume, a lightweight RabbitMQ can be used and switched later. |
| **Cache / Session Store** | Redis (cluster mode) – for request caching, rate‑limit buckets, JWT revocation list | Sub‑ms latency, TTL‑based expiration fits the 30‑second analysis SLA. |
| **Primary Data Store** | PostgreSQL (13+) – relational storage for users, matches, predictions, odds, logs | ACID guarantees, powerful SQL analytics, native JSONB for flexible fields (e.g., prediction payloads). |
| **Search / Full‑Text** | ElasticSearch (optional) – for fast team/player search | Scales horizontally; can be introduced later when search volume grows. |
| **Object Storage** | Amazon S3 (or MinIO on‑prem) – for static assets, PDF reports, avatar images | Cheap, durable, easy CDN integration (CloudFront / Cloudflare). |
| **CI/CD** | GitHub Actions → Docker Build → Amazon ECR → EKS (Kubernetes) | End‑to‑end pipeline, automatic canary rolls, secret management via AWS Secrets Manager. |
| **Container Orchestration** | Kubernetes (EKS / GKE / AKS) – Helm charts for all services | Enables auto‑scaling, rolling updates, resource‑quota isolation. |
| **Observability** | Prometheus + Grafana (metrics) <br> Loki + Grafana (logs) <br> OpenTelemetry (tracing) | Cloud‑native standards; easy to monitor latency < 30 s per analysis, error rates, and business KPIs. |
| **Security** | AWS IAM + Cognito (user pool) or Auth0 (SaaS) <br> JWT (access + refresh tokens) <br> OAuth2.0 + PKCE for mobile | Centralized user management, MFA support, GDPR‑ready token revocation. |
| **Third‑Party Integrations** | • **Data Ingestion** – API‑Football (football‑data.org) & FotMob (paid) <br>• **Betting Odds** – OddsAPI (or direct SDKs from Bet365, Pinnacle) <br>• **LLM Provider** – Anthropic Claude 3 (via Amazon Bedrock) or OpenAI GPT‑4 (Azure) – select based on cost/latency of token usage | These providers already host the raw sports data & betting odds needed; using a managed LLM reduces infra overhead. |
| **Dev/Test** | Docker‑Compose for local dev, Playwright for end‑to‑end UI tests, Jest + React Testing Library for unit tests | Fast feedback loop; can spin up a full stack locally before pushing to CI. |
| **Infrastructure as Code** | Terraform (AWS provider) | Reproducible environments, version‑controlled infra, drift detection. |
| **Disaster Recovery** | Multi‑AZ RDS read‑replicas, S3 cross‑region replication, Redis replication | Guarantees 99.5 % uptime SLA. |

---  

## 2. System Architecture (textual + Mermaid)

```mermaid
graph TD
  %% ==== External Users ====
  UI[User (Web / Mobile)] -->|HTTPS| LB[API Gateway (NGINX + Kong)]
  LB -->|REST| Auth[Auth Service (OAuth2/JWT)]
  LB -->|REST| DataIngest[Data Ingestion Service]
  LB -->|REST| MatchSvc[Match Service]
  LB -->|REST| PredictionSvc[Prediction Orchestrator]
  LB -->|REST| OddsSvc[Odds Service]
  LB -->|REST| NotificationSvc[Notification Service]

  %% ==== Data Stores ====
  DataIngest -->|Write| PG[(PostgreSQL)]
  PredictionSvc -->|Read/Write| PG
  NotificationSvc -->|Write| Redis[(RedisCache)]
  MatchSvc -->|Read| Elastic[(ElasticSearch)]
  OddsSvc -->|Read| PG

  %% ==== Event Bus ====
  DataIngest -->|Publish| Kafka[(Kafka Topic: match_events)]
  PredictionSvc -->|Publish| Kafka[(Kafka Topic: prediction_results)]
  Kafka -->|Consume| NotificationSvc
  Kafka -->|Consume| OddsSvc

  %% ==== Third‑Party Consumers ====
  DataIngest -->|Call| FootballAPI[(Football‑API / FotMob)]
  OddsSvc -->|Call| OddsAPI[(Odds Providers)]

  %% ==== ML / LLM Services ====
  PredictionSvc -->|Call| MLWorker[Python ML Service (FastAPI)]
  MLWorker -->|Call| LLMWorker[LLM Service (Claude/GPT)]

  %% ==== Monitoring & Logging ====
  subgraph Observability
    Prometheus[Prometheus]
    Grafana[Grafana]
    Loki[ Loki (logs) ]
    Otel[OpenTelemetry]
  end
  Prometheus -->|Scrape| GoServices
  Grafana -->|Query| Prometheus
  Loki -->|Collect| GoServices & PythonServices
  Otel -->|Trace| AllServices

  %% ==== Deployment ====
  style UI fill:#f9f,stroke:#333,stroke-width:2px
  style LB fill:#bb88cc,stroke:#333,stroke-width:2px
  style Auth fill:#ff7733,stroke:#333,stroke-width:2px
  style DataIngest fill:#2ca02c,stroke:#333,stroke-width:2px
  style MatchSvc fill:#2ca02c,stroke:#333,stroke-width:2px
  style PredictionSvc fill:#2ca02c,stroke:#333,stroke-width:2px
  style OddsSvc fill:#2ca02c,stroke:#333,stroke-width:2px
  style NotificationSvc fill:#2ca02c,stroke:#333,stroke-width:2px
  style Kafka fill:#999,stroke:#333,stroke-width:2px
  style PG fill:#666,stroke:#333,stroke-width:2px
  style Redis fill:#666,stroke:#333,stroke-width:2px
  style Elastic fill:#666,stroke:#333,stroke-width:2px
  style MLWorker fill:#ff9900,stroke:#333,stroke-width:2px
  style LLMWorker fill:#ff9900,stroke:#333,stroke-width:2px
  style Observability fill:#ddd,stroke:#555,stroke-dasharray: 5 5
```

**Explanation of the flow**

1. **User → API Gateway** – The front‑end (React/React‑Native) makes HTTPS calls to a single entry point (NGINX + Kong). Kong enforces rate limits, JWT validation, and metrics collection.  
2. **Gateway → Auth Service** – Handles sign‑up, login, social‑login (Google/Apple), issues short‑lived access tokens and refresh tokens stored in Redis.  
3. **Gateway → Data Ingestion Service** – Orchestrates calls to external providers (Football‑API, FotMob, OddsAPI), normalises the payloads, writes raw events to PostgreSQL **and** publishes them to Kafka for downstream processing.  
4. **Match Service** – Provides UI‑ready match listings, filtering, and static team cards. It reads from PostgreSQL and cached data in Redis.  
5. **Prediction Orchestrator** – Stateless microservice that:  
   - Pulls latest match & injury data.  
   - Calls the **Poisson / ELO / Form** statistical engine (Go library).  
   - Sends the enriched payload to the **ML Service** (Python) for ensemble scoring.  
   - Takes the scored output and feeds it to an **LLM Service** (Claude/GPT) for the “Why this prediction?” natural‑language explanation.  
   - Applies the **MiniMax M2.5** post‑processing logic (weights, confidence calculation).  
   - Stores the final prediction, odds, confidence score, and explanation back into PostgreSQL; also publishes to Kafka for downstream notifications.  
6. **Odds Service** – Consolidates live odds from multiple betting providers, normalises them, ranks them, and returns the best value to the UI.  
7. **Notification Service** – Consumes `prediction_results` and `match_events` from Kafka; pushes push‑notifications (APNs/FCM) and/or email digests.  
8. **Observability** – Prometheus scrapes metrics from Go and Python services; logs flow to Loki; distributed tracing via OpenTelemetry links requests across services.  

---

## 3. Database Schema (core tables)

| Table | Primary Key | Key Columns | Relationships / Notes |
|-------|-------------|-------------|-----------------------|
| **users** | `id` (UUID) | `email`, `password_hash`, `username`, `created_at`, `is_verified`, `preferred_lang` | One‑to‑many → `user_devices`; many‑to‑many → `user_favorite_teams`. |
| **user_devices** | `id` (UUID) | `user_id` (FK), `device_token`, `platform` (`android|ios|web`) | Used for push notifications. |
| **teams** | `team_id` (string, external provider ID) | `name`, `short_name`, `logo_url`, `league`, `country` | Static reference data; versioned via `team_versions`. |
| **matches** | `match_id` (UUID) | `home_team_id` (FK), `away_team_id` (FK), `kickoff_ts`, `status`, `stadium`, `weather`, `referee_id` | One‑to‑many → `match_predictions`; many‑to‑one → `venue`. |
| **injuries** | `injury_id` (UUID) | `match_id` (FK), `player_id` (FK), `status` (`suspended|injured|available`), `timestamp` | Enriched by `fetch_live_injuries`; used by prediction engine. |
| **player_stats** | `player_id` (UUID) | `team_id` (FK), `season`, `appearances`, `goals`, `assists`, `xG`, `pass_completion` | Snapshot per season; joined for form calculations. |
| **betting_odds** | `odd_id` (UUID) | `match_id` (FK), `provider_name`, `odds_1x2`, `odds_over_under_25`, `last_updated_ts` | Cached in Redis; used for odds ranking UI. |
| **predictions** | `pred_id` (UUID) | `match_id` (FK), `user_id` (FK), `home_score_prob_dist` (JSONB), `away_score_prob_dist` (JSONB), `confidence_score` (float), `explanation` (text), `model_agreement` (float), `created_at` | Stores full prediction payload plus user‑specific metadata. |
| **user_favorite_teams** | `id` (UUID) | `user_id` (FK), `team_id` (FK) | Enables personalized notifications. |
| **audit_logs** | `log_id` (UUID) | `entity_type`, `entity_id`, `action`, `actor_id` (FK → users), `timestamp`, `details` (JSONB) | Immutable, GDPR‑compliant retention. |
| **subscription_plans** | `plan_id` (UUID) | `name`, `price_curr`, `price_amount`, `features_json`, `is_active` | Used by billing system. |

*All JSONB fields (e.g., probability distributions) are stored in PostgreSQL to keep the schema flexible while still queryable via GIN indexes.*

---

## 4. API Endpoints (REST – versioned **/api/v1**)

| Category | Endpoint | Method | Description | Request Payload | Response |
|----------|----------|--------|-------------|----------------|----------|
| **Auth** | `/auth/login` | POST | Email + password or OAuth token exchange | `{ "email": "...", "password":"..." }` or `{ "provider":"google", "code":"..." }` | `{ "access_token":"...", "refresh_token":"...", "expires_in":3600 }` |
| | `/auth/register` | POST | New user sign‑up | `{ "email":"...", "username":"...", "password":"..." }` | `{ "user_id":"...", "verification_sent":true }` |
| **Matches** | `/matches` | GET | List upcoming & finished matches with filters | Query params: `league=Süper+Lig`, `date=2026-03-05`, `home_team_id=...` | `{ "items":[{ "match_id":"...", "home":"...", "away":"...", "kickoff":"..."}]}` |
| | `/matches/{match_id}` | GET | Detailed match card (team stats, line‑ups, injury list) | — | Full match JSON including `team_home`, `team_away`, `injuries[]` |
| **Predictions** | `/predictions/{match_id}` | GET | Returns prediction, confidence, explanation, odds | — | `{ "confidence":79, "analysis":"...", "explanation":"...", "probable_score":{"1-0":0.28,"2-1":0.12,...}, "best_odds":{ "provider":"Bet365","odds":2.45 } }` |
| | `/predictions/{match_id}` | POST | (Optional) allow users to submit their own model weight tweaks | `{ "weights":{"poisson":0.5,"elo":0.3,"form":0.2} }` | Echoes back re‑computed result |
| **Odds** | `/odds/compare?match_id=...` | GET | Returns ranked odds across providers | — | `{ "best_price": {"provider":"Pinnacle","odds":3.10}, "ranked": [{provider, odds, margin}] }` |
| **Notifications** | `/notifications` | GET | Unread count / list | — | `{ "unread":12, "items":[ {...}] }` |
| **Billing** | `/subscriptions` | GET/PUT | User subscription info | — | `{ "plan_id":"premium_monthly", "status":"active", "next_billing":"2026-04-01" }` |
| **Admin** | `/admin/metrics` | GET | Internal performance summary (only for ops) | — | `{ "requests_per_sec":1240, "latency_p99":280ms }` |

*All responses are wrapped in a standard envelope: `{ "status":"ok", "data":..., "meta":{ "request_id":"..."} }`. Errors follow RFC 7807 problem‑detail format.*

---

## 5. Authentication & Authorization Strategy

| Aspect | Implementation |
|--------|----------------|
| **User Identity** | Managed by **AWS Cognito** (or Auth0) – provides social login, email verification, MFA, password‑reset flows. |
| **Tokens** | Upon successful login, Cognito issues a **JWT access token** (15 min) and a **refresh token** (long‑lived, stored encrypted in Redis). Access token contains `sub`, `iss`, `exp`, `scope` (`read:matches write:predictions`). |
| **Authorization Middleware** | Kong plugin (or custom Go middleware) validates JWT signature, checks scopes, and enforces per‑endpoint policies. |
| **RBAC / ABAC** | • **Roles**: `guest`, `user`, `premium`, `admin`. <br>• **Permissions**: `read:match`, `write:prediction`, `notify:push`. <br>• **ABAC** for usage‑based limits (e.g., premium users get higher prediction‑concurrency quota). |
| **Device‑Level** | Push‑notification token stored per device; stored in `user_devices` table to target specific platforms. |
| **Audit** | Each request logged with `user_id`, `endpoint`, `outcome`. Logs retained 90 days for compliance. |
| **Password Policy** | Minimum 12 characters, must contain upper/lower/digit/special; hashed with Argon2id (via Cognito). |
| **GDPR / Data Deletion** | Endpoint `/users/{id}/erase` triggers soft‑delete of personal fields, anonymises related rows, and notifies user. |

---

## 6. Deployment Architecture (Cloud‑native)

| Component | Cloud Service | Reasoning |
|-----------|---------------|-----------|
| **Compute (Containers)** | **Amazon EKS** (Kubernetes) | Managed Kubernetes removes operational overhead of control‑plane; integrates with IAM roles for service accounts → least‑privilege security. |
| **Container Registry** | **Amazon ECR** | Private, IAM‑locked, supports image scan for vulnerabilities. |
| **Serverless (Event‑driven)** | **AWS Lambda** for lightweight webhook handling (e.g., webhook from Odds provider) | Pay‑per‑use, auto‑scales, no server maintenance. |
| **Database** | **Amazon RDS PostgreSQL (Multi‑AZ)** | Automated backups, fail‑over, read replicas for scaling reads. |
| **Cache / Session Store** | **Amazon ElastiCache (Redis, cluster mode)** | Sub‑ms latency, automatic sharding for scaling. |
| **Object Storage** | **Amazon S3 + CloudFront CDN** | Durable storage of PDF/HTML reports, images; low‑cost static asset delivery. |
| **Search** | **Amazon OpenSearch Service** (optional) | Managed OpenSearch for fast full‑text team/player search; can be swapped with Elastic later. |
| **Message Bus** | **Amazon MSK (Managed Kafka)** | Fully managed, integrates with IAM, scaling on demand. |
| **Domain / Edge** | **Route 53 + CloudFront** | Global DNS, SSL termination, caching headers for static assets. |
| **Monitoring** | **Amazon CloudWatch + Grafana (via Prometheus Operator)** | Unified metrics, alarms, dashboards; can export custom metrics from services. |
| **CI/CD** | **GitHub Actions** → **ECR** → **EKS** (Argo CD for Git‑Ops) | Automatic canary deployments, roll‑backs, secret injection via SealedSecrets. |
| **Secrets Management** | **AWS Secrets Manager** + **Parameter Store** | Centralised secret storage, automatic rotation, audit logs. |
| **Disaster Recovery** | Cross‑region RDS read replica (e.g., EU (Frankfurt) ↔ US‑East‑1) + S3 Cross‑Region Replication | Meets 99.5 % SLA; fail‑over script swaps DNS to secondary endpoint. |

**Deployment Stages**

1. **MVP (0‑3 months)** – Single‑node EKS cluster (2‑3 worker nodes) + RDS single‑AZ; sufficient for ≤ 1K concurrent users.  
2. **Growth (3‑12 months)** – Expand to multi‑AZ RDS read replicas, enable horizontal pod autoscaling (HPA) based on CPU/latency metrics; introduce Kafka partitioning per league.  
3. **Scale (≥ 12 months)** – Deploy multi‑region EKS clusters (US‑East‑1, EU‑West‑1), use **AWS Global Accelerator** for reduced latency, enable **Kubernetes Federation** for fail‑over across continents.  

---

## 7. Third‑Party Integrations Checklist

| Integration | Provider | API Type | Data Flow | Cost / Rate Limits |
|-------------|----------|----------|-----------|--------------------|
| **Sports Data** | **API‑Football** (football‑data.org) | REST (GET) | Pull fixtures, line‑ups, stats → Data Ingestion Service | ~ $30/mo for 1 k calls; 1 req / sec rate‑limit (can be relaxed with cache). |
| **Live Injuries** | **FotMob** (paid) | WebSocket / REST | Real‑time injury/red‑card feed → `fetch_live_injuries` | Tiered pricing; 5 req / sec limit. |
| **Betting Odds** | **OddsAPI** (or direct provider SDKs) | REST | Returns live odds → `Odds Service` (caching in Redis) | Free tier limited; paid plans per match. |
| **LLM** | **Anthropic Claude 3** via **Amazon Bedrock** (or OpenAI GPT‑4 via Azure) | HTTP (POST) | Sends prompt → receives explanation & classification → LLM Service | Pay‑per‑token; cost ≈ $0.0015 / 1k tokens (Claude). |
| **Push Notifications** | **Amazon Pinpoint** / **Firebase Cloud Messaging** | HTTP | Sends push to devices stored in `user_devices` | Free tier up to 1 M messages/mo. |
| **Email** | **Amazon SES** | SMTP/HTTP | Sends daily summary or alerts | Pay‑as‑you‑go, cheap. |
| **Analytics** | **Mixpanel** or **Amplitude** | SDK | Event tracking (match view, prediction click) | Free tier for ≤ 10 M events/mo. |
| **Payment** | **Iyzico** (Turkey) / **Stripe** | REST | Subscriptions, one‑off payments → webhook → billing micro‑service | Transaction fees ~ 2.9 % + fixed. |

---

## 8. Scalability & Elasticity Considerations

| Dimension | Current Load (MVP) | Projected Load (Scale) | Scaling Mechanism |
|-----------|--------------------|------------------------|-------------------|
| **Incoming Requests** | ≤ 5 k RPM (peak during match days) | 100 k RPM during major tournaments (World Cup) | API‑Gateway throttles; Auto‑scale HPA on Go & Python pods; optional **Kong rate‑limiting** per user tier. |
| **Prediction Computation** | ~30 s per match (single‑thread) | 5 s per match using multiple CPU cores | Deploy **ML Worker** as a **Kubernetes Job** pool sized to number of matches pending; use **GPU‑enabled nodes** only for LLM calls (spot instances for cost efficiency). |
| **Data Ingestion** | ~2 k matches/day | 10‑20 k matches/day (including lower‑division leagues) | Kafka partitions per league; **consumer groups** scale independently; back‑pressure handling via consumer lag monitoring. |
| **Cache Hit Ratio** | Target ≥ 80 % for team‑card lookups | ≥ 95 % for repeat queries | Use ** Redis LRU**; warm cache on deployment; fallback to PostgreSQL when miss. |
| **Database Read Load** | 60 % reads, 40 % writes | 90 % reads (analytics) | Enable **read replicas** (up to 3); use **connection pooling** (PgBouncer). |
| **Network I/O** | 5 GB/day outbound | 50 GB/day (global users) | CDN for static assets; enable **HTTP/2** & **gzip** compression on API responses. |
| **Cost Management** | Fixed small EC2 instance | Dynamic spot instances for batch jobs; use **Savings Plans** for EC2 & RDS usage | Monitor spend via **AWS Cost Explorer**; shut down dev clusters automatically after office hours. |

---

## 9. Trade‑off Summary (Why These Choices?)

| Decision | Benefit | Potential Drawback | Mitigation |
|----------|----------|-------------------|------------|
| **Go for core services** | Low latency, strong concurrency, easy to compile static binaries → predictable performance for high‑QPS APIs. | Less mature ML libraries → hand‑off to Python for heavy numeric work. | Keep ML inference in separate Python service; communicate via gRPC/HTTP. |
| **Python + FastAPI for ML/LLM** | Rich ecosystem (PyTorch, Transformers), rapid iteration, easy prototyping of prompts. | Interpreted language → higher latency, more memory; needs sandboxing. | Deploy in isolated containers with CPU limits; use **Karafka** or **Celery** to queue heavy jobs; cache results aggressively. |
| **Kubernetes on AWS EKS** | Managed scaling, self‑healing, extensive ecosystem, aligns with GitOps practices. | Learning curve; higher operational cost if not fully utilized. | Start with **managed** EKS (no self‑master) and **auto‑scaling groups**; use Helm charts for reproducibility. |
| **Managed LLM (Claude via Bedrock)** | No server‑maintenance, pay‑per‑token, built‑in compliance (SOC‑2). | Vendor lock‑in; latency depends on AWS region. | Choose region closest to primary user base; implement fallback to smaller open‑source model (e.g., Llama‑3‑8B) if cost spikes. |
| **PostgreSQL for core data** | ACID guarantees, powerful SQL for analytics, native JSONB for flexible payloads. | Vertical scaling may become a bottleneck at massive scale. | Horizontal sharding via **Citus** extension; read replicas for reporting workloads. |
| **Redis for caching & rate limiting** | Sub‑ms response for hot data; atomic operations for token buckets. | Data loss on crash if not persisted; memory cost grows with dataset. | Enable **Redis AOF persistence**; use **Redis Cluster** to scale; populate cache lazily (cache‑aside pattern). |
| **Kafka for event bus** | Durable, replayable, decouples services; handles bursty traffic. | Added complexity; requires schema evolution planning. | Adopt **Avro schemas** and **Schema Registry**; start with a single topic and evolve. |
| **GraphQL not used for public API** | Simpler versioning, easier caching. | Overkill for current use‑cases; harder to secure at scale. | Adopt GraphQL only for internal admin UI where flexible queries justify the cost. |
| **Multi‑language front‑end (React + React‑Native)** | Code reuse, consistent UX, fast iteration. | Larger bundle size; need separate CI pipelines for web vs. native. | Use **Monorepo** (Turborepo) to share components; lazy‑load native modules only when needed. |

---

### Bottom Line

The architecture outlined balances **performance**, **maintainability**, and **cost‑effectiveness** while staying aligned with the business goals:

* **MVP** can be launched on a modest EKS cluster with a single PostgreSQL instance and a small Redis cache.  
* **Scalable** design allows seamless growth to multi‑region, high‑throughput operation during global tournaments.  
* **Clear separation of concerns** (data ingestion → prediction orchestration → presentation) enables independent development, testing, and deployment of each module.  
* **Observability, security, and disaster‑recovery** are baked in from day‑one, ensuring compliance with the 99.5 % uptime SLA and GDPR requirements.  

With this foundation, the team can start building the MVP features (match listing, team cards, AI prediction, confidence score, “why this prediction?” explanations) and iterate based on real‑world usage data. Happy building!