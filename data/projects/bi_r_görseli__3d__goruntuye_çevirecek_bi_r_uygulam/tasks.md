# IDEA-TO-PROJECT: PHASE 4 — DETAILED IMPLEMENTATION PLAN

## PROJECT OVERVIEW
**Img2Mesh** — 2D image to 3D model converter (local-first, dual-hardware support)

**Hardware targets:**
- **Machine A**: AMD Ryzen 5, 16GB RAM, 512GB SSD, GPU (GTX 1650, 8GB VRAM)
- **Machine B**: GPU-less server, 8GB RAM

**Total estimated time: 4-5 weeks** (adjustable based on team size)

---

## SPRINT 1 — MVP (Weeks 1-2)

**Goal**: Working prototype that converts a single image to a downloadable 3D model on both hardware configurations.

### Infrastructure & Setup (8 hours)

- [ ] **Initialize project repository** (2h)
  - Create monorepo structure: `frontend/`, `backend/`, `ml-service/`, `docker/`, `docs/`
  - Setup `.gitignore`, `README.md`, license (MIT)
  - Dependency: None

- [ ] **Docker environment setup** (4h)
  - Write `docker-compose.yml` with services: frontend (React/NGINX), backend (FastAPI), ml-service (PyTorch), db (PostgreSQL)
  - Create Dockerfiles for each service
  - Test `docker-compose up` on both target machines
  - Dependency: Task 1

- [ ] **CI/CD pipeline (GitHub Actions)** (2h)
  - Workflow: lint (black, flake8, eslint) → test (pytest) → build images → push to local registry
  - Setup local registry on target machine if needed
  - Dependency: Task 1

### Backend Core (20 hours)

- [ ] **FastAPI project skeleton** (4h)
  - Create `app/main.py`, `app/core/config.py`, `app/api/` structure
  - Setup CORS, rate limiting middleware
  - Add health check endpoint (`/health`)
  - Dependency: Task 1

- [ ] **Database models & migrations** (4h)
  - Define SQLAlchemy models: User, Model, ModelFile, AuditLog (as per PRD)
  - Setup Alembic migrations
  - Create initial migration
  - Dependency: Task 5

- [ ] **File upload service** (4h)
  - Implement `/api/v1/upload` endpoint (multipart/form-data)
  - Validate file types (JPG, PNG, WEBP), max size (10MB)
  - Save to `./data/uploads/{uuid}.{ext}`
  - Generate unique upload_id
  - Dependency: Task 5

- [ ] **Model inference service** (8h)
  - Create `ml_service/inference.py`
  - Implement model loader: TripoSR (GPU) with CPU fallback (ONNX quantized)
  - Auto-detect hardware: `torch.cuda.is_available()` → choose GPU/CPU path
  - Quantization: load int8 model for 8GB VRAM/8GB RAM constraints
  - Output: mesh file (GLB) + preview thumbnail
  - Dependency: Task 5, TripoSR repo clone

### Frontend Core (24 hours)

- [ ] **React + TypeScript setup** (4h)
  - Create React app with Vite
  - Install dependencies: `three.js`, `@react-three/fiber`, `@react-three/drei`, `axios`, `tailwindcss`
  - Setup routing (React Router)
  - Dependency: Task 1

- [ ] **Upload UI component** (4h)
  - Drag-and-drop file upload zone
  - File validation (type, size)
  - Progress bar for upload
  - Dependency: Task 13

- [ ] **3D viewer component** (8h)
  - Integrate Three.js via React Three Fiber
  - Implement orbit controls (rotate, zoom, pan)
  - Load GLB/OBJ models from URL
  - Basic lighting and grid helper
  - Dependency: Task 13

- [ ] **Process & status UI** (4h)
  - Display job status (queued, processing, done, error)
  - Polling `/status/{job_id}` every 2s
  - Progress bar with ETA
  - Dependency: Task 13, Task 9

- [ ] **Download & history UI** (4h)
  - List of generated models (from `/models` endpoint)
  - Download button for each model
  - Delete button (calls DELETE endpoint)
  - Dependency: Task 13, Task 10

### ML Integration (16 hours)

- [ ] **TripoSR model integration** (8h)
  - Clone and setup TripoSR in `ml-service/`
  - Create inference script: `python infer.py --image path/to/img.jpg --output model.glb`
  - Test on GPU machine: ensure < 10s inference
  - Dependency: Task 5

