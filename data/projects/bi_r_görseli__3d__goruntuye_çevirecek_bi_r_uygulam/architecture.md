## IDEA‑TO‑PROJECT: PHASE 3 — TECHNICAL ARCHITECTURE  
*(Tüm öngörüler, Phase‑2 PRD’deki **P0‑P1** fonksiyonel gereksinimlerine ve donanım kısıtlamalarına (8 GB RAM, 512 GB SSD, GPU = GTX 1650‑tipe with 8 GB VRAM) göre hazırlanmıştır.)*  

---  

### 1️⃣ REKOMENDJAN TECH STACK  

| Kategori | Teknoloji | Neden / Pozitif Özellik |
|----------|-----------|------------------------|
| **Frontend** | **React + TypeScript** + **Three.js** (WebGL) + **Gradio** (opsiyonel fallback) | • Tek sayfalı, responsive UI <br> • 3D sahnelerde yüksek FPS (Three.js) <br> • Gradio ile hızlı prototip (Python‑tabanlı) <br> • Material‑UI / Tailwind for tema/yerel (Türkçe) |
| **Backend API** | **FastAPI** (Python 3.11) | • Async‑first, OpenAPI otomatik dokümantasyon <br> • GPU‑aware (CUDA) ve CPU‑fallback destek <br> • Helmet‑CORS‑rate‑limit ile güvenlik |
| **ML Engine** | **TripoSR** (MIT, 0.5 s tek‑görsel → 3D) <br> **LGM** (StabilityAI) <br> **Stable Dream3D** (fallback) | • Open‑source, Linux/Windows/macOS <br> • CUDA & CPU (ONNX) destek <br> • Model quantisation (int8) → 8 GB VRAM’da %30‑40 VRAM tasarruf <br> • Community‑aktif, sadece 1‑2 satır Python kodu |
| **Model Serving** | **torchserve** / **FastAPI‑direct inference** | • Tek bir endpoint (`/model/generate`) üzerinden istek yönlendirme <br> • Model yükleme (warm‑up) → ilk çağrıdan sonra latency < 1 s (GPU), < 30 s (CPU) |
| **Containerisation** | **Docker Compose** (Linux/WSL2) | • Bağımlılık izolasyonu, tek‑komutu “docker‑up” ile çalıştırma <br> • GPU‑destek için *nvidia‑container‑runtime* (Docker‑Engine ≥ 20.10) |
| **Database** | **SQLite** (MVP) → **PostgreSQL** (v2) | • SQLite tek‑dosyaya yerleştirilebilir, dev‑testta yeterli <br> • PostgreSQL → çoklu kullanıcı, acid‑transactions, full‑text search (model metadata) |
| **Authentication** | **JWT‑Bearer** (local‑only) | • Kullanıcı hesabı gerekmez; isteğe bağlı “guest” token <br> • İsterseniz “username/password” + bcrypt + email‑verify (opsiyonel) |
| **Security / Isolation** | **Docker‑sandbox**, **AppArmor/SELinux**, **File‑system read‑only** (tmp) | • Veri dışarıya nunca flows yok, işlemler sandbox içinde <br> • Geçici dosyalar işlem sonrası `tmpfs` → otomatik silinir |
| **CI/CD** | **GitHub Actions** (lint, pytest, safety‑scan) | • PR sonrası otomatik test, kod tarama (Bandit, Safety) |
| **Monitoring** | **Prometheus** + **Grafana** (opsiyonel) | • CPU/GPU utilisation, latency, error‑rate izleme |
| **Backup / Persistence** | **Rclone** → yerel/network storage (opsiyonel) | • Model & user‑data yedekleme opak dosyaları sıkıştırma ile |

---

### 2️⃣ SISTEMEKSEL DIYAGRAM (Metin/​Mermaid)  

