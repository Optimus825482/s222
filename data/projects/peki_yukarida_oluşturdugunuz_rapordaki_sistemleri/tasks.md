**IDEA‑TO‑PROJECT: PHASE 4 — DETAILED TASK BREAKDOWN**  
*DeskApp 3‑D Converter – MVP implementation plan*  

---

### 📅 Overall Timeline (5 weeks, ~200 h total)

| Sprint | Duration | Focus | Estimated Hours |
|--------|----------|-------|-----------------|
| **Sprint 1** | 2 weeks | Core pipeline & basic UI | 72 h |
| **Sprint 2** | 2 weeks | Enhancements, polish, testing | 82 h |
| **Sprint 3** | 1 week | Packaging, installers, release | 42 h |
| **Buffer** | – | Unforeseen issues | 4 h |
| **Total** | 5 weeks | – | **200 h** |

---

## 🚀 SPRINT 1: FOUNDATION & CORE PIPELINE (2 weeks)

**Goal:** A working prototype that can take a single image, run depth estimation on CPU, generate a mesh, and export to OBJ/PLY/STL.

| Task | Est. (h) | Dependencies | Notes |
|------|----------|--------------|-------|
| **1.1 Project setup** | 4 | – | Create Git repo, structure (`src/`, `models/`, `tests/`), Python 3.12 venv, `requirements.txt` with pinned versions. |
| **1.2 ONNX model integration** | 8 | 1.1 | Download Depth‑Anything‑V2‑Small ONNX; create `DepthEstimator` class using ONNX Runtime (CPU). Add resolution options (384, 518). |
| **1.3 Depth‑to‑pointcloud** | 6 | 1.2 | Implement back‑projection using simple pinhole camera (focal length = 1.0, principal point = image centre). Output Open3D `PointCloud`. |
| **1.4 Poisson surface reconstruction** | 6 | 1.3 | Integrate Open3D `PoissonReconstruction`. Tune depth/scale parameters for typical consumer photos. |
| **1.5 Export formats** | 4 | 1.4 | Save mesh as OBJ (with MTL), PLY, STL using Open3D. Ensure normals are computed. |
| **1.6 Basic UI skeleton** | 8 | 1.1 | PyQt6 main window, menu bar, status bar, central widget placeholder. Use `QThread` for background jobs. |
| **1.7 File open & image loading** | 4 | 1.6 | `QFileDialog` → OpenCV (`cv2.imread`) → convert to RGB → resize to model input. Show preview. |
| **1.8 Pipeline orchestration** | 8 | 1.2,1.3,1.4 | `PipelineWorker` (QObject) that runs steps sequentially, emits progress (0‑100), supports cancellation. |
| **1.9 Error handling & validation** | 4 | 1.7,1.8 | Catch file errors, OOM, model load failures; show user‑friendly messages. |
| **1.10 Unit tests (core)** | 8 | 1.2,1.3,1.4 | `pytest` coverage: depth inference on a test image (output shape), pointcloud non‑empty, mesh valid. |
| **1.11 Cross‑platform sanity check** | 4 | 1.8 | Run on Windows, Linux, macOS (VMs) to catch OS‑specific path or library issues. |
| **1.12 Documentation: README & usage** | 4 | 1.5,1.8 | Install instructions, quick start, known limitations (CPU speed). |
| **Sprint 1 Total** | **72** | – | – |

**Deliverable:** Functional prototype (single‑image → 3D model) with basic UI, running on all three OSes.

---

## ✨ SPRINT 2: ENHANCEMENTS & POLISH (2 weeks)

**Goal:** Batch processing, settings, 3D viewer, performance tuning, and stable testing.

| Task | Est. (h) | Dependencies | Notes |
|------|----------|--------------|-------|
| **2.1 Batch processing queue** | 12 | 1.8 | Add `BatchQueue` dialog; limit concurrent jobs via thread‑pool; per‑image progress; pause/resume. |
| **2.2 Settings panel** | 8 | 1.6 | `QSettings` backed by SQLite; UI for: thread count, memory limit, default resolution, export format, theme (dark/light). |
| **2.3 Advanced 3D viewer** | 12 | 1.4 | Integrate Open3D visualizer (or `pyqtgraph`/`vtk`?) with rotate/zoom/pan; show point cloud and mesh; wireframe toggle. |
| **2.4 Model variant selection** | 6 | 1.2 | UI dropdown for Small/Base/Large; load corresponding ONNX file. |
| **2.5 Memory guard** | 4 | 2.1 | Before each image, check `psutil.virtual_memory().available`; if below threshold, wait or stop batch. |
| **2.6 Performance optimisation** | 8 | 1.2,1.8 | Profile CPU usage; enable ONNX Runtime optimisations (intra‑op threads); test quantised INT8 model variant. |
| **2.7 UI polish** | 8 | 1.6,2.3 | Add icons, tooltips, responsive layout; ensure scaling on HiDPI screens. |
| **2.8 License key system** | 8 | 2.2 | Simple RSA‑signed JSON licence; check at startup; unlock “Pro” (unlimited batch, Large model). Store hash in SQLite. |
| **2.9 Comprehensive testing** | 12 | 2.1,2.3 | Integration tests (batch → multiple exports) using `pytest‑qt`; cross‑platform run on CI; add coverage reporting. |
| **2.10 Bug‑fix & refinement** | 4 | – | Address issues found in Sprint 1 & early Sprint 2 testing. |
| **Sprint 2 Total** | **82** | – | – |

