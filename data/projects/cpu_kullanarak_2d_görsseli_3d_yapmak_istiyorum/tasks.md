# IDEA-TO-PROJECT: PHASE 4 — TASK BREAKDOWN

## Sprint 1: MVP Core Pipeline (8-10 days, ~60 hours)

### Sprint Goal
A working command-line prototype that converts a single 2D image to a 3D mesh using CPU-only inference, with basic GUI shell.

---

### Tasks

- [ ] **Project Setup & Environment** (4h)
  - Create project structure (src/, tests/, models/, docs/)
  - Set up Python 3.11 virtual environment
  - Install core dependencies: onnxruntime-cpu, opencv-python, open3d, numpy
  - Configure pre-commit hooks (black, flake8, mypy)
  - Initialize Git repo with .gitignore

- [ ] **DepthAnything V2 Integration** (12h)
  - Download DepthAnything V2 ONNX model (find correct URL/weights)
  - Create model loader with fallback for CPU-only
  - Implement image preprocessing pipeline (resize, normalize, BGR→RGB)
  - Write inference wrapper function returning depth map as numpy array
  - Add quantization option (INT8) for speed boost
  - **Dependencies:** Project Setup

- [ ] **Point Cloud Generation** (8h)
  - Convert depth map to 3D points using pinhole camera model
  - Implement focal length estimation from image size
  - Generate Open3D PointCloud object with colors from original image
  - Add outlier removal (statistical/radius)
  - **Dependencies:** DepthAnything V2 Integration

- [ ] **Mesh Reconstruction** (10h)
  - Implement Poisson surface reconstruction (Open3D)
  - Add alternative: Ball Pivoting algorithm for thin structures
  - Mesh simplification (quadric edge collapse) for performance
  - Basic mesh cleaning: remove degenerate triangles, duplicate vertices
  - **Dependencies:** Point Cloud Generation

- [ ] **Texture Projection** (6h)
  - Generate UV mapping for mesh (Open3D or custom)
  - Project original image onto UV-unwrapped mesh
  - Export texture as PNG alongside mesh
  - **Dependencies:** Mesh Reconstruction

- [ ] **Export Formats** (4h)
  - Write OBJ exporter (vertices, faces, texture coordinates)
  - Write GLTF/GLB exporter (binary)
  - Optional: STL exporter (no texture)
  - **Dependencies:** Mesh Reconstruction, Texture Projection

- [ ] **Basic PyQt6 GUI** (12h)
  - Create main window with menu bar and central widget
  - Implement drag-and-drop file upload area
  - Add image preview widget (QPixmap)
  - Add depth map preview widget
  - Add 3D mesh viewer (using Open3D visualizer or PyQtGraph)
  - Progress bar and status labels
  - **Dependencies:** All core pipeline tasks

- [ ] **Controller & Workflow** (6h)
  - Wire UI events to pipeline functions
  - Implement threading (QThread) to keep UI responsive
  - Add cancel/stop functionality
  - Error handling with user-friendly messages
  - **Dependencies:** Basic PyQt6 GUI, all core pipeline

- [ ] **MVP Testing** (8h)
  - Test with 10+ sample images (different sizes, subjects)
  - Measure inference time (target: <90s for 1080p)
  - Measure memory usage (target: <4GB)
  - Verify output mesh integrity (no holes, correct texture)
  - Cross-platform sanity check (Windows/Linux)
  - **Dependencies:** Controller & Workflow

---

## Sprint 2: Enhancement & Polish (8-10 days, ~50 hours)

### Sprint Goal
Polished UI, additional features, robust error handling, and test coverage.

---

### Tasks

- [ ] **Quality Settings Implementation** (6h)
  - Add UI dropdown: Fast/Low/Medium/High quality
  - Fast: lower resolution depth model (e.g., 384px), quick Poisson
  - High: full resolution (518px), detailed Poisson, smoothing
  - Benchmark each mode and display estimated time
  - **Dependencies:** Sprint 1 completion

- [ ] **Batch Processing** (10h)
  - Multi-file upload support (QFileDialog multi-select)
  - Process queue sequentially or parallel (configurable)
  - Batch progress summary (success/failure counts)
  - Export all results to single output folder
  - **Dependencies:** Quality Settings, Controller