```mermaid
graph TD
  %% Frontend
  FE[React Frontend (HTTPS)]
  %% Backend
  API[FastAPI (REST) <-> Auth (JWT)]
  %% ML Service
  ML[ML Service (TripoSR / LGM / Dream3D)]
  %% Database
  DB[(PostgreSQL)]
  %% Storage
  FS[Local Persistent Volume (SSD)]
  %% GPU
  GPU[GPU (CUDA) Driver]

  FE -->|HTTPS| API
  API -->|/generate| ML
  ML -->|model files| FS
  ML -->|GPU| GPU
  API -->|metadata| DB
  DB -->|read/write| FS
  GPU -->|CUDA| ML

  style FE fill:#E3F2FD,stroke:#1565C0
  style API fill:#FFF3E0,stroke:#EF6C00
  style ML fill:#E8F5E9,stroke:#2E7D32
  style DB fill:#F3E5F5,stroke:#6A1B9A
  style FS fill:#F1F8E9,stroke:#7CB342
  style GPU fill:#ECEFF1,stroke:#9E9E9E
```

**açıklama**  
- **Frontend**: Tarayıcı (Chrome/Firefox/Edge) üzerinden `https://localhost:8080` erişim.  
- **Backend API**: FastAPI ≈ `/upload`, `/process`, `/download`, `/status`, `/models` gibi endpoint’ler.  
- **ML Service**: Docker‑container içinde **TripoSR** (veya alternatif) çalıştırılır; GPU‑destekli inference otomatik olarak `torch.cuda.is_available()` kontrolüyle seçilir.  
- **Database**: Model metadata (user‑id, file‑hash, creation‑time, quality‑settings) saklanır.  
- **Local Persistent Volume**: Unity‑model‑files (GLB/OBJ/STL) ve geçici işlem dosyaları `./data` klasörüne tutulur.  
- **GPU**: Docker‑runtime + `nvidia-docker` ile CUDA erişimi sağlanır; CPU‑modunda ise **ONNX Runtime** + **OpenVINO** (CPU‑optimized) fallback kullanılır.  

---

### 3️⃣ DATABASE SCHEMA (PostgreSQL)  

| Table | Primary Key | Important Columns | Açıklama |
|-------|-------------|-------------------|----------|
| **users** | `id` (UUID) | `username`, `email`, `password_hash`, `created_at`, `is_active` |Opsiyonel verwendet; sadece “guest” token gerekirse boş bırakılabilir. |
| **models** | `id` (UUID) | `user_id` (FK), `created_at`, `updated_at`, `status` (queued/processing/done), `quality` (low/medium/high), `format` (glb/obj/zip), `preview_url` | Üretilen 3D modelin meta‑verisi. |
| **model_files** | `id` (UUID) | `model_id` (FK), `file_path` (relative), `size_bytes`, `checksum_sha256`, `download_url` | GLB/OBJ/STL vb. fiziksel dosya konumu. |
| **sessions** | `id` (UUID) | `user_id`, `created_at`, `expires_at`, `jti` (token) | JWT oturum izleme (opsiyonel). |
| **audit_logs** | `id` (UUID) | `user_id`, `action`, `resource`, `timestamp`, `details` | Güvenlik/privacy denetimi. |

**Indexler**: `idx_models_user`, `idx_models_status`, `idx_files_model`, `idx_audit_timestamp`.  

---

### 4️⃣ API ENDPOINTS (REST)  

| Method | Path | Purpose | Request Body | Response |
|--------|------|---------|--------------|----------|
| **POST** | `/api/v1/upload` | Görsel upload (multipart/form‑data) | `file` (JPG/PNG/WEBP) | `{upload_id, status:"received"}` |
| **POST** | `/api/v1/process` | Model üretim işlemi tetikleme | `{upload_id, quality:"high|medium|low", format:"glb|obj|stl"}` | `{job_id, status:"queued"}` |
| **GET** | `/api/v1/status/{job_id}` | İş akışı durumu | – | `{job_id, status, progress:0‑100, eta_seconds}` |
| **GET** | `/api/v1/download/{job_id}` | İşlem tamamlandığında dosya indirme linki | – | `{download_url, model_info}` |
| **GET** | `/api/v1/models` | Kullanıcı‑aşamasına ait modeller listesi | – | `[{id, created_at, format, quality}]` |
| **DELETE** | `/api/v1/models/{model_id}` | Model silme (gizlilik) | – | `{deleted:true}` |
| **GET** | `/api/v1/health` | Service health check | – | `{status:"ok"}` |
| **POST** | `/api/v1/auth/login` *(opsiyonel)* | JWT token al (kullanıcı kaydı) | `{username,password}` | `{access_token, token_type:"Bearer"}` |

