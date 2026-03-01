**IDEA‑TO‑PROJECT: PHASE 3 – TECHNICAL ARCHITECTURE**  
*(DeskApp 3‑D Converter – CPU‑only 2D → 3D pipeline)*  

---

## 1️⃣ Recommended Tech‑Stack  

| Layer | Component | Why it fits the DeskApp requirements? | Alternatives discussed & why they were dropped |
|-------|-----------|---------------------------------------|-----------------------------------------------|
| **Language / Runtime** | **Python 3.12** | • Mature scientific ecosystem (torch, numpy, OpenCV, Open3D) <br>• Excellent support for model inference (ONNX, PyTorch) <br>• Cross‑platform (Win/macOS/Linux) | • Node.js – would require extra C++ bindings for Open3D <br>• Go – no native bindings for most ML libs |
| **Model Inference** | **ONNX Runtime + Depth‑Anything‑V2 (ONNX‑Exported)** | • Runs **purely on CPU** with multithreading optimisations <br>• Small binary size; no heavy Python runtime needed at client side <br>• Direct API to pull‑in quantised INT8 models for speed | • TensorRT – requires GPU <br>• TorchScript – needs Python interpreter on client |
| **3‑D Geometry & Processing** | **Open3D (python API)** → compiled to native libs via **PyInstaller** | • Proven implementations of depth‑to‑point‑cloud, Poisson mesh, smoothing, outlier removal <br>• Well‑documented, permissive MIT licence <br>• Works on CPU only | • CGAL – heavy C++ dependency, larger binary <br>• PyTorch3D – GPU‑biased |
| **UI Framework** | **PyQt6** (Qt 6) | • Native‑look desktop app on all target OSes <br>• Mature, supports dark/light themes, threading, OpenGL widget for 3‑D viewer <br>• Easy to bundle with PyInstaller | • Electron – larger runtime, uses Node/Web tech (overkill for a native tool) |
| **File Formats** | **.OBJ, .PLY, .STL, .GLTF/GLB, .FBX** (via Open3D + trimesh) | • All required by PRD for export <br>• trimesh can read/write them without external libs | • Blender‑Python API – adds large dependency & UI complexity |
| **Packaging / Distribution** | **PyInstaller** + **NSIS** (Windows), **pkgbuild**/**productbuild** (macOS), **deb/rpm** (Linux) | • Produces a single executable per platform; can bundle ONNX runtime & model binaries; offline‑ready (no external installers) | • Docker containers – would force a separate runtime and violate “desktop, offline” requirement |
| **Database** | **SQLite 3** (embedded) | • Zero‑install, portable, ACID‑compliant, fits small config/metadata storage <br>• Perfect for storing user settings, work‑order history, licence key | • PostgreSQL/MySQL – overkill, requires server component & network access |
| **Configuration Management** | **Python‑based `pydantic` settings + environment variables** | • Type‑safe config, easy to override for production vs dev (e.g., thread count, RAM limit) | • TOML/YAML files – more error‑prone for complex nested structures |
| **CI / CD** | **GitHub Actions** (Ubuntu, Windows, macOS runners) | • Automated builds for all three OSes, test matrix, produce release artefacts, generate signed installers | • Jenkins/CircleCI – extra infra not needed for a small open‑source‑style project |
| **Issue & Project Tracking** | **GitHub Issues + Projects** | • Already used for source, keeps everything in one place | – |
| **Version Control** | **Git** (hosted on GitHub) | – | – |

---

## 2️⃣ System Architecture (textual + mermaid)

```
graph TD
    %% UI layer
    UI[Desktop UI (PyQt6)]
    %% Processing layer
    PROC[Pipeline Engine (Python)]
    %% Model loading
    MODEL[ONNX Runtime + Depth‑Anything‑V2<br/>+ Custom optional models]
    %% 3D lib
    OPEN3D[Open3D geometry lib]
    %% DB layer
    DB[(SQLite DB)]
    %% Installer/Bundle
    INST[PyInstaller Bundle + NSIS/PKGS]
    
    %% Connections
    UI -->|User actions| PROC
    PROC -->|Load model & process| MODEL
    MODEL -->|Inference| OPEN3D
    OPEN3D -->|Create mesh| PROC
    PROC -->|Save result| DB
    PROC -->|Write files| UI[Export dialogs (OBJ/PLY/etc.)]
    UI -->|Settings| PROC
    PROC -->|Persist config| DB
    INST --> UI
    style UI fill:#f9f,stroke:#333,stroke-width:2px
    style PROC fill:#bbf,stroke:#333,stroke-width:2px
    style MODEL fill:#cfc,stroke:#333,stroke-width:1px
    style OPEN3D fill:#ffb,stroke:#333,stroke-width:1px
    style DB fill:#dfd,stroke:#333,stroke-width:1px
    style INST fill:#eee,stroke:#666,stroke-dasharray: 5 5
```

**Explanation of Flow**

1. **User Interaction** – All UI events (load image, start batch, change thread count, cancel) are captured by the PyQt6 window.  
2. **Validation** – Input files are checked (extension, size, corruption) before being passed to the **Processing Engine**.  
3. **Pipeline Engine** – A multi‑threaded orchestrator (uses `concurrent.futures.ThreadPoolExecutor`) dispatches steps:
   - *Pre‑process* → *Depth inference* → *Depth → Point‑cloud* → *Mesh reconstruction* → *Post‑process* (smoothing, outlier removal) → *Export*.  
   Each step can be swapped (e.g., replace Depth‑Anything‑V2 with a user‑provided ONNX model) without touching the UI.  
4. **Model Inference** – ONNX Runtime executes the depth model on the **CPU** using all configured threads (`OMP_NUM_THREADS`/`MKL_NUM_THREADS`). The ONNX files are bundled with the executable; at start‑up they are extracted to a temporary folder and loaded once.  
5. **3‑D Processing** – Open3D provides high‑level functions (`create_from_depth_image`, `compute_point_cloud`, `compute_mesh_surface`, `remove_statistical_outliers`, `simplify_quadric_decimation`). All of these are **CPU‑only** but heavily optimised (OpenMP, multi‑threaded).  
6. **Export** – The final mesh is written to the user‑selected folder in the requested format (OBJ/PLY/STL/GLTF). Export is performed via Open3D’s `write_triangle_mesh` or `write_point_cloud`.  
7. **Persistence** – All operational metadata (project name, last used folder, chosen settings, history of recent files) are stored in a **SQLite** database (`deskapp.db`) located in the user’s profile folder (`%APPDATA%/DeskApp` on Windows, `~/Library/Application Support/DeskApp` on macOS, `~/.local/share/DeskApp` on Linux).  
8. **Packaging** – When a release is built, **PyInstaller** bundles the Python interpreter, all compiled wheels (torch, onnxruntime, open3d, pyqt6), and the ONNX model files into a single executable per platform. NSIS creates an installer, macOS uses `pkgbuild`, Linux creates `deb`/`rpm` with a proper entry‑point script.

---

## 3️⃣ Database Schema  

| Table | Primary Key | Columns (type) | Description |
|-------|-------------|----------------|-------------|
| **users** | `user_id` (INTEGER) | `email TEXT`, `created_at DATETIME`, `license_type TEXT` (FREE / PRO) | Stores licence information for the Pro version (single‑seat key). |
| **projects** | `project_id` (INTEGER) | `user_id INTEGER`, `name TEXT`, `created_at DATETIME`, `status TEXT` (CREATED / RUNNING / FINISHED / CANCELLED), `settings_json TEXT` | One logical work‑order per user session. Settings JSON contains thread count, selected model variant, resolution, export options. |
| **project_files** | `file_id` (INTEGER) | `project_id INTEGER`, `file_path TEXT`, `stage TEXT` (PREPROCESS / DEPTH / POINT_CLOUD / MESH / EXPORT), `timestamp DATETIME`, `output_path TEXT` | Tracks each intermediate artefact; useful for resuming cancelled jobs. |
| **settings** | `config_key` (TEXT) | `user_id INTEGER`, `key TEXT`, `value TEXT` | Simple key‑value store for UI‑level preferences (e.g., `theme=dark`, `threads=8`, `memory_limit=4096`). |
| **export_history** | `history_id` (INTEGER) | `user_id INTEGER`, `project_id INTEGER`, `output_path TEXT`, `output_format TEXT`, `created_at DATETIME` | Keeps a log of successful exports (helps UI display recent files). |
| **audit_log** | `log_id` (INTEGER) | `user_id INTEGER`, `event TEXT`, `details TEXT`, `timestamp DATETIME` | For compliance / debugging (e.g., “User cancelled job after 12 min”). |

**SQL Example (SQLite)**  
```sql
CREATE TABLE users (
    user_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    email     TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    license_type TEXT CHECK(license_type IN ('FREE','PRO'))
);

CREATE TABLE projects (
    project_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    name         TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    status       TEXT CHECK(status IN ('CREATED','RUNNING','FINISHED','CANCELLED')),
    settings_json TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE project_files (
    file_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL,
    file_path    TEXT NOT NULL,
    stage        TEXT CHECK(stage IN ('PREPROCESS','DEPTH','POINT_CLOUD','MESH','EXPORT')),
    timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,
    output_path  TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(project_id)
);
```

The schema is deliberately lightweight; it can be expanded later (e.g., adding *product* table for multi‑license management) without affecting the core pipeline.

---

## 4️⃣ API Endpoints  

DeskApp is **a pure desktop client** – there is **no public HTTP API** required for core functionality.  
Nevertheless, the internal services expose a **restricted, in‑process REST‑like interface** (via **FastAPI** or **Starlette**) for future cloud‑sync or remote‑control extensions.  

| Endpoint (local) | Method | Request Body | Response | Purpose |
|------------------|--------|--------------|----------|---------|
| `/health` | GET | – | `{status: "ok"}` | Liveness probe used by CI and installer scripts |
| `/pipeline/start` | POST | `{project_id, settings}` | `{job_id, status:"queued"}` | Kick‑off a processing job from UI or external script |
| `/pipeline/status` | GET | `?job_id=xyz` | `{status:"running"/"completed"/"failed", progress:0‑100, eta_seconds:…}` | UI polls to update progress bar |
| `/pipeline/cancel` | POST | `{job_id}` | `{status:"cancelled"}` | Graceful cancellation |
| `/export/history` | GET | – | `{exports:[{path,format,date}]}` | Return list of recent exports (used for UI “Recent” menu) |
| `/settings/get` | GET | – | `{theme:"dark", threads:8, memory_limit:4096}` | Retrieve persisted config |
| `/settings/set` | POST | `{key,value}` | `{ok:true}` | Persist UI settings |

All endpoints are **optional placeholders**; they can be disabled at release time. They are implemented using **Starlette** (≈ 2 kB) and started as a background thread inside the same process; they do **not** open any external ports unless explicitly enabled for remote management.

If a future **cloud‑sync** feature is added (e.g., optional backup to a private server), this API will be the entry point.

---

## 5️⃣ Authentication & Authorization Strategy  

| Layer | Considerations | Implementation |
|-------|----------------|----------------|
| **Desktop login** | No network authentication required for core offline use. | None – the app can be used by anyone who launches it. |
| **Pro licence key** (optional paid tier) | Validate a **single‑seat licence** to unlock premium features (e.g., higher‑resolution Large model, unlimited batch size). | - Store licence hash in `users` table. <br>- At start‑up, read a **public key** embedded in the binary, verify the licence file (signed JSON). <br>- UI disables Pro‑only UI elements when validation fails. |
| **Future cloud sync** | If remote storage is introduced, use **OAuth2** (Google/ Microsoft) or **JWT** with short‑lived tokens. | - Leverage **OAuthLib** library. <br>- Tokens saved in an encrypted file (`~/.config/deskapp/oauth_token.json`). |
| **File system permissions** | Prevent unauthorized users on shared machines from reading/writing other users’ projects. | - Store data under the per‑user profile directory (`%APPDATA%/DeskApp` etc.). <br>- On Windows use ACLs to restrict access; on *nix use file permissions (0700). |
| **Code signing** | Prevent tampering of the packaged executable. | - On Windows, sign the installer with an EV code‑signing certificate; on macOS, sign the app bundle with an Apple Developer ID; on Linux, provide GPG‑signed `.deb/.rpm` packages. |

**Result:** The base MVP can run **without any login**, satisfying the “offline, no account” requirement. Pro licences are purely optional and enforced locally.

---

## 6️⃣ Deployment Architecture  

```
+-------------------+      +--------------------+      +-------------------+
|   Developer CI    | ---> |   Artifact Store   | ---> |   Release Packages|
| (GitHub Actions)  |      | (GitHub Releases)  |      | (NSIS, pkgbuild, .deb) |
+-------------------+      +--------------------+      +-------------------+
        ^                                                          |
        |                                                          |
        +-------------------+  Build scripts  +-------------------+
                            |                     |
                        +---v-----------------v---+
                        |   Platform‑specific   |
                        |   Installer Builder   |
                        +-----------------------+
```

### Development & Build Pipeline  

| Stage | CI Job (GitHub Actions) | Output |
|-------|------------------------|--------|
| **Lint/Unit Tests** | `python -m flake8`, `pytest` | Code quality badge |
| **Model Validation** | Download ONNX model, run a quick inference sanity check | Ensure model integrity |
| **Package Build** (Windows) | Install NSIS, run `pyinstaller --onefile ...`, then `nsis` installer creator | `DeskApp-Setup.exe` |
| **Package Build** (macOS) | Run `pyinstaller --windowed ...`, then `pkgbuild --installer` | `DeskApp.dmg` |
| **Package Build** (Linux) | Run `pyinstaller --onefile ...`, then `fpm` to create `.deb` and `.rpm` | `deskapp_1.0.0_amd64.deb` etc. |
| **Publish** | Upload artefacts to GitHub Releases, attach checksums | User downloads |
| **Post‑release** | Optional auto‑notify via GitHub Issues or email | – |

All builds are **deterministic**: lock‑file (`requirements.txt` + `hashes.txt`) ensures the exact binary is reproduced.

### Runtime Environment (User Machine)

- **No external dependencies** beyond the bundled libraries.  
- **CPU usage** is configurable via UI (`Settings → Threads`, `Settings → Memory limit`).  
- **Memory guard**: The pipeline checks `psutil.virtual_memory().available` before each major step; if available < configured limit, it pauses and notifies the user.

---

## 7️⃣ Third‑Party Integrations  

| Integration | Reason | Library / Service |
|------------|--------|-------------------|
| **OpenCV** | Image loading, resizing, colour conversion | `opencv-python` |
| **ONNX Runtime** | CPU‑only inference of Depth‑Anything‑V2 & any custom user‑provided model | `onnxruntime` |
| **PyQt6** | Native desktop UI, 3‑D OpenGL viewer | `PyQt6` |
| **Open3D** | Geometry processing (point cloud, Poisson, mesh simplification) | `open3d` |
| **trimesh** | Additional file‑format support (GLTF, FBX) | `trimesh` |
| **psutil** | Query system resources for memory guard | `psutil` |
| **SQLite3** (builtin) | Persistence of settings & history | – |
| **GitHub Actions** | CI/CD automation | – |
| **FastAPI / Starlette** (optional) | Expose internal health & status endpoints (future cloud‑sync) | – |
| **pydantic** | Typed settings validation | – |
| **pyinstaller** | Create distributable executables | – |
| **nsis** (Windows), **pkgbuild/productbuild** (macOS), **fpm** (Linux) | Installer packaging | – |
| **Optional cloud storage** (future) | User can upload finished models to Sketchfab or Google Drive | `google-api-python-client`, `requests` |

All third‑party libraries are **MIT / Apache 2.0** or similarly permissive licences, satisfying the project’s open‑source philosophy.

---

## 8️⃣ Scalability & Future‑Proofing  

| Concern | Current Solution | Extension Path |
|---------|------------------|----------------|
| **Concurrency (multiple batch jobs)** | The pipeline uses a thread‑pool limited by `Settings → Max concurrent pipelines`. | Add a **job‑queue** (e.g., SQLite‑backed `jobs` table) and a **worker pool** that can be scaled to N cores. |
| **Large image batches (>500)** | Chunked processing – each image processed sequentially to keep memory < limit. | Introduce **asynchronous chunking** with a producer‑consumer pattern; allow user‑selected chunk size. |
| **Model updates** | ONNX models are versioned in `/models/` folder; on start‑up the app checks for a newer hash. | Build an **auto‑update checker** that pulls the latest `depth_anything_v2_large.onnx` from a CDN (e.g., GitHub releases). |
| **Multi‑user licences** | Currently a single‑seat licence stored locally. | Add a **license server** (tiny Flask API) that hands out signed tokens for per‑seat licences, enabling enterprise deployment. |
| **Internationalisation** | All UI strings are loaded from `.qm` files generated via `pylupdate5`. | Extend translation files to support **right‑to‑left** languages (Arabic/Persian). |
| **GPU fallback (future)** | Not required now. | When a machine with a compatible GPU is detected, the pipeline can auto‑switch to the **CUDA** ONNX Runtime backend for up to 5× speed‑up, without breaking the CPU‑only contract. |
| **CI/CD for multiple Python versions** | Currently tested on 3.11, 3.12. | Add matrix testing on 3.10‑3.13 to guarantee forward compatibility. |
| **Telemetry (optional, opt‑in)** | None in MVP. | Add **opt‑in anonymous usage metrics** (e.g., number of images processed) stored locally; can be exported to a remote analytics endpoint if user enables it. |

---

## 9️⃣ Summary of Technical Foundations  

| Area | Decision | Key Benefit |
|------|----------|-------------|
| **Language** | Python 3.12 | Rich ML ecosystem, cross‑platform |
| **Model execution** | ONNX Runtime (CPU) | Zero‑GPU requirement, fast multi‑threaded inference |
| **3‑D pipeline** | Open3D + trimesh | Proven algorithms, MIT licence, easy file‑format export |
| **UI** | PyQt6 | Native look on all OSes, easy bundling |
| **Packaging** | PyInstaller + platform‑specific installers | Single‑file executables, no external runtime |
| **Data persistence** | SQLite | Tiny, zero‑admin, portable |
| **Build pipeline** | GitHub Actions → release artefacts | Automated, reproducible builds |
| **Licensing** | Optional Pro key stored locally | Enables freemium model without server |
| **Extensibility** | Modular pipeline + settings JSON | Easy swap of model variants, future cloud‑sync or GPU fallback |

With these choices the **DeskApp** architecture satisfies every functional requirement from the PRD (CPU‑only operation, batch processing, multi‑format export, offline usage) while remaining **maintainable**, **testable**, and **future‑ready** for incremental feature additions (e.g., GPU acceleration, cloud sync, enterprise licensing).  

---  

**Next Phase** – Move to **Phase 4: Detailed Implementation Plan** (task breakdown, sprint schedule, prototype proof‑of‑concept).  

*Prepared by: Reasoner Agent (Technical Architecture Layer)*  
*Date: 23 February 2026*