- [ ] **CPU fallback with quantization** (8h)
  - Convert TripoSR to ONNX (or use LGM/Stable Dream3D smaller model)
  - Quantize to int8 (reduce VRAM/RAM usage)
  - Test on 8GB RAM machine: ensure completion < 10 min
  - Implement auto-selection logic in backend
  - Dependency: Task 5, Task 16

### Testing (12 hours)

- [ ] **Unit tests - Backend** (4h)
  - Test upload endpoint (valid/invalid files)
  - Test model generation (mock inference)
  - Test database operations
  - Dependency: Task 5, Task 9

- [ ] **Unit tests - Frontend** (4h)
  - Test upload component
  - Test 3D viewer component (mock model)
  - Test status polling
  - Dependency: Task 13-17

- [ ] **Integration test - End-to-End** (4h)
  - Test full flow: upload → process → download on both hardware configs
  - Measure performance metrics (time, memory)
  - Dependency: All previous tasks

---

## SPRINT 2 — ENHANCEMENT (Weeks 3-4)

**Goal**: Polish, additional features, robustness, performance optimization.

### Enhanced Features (24 hours)

- [ ] **Batch processing** (8h)
  - Extend API: `/api/v1/process` accepts array of upload_ids
  - Implement queue system (Redis or in-memory with FastAPI BackgroundTasks)
  - Frontend: multi-select file upload, batch progress view
  - Dependency: Sprint 1 complete

- [ ] **Quality settings** (4h)
  - Add quality parameter: low (512x512), medium (1024x1024), high (original)
  - Backend: adjust model input resolution based on quality
  - Frontend: quality dropdown in process form
  - Dependency: Task 9

- [ ] **Export formats** (4h)
  - Support OBJ, STL, FBX exports (use `trimesh` library to convert GLB)
  - Add format selector in UI
  - Dependency: Task 9

- [ ] **Background removal (optional)** (4h)
  - Integrate RemBG (Python library) for auto background removal
  - Add toggle in UI: "Remove background before processing"
  - Dependency: Task 9

- [ ] **Turkish localization** (4h)
  - Translate all UI strings to Turkish
  - Use i18n library (react-i18next)
  - Dependency: Frontend components

### Performance & Optimization (16 hours)

- [ ] **Model caching** (4h)
  - Cache inference results by image hash (SHA256)
  - Store in `./data/cache/{hash}.glb`
  - On new request: compute hash → check cache → return cached if exists
  - Dependency: Task 9

- [ ] **GPU memory optimization** (4h)
  - Implement `torch.cuda.empty_cache()` after each inference
  - Add configurable batch size for GPU
  - Monitor VRAM usage, adjust model precision if needed
  - Dependency: Task 16

- [ ] **CPU performance tuning** (4h)
  - Profile CPU inference, optimize data loading
  - Use `multiprocessing` for CPU-bound tasks
  - Add `--workers` flag for parallel CPU inference (if multiple cores)
  - Dependency: Task 16

- [ ] **Progressive loading (preview)** (4h)
  - Generate low-poly preview mesh first (10k vertices)
  - Stream preview to frontend while full model generates
  - Dependency: Task 9, Task 27

### Testing & QA (16 hours)

- [ ] **Load testing** (4h)
  - Simulate 5 concurrent users on both hardware configs
  - Measure queue times, resource usage
  - Identify bottlenecks
  - Dependency: All features complete

- [ ] **Cross-browser testing** (4h)
  - Test on Chrome, Firefox, Safari, Edge
  - Ensure 3D viewer works across browsers
  - Fix any WebGL compatibility issues
  - Dependency: Frontend complete

- [ ] **Bug fixing & polish** (8h)
  - Fix issues found in load testing
  - Improve error messages
  - Add loading skeletons, better UX feedback
  - Dependency: All testing

---

## SPRINT 3 — LAUNCH (Week 5)

**Goal**: Production readiness, monitoring, documentation, final deployment.

### Deployment & Ops (16 hours)

- [ ] **Production Docker images** (4h)
  - Optimize Dockerfiles (multi-stage builds, smaller images)
  - Add health checks to Docker Compose
  - Setup `docker-compose.prod.yml` with resource limits
  - Dependency: Sprint 2 complete

- [ ] **Monitoring & logging** (4h)
  - Integrate Prometheus metrics in FastAPI (`prometheus-fastapi-instrumentator`)
  - Add Grafana dashboard for: CPU/GPU usage, memory, request latency, queue length
  - Centralized logging (JSON logs, optionally Loki)
  - Dependency: Task 35

- [ ] **Backup & persistence** (4h)
  - Configure volume mounts for `./data` (uploads, models, cache)
  - Add optional rclone backup script for cloud storage
  - Test restore from backup
  - Dependency: Task 35

