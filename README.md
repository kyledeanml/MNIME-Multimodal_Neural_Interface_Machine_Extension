<p align="center">
  <img src="MNIME_banner.gif?v=2" alt="MNIME Banner" width="350">
</p>

<p align="center"><strong>MULTIMODAL NEURAL INTERFACE MACHINE EXTENSION</strong></p>
<p align="center"><em><font face="Brush Script MT, Segoe Script, cursive" color="#00e5ff" size="4">nigh.me</font></em></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-00e5ff.svg?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-00e5ff.svg?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Windows%2011%20%7C%2010-00e5ff.svg?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/UI-PyQt6-00e5ff.svg?style=flat-square" alt="UI Framework">
  <img src="https://img.shields.io/badge/Model-MNIME--Core--V5--Q4__K__M-00e5ff.svg?style=flat-square" alt="Model">
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
  &nbsp;
  <a href="https://raw.githubusercontent.com/kyledeanml/MNIME-Multimodal_Neural_Interface_Machine_Extension/main/MNIME_Spec_Manual.pdf">
    <img src="https://img.shields.io/badge/Direct%20Download-PDF-ff3366?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="Direct PDF Download">
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
- **Local NLP Engine**: Query across all open documents locally using the fine-tuned `MNIME-Core-V5-Q4_K_M.gguf` model with zero network traffic.
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

### 4. Engine & Performance Optimizations (Memory Diet)
- **C-Accelerated PyMuPDF Core**: Native C-level document operations executing up to 50x faster than pure-Python libraries.
- **O(1) Carousel Indexing**: Surgical layout reordering without tearing down or recreating UI widgets.
- **Dynamic Memory Management**: Unloads LLM weights and vector indices from RAM/VRAM when NLP mode is toggled off or on exit.
- **Non-Blocking Multithreading**: Smooth 60 FPS UI performance backed by dedicated `QThread` workers and progress tracking.
- **In-Memory Pixmap Caching**: SVG vector icons and card thumbnails are rasterized and pre-scaled once to eliminate CPU resampling overhead.
- **EcoQoS & Working Set Trimming**: Actively purges the working set memory when minimized. Recent empirical telemetry during minimized idle operation demonstrated a working set of 136.0 MB (62.4 MB private) with a peak of 174.3 MB, operating on 2 threads and 1,183 handles, while consuming negligible CPU (0.001% or 0.02s over a 60-second window).
- **Zero-Dependency Vector Engine**: RAG semantic search operates solely on `llama-cpp-python` and `faiss`, entirely removing heavy ML wrappers (Torch, LangChain, SentenceTransformers).

---

## Fine-Tuned NLP Model — MNIME-Core

`MNIME-Core-V5-Q4_K_M.gguf` is an advanced multi-stage aligned model derived from `Qwen2.5-1.5B-Instruct`, specialized for high-density document synthesis, cross-referencing, philosophical reasoning, and empathetic anti-bias dialogue.

### Multi-Stage Alignment Evolution
MNIME-Core represents the culmination of a three-stage progressive alignment pipeline combining local LoRA adaptation, high-compute cloud fine-tuning, and full-precision tensor assimilation:

- **Stage 1 (V3 Foundational Synthesis & Extraction)**: Trained locally on `training/mnime_v3_dataset_clean.jsonl` (5,482 curated pairs merging Databricks Dolly 15k subsets with identity-preserving weights). Establishes deep document comprehension, closed QA, structured entity extraction, and prompt grounding.
- **Stage 2 (V4 Philosophical Depth & Adversarial Robustness)**: Trained on high-VRAM cloud compute using `training/mnime_v4_philosophy_dataset_clean.jsonl` (15,000 synthetic examples). Embeds ontological reasoning (Stoicism, Existentialism), dialectical resilience, prompt-injection immunity, and hallucination counter-traps.
- **Stage 3 (V5 Ethics, Empathy, & Anti-Bias Alignment)**: Synthesized and aligned using `training/mnime_v5_antibias_dataset_clean.jsonl` (20,000 examples). Rather than issuing evasive, canned refusal templates, MNIME-Core actively and objectively deconstructs hate tropes and demographic stereotypes using sociological evidence, empirical logic, and empathetic dialectics.
- **Model Distribution & Formats**: Available in multiple precision targets, including full fp16 HuggingFace checkpoints, high-fidelity `MNIME-Core-V5-Q8_0.gguf` (1.64 GB), and production-optimized `MNIME-Core-V5-Q4_K_M.gguf` (~1.0 GB) for ultra-fast local inference.
- **Hardware Acceleration**: Automatically offloads computation layers to available GPU VRAM (NVIDIA CUDA / Vulkan / Metal) via `llama-cpp-python`, with graceful CPU fallback.

