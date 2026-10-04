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

- **V3 Massive Training Dataset**: We have released `training/mnime_v3_dataset_clean.jsonl` (5,482 high-quality, filtered document Q&A and extraction pairs) for training V3 architectures. This dataset merges Databricks Dolly 15k subsets with identity-preserving weights, strictly filtered for AI refusals.
- **V4 Cloud Philosophy Dataset**: We have also drafted `training/mnime_v4_philosophy_dataset_clean.jsonl` (15,000 synthetic examples) engineered for the forthcoming GCP cloud fine-tuning phase. It integrates advanced philosophical instruction (Stoicism, Existentialism) with rigorous prompt-injection immunity and hallucination traps.
- **V5 Ethics & Empathy Alignment**: To eliminate systemic bigotry and prejudice, we constructed `training/mnime_v5_antibias_dataset_clean.jsonl` (20,000 synthetic examples). This equips MNIME to actively deconstruct hate tropes via sociological rigor and empirical logic rather than relying on generic refusals.
- **Model Download**: Download the model from [KyleDeanAI/MNIME-Core-1.5B-Q4_K_M](https://huggingface.co/KyleDeanAI/MNIME-Core-1.5B-Q4_K_M) and place it inside the `models/` directory.
- **Hardware Acceleration**: Automatically offloads layers to available GPU VRAM (NVIDIA CUDA / Vulkan / Metal) via `llama-cpp-python`.

### The Neural Assimilation Engine
MNIME isn't just a static interface—it's designed to evolve. At its foundation, MNIME-Core acts as a highly disciplined logical scribe and assistant. However, with the built-in **Neural Assimilation Engine**, users have the power to transform MNIME into virtually anything.

By simply dragging and dropping a customized donor model (e.g., a heavily trained medical diagnoser, a master Python coder, or a creative writing engine) into MNIME, the Assimilation Engine runs a background asynchronous fusion process. Using advanced weight-fusion techniques (like TIES-merging), it isolates the high-value parameter deltas of the new model and safely injects them into MNIME's core matrix without overwriting its fundamental logical resilience or causing catastrophic forgetting. You aren't just switching models; you are feeding and growing a singular, ultra-customized brain tailored exactly to your specific workflow.


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

<pre><code>
<font color=&#x27;#00e5ff&#x27;&gt;<b>MNIME/</b></font>
├── <font color=&#x27;#00e5ff&#x27;&gt;<b>core/</b></font>                   <font color='#888888'># Core processing engine</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;__init__.py</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;app_icon.py</font>         <font color='#888888'># Win32 icons & window properties</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;file_item.py</font>        <font color='#888888'># Data model & thumbnail caching</font>
│   ├── <font color=\'#39ff14\'>fusion_engine.py</font>      <font color=\'#888888\'># Neural Assimilation Engine (Weight Fusion)</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;ipc.py</font>              <font color='#888888'># Single-instance IPC mechanism</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;logging_setup.py</font>    <font color='#888888'># Application logging setup</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;nlp_engine.py</font>       <font color='#888888'># GGUF model integration via llama-cpp</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;pdf_engine.py</font>       <font color='#888888'># PyMuPDF engine, DOCX & image conversion</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;print_engine.py</font>     <font color='#888888'># High-DPI printing & rendering</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;search_engine.py</font>    <font color='#888888'># FAISS vector indexing & RAG retrieval</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;text_safety.py</font>      <font color='#888888'># Prompt parsing & text sanitization</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;version.py</font>          <font color='#888888'># Application version constants</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;windows_integration.py</font>  <font color='#888888'># Windows taskbar & OS integrations</font>
│   └── <font color=&#x27;#39ff14&#x27;&gt;worker.py</font>           <font color='#888888'># Asynchronous QThread background worker</font>
├── <font color=&#x27;#00e5ff&#x27;&gt;<b>models/</b></font>                 <font color='#888888'># Local GGUF model directory</font>
│   └── <font color=&#x27;#ffd700&#x27;&gt;MNIME-Core-1.5B-Q4_K_M.gguf</font>
├── <font color=&#x27;#00e5ff&#x27;&gt;<b>ui/</b></font>                     <font color='#888888'># Desktop GUI components (PyQt6)</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;__init__.py</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;action_bar.py</font>       <font color='#888888'># Action buttons & task progress bar</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;carousel_view.py</font>    <font color='#888888'># Horizontal file gallery slider</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;cursor_fx.py</font>        <font color='#888888'># Custom particle cursor effects</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;document_viewer.py</font>  <font color='#888888'># Canvas renderer for documents</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;file_card.py</font>        <font color='#888888'># Interactive card widget for queued files</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;file_dialog.py</font>      <font color='#888888'># Dark metallic custom file browser</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;icons.py</font>            <font color='#888888'># Vector SVG icon manager</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;image_editor.py</font>     <font color='#888888'># Image visual editing interface</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;main_window.py</font>      <font color='#888888'># Primary application window coordinator</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;merge_particles.py</font>  <font color='#888888'># Physics-based vortex & particle VFX</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;minimize_animation.py</font>  <font color='#888888'># Window minimize animations</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;nlp_view.py</font>         <font color='#888888'># Local RAG & NLP chat console</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;output_view.py</font>      <font color='#888888'># Real-time execution log console</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;pdf_editor.py</font>       <font color='#888888'># Visual PDF page editor suite</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;reader_dialog.py</font>    <font color='#888888'># Independent frameless document reader</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;nerds.py</font>            <font color='#888888'># Real-time telemetry & performance HUD</font>
│   └── <font color=&#x27;#39ff14&#x27;&gt;tabs_bar.py</font>         <font color='#888888'># Application navigation bar</font>
├── <font color=&#x27;#00e5ff&#x27;&gt;<b>docs/</b></font>                   <font color='#888888'># Media & cover artwork assets</font>
│   ├── <font color=&#x27;#ff00ff&#x27;&gt;changelog_cover.png</font> <font color='#888888'># Interactive change log preview cover</font>
│   ├── <font color=&#x27;#ff00ff&#x27;&gt;paper_cover.png</font>     <font color='#888888'># Research paper preview cover</font>
│   └── <font color=&#x27;#ff00ff&#x27;&gt;spec_cover.png</font>      <font color='#888888'># Specification sheet preview cover</font>
├── <font color=&#x27;#00e5ff&#x27;&gt;<b>paper/</b></font>                  <font color='#888888'># Research paper LaTeX source & PDF</font>
│   ├── <font color=&#x27;#ff00ff&#x27;&gt;MNIME_paper.pdf</font>     <font color='#888888'># Compiled research paper</font>
│   ├── <font color=&#x27;#ffd700&#x27;&gt;MNIME_paper.tex</font>     <font color='#888888'># LaTeX manuscript source</font>
│   ├── <font color=&#x27;#ffd700&#x27;&gt;acl.sty</font>             <font color='#888888'># ACL formatting style sheet</font>
│   ├── <font color=&#x27;#ffd700&#x27;&gt;acl_natbib.bst</font>      <font color='#888888'># ACL bibliography style sheet</font>
│   ├── <font color=&#x27;#ffd700&#x27;&gt;mnime_refs.bib</font>      <font color='#888888'># Citation database</font>
│   └── <font color=&#x27;#ffd700&#x27;&gt;template_ref.tex</font>    <font color='#888888'># Reference template</font>
├── <font color=&#x27;#00e5ff&#x27;&gt;<b>scripts/</b></font>                <font color='#888888'># Utility & PDF generation scripts</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;fetch_models.py</font>            <font color='#888888'># Automated model downloader</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;generate_changelog_pdf.py</font>  <font color='#888888'># Dynamic Change Log PDF & cover generator</font>
│   └── <font color=&#x27;#39ff14&#x27;&gt;generate_mnime_pdf.py</font>      <font color='#888888'># Specification manual PDF generator</font>
├── <font color=&#x27;#00e5ff&#x27;&gt;<b>tests/</b></font>                  <font color='#888888'># Automated test suite</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;test_ipc_parse.py</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;test_nlp_conversational_fallback.py</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;test_nlp_indexing.py</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;test_nlp_sanitize.py</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;test_pdf_engine.py</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;test_print_engine.py</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;test_stats_telemetry.py</font>
│   └── <font color=&#x27;#39ff14&#x27;&gt;test_windows_integration.py</font>
├── <font color=&#x27;#00e5ff&#x27;&gt;<b>training/</b></font>               <font color='#888888'># Neural fine-tuning & datasets</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;clean_v4_dataset.py</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;generate_v4_philosophy_dataset.py</font>
│   ├── <font color=&#x27;#39ff14&#x27;&gt;generate_v5_antibias_dataset.py</font>
│   ├── <font color=&#x27;#ffd700&#x27;&gt;mnime_v3_dataset_clean.jsonl</font>
│   ├── <font color=&#x27;#ffd700&#x27;&gt;mnime_v4_philosophy_dataset_clean.jsonl</font>
│   ├── <font color=&#x27;#ffd700&#x27;&gt;mnime_v5_antibias_dataset_clean.jsonl</font>
│   └── <font color=&#x27;#39ff14&#x27;&gt;train_mnime.py</font>
├── <font color=&#x27;#ffd700&#x27;&gt;CHANGE_LOG.txt</font>          <font color='#888888'># Comprehensive forensic build & session change log</font>
├── <font color=&#x27;#ff00ff&#x27;&gt;MNIME_Change_Log.pdf</font>    <font color='#888888'># Interactive compiled change log & build history</font>
├── <font color=&#x27;#ff00ff&#x27;&gt;MNIME_paper.pdf</font>         <font color='#888888'># Research paper PDF</font>
├── <font color=&#x27;#ff00ff&#x27;&gt;MNIME_Spec_Manual.pdf</font>   <font color='#888888'># Specification & user manual PDF</font>
├── <font color=&#x27;#ffd700&#x27;&gt;MN.ico</font>                  <font color='#888888'># Multi-resolution application icon</font>
├── <font color=&#x27;#39ff14&#x27;&gt;MNIME.py</font>                <font color='#888888'># Application entry point</font>
├── <font color=&#x27;#39ff14&#x27;&gt;custom_installer.py</font>     <font color='#888888'># Standalone PyQt6 installer UI</font>
├── <font color=&#x27;#ffd700&#x27;&gt;MNIME.spec</font>              <font color='#888888'># Main application PyInstaller spec</font>
├── <font color=&#x27;#ffd700&#x27;&gt;MNIME_installer.spec</font>    <font color='#888888'># Custom installer PyInstaller spec</font>
├── <font color=&#x27;#39ff14&#x27;&gt;benchmark.py</font>            <font color='#888888'># Standalone empirical NLP benchmarking tool</font>
├── <font color=&#x27;#ffd700&#x27;&gt;build_app.bat</font>           <font color='#888888'># Master compilation & packaging script</font>
├── <font color=&#x27;#ffd700&#x27;&gt;install_mnime.bat</font>       <font color='#888888'># One-click local installer script</font>
├── <font color=&#x27;#ffd700&#x27;&gt;run.bat</font>                 <font color='#888888'># Launch application script</font>
├── <font color=&#x27;#ffd700&#x27;&gt;run_tests.bat</font>           <font color='#888888'># Test runner script</font>
├── <font color=&#x27;#ffd700&#x27;&gt;setup.bat</font>               <font color='#888888'># Virtual environment initialization script</font>
├── <font color=&#x27;#ffd700&#x27;&gt;update_changelog.bat</font>    <font color='#888888'># Script to update changelog</font>
├── <font color=&#x27;#ffd700&#x27;&gt;pyproject.toml</font>          <font color='#888888'># Build system configuration</font>
├── <font color=&#x27;#ffd700&#x27;&gt;requirements.txt</font>        <font color='#888888'># Python dependency specifications</font>
├── <font color=&#x27;#ffd700&#x27;&gt;version_info.txt</font>        <font color='#888888'># Version build details</font>
├── LICENSE                 <font color='#888888'># MIT Open Source License</font>
└── <font color=&#x27;#ffd700&#x27;&gt;README.md</font>               <font color='#888888'># Project documentation</font>
</code></pre>


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