> **Not:** Tüm işlemler **asenkron** (Celery/RQ) ya da **FastAPI background tasks** ile yürütülür; `/status` endpoint’i polling üzerinden sonucu döndürür.  

---

### 5️⃣ AUTHENTICATION & AUTHORIZATION STRATEGY  

| Katman | Çözüm | Açıklama |
|--------|-------|----------|
| **Giriş** | **JWT‑Bearer** (opsiyonel) | Kullanıcı kaydı/oturum açma gerekmez; “guest” token ile anonim kullanım mümkün. Auth headerı gönderilmezse işlem “anonymous” olarak değerlendirilir. |
| **Yetkilendirme** | **Role‑Based Access Control (RBAC)** – sadece **admin** (opsiyonel) erişim izni verir. |  MVP’de “anonim” ≈ yetki; veri gizliliği için her işlem Authorization headerı kontrolü eklenir, yoksa **401**. |
| **Şifreleme** | **TLS 1.3** (HTTPS) + **File‑system encryption** (optional) | Ağ trafiği şifre, ortak klasör erişimi sadece `docker` user‑u. |
| **Auditing** | **Audit log** → `audit_logs` tablosu | Her upload / process / download işlemi loglanır (kullanıcı‑id, IP, timestamp). |
| **Sandbox** | **Docker‑AppArmor/SELinux** profile | Her container sandbox içinde, dışarıdan dosya erişimi yasak. |

---

### 6️⃣ DEPLOYMENT ARCHITECTURE  

| Ortam | Seçenek | Açıklama |
|-------|----------|----------|
| **Geliştirme** | **Docker‑Compose** (`docker-compose.yml`) | `frontend`, `api`, `ml-service`, `db` (SQLite) + `minio` (opsiyonel storage) |
| **Prod (Lokal)** | **Docker‑Swarm** (tek‑host) veya **K3s** (léger) | GPU‑destekli servis `deploy` komutuyla `--gpus all` ile çalıştırılır. CPU‑fallback için `runtime: "cpu"` etiketi. |
| **Yerel Sunucu (8 GB RAM, 8 GB VRAM)** | **Ubuntu 22.04 LTS** + **WSL 2 on Windows 10/11** (or native Linux) | • `docker` + `nvidia-docker` kurulumu <br>• `docker-compose up -d` <br>• `ulimit -n 65535` (dosya limiti) |
| **Yerel Sunucu (CPU‑only)** | **ONNX Runtime + OpenVINO** | Modeli **int8‑quantized** (≈ 0.8 GB) → 8 GB RAM’da 2‑3 dakika/iş. |
| **Yerel Docker Image** | `img2mesh-frontend:latest` (nginx) <br>`img2mesh-api:latest` (fastapi) <br>`img2mesh-ml:latest` (triposr) | Görsel `docker build` ve push **locally** (registry yok) → `docker compose up` |

**Scaling (v2)**: Tekrar **K8s** cluster (DigitalOcean, AWS‑EC2, Hetzner) にて **GPU‑node‑pool** ve **CPU‑node‑pool** oluşturulup **HorizontalPodAutoscaler** ile otomasyon sağlanabilir.  

---

### 7️⃣ THIRD‑PARTY INTEGRATIONS  