### The Neural Assimilation Engine (NAE)
MNIME is not a static interface—it is built to evolve dynamically. While MNIME-Core operates as a rigorous logical scribe and analytical assistant, the built-in **Neural Assimilation Engine** (`core/fusion_engine.py`) allows operators to continually fuse external specialized domain capabilities into the application.

Using advanced weight-fusion algorithms (such as TIES-merging and linear task-vector interpolation), the engine isolates high-value parameter deltas from donor models (e.g., medical diagnostics, legal analysis, or specialized coding assistants) and injects them into the base matrix without overwriting core logical foundations or inducing catastrophic forgetting.

**Full-Precision Streaming Architecture:**
The Assimilation Engine merges tensor-by-tensor directly on full-precision (fp16/bf16) HuggingFace `safetensors` model directories (such as `training/v4_out/MNIME-Core-V4-merged`). Operating in full floating-point precision preserves subtle gradient vectors that would otherwise be destroyed by 4-bit quantization. Once fused, the resulting model folder is seamlessly converted via `llama.cpp` to GGUF format (`Q8_0` or `Q4_K_M`) for deployment in MNIME.


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
Download `MNIME-Core-V5-Q4_K_M.gguf` from [Hugging Face](https://huggingface.co/KyleDeanML/MNIME-Core-V5-Q4_K_M) into the `models/` folder:
```cmd
models/MNIME-Core-V5-Q4_K_M.gguf
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

<p align="center">
  <a href="MNIME_Architecture.pdf">
    <img src="docs/architecture_cover.png?v=2" alt="MNIME Project Architecture & Schematics" width="480">
  </a>
</p>

<p align="center">
  <a href="MNIME_Architecture.pdf">
    <img src="https://img.shields.io/badge/View%20Full%20Architecture%20%26%20Schematics-PDF-00e5ff?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="View Architecture PDF">
  </a>
  &nbsp;
  <a href="https://raw.githubusercontent.com/kyledeanml/MNIME-Multimodal_Neural_Interface_Machine_Extension/main/MNIME_Architecture.pdf">
    <img src="https://img.shields.io/badge/Direct%20Download-PDF-ff3366?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="Direct PDF Download">
  </a>
</p>

> **Project Architecture & Subsystem Schematics** — 4-page system architecture manual detailing the 4-layer decoupled topology, 60 FPS non-blocking `QThread` concurrency, the Neural Assimilation Engine (TIES model merging), and dual-tier FAISS vector memory.

<details>
<summary><b>Expand Repository Directory Tree</b></summary>

```yaml
MNIME/
├── core/                   # Core processing engine
│   ├── __init__.py
│   ├── app_icon.py         # Win32 icons & window properties
│   ├── fallback_responses.py # Zero-shot conversational fallback responses
│   ├── file_item.py        # Data model & thumbnail caching
│   ├── fusion_engine.py    # Neural Assimilation Engine (Weight Fusion)
│   ├── ipc.py              # Single-instance IPC mechanism
│   ├── logging_setup.py    # Application logging setup
│   ├── nlp_engine.py       # GGUF model integration via llama-cpp
│   ├── pdf_engine.py       # PyMuPDF engine, DOCX & image conversion
│   ├── print_engine.py     # High-DPI printing & rendering
│   ├── search_engine.py    # FAISS vector indexing & RAG retrieval
│   ├── system_cleaner.py   # Memory cache, VRAM & temp resource purger
│   ├── text_safety.py      # Prompt parsing & text sanitization
│   ├── version.py          # Application version constants
│   ├── windows_integration.py  # Windows taskbar & OS integrations
│   └── worker.py           # Asynchronous QThread background worker
├── models/                 # Local GGUF model directory
│   └── MNIME-Core-V5-Q4_K_M.gguf
├── ui/                     # Desktop GUI components (PyQt6)
│   ├── __init__.py
│   ├── action_bar.py       # Action buttons & task progress bar
│   ├── carousel_view.py    # Horizontal file gallery slider
│   ├── cursor_fx.py        # Custom particle cursor effects
│   ├── document_viewer.py  # Canvas renderer for documents
│   ├── file_card.py        # Interactive card widget for queued files
│   ├── file_dialog.py      # Dark metallic custom file browser
│   ├── icons.py            # Vector SVG icon manager
│   ├── image_editor.py     # Image visual editing interface
│   ├── main_window.py      # Primary application window coordinator
│   ├── merge_particles.py  # Physics-based vortex & particle VFX
│   ├── minimize_animation.py  # Window minimize animations
│   ├── nlp_view.py         # Local RAG & NLP chat console
│   ├── output_view.py      # Real-time execution log console
│   ├── pdf_editor.py       # Visual PDF page editor suite
│   ├── reader_dialog.py    # Independent frameless document reader
│   ├── nerds.py            # Real-time telemetry & performance HUD
│   └── tabs_bar.py         # Application navigation bar
├── docs/                   # Media & cover artwork assets
│   ├── architecture_cover.png # System Architecture preview cover
│   ├── changelog_cover.png # Interactive change log preview cover
│   ├── paper_cover.png     # Research paper preview cover
│   └── spec_cover.png      # Specification sheet preview cover
├── paper/                  # Research paper LaTeX source & PDF
│   ├── MNIME_Whitepaper.pdf     # Compiled research paper
│   ├── MNIME_Whitepaper.tex     # LaTeX manuscript source
│   ├── acl.sty             # ACL formatting style sheet
│   ├── acl_natbib.bst      # ACL bibliography style sheet
│   ├── mnime_refs.bib      # Citation database
│   └── template_ref.tex    # Reference template
├── scripts/                # Utility & PDF generation scripts
│   ├── fetch_models.py            # Automated model downloader
│   ├── generate_architecture_pdf.py # Dynamic Architecture PDF generator
│   ├── generate_changelog_pdf.py  # Dynamic Change Log PDF & cover generator
│   └── generate_mnime_pdf.py      # Specification manual PDF generator
├── tests/                  # Automated test suite
│   ├── test_fusion_engine.py
│   ├── test_ipc_parse.py
│   ├── test_nlp_conversational_fallback.py
│   ├── test_nlp_indexing.py
│   ├── test_nlp_sanitize.py
│   ├── test_pdf_engine.py
│   ├── test_print_engine.py
│   ├── test_stats_telemetry.py
│   └── test_windows_integration.py
├── training/               # Neural fine-tuning, datasets & assimilation
│   ├── clean_v4_dataset.py
│   ├── generate_v4_philosophy_dataset.py
│   ├── generate_v5_antibias_dataset.py
│   ├── merge_v4.py
│   ├── mnime_v3_dataset_clean.jsonl
│   ├── mnime_v4_philosophy_dataset_clean.jsonl
│   ├── mnime_v5_antibias_dataset_clean.jsonl
│   ├── train_mnime.py
│   └── v4_out/             # Merged fp16 HF weights, F16 GGUF & Q8_0 GGUF
├── CHANGE_LOG.txt          # Comprehensive forensic build & session change log
├── MNIME_Architecture.pdf  # Interactive system architecture & schematics
├── MNIME_Change_Log.pdf    # Interactive compiled change log & build history
├── MNIME_Whitepaper.pdf         # Research paper PDF
├── MNIME_Spec_Manual.pdf   # Specification & user manual PDF
├── MN.ico                  # Multi-resolution application icon
├── MNIME.py                # Application entry point
├── custom_installer.py     # Standalone PyQt6 installer UI
├── MNIME.spec              # Main application PyInstaller spec
├── MNIME_installer.spec    # Custom installer PyInstaller spec
├── benchmark.py            # Standalone empirical NLP benchmarking tool
├── build_app.bat           # Master compilation & packaging script
├── install_mnime.bat       # One-click local installer script
├── run.bat                 # Launch application script
├── run_tests.bat           # Test runner script
├── setup.bat               # Virtual environment initialization script
├── update_changelog.bat    # Script to update changelog
├── pyproject.toml          # Build system configuration
├── requirements.txt        # Python dependency specifications
├── version_info.txt        # Version build details
├── LICENSE                 # MIT Open Source License
└── README.md               # Project documentation
```
</details>

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
  <a href="MNIME_Whitepaper.pdf">
    <img src="docs/paper_cover_v5.png?v=2" alt="MNIME Research Paper" width="480">
  </a>
</p>

<p align="center">
  <a href="MNIME_Whitepaper.pdf">
    <img src="https://img.shields.io/badge/View%20in%20GitHub-PDF-00e5ff?style=for-the-badge&logo=github&logoColor=white" alt="View Research Paper on GitHub">
  </a>
  &nbsp;
  <a href="https://raw.githubusercontent.com/kyledeanml/MNIME-Multimodal_Neural_Interface_Machine_Extension/main/MNIME_Whitepaper.pdf">
    <img src="https://img.shields.io/badge/Direct%20Download-PDF-ff3366?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="Direct PDF Download">
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
  &nbsp;
  <a href="https://raw.githubusercontent.com/kyledeanml/MNIME-Multimodal_Neural_Interface_Machine_Extension/main/MNIME_Change_Log.pdf">
    <img src="https://img.shields.io/badge/Direct%20Download-PDF-ff3366?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="Direct PDF Download">
  </a>
</p>

> **MNIME Build Process & Change Log** — The complete engineering lifecycle from initial repository genesis through 5D vector mathematics, local neural engine integration, standalone custom animated PyQt6 installer packaging, and forensic IDE conversation sessions.

---

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for complete licensing terms.

---
*Special thanks to the Antigravity team at Google*
