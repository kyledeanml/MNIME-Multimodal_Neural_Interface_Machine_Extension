<p align="center">
  <img src="MNIME_banner.gif?v=2" alt="MNIME Banner" width="350">
</p>

<p align="center"><strong>MULTIMODAL NEURAL INTERFACE MACHINE EXTENSION</strong></p>
<p align="center"><em><font face="Brush Script MT, Segoe Script, cursive" color="#00e5ff" size="4">nigh.mh</font></em></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-00e5ff.svg?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-00e5ff.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Windows%2011%20%7C%2010-00e5ff.svg?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/UI-PyQt6-00e5ff.svg?style=flat-square" alt="UI Framework">
  <img src="https://img.shields.io/badge/Model-MNIME--Core--1.5B--Q4__K__M-00e5ff.svg?style=flat-square" alt="Model">
</p>

A modern, private, ultra-fast desktop interface with a fine-tuned local NLP engine built in. Engineered with Python and PyQt6, MNIME runs 100% locally and offline on your machine with zero cloud dependencies or data uploads, delivering conversation and document intelligence directly over your files.

---

## Specification Sheet & User Manual

<p align="center">
  <a href="MNIME_Spec_Manual.pdf">
    <img src="docs/spec_cover.png?v=3" alt="MNIME Specification Sheet & User Manual" width="480">
  </a>
</p>

<p align="center">
  <a href="MNIME_Spec_Manual.pdf">
    <img src="https://img.shields.io/badge/View%20Full%20Spec%20%26%20Manual-PDF-00e5ff?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="View Spec Sheet PDF">
  </a>
</p>

> **Specification Sheet & User Manual** — 14 sections covering all features, technical specs, architecture, NLP engine details, UI guide, installation, keyboard shortcuts, performance notes, dependency stack, error handling, and changelog.

---

## Key Features

### 1. Document & File Processing Suite
- **Combine PDF**: Select up to 5,000 PDF and image files, drag and drop to reorder, and merge sequentially into a unified document.
- **Edit Suite (Images & PDFs)**: Visually crop and rotate images and all pages within PDF documents seamlessly in-app.
- **JPG to PDF**: Convert image formats (`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`) into crisp, vector-scaled PDFs.
- **TXT to PDF**: Rapidly render raw text documents into formatted, searchable PDF files.
- **PDF to JPG**: Extract all pages from a PDF document into high-resolution JPG images.
- **Split PDF**: Separate multi-page PDFs with NLP-powered Smart Naming that analyzes page content to generate unique filenames.
- **Compress PDF**: Optimize and reduce PDF file size by compressing content streams and duplicate objects.
- **PDF to DOCX**: Reconstruct PDF layouts into fully editable Word documents.
- **Semantic Bookmarks**: Intelligently analyze PDF typography and leverage the bundled NLP engine to generate context-aware chapter summaries.

### 2. Local Intelligence & RAG Engine
- **Local NLP Engine**: Query across all open documents locally using the fine-tuned `MNIME-Core-1.5B-Q4_K_M.gguf` model with zero network traffic.
- **LoRA Adapter Loading**: Load an optional LoRA adapter (`.gguf`) on top of the base model from the **LORA** button in the NLP view (right-click to remove). The model reloads in the background.
- **Semantic Search (RAG)**: Fast vector search powered by FAISS embeddings (`bge-small-en-v1.5`).
- **Persistent Global Vector Store**: Every indexed document is also saved to a global FAISS store in `%LOCALAPPDATA%\MNIME\global_vector_store`. Chat queries pull relevant passages from it, so documents from earlier sessions can inform answers.
- **System Resource Purger**: On exit, unloads the LLM (freeing VRAM), releases the vector store from memory, and removes leftover `*.tmp` / `*.tmp.pdf` files.
- **Document Cross-Referencing**: Highlight sections in a document to synthesize an automated comparative brief against other open files.
- **Translucent Pop-Out Console**: Double-click the NLP console to spawn a magnetic, translucent floating chat window synchronized with the primary window.

### 3. Visual & Aesthetic Architecture
- **Free-Floating Dark Metallic Interface**: Frameless obsidian and brushed gunmetal theme built with native PyQt6 styling.
- **5D Penteract Visual Branding**: Procedurally rendered 5D Penteract projection with true depth-sorting and an independently orbiting 3D element.
- **Interactive Gallery Carousel**: Horizontal file card slider featuring drag-and-drop reordering, status overlays, and thumbnail pre-rendering.
- **Custom File Explorer**: Fully integrated PyQt6 file dialog replacing generic OS file pickers to maintain dark metallic UI consistency.
- **Cinematic Transitions & VFX**: Real-time particle physics simulation during background operations with smooth screen-flash transitions.

### 4. Engine & Performance Optimizations
- **C-Accelerated PyMuPDF Core**: Native C-level document operations executing up to 50x faster than pure-Python libraries.
- **O(1) Carousel Indexing**: Surgical layout reordering without tearing down or recreating UI widgets.
- **Dynamic Memory Management**: Unloads LLM weights and vector indices from RAM/VRAM when NLP mode is toggled off or on exit.
- **Non-Blocking Multithreading**: Smooth 60 FPS UI performance backed by dedicated `QThread` workers and progress tracking.
- **In-Memory Pixmap Caching**: SVG vector icons and card thumbnails are rasterized and pre-scaled once to eliminate CPU resampling overhead.