- [ ] **Mesh Editing Tools** (12h)
  - Simple mesh cleanup: fill holes, remove floating vertices
  - Mesh simplification slider (decimation)
  - Basic transform: rotate/scale/translate mesh
  - Export edited mesh
  - **Dependencies:** Sprint 1 completion

- [ ] **Improved 3D Viewer** (8h)
  - Integrate Open3D visualizer with PyQt (using QWindow)
  - Add mouse controls: orbit, pan, zoom
  - Wireframe/solid/texture toggle
  - Lighting adjustment
  - **Dependencies:** Sprint 1 completion

- [ ] **Error Handling & Logging** (6h)
  - Comprehensive try/except blocks throughout pipeline
  - Log errors to file (`~/.depth2mesh/logs/`)
  - User-friendly error dialogs with suggested fixes
  - Graceful degradation (e.g., fallback to Ball Pivoting if Poisson fails)
  - **Dependencies:** All Sprint 2 features

- [ ] **Unit & Integration Tests** (8h)
  - Write pytest tests for each module
  - Mock ONNX inference for fast tests
  - Integration test: image → OBJ (verify file exists, valid mesh)
  - CI pipeline: GitHub Actions to run tests on push
  - **Dependencies:** Error Handling

---

## Sprint 3: Launch & Distribution (5-7 days, ~35 hours)

### Sprint Goal
Production-ready installers, documentation, and release.

---

### Tasks

- [ ] **PyInstaller Packaging** (6h)
  - Create spec file for PyQt6 + Open3D + onnxruntime
  - Test onefile bundle on Windows (exe), macOS (app), Linux (AppImage)
  - Handle Open3D's dynamic libraries and Visual C++ runtime
  - Reduce bundle size (exclude unnecessary packages)
  - **Dependencies:** Sprint 2 completion

- [ ] **Installer Creation** (6h)
  - Windows: Inno Setup script with license, README, uninstaller
  - macOS: pkgbuild or create .dmg with Applications shortcut
  - Linux: Create AppImage with desktop file, or .deb package
  - Sign installers (optional, requires certificates)
  - **Dependencies:** PyInstaller Packaging

- [ ] **Documentation** (10h)
  - Write user guide (PDF + online MkDocs)
  - Installation instructions per OS
  - Troubleshooting section (common errors, solutions)
  - API reference (if any)
  - Screenshots and GIFs
  - **Dependencies:** All features finalized

- [ ] **Release Preparation** (8h)
  - Create GitHub release page (v1.0.0)
  - Upload binaries, checksums, signature
  - Write changelog
  - Set up GitHub Pages for documentation
  - Create social media assets (banner, icon)
  - **Dependencies:** Installer Creation, Documentation

- [ ] **Final Testing & QA** (5h)
  - End-to-end testing on clean VMs (no Python installed)
  - Performance benchmarks on low-end hardware
  - Security scan (check for vulnerabilities in dependencies)
  - Verify license compliance (all dependencies permissive)
  - **Dependencies:** Release Preparation

---

## Total Estimate

| Sprint | Duration | Hours |
|--------|----------|-------|
| Sprint 1 | 8-10 days | ~60h |
| Sprint 2 | 8-10 days | ~50h |
| Sprint 3 | 5-7 days | ~35h |
| **Total** | 21-27 days | **~145 hours** |

---

## Critical Path & Dependencies

```
Project Setup → DepthAnything Integration → Point Cloud → Mesh → Texture → Export → GUI → Controller → MVP Testing
                                                                                   ↓
Quality Settings ← Batch Processing ← Mesh Editing ← Improved Viewer ← Error Handling ← Tests
                                                                                   ↓
PyInstaller ← Installer ← Documentation ← Release ← Final QA
```

**Key Risks:**
1. DepthAnything V2 model may be too slow on CPU (need quantization or smaller variant)
2. Open3D packaging for PyInstaller can be tricky (dynamic libs)
3. Poisson reconstruction may fail on some images (need fallback)
4. PyQt6 licensing (GPL) may require careful handling for commercial use

**Mitigation:**
- Benchmark early (end of Sprint 1 Day 2) to adjust quality targets
- Test PyInstaller build on Day 1 of Sprint 3
- Implement multiple mesh algorithms as fallbacks
- Consider switching to PySide6 (LGPL) if commercial licensing is a concern

---

**Ready to execute.**