| Inteграция | Kullanım Senaryosu | Detay |
|------------|-------------------|-------|
| **RemBG / Background‑Removal API** | Görsel ön işleme (arkaplan temizleme) | HTTP‑GET → `https://rembgapi.com/remove` → sonucu `temp.png` |
| **Stable Diffusion (text‑to‑texture)** | 2D texture/renk değiştirme otomasyonu | `diffusers` Python library → texture inference (opsiyonel P1). |
| **Redis Queue (RQ / Celery)** | Arka‑plan job yönetimi | Job queue → `\`process_task\` → status stored in DB. |
| **OAuth2 (Google / GitHub)** | Kullanıcı kimliği (opsiyonel) | JWT token creation, 2FA destek. |
| **Sentry** | Hata izleme & raporlamalar | Uncaught exception & performance monitoring. |
| **Prometheus + Grafana** | Metrics (CPU/GPU usage, latency) | `cAdvisor` + custom `/metrics` endpoint. |

---

### 8️⃣ SCALABILITY & PERFORMANCE CONSIDERATIONS  

| Senaryo | Çözüm / Optimizasyon |
|----------|----------------------|
| **GPU‑yetersiz (8 GB VRAM) CPU‑only** | • **Model Quantization** – `bitsandbytes` 8‑bit, `optimum.intel` 4‑bit <br>• **ONNX Runtime** + `ort_directml` (Windows) <br>• **Batch Queue** – birden fazla kullanıcı için job‑queue (FIFO) |
| **Yüksek concurrency (5+ aynı anda)** | • **Gunicorn + Uvicorn workers** (CPU‑bound) <br>• **Redis**‑based task queue (parallel processing) <br>• **GPU‑pool** ( successivement 2‑3 model instance) |
| **Model update / patch** | • **Docker‑pull‑policy: always** – upstream repo (`VAST-AI-Research/TripoSR`) otomatik güncelle <br>• **Versioned image tags** (`v1.0`, `v1.1`) ve backward‑compatible DB migrasyonları |
| **Bellek yönetimi** | • **GPU memory‑caching** – `torch.cuda.empty_cache()` iş parçacığı sonunda <br>• **Swap‑aware** – CPU‑ fallback için `--memory_limit=6GB` Docker arg. |
| **Güvenlik / Veri gizliliği** | • **No outbound network** – `network_mode: none` Dockerfile’de; sadece internal sockets açık <br>• **File‑system read‑only** – `tmpfs` erişim sadece `RW` izinli klasörlerde. |
| **Uzun süreli işlem (CPU‑only)** | • **Progressive download** – ilk başlangıçta “preview” mesh (10k vertex) üretilir, kalan aşamada full‑resolution  <br>• **Caching** – aynı input görsel hash → aynı model → tekrar işleme kaçınılır. |

---

## 📌 ÖZET & ÖNERİLER  

| Konu | Öneri |
|------|-------|
| **MVP‑Ready Stack** | React + Three.js (Frontend) – FastAPI (Backend) – TripoSR (GPU) / ONNX‑CPU (CPU) – Docker‑Compose (Yerel) |
| **Donanım Kısıtlamaları** | 8 GB VRAM GPU → quantized‑TripoSR (int8) → 5‑10 s inference <br> CPU‑only → 2‑5 dk (optimize + batch) |
| **Gizlilik** | Tüm işlemler **yerel** Docker sandbox; dışarıdan ağ isteği yok; veriler sadece `./data` klasöründe kalır. |
| **Güvenlik** | Docker‑AppArmor, TLS‑HTTPS, JWT‑optional, audit‑log, sandbox seviye izоляции. |
| **Gelecekte** | K8s‑cluster, GPU‑node‑pool, UI temaları (Türkçe), Auth‑service, API‑rate‑limiting, model‑caching CDN. |
| **Dökümantasyon** | Swagger UI (FastAPI) → `/docs` ; OpenAPI spec → Git‑Repo içinde `openapi.yaml`. |
| **CI/CD** | GitHub Actions → `lint + pytest + safety + build-image`. |
| **Perf Monitoring** | Prometheus `/metrics` endpoint + Grafana dashboards (latency, GPU‑util). |

---  

### 🚀 SONRAKİ ADIM  

**Phase 4 – Detaylı Implementasyon Planı**  
1. Proje dizin yapısı (`frontend/`, `backend/`, `ml-service/`).  
2. Docker‑files ve `docker-compose.yml` örnekleri.  
3. Model yükleme / quantization adımları.  
4. UI‑mock (wireframe) ve 3D‑viewer entegrasyonu.  
5. CI‑pipeline kurulumu.  

Bu adımları ve daha fazla teknik dokümantasyonu **devam eden** job‑specification’te bulacaksınız.  

**Devam etmek ister misiniz?**  → *Evet,Phase‑4‑detaylı‑implementasyon‑planı*  ya da *Bir adım geri (Phase‑2‑PRD‑inceleme)*?  

*(Her iki seçenek de aynı formatta, size en uygun yolu seçmenizi sağlar.)*