```text
depth2mesh/
├── .env.example
├── .gitignore
├── Dockerfile
├── LICENSE
├── MANIFEST.in
├── README.md
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── scripts/
│   ├── build.py
│   └── download_model.py
├── src/
│   ├── __init__.py
│   ├── cli.py
│   ├── gui.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── depth_estimator.py
│   │   ├── point_cloud.py
│   │   ├── mesh_builder.py
│   │   ├── exporter.py
│   │   └── utils.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   └── routes.py
│   └── db/
│       ├── __init__.py
│       ├── models.py
│       └── database.py
├── tests/
│   ├── __init__.py
│   ├── test_depth.py
│   ├── test_point_cloud.py
│   ├── test_mesh.py
│   └── test_exporter.py
└── models/
    └── README.md
```

---

## 1. Root configuration files

### `pyproject.toml`
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "depth2mesh"
version = "1.0.0"
description = "CPU-only 2D to 3D mesh conversion using DepthAnything V2"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "Depth2Mesh Team", email = "contact@example.com"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Topic :: Multimedia :: Graphics :: 3D Modeling",
]
keywords = ["2d-to-3d", "depth-estimation", "mesh-generation", "cpu-only"]
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.24.0",
    "opencv-python>=4.8.0",
    "open3d>=0.18.0",
    "onnxruntime>=1.16.0",
    "onnxruntime-cpu>=1.16.0",
    "pyqt6>=6.6.0",
    "sqlalchemy>=2.0.0",
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "python-multipart>=0.0.6",
    "pydantic>=2.5.0",
    "pillow>=10.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",
    "pre-commit>=3.4.0",
]
server = [
    "celery>=5.3.0",
    "redis>=5.0.0",
]

[project.scripts]
depth2mesh = "depth2mesh.cli:main"
depth2mesh-gui = "depth2mesh.gui:main"

[tool.setuptools]
package-dir = {"" = "src"}
include-package-data = true

[tool.setuptools.package-data]
depth2mesh = ["models/*.onnx"]

[tool.black]
line-length = 88
target-version = ["py311"]

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

---

### `requirements.txt`
```text
# Core dependencies (same as pyproject.toml)
numpy>=1.24.0
opencv-python>=4.8.0
open3d>=0.18.0
onnxruntime>=1.16.0
onnxruntime-cpu>=1.16.0
pyqt6>=6.6.0
sqlalchemy>=2.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
python-multipart>=0.0.6
pydantic>=2.5.0
pillow>=10.0.0

# Development dependencies
pytest>=7.4.0
pytest-cov>=4.1.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
pre-commit>=3.4.0

# Optional server dependencies
celery>=5.3.0
redis>=5.0.0
```

---

### `.env.example`
```bash
# Application
APP_ENV=development
LOG_LEVEL=INFO
MODELS_DIR=models
OUTPUT_DIR=output

# Database (SQLite for desktop, PostgreSQL for server)
DATABASE_URL=sqlite:///depth2mesh.db

# API (for server mode)
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=change-this-to-a-random-secret-key

# Celery (for server mode)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Model settings
DEFAULT_QUALITY=medium
MAX_IMAGE_SIZE=1920
ENABLE_QUANTIZATION=false
```

---