**Deliverable:** Feature‑complete MVP with batch, settings, viewer, and performance guards; test coverage >80%.

---

## 📦 SPRINT 3: RELEASE PREPARATION (1 week)

**Goal:** Produce signed installers for all platforms and publish.

| Task | Est. (h) | Dependencies | Notes |
|------|----------|--------------|-------|
| **3.1 PyInstaller packaging** | 12 | 2.10 | Create `.spec` files per OS; bundle ONNX models, Qt plugins; test standalone executables. |
| **3.2 Installer creation** | 8 | 3.1 | Windows: NSIS script; macOS: `pkgbuild` + `productbuild`; Linux: `fpm` → `.deb`/`.rpm`. |
| **3.3 Code signing setup** | 4 | 3.2 | (Optional) Obtain EV cert; sign Windows installer and macOS app. If no cert, produce unsigned with warning. |
| **3.4 Final QA on clean VMs** | 8 | 3.2 | Test install, uninstall, first‑run on fresh Windows 10/11, Ubuntu 22.04, macOS 13+. Verify no missing DLLs. |
| **3.5 Documentation finalisation** | 4 | 2.12,3.4 | User manual (PDF), FAQ, release notes (new features, known issues). |
| **3.6 GitHub page & release** | 4 | 3.4 | Build workflow to auto‑upload assets; create GitHub Release page with screenshots, changelog. |
| **3.7 Post‑release monitoring plan** | 2 | – | Define how to collect crash reports (e.g., Sentry opt‑in) and user feedback. |
| **Sprint 3 Total** | **42** | – | – |

**Deliverable:** Production‑ready installers for Windows/macOS/Linux, published on GitHub, with documentation.

---

## 🔗 DEPENDENCY GRAPH (simplified)

```
Sprint 1: 1.1 → 1.2 → 1.3 → 1.4 → 1.5
          1.1 → 1.6 → 1.7 → 1.8 → 1.9
          1.2,1.3,1.4 → 1.10
          1.8 → 1.11
          1.5,1.8 → 1.12

Sprint 2: 1.8 → 2.1
          1.6 → 2.2
          1.4 → 2.3
          1.2 → 2.4
          2.1 → 2.5
          1.2,1.8 → 2.6
          1.6,2.3 → 2.7
          2.2 → 2.8
          2.1,2.3 → 2.9
          2.9 → 2.10

Sprint 3: 2.10 → 3.1 → 3.2 → 3.4
          3.2 → 3.3 (optional)
          3.4 → 3.5 → 3.6
```

---

## ⚙️ NOTES & RISK MITIGATION

- **CPU performance:** Depth Anything V2‑Small on an 8‑core CPU (i7‑12700) ~0.8‑2 s per 518×518 image. Batch processing will be I/O‑bound; ensure pipeline can handle 10‑20 images/hour.  
- **Memory usage:** Keep batch size small (1 image at a time) or add configurable chunk size. Monitor with `psutil`.  
- **Cross‑platform quirks:**  
  - Windows: bundle `vcruntime140.dll` if needed.  
  - macOS: handle notarisation if distributing outside App Store (optional).  
  - Linux: manylinux wheel compatibility; test on Ubuntu 20.04+.  
- **ONNX model size:** ~200 MB for Large; include only Small in base installer, offer Large as optional download.  
- **Testing coverage:** Use `pytest‑cov` to enforce >80% coverage on core modules (`pipeline`, `depth`, `mesh`). UI tests can be manual + automated with `pytest‑qt` for critical paths.  
- **Licensing:** Pro key can be a simple RSA‑signed JSON; generate keys offline with a script; verification uses embedded public key.  

---

## 📋 SUMMARY CHECKLIST

- [ ] Repository scaffolded (Git, venv, CI)  
- [ ] Depth Anything V2 ONNX integrated & CPU‑tested  
- [ ] Depth→pointcloud→mesh pipeline functional  
- [ ] Export to OBJ/PLY/STL working  
- [ ] Basic PyQt6 UI with file open, progress, cancel  
- [ ] Batch queue & settings panel  
- [ ] 3D viewer (Open3D) embedded  
- [ ] Memory guard & performance tuning  
- [ ] Unit + integration tests (CI)  
- [ ] Installers built for Windows/macOS/Linux  
- [ ] Documentation complete  
- [ ] GitHub release published  

---

**Next step:** Approve this plan → start **Sprint 1** task **1.1** (project setup).  

*Prepared by: Speed Agent (Task Breakdown)*  
*Date: 23 February 2026*