- [ ] **Security hardening** (4h)
  - Review Docker security: non-root user, read-only filesystem where possible
  - Add TLS/HTTPS (self-signed or Let's Encrypt if exposed)
  - Audit all endpoints for authz (ensure no unauthorized access)
  - Dependency: Task 35

### Documentation (12 hours)

- [ ] **User documentation** (4h)
  - Write installation guide for both hardware setups
  - Create quickstart tutorial (step-by-step with screenshots)
  - FAQ section (common issues, performance expectations)
  - Dependency: All features complete

- [ ] **Developer documentation** (4h)
  - Architecture overview
  - API reference (OpenAPI/Swagger auto-doc)
  - Contributing guidelines
  - Code structure explanation
  - Dependency: All features complete

- [ ] **Deployment guide** (4h)
  - Production deployment checklist
  - Monitoring setup instructions
  - Scaling considerations (K8s, multiple GPUs)
  - Dependency: Task 35

### Final Testing & Release (8 hours)

- [ ] **Smoke test on both target machines** (2h)
  - Full end-to-end test on Machine A (GPU) and Machine B (CPU-only)
  - Verify performance meets PRD specs
  - Dependency: All above

- [ ] **Create release package** (2h)
  - Build final Docker images with version tags
  - Create release tarball with docker-compose, configs, docs
  - Generate checksums
  - Dependency: Task 35

- [ ] **User acceptance testing (UAT)** (4h)
  - Deploy on target machines for final user testing
  - Collect feedback, fix critical bugs
  - Final sign-off
  - Dependency: All above

---

## DEPENDENCY GRAPH (Simplified)

```
Sprint 1:
  Setup (1-4) → Backend (5-10) → ML (15-16) → Frontend (11-14) → Testing (17-19)
  
Sprint 2:
  Sprint1 complete → Features (20-24) → Optimization (25-28) → Testing (29-32)
  
Sprint 3:
  Sprint2 complete → Deployment (33-36) → Docs (37-39) → Release (40-42)
```

---

## REALISTIC ESTIMATES BY ROLE

If you have a team:

| Role | Hours (Sprint 1) | Hours (Sprint 2) | Hours (Sprint 3) |
|------|------------------|------------------|------------------|
| **Backend Developer** | 20 | 12 | 8 |
| **Frontend Developer** | 24 | 16 | 4 |
| **ML Engineer** | 16 | 8 | 0 |
| **DevOps** | 8 | 8 | 16 |
| **Tech Writer** | 0 | 0 | 12 |
| **QA Engineer** | 12 | 16 | 8 |
| **Total (person-hours)** | 80 | 60 | 48 |

**Total: ~188 person-hours** ≈ **4-5 weeks** with 1 person, or **2-3 weeks** with a 2-3 person team.

---

## HARDWARE-SPECIFIC CONSIDERATIONS

### For GPU Machine (8GB VRAM):
- Use full-precision TripoSR (or lightly quantized)
- Expect inference: 3-8 seconds per image
- Enable CUDA in Docker: `--gpus all`

### For CPU-Only Machine (8GB RAM):
- Use int8-quantized ONNX model (~800MB)
- Expect inference: 2-10 minutes per image (depending on CPU)
- Use all CPU cores: `--cpuset-cpus="0-7"` in Docker
- Consider adding swap file (4GB) to avoid OOM

---

## RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| **TripoSR model too large for 8GB RAM** | Have fallback model (Stable Dream3D tiny variant, ~500MB) |
| **Docker GPU passthrough complex** | Provide detailed setup guide for NVIDIA Container Toolkit; offer WSL2 instructions for Windows |
| **3D viewer performance issues** | Use `draco` compression for GLB, limit polygon count to 100k for preview |
| **Long CPU inference times** | Implement job queue with email notification; generate preview quickly, full model in background |
| **Model quality unsatisfactory** | Add post-processing (mesh simplification, smoothing) and user-adjustable parameters |

---

## SUCCESS METRICS (MVP)

- ✅ Single image upload → GLB download in < 30s on GPU machine
- ✅ Same workflow completes in < 10 min on CPU-only machine
- ✅ 3D viewer loads model with >30 FPS for meshes < 200k polygons
- ✅ All data stays local (no outbound network calls from app)
- ✅ Turkish UI fully functional
- ✅ Docker-compose up works on Ubuntu 22.04 and Windows 10+ (WSL2)

---

**Ready to proceed?** This plan covers all phases from infrastructure to launch. Adjust sprint lengths based on your available time and team size.