---

## Fine-Tuned NLP Model — MNIME-Core

`MNIME-Core-1.5B-Q4_K_M.gguf` is a fine-tuned version of `Qwen2.5-1.5B-Instruct`, quantized to Q4_K_M, specialized for high-density document synthesis, extraction, and cross-referencing.

- **V3 Massive Training Dataset**: We have released `training/mnime_v3_dataset_clean.jsonl` (4.7k high-quality, filtered document Q&A and extraction pairs) for training V3 architectures. This dataset merges Databricks Dolly 15k subsets with identity-preserving weights, strictly filtered for AI refusals.
- **Model Download**: Download the model from [KyleDeanAI/MNIME-Core-1.5B-Q4_K_M](https://huggingface.co/KyleDeanAI/MNIME-Core-1.5B-Q4_K_M) and place it inside the `models/` directory.
- **Hardware Acceleration**: Automatically offloads layers to available GPU VRAM (NVIDIA CUDA / Vulkan / Metal) via `llama-cpp-python`.

---

## Setup & Installation

### Option A — One-Click Automated Local Installer (Recommended)

Run `install_mnime.bat` directly from the repository root:

```cmd
install_mnime.bat
```

**How it works:**
1. **Automated Stale-Build Check**: Compares source file timestamps (`core/` and `ui/`) against existing compiled binaries.
2. **Auto-Compilation**: Automatically invokes `build_app.bat` to compile PyInstaller binaries and the custom PyQt6 installer if source files have updated or binaries are missing.
3. **Application Deployment**: Copies application files to `%LOCALAPPDATA%\Programs\MNIME`.
4. **Windows System Integration**: Creates Desktop and Start Menu shortcuts (`MNIME.lnk`), configures PDF document file associations, and registers an entry in Windows Add/Remove Programs with a clean uninstaller (`uninstall.bat`).

*(Note: Pre-compiled binary executables are git-ignored and built locally on your machine via `install_mnime.bat` or `build_app.bat`.)*

### Option B — Run from Source

**1. Clone & Place Model**
Download `MNIME-Core-1.5B-Q4_K_M.gguf` from [Hugging Face](https://huggingface.co/KyleDeanAI/MNIME-Core-1.5B-Q4_K_M) into the `models/` folder:
```cmd
models/MNIME-Core-1.5B-Q4_K_M.gguf
```

**2. Virtual Environment Setup**
Run `setup.bat` to initialize the Python virtual environment and install all dependencies:
```cmd
setup.bat
```

**3. Launch Application**
Execute `run.bat` or run directly via Python:
```cmd
run.bat
```
Or manually:
```cmd
.venv\Scripts\python.exe MNIME.py
```

**4. Run Tests**
To run the automated test suite:
```cmd
run_tests.bat
```

---

## Building the Application

Run `build_app.bat` (requires PyInstaller):

```cmd
build_app.bat
```

**Build Workflow:**
1. Validates `.venv` environment and installs build packages.
2. Compiles `MNIME.py` into a standalone binary payload (`dist/MNIME/`) via `MNIME.spec`.
3. Compiles custom installer `installer/MNIME_installer.exe` via `MNIME_installer.spec` and `custom_installer.py`.

---

## Project Architecture

```
MNIME/
├── core/                  # Core processing engine
│   ├── __init__.py
│   ├── app_icon.py        # Win32 icons & window properties
│   ├── file_item.py       # Data model & thumbnail caching
│   ├── ipc.py             # Single-instance IPC mechanism
│   ├── logging_setup.py   # Application logging setup
│   ├── nlp_engine.py      # GGUF model integration via llama-cpp
│   ├── pdf_engine.py      # PyMuPDF engine, DOCX & image conversion
│   ├── print_engine.py    # High-DPI printing & rendering
│   ├── search_engine.py   # FAISS vector indexing & RAG retrieval
│   ├── text_safety.py     # Prompt parsing & text sanitization
│   ├── version.py         # Application version constants
│   ├── windows_integration.py # Windows taskbar & OS integrations
│   └── worker.py          # Asynchronous QThread background worker
├── models/                # Local GGUF model directory
│   └── MNIME-Core-1.5B-Q4_K_M.gguf
├── ui/                    # Desktop GUI components (PyQt6)
│   ├── __init__.py
│   ├── action_bar.py      # Action buttons & task progress bar
│   ├── carousel_view.py   # Horizontal file gallery slider
│   ├── cursor_fx.py       # Custom particle cursor effects
│   ├── document_viewer.py # Canvas renderer for documents
│   ├── file_card.py       # Interactive card widget for queued files
│   ├── file_dialog.py     # Dark metallic custom file browser
│   ├── icons.py           # Vector SVG icon manager
│   ├── image_editor.py    # Image visual editing interface
│   ├── main_window.py     # Primary application window coordinator
│   ├── merge_particles.py # Physics-based vortex & particle VFX
│   ├── minimize_animation.py # Window minimize animations
│   ├── nlp_view.py        # Local RAG & NLP chat console
│   ├── output_view.py     # Real-time execution log console
│   ├── pdf_editor.py      # Visual PDF page editor suite
│   ├── reader_dialog.py   # Independent frameless document reader
│   ├── nerds.py           # Real-time telemetry & performance HUD
│   └── tabs_bar.py        # Application navigation bar
├── docs/                  # Media & cover artwork assets
│   ├── changelog_cover.png# Interactive change log preview cover
│   ├── paper_cover.png    # Research paper preview cover
│   └── spec_cover.png     # Specification sheet preview cover
├── paper/                 # Research paper LaTeX source & PDF
│   ├── MNIME_paper.pdf    # Compiled research paper
│   ├── MNIME_paper.tex    # LaTeX manuscript source
│   ├── acl.sty            # ACL formatting style sheet
│   ├── acl_natbib.bst     # ACL bibliography style sheet
│   ├── mnime_refs.bib     # Citation database
│   └── template_ref.tex   # Reference template
├── scripts/               # Utility & PDF generation scripts
│   ├── fetch_models.py           # Automated model downloader
│   ├── generate_changelog_pdf.py # Dynamic Change Log PDF & cover generator
│   └── generate_mnime_pdf.py     # Specification manual PDF generator
├── tests/                 # Automated test suite
│   ├── test_ipc_parse.py
│   ├── test_nlp_conversational_fallback.py
│   ├── test_nlp_indexing.py
│   ├── test_nlp_sanitize.py
│   ├── test_pdf_engine.py
│   ├── test_print_engine.py
│   ├── test_stats_telemetry.py
│   └── test_windows_integration.py
├── CHANGE_LOG.txt         # Comprehensive forensic build & session change log
├── MNIME_Change_Log.pdf   # Interactive compiled change log & build history
├── MNIME_paper.pdf        # Research paper PDF
├── MNIME_Spec_Manual.pdf  # Specification & user manual PDF
├── MN.ico                 # Multi-resolution application icon
├── MNIME.py               # Application entry point
├── custom_installer.py    # Standalone PyQt6 installer UI
├── MNIME.spec             # Main application PyInstaller spec
├── MNIME_installer.spec   # Custom installer PyInstaller spec
├── benchmark.py           # Standalone empirical NLP benchmarking tool
├── build_app.bat          # Master compilation & packaging script
├── install_mnime.bat      # One-click local installer script
├── run.bat                # Launch application script
├── run_tests.bat          # Test runner script
├── setup.bat              # Virtual environment initialization script
├── update_changelog.bat   # Script to update changelog
├── pyproject.toml         # Build system configuration
├── requirements.txt       # Python dependency specifications
├── version_info.txt       # Version build details
├── LICENSE                # MIT Open Source License
└── README.md              # Project documentation
```

---

## Empirical Benchmarking & Telemetry HUD

MNIME includes a telemetry dashboard and benchmarking suite (`ui/nerds.py` & `benchmark.py`) for analyzing on-device model performance and document processing throughput:

- **Translucent HUD**: Accessible via the `STATS` tab or directly via `.venv\Scripts\python.exe benchmark.py`.
- **60 FPS Real-Time Vector Charts**: Live rendering of token throughput (tokens/sec), inter-token latency (ms), and memory allocation (RAM working set in MB).
- **Multi-Metric Telemetry**: Benchmarks prompt prefill processing, time-to-first-token (TTFT), sustained text generation, PyMuPDF page rasterization rate, and FAISS retrieval latency.
- **Benchmark Replication**: Ground empirical metrics locally with exportable JSON benchmark records.

---

## Research Paper

<p align="center">
  <a href="MNIME_paper.pdf">
    <img src="docs/paper_cover.png?v=4" alt="MNIME Research Paper" width="480">
  </a>
</p>

<p align="center">
  <a href="MNIME_paper.pdf">
    <img src="https://img.shields.io/badge/Read%20the%20Research%20Paper-PDF-00e5ff?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="Read Research Paper PDF">
  </a>
</p>

> **MNIME Research Paper** — Details the system architecture, model fine-tuning methodology, RAG search engine implementation, empirical performance benchmarks, and privacy-first design principles.

---

## Build Process & Change Log

<p align="center">
  <a href="MNIME_Change_Log.pdf">
    <img src="docs/changelog_cover.png?v=1" alt="MNIME Build Process & Change Log" width="480">
  </a>
</p>

<p align="center">
  <a href="MNIME_Change_Log.pdf">
    <img src="https://img.shields.io/badge/View%20Full%20Change%20Log-PDF-00e5ff?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="View Change Log PDF">
  </a>
</p>

> **MNIME Build Process & Change Log** — Interactive document outlining the complete engineering lifecycle from initial repository genesis through 5D vector mathematics, local neural engine integration, dual-installer packaging, and 22 forensic IDE conversation sessions.

---

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for complete licensing terms.

---

*Special thanks to the Antigravity team at Google*