### `.gitignore`
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
models/*.onnx
*.log
output/
temp/
*.db
*.sqlite

# Testing
.pytest_cache/
.coverage
htmlcov/

# Build artifacts
*.exe
*.dmg
*.AppImage
*.deb
*.rpm
```

---

### `LICENSE`
```text
MIT License

Copyright (c) 2026 Depth2Mesh Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

### `MANIFEST.in`
```text
include models/*.onnx
include .env.example
recursive-include docs *
global-exclude *.pyc
```

---

### `README.md`
```markdown
# Depth2Mesh

CPU-only 2D-to-3D mesh conversion tool using DepthAnything V2.

Convert any 2D image into a 3D mesh model without requiring a GPU. Fully offline, open-source, and privacy-focused.

## Features

- **CPU-only inference** – runs on any modern processor
- **DepthAnything V2** – state-of-the-art depth estimation
- **One-click conversion** – image to 3D mesh in minutes
- **Multiple formats** – export to OBJ, GLTF/GLB, STL
- **Batch processing** – convert multiple images at once
- **Cross-platform** – Windows, macOS, Linux

## Quick Start

### Prerequisites

- Python 3.11 or higher
- (Optional) Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/depth2mesh.git
cd depth2mesh
```

2. Create a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Download the DepthAnything V2 model (≈500MB):
```bash
python scripts/download_model.py
```

### Command Line Usage

```bash
depth2mesh input.jpg -o output.obj --quality high
```

Options:
- `-o`, `--output` – output file path
- `-q`, `--quality` – fast/medium/high (default: medium)
- `-f`, `--format` – obj/glb/stl (default: glb)
- `--no-gpu` – force CPU inference (default)

### GUI Usage

```bash
depth2mesh-gui
```

Drag and drop an image, adjust quality settings, and click "Convert".

## Building Standalone Executables

We provide scripts to build single-file executables for Windows, macOS, and Linux:

```bash
# Windows
python scripts/build.py --platform windows

# macOS
python scripts/build.py --platform macos

# Linux
python scripts/build.py --platform linux
```

Outputs will be in the `dist/` directory.

## Docker (Server Mode)

For server/API deployment:

```bash
docker-compose up -d
```

The API will be available at `http://localhost:8000`.

See [API Documentation](docs/api.md) for endpoints.

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black src/ tests/
flake8 src/ tests/
mypy src/
```

### Pre-commit Hooks

```bash
pre-commit install
```

## Project Structure

```
depth2mesh/
├── src/              # Source code
│   ├── cli.py        # Command-line interface
│   ├── gui.py        # Desktop GUI (PyQt6)
│   ├── core/         # Core pipeline modules
│   ├── api/          # FastAPI server (optional)
│   └── db/           # Database models
├── models/           # Downloaded ML models
├── scripts/          # Build and utility scripts
├── tests/            # Unit and integration tests
└── docs/             # Documentation
```

## How It Works

1. **Depth Estimation** – The input image is preprocessed and fed into DepthAnything V2 (ONNX) to produce a depth map.
2. **Point Cloud** – The depth map is back-projected into a 3D point cloud using a pinhole camera model.
3. **Mesh Reconstruction** – Poisson surface reconstruction converts the point cloud into a watertight mesh.
4. **Mesh Cleaning** – Degenerate triangles are removed, holes are filled, and the mesh is simplified.
5. **Export** – The final mesh is saved in the requested format.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

MIT – see [LICENSE](LICENSE) file.

## Acknowledgments

- [DepthAnything V2](https://github.com/DepthAnything/Depth-Anything) – depth estimation model
- [Open3D](https://www.open3d.org/) – 3D data processing
- [ONNX Runtime](https://onnxruntime.ai/) – CPU inference
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) – GUI framework
```

---

### `Dockerfile`
```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY src/ src/
COPY models/ models/
COPY pyproject.toml .
COPY README.md .

# Create necessary directories
RUN mkdir -p output logs

# Expose API port
EXPOSE 8000

# Run the API server
CMD ["uvicorn", "depth2mesh.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### `docker-compose.yml`
```yaml
version: '3.8'

services:
  depth2mesh-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///depth2mesh.db
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - LOG_LEVEL=INFO
    volumes:
      - ./output:/app/output
      - ./logs:/app/logs
    restart: unless-stopped

  # Optional: Redis for Celery task queue (if using async processing)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

volumes:
  redis_data:
```

---

## 2. Source code files

### `src/__init__.py`
```python
"""Depth2Mesh: CPU-only 2D to 3D conversion."""
__version__ = "1.0.0"
```

---

### `src/core/__init__.py`
```python
from .depth_estimator import DepthEstimator
from .point_cloud import PointCloudGenerator
from .mesh_builder import MeshBuilder
from .exporter import Exporter
from .utils import load_image, save_mesh, ensure_dir

__all__ = [
    "DepthEstimator",
    "PointCloudGenerator",
    "MeshBuilder",
    "Exporter",
    "load_image",
    "save_mesh",
    "ensure_dir",
]
```

---

### `src/core/utils.py`
```python
import os
import logging
from pathlib import Path
from typing import Tuple, Optional
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

def load_image(
    path: str | Path,
    max_size: int = 1920,
    convert_rgb: bool = True
) -> Tuple[np.ndarray, int, int]:
    """
    Load an image from disk, optionally resize and convert to RGB.

    Args:
        path: Image file path
        max_size: Maximum dimension (width or height) for resizing
        convert_rgb: Convert BGR (OpenCV) to RGB

    Returns:
        Tuple of (image_array, original_width, original_height)
    """
    try:
        img = Image.open(path).convert("RGB")
        orig_w, orig_h = img.size

        # Resize if needed
        if max(orig_w, orig_h) > max_size:
            scale = max_size / max(orig_w, orig_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            logger.info(f"Resized image from {orig_w}x{orig_h} to {new_w}x{new_h}")
        else:
            new_w, new_h = orig_w, orig_h

        img_np = np.array(img)

        if convert_rgb:
            # Already RGB from PIL
            pass

        return img_np, new_w, new_h

    except Exception as e:
        logger.error(f"Failed to load image {path}: {e}")
        raise

def ensure_dir(path: str | Path) -> Path:
    """Create directory if it doesn't exist."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def save_mesh(
    mesh,
    output_path: str | Path,
    texture_image: Optional[np.ndarray] = None,
    uv_coords: Optional[np.ndarray] = None
):
    """
    Save mesh to file. Supports OBJ, GLTF/GLB, STL.

    Args:
        mesh: Open3D TriangleMesh
        output_path: Output file path
        texture_image: Optional texture image (HxWx3 uint8)
        uv_coords: Optional UV coordinates per vertex (Nx2)
    """
    import open3d as o3d

    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    suffix = output_path.suffix.lower()

    if texture_image is not None and uv_coords is not None:
        # Assign texture and UVs to mesh
        mesh.texture = o3d.geometry.Image(texture_image)
        mesh.triangle_uvs = uv_coords  # This expects per-triangle UVs; need to convert from per-vertex

    try:
        if suffix == ".obj":
            o3d.io.write_triangle_mesh(str(output_path), mesh, write_vertex_colors=True)
        elif suffix in [".gltf", ".glb"]:
            o3d.io.write_triangle_mesh(str(output_path), mesh, write_vertex_colors=True)
        elif suffix == ".stl":
            o3d.io.write_triangle_mesh(str(output_path), mesh)
        else:
            raise ValueError(f"Unsupported format: {suffix}")
        logger.info(f"Mesh saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save mesh: {e}")
        raise
```

---

### `src/core/depth_estimator.py`
```python
import logging
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
import onnxruntime as ort
import cv2

logger = logging.getLogger(__name__)

class DepthEstimator:
    """
    Depth estimation using DepthAnything V2 ONNX model.
    Runs on CPU only.
    """

    def __init__(
        self,
        model_path: str | Path,
        input_size: int = 518,
        quantize: bool = False,
        providers: Optional[list] = None
    ):
        """
        Initialize the depth estimator.

        Args:
            model_path: Path to ONNX model file
            input_size: Model input resolution (default 518)
            quantize: If True, use INT8 quantization (faster, slightly lower quality)
            providers: ONNX Runtime providers (defaults to CPUExecutionProvider)
        """
        self.model_path = Path(model_path)
        self.input_size = input_size
        self.quantize = quantize

        if providers is None:
            providers = ["CPUExecutionProvider"]

        # Load ONNX model
        try:
            self.session = ort.InferenceSession(
                str(self.model_path),
                providers=providers
            )
            logger.info(f"Loaded ONNX model from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            raise

        # Get model input details
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape
        # Typically: [1, 3, 518, 518]
        logger.debug(f"Model input shape: {self.input_shape}")

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for model input.

        Steps:
        1. Resize to model input size (square)
        2. Convert BGR to RGB if needed
        3. Normalize with ImageNet stats
        4. Convert to float32 and add batch dimension

        Args:
            image: Input image as numpy array (HxWx3) in RGB

        Returns:
            Preprocessed tensor (1x3xHxW)
        """
        # Resize to square input size
        if image.shape[0] != self.input_size or image.shape[1] != self.input_size:
            img_resized = cv2.resize(
                image,
                (self.input_size, self.input_size),
                interpolation=cv2.INTER_AREA
            )
        else:
            img_resized = image

        # Normalize with ImageNet mean/std
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img_normalized = (img_resized.astype(np.float32) / 255.0 - mean) / std

        # HWC to CHW
        img_chw = np.transpose(img_normalized, (2, 0, 1))
        # Add batch dimension
        img_batch = np.expand_dims(img_chw, axis=0)

        return img_batch

    def infer(self, input_tensor: np.ndarray) -> np.ndarray:
        """
        Run inference on preprocessed input.

        Args:
            input_tensor: Preprocessed input (1x3xHxW)

        Returns:
            Raw depth map output from model (1x1xH_outxW_out)
        """
        try:
            outputs = self.session.run(
                [self.output_name],
                {self.input_name: input_tensor}
            )
            depth_raw = outputs[0]  # shape: (1, 1, H_out, W_out)
            return depth_raw
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            raise

    def postprocess(
        self,
        depth_raw: np.ndarray,
        original_size: Tuple[int, int]
    ) -> np.ndarray:
        """
        Postprocess depth map to match original image size.

        Args:
            depth_raw: Raw model output
            original_size: (width, height) of original image

        Returns:
            Depth map as 2D numpy array (HxW) in original size
        """
        # Remove batch and channel dimensions
        depth_map = depth_raw[0, 0]  # shape: (H_out, W_out)

        # Resize to original size
        depth_resized = cv2.resize(
            depth_map,
            original_size,
            interpolation=cv2.INTER_LINEAR
        )

        # Normalize to 0-1 for consistency (optional scaling)
        depth_min = depth_resized.min()
        depth_max = depth_resized.max()
        if depth_max > depth_min:
            depth_normalized = (depth_resized - depth_min) / (depth_max - depth_min)
        else:
            depth_normalized = np.zeros_like(depth_resized)

        return depth_normalized

    def get_depth(
        self,
        image: np.ndarray,
        original_size: Optional[Tuple[int, int]] = None
    ) -> np.ndarray:
        """
        Full pipeline: preprocess, infer, postprocess.

        Args:
            image: Input image as numpy array (HxWx3) in RGB
            original_size: Original image size (width, height). If None,
                          uses image.shape[1], image.shape[0]

        Returns:
            Depth map (HxW) normalized to [0,1]
        """
        if original_size is None:
            original_size = (image.shape[1], image.shape[0])

        input_tensor = self.preprocess(image)
        depth_raw = self.infer(input_tensor)
        depth_map = self.postprocess(depth_raw, original_size)

        return depth_map
```

---

### `src/core/point_cloud.py`
```python
import logging
from typing import Tuple, Optional
import numpy as np
import open3d as o3d

logger = logging.getLogger(__name__)

class PointCloudGenerator:
    """Generate 3D point cloud from depth map and original image."""

    def __init__(
        self,
        scale_factor: float = 1.0,
        remove_outliers: bool = True,
        nb_neighbors: int = 20,
        std_ratio: float = 2.0
    ):
        """
        Initialize point cloud generator.

        Args:
            scale_factor: Scale factor for depth values (adjust for better mesh)
            remove_outliers: Apply statistical outlier removal
            nb_neighbors: Number of neighbors for outlier detection
            std_ratio: Standard deviation threshold for outlier detection
        """
        self.scale_factor = scale_factor
        self.remove_outliers = remove_outliers
        self.nb_neighbors = nb_neighbors
        self.std_ratio = std_ratio

    def generate(
        self,
        image: np.ndarray,
        depth_map: np.ndarray,
        fx: float = 1.0,
        fy: float = 1.0,
        cx: Optional[float] = None,
        cy: Optional[float] = None
    ) -> o3d.geometry.PointCloud:
        """
        Generate point cloud from image and depth map.

        Uses pinhole camera model: X = (u - cx) * depth / fx, Y = (v - cy) * depth / fy, Z = depth

        Args:
            image: Original RGB image (HxWx3)
            depth_map: Depth map (HxW) normalized [0,1] or absolute
            fx, fy: Focal lengths (default 1.0 for arbitrary scale)
            cx, cy: Principal point (defaults to image center)

        Returns:
            Open3D PointCloud object with points and colors
        """
        h, w = depth_map.shape
        if cx is None:
            cx = w / 2.0
        if cy is None:
            cy = h / 2.0

        # Create grid of pixel coordinates
        u, v = np.meshgrid(np.arange(w), np.arange(h))
        u = u.astype(np.float32)
        v = v.astype(np.float32)

        # Apply scale factor to depth
        depth_scaled = depth_map * self.scale_factor

        # Back-project to 3D
        x = (u - cx) * depth_scaled / fx
        y = (v - cy) * depth_scaled / fy
        z = depth_scaled

        # Stack into (N, 3) array
        points = np.stack([x, y, z], axis=-1).reshape(-1, 3)

        # Get colors from original image (RGB, 0-255)
        colors = image.reshape(-1, 3) / 255.0

        # Create Open3D point cloud
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        pcd.colors = o3d.utility.Vector3dVector(colors)

        # Optional outlier removal
        if self.remove_outliers:
            pcd, ind = pcd.remove_statistical_outlier(
                nb_neighbors=self.nb_neighbors,
                std_ratio=self.std_ratio
            )
            logger.info(f"Removed {len(points) - len(ind)} outlier points")

        logger.info(f"Generated point cloud with {len(pcd.points)} points")
        return pcd
```

---

### `src/core/mesh_builder.py`
```python
import logging
from typing import Tuple, Optional
import open3d as o3d
import numpy as np

logger = logging.getLogger(__name__)

class MeshBuilder:
    """Build watertight mesh from point cloud."""

    def __init__(
        self,
        poisson_depth: int = 8,
        poisson_scale: float = 1.1,
        poisson_linear_fit: bool = False,
        simplify_ratio: float = 0.5,
        remove_degenerate: bool = True,
        fill_holes: bool = True,
        min_hole_size: int = 100
    ):
        """
        Initialize mesh builder.

        Args:
            poisson_depth: Depth of Poisson reconstruction (higher = more detail)
            poisson_scale: Scale factor for Poisson reconstruction
            poisson_linear_fit: Use linear fit for Poisson (faster)
            simplify_ratio: Target triangle count ratio after simplification (0-1)
            remove_degenerate: Remove degenerate triangles/vertices
            fill_holes: Fill small holes in mesh
            min_hole_size: Minimum hole area (in pixels) to fill
        """
        self.poisson_depth = poisson_depth
        self.poisson_scale = poisson_scale
        self.poisson_linear_fit = poisson_linear_fit
        self.simplify_ratio = simplify_ratio
        self.remove_degenerate = remove_degenerate
        self.fill_holes = fill_holes
        self.min_hole_size = min_hole_size

    def build(
        self,
        point_cloud: o3d.geometry.PointCloud,
        quality: str = "medium"
    ) -> o3d.geometry.TriangleMesh:
        """
        Build mesh from point cloud.

        Args:
            point_cloud: Input point cloud
            quality: Quality preset (fast/medium/high) - adjusts parameters

        Returns:
            TriangleMesh
        """
        # Adjust parameters based on quality
        if quality == "fast":
            depth = 6
            simplify = 0.3
        elif quality == "high":
            depth = 10
            simplify = 0.7
        else:  # medium
            depth = self.poisson_depth
            simplify = self.simplify_ratio

        # Estimate normals (required for Poisson)
        logger.info("Estimating point cloud normals...")
        point_cloud.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=0.1 * (point_cloud.get_axis_aligned_bounding_box().get_max_extent()),
                max_nn=30
            )
        )
        point_cloud.orient_normals_consistent_tangent_plane(100)

        # Poisson reconstruction
        logger.info(f"Running Poisson reconstruction (depth={depth})...")
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            point_cloud,
            depth=depth,
            width=0,
            scale=self.poisson_scale,
            linear_fit=self.poisson_linear_fit
        )

        # Crop to bounding box of original point cloud (remove floating artifacts)
        bbox = point_cloud.get_axis_aligned_bounding_box()
        mesh = mesh.crop(bbox)

        # Remove low-density vertices (optional)
        if densities is not None:
            vertices_to_keep = densities > np.quantile(densities, 0.1)
            mesh = mesh.select_by_index(np.where(vertices_to_keep)[0])

        # Mesh cleaning
        if self.remove_degenerate:
            logger.info("Cleaning mesh...")
            mesh.remove_degenerate_triangles()
            mesh.remove_duplicated_vertices()
            mesh.remove_duplicated_triangles()
            mesh.remove_non_manifold_edges()

        # Mesh simplification
        target_triangles = int(len(mesh.triangles) * simplify)
        if target_triangles < len(mesh.triangles):
            logger.info(f"Simplifying mesh to ~{target_triangles} triangles...")
            mesh = mesh.simplify_quadric_decimation(target_number_of_triangles=target_triangles)

        # Fill holes
        if self.fill_holes:
            logger.info("Filling holes...")
            mesh = mesh.fill_holes(self.min_hole_size)

        # Compute vertex normals for shading
        mesh.compute_vertex_normals()

        logger.info(f"Final mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")
        return mesh
```

---

### `src/core/exporter.py`
```python
import logging
from pathlib import Path
from typing import Optional
import open3d as o3d
import numpy as np

logger = logging.getLogger(__name__)

class Exporter:
    """Export mesh to various formats."""

    @staticmethod
    def export(
        mesh: o3d.geometry.TriangleMesh,
        output_path: str | Path,
        texture_image: Optional[np.ndarray] = None,
        uv_coords: Optional[np.ndarray] = None
    ):
        """
        Export mesh to file.

        Args:
            mesh: Open3D TriangleMesh
            output_path: Output file path (extension determines format)
            texture_image: Optional texture image (HxWx3 uint8)
            uv_coords: Optional UV coordinates per triangle (Nx3x2)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        suffix = output_path.suffix.lower()

        # If texture and UVs provided, attach to mesh
        if texture_image is not None and uv_coords is not None:
            # Open3D expects texture as Image and triangle_uvs as list
            mesh.texture = o3d.geometry.Image(texture_image)
            mesh.triangle_uvs = uv_coords

        try:
            if suffix == ".obj":
                # OBJ exporter writes MTL if texture is present
                o3d.io.write_triangle_mesh(
                    str(output_path),
                    mesh,
                    write_vertex_colors=True,
                    write_vertex_normals=True,
                    write_vertex_texcoords=True
                )
                # If texture exists, also write the texture image
                if texture_image is not None:
                    tex_path = output_path.with_suffix(".png")
                    cv2.imwrite(str(tex_path), cv2.cvtColor(texture_image, cv2.COLOR_RGB2BGR))
            elif suffix in [".gltf", ".glb"]:
                o3d.io.write_triangle_mesh(
                    str(output_path),
                    mesh,
                    write_vertex_colors=True,
                    write_vertex_normals=True,
                    write_vertex_texcoords=True
                )
            elif suffix == ".stl":
                o3d.io.write_triangle_mesh(str(output_path), mesh)
            else:
                raise ValueError(f"Unsupported format: {suffix}")

            logger.info(f"Exported mesh to {output_path}")

        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise
```

---

### `src/core/depth_estimator.py` (already shown above)

---

### `src/core/point_cloud.py` (already shown above)

---

### `src/core/mesh_builder.py` (already shown above)

---

### `src/core/exporter.py` (already shown above)

---

## 3. Database models

### `src/db/models.py`
```python
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class JobStatus(enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    theme = Column(String, default="light")

    histories = relationship("History", back_populates="user")
    settings = relationship("Setting", back_populates="user", uselist=False)
    api_tokens = relationship("APIToken", back_populates="user")

class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    input_path = Column(Text, nullable=False)
    output_path = Column(Text, nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.queued)
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="histories")

class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    default_output_dir = Column(Text, nullable=True)
    default_quality = Column(String, default="medium")
    last_used_format = Column(String, default="glb")

    user = relationship("User", back_populates="settings")

class APIToken(Base):
    __tablename__ = "api_tokens"

    token = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="api_tokens")
```

---

### `src/db/database.py`
```python
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pathlib import Path
from .models import Base

logger = logging.getLogger(__name__)

class Database:
    """Simple database wrapper."""

    def __init__(self, url: str = "sqlite:///depth2mesh.db"):
        self.engine = create_engine(url, echo=False, future=True)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False
        )

    def init_db(self):
        """Create all tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database initialized")

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

# Global instance
db = Database()
```

---

## 4. CLI and GUI entry points

### `src/cli.py`
```python
#!/usr/bin/env python3
"""
Command-line interface for Depth2Mesh.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from depth2mesh.core import DepthEstimator, PointCloudGenerator, MeshBuilder, Exporter, load_image, ensure_dir
from depth2mesh.db.database import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert 2D image to 3D mesh using CPU-only depth estimation."
    )
    parser.add_argument(
        "input",
        type=str,
        help="Input image file path (JPG, PNG, WEBP)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path (default: same as input with .glb extension)"
    )
    parser.add_argument(
        "-q", "--quality",
        type=str,
        choices=["fast", "medium", "high"],
        default="medium",
        help="Conversion quality preset"
    )
    parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["obj", "glb", "stl"],
        default="glb",
        help="Output format"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="models/depth_anything_v2.onnx",
        help="Path to ONNX model file"
    )
    parser.add_argument(
        "--no-quantize",
        action="store_true",
        help="Disable INT8 quantization (slower but higher quality)"
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Depth scale factor (adjust for better mesh)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()

def main():
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(f".{args.format}")

    ensure_dir(output_path.parent)

    # Initialize database (for history tracking, optional)
    try:
        db.init_db()
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")

    logger.info(f"Processing {input_path} -> {output_path}")
    logger.info(f"Quality: {args.quality}, Format: {args.format}")

    try:
        # 1. Load image
        logger.info("Loading image...")
        image, w, h = load_image(input_path, max_size=1920)

        # 2. Depth estimation
        logger.info("Estimating depth...")
        estimator = DepthEstimator(
            model_path=args.model,
            quantize=not args.no_quantize
        )
        depth_map = estimator.get_depth(image, original_size=(w, h))

        # 3. Point cloud
        logger.info("Generating point cloud...")
        generator = PointCloudGenerator(scale_factor=args.scale)
        pcd = generator.generate(image, depth_map)

        # 4. Mesh building
        logger.info("Building mesh...")
        builder = MeshBuilder()
        mesh = builder.build(pcd, quality=args.quality)

        # 5. Export
        logger.info("Exporting mesh...")
        Exporter.export(mesh, output_path)

        logger.info("Conversion completed successfully!")
        print(f"✓ Output saved to: {output_path}")

    except Exception as e:
        logger.exception("Conversion failed")
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

### `src/gui.py`
```python
#!/usr/bin/env python3
"""
Desktop GUI for Depth2Mesh using PyQt6.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QFileDialog, QMessageBox,
    QComboBox, QSpinBox, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage, QAction, QIcon

from depth2mesh.core import DepthEstimator, PointCloudGenerator, MeshBuilder, Exporter, load_image, ensure_dir
from depth2mesh.db.database import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class ConversionWorker(QThread):
    """Worker thread for running conversion pipeline."""

    progress = pyqtSignal(int, str)  # percentage, message
    finished = pyqtSignal(bool, str, Path)  # success, error_msg, output_path
    log = pyqtSignal(str)  # log message

    def __init__(
        self,
        input_path: Path,
        output_path: Path,
        quality: str = "medium",
        format: str = "glb",
        model_path: Path = Path("models/depth_anything_v2.onnx"),
        scale: float = 1.0,
        quantize: bool = True
    ):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.quality = quality
        self.format = format
        self.model_path = model_path
        self.scale = scale
        self.quantize = quantize
        self._is_running = True

    def run(self):
        try:
            self.progress.emit(0, "Loading image...")
            image, w, h = load_image(self.input_path, max_size=1920)

            self.progress.emit(20, "Estimating depth...")
            self.log.emit("Initializing depth estimator...")
            estimator = DepthEstimator(
                model_path=self.model_path,
                quantize=self.quantize
            )
            depth_map = estimator.get_depth(image, original_size=(w, h))

            self.progress.emit(40, "Generating point cloud...")
            self.log.emit(f"Point cloud scale: {self.scale}")
            generator = PointCloudGenerator(scale_factor=self.scale)
            pcd = generator.generate(image, depth_map)

            self.progress.emit(60, "Building mesh...")
            builder = MeshBuilder()
            mesh = builder.build(pcd, quality=self.quality)

            self.progress.emit(80, "Exporting mesh...")
            output_file = self.output_path.with_suffix(f".{self.format}")
            Exporter.export(mesh, output_file)

            self.progress.emit(100, "Done!")
            self.finished.emit(True, "", output_file)

        except Exception as e:
            logger.exception("Conversion failed in worker")
            self.finished.emit(False, str(e), Path())

    def stop(self):
        self._is_running = False
        self.terminate()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Depth2Mesh")
        self.setMinimumSize(1000, 700)

        # State
        self.input_path: Optional[Path] = None
        self.worker: Optional[ConversionWorker] = None

        self.init_ui()
        self.setup_menu()

        # Initialize DB
        try:
            db.init_db()
        except Exception as e:
            logger.warning(f"DB init failed: {e}")

    def setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        open_action = QAction("Open Image...", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        export_action = QAction("Export...", self)
        export_action.triggered.connect(self.export_file)
        file_menu.addAction(export_action)

        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.add