# 01 - Intelligent Merging & Synthesis

## Goal
Inject the `MNIME-Core V5` NLP engine into the PDF merging pipeline to provide semantic synthesis alongside raw binary merging.

## Key Features
1. **Auto-Generated Cover Pages**: When merging multiple documents, the NLP engine ingests the first few pages of each source file to automatically generate an "Executive Summary" cover page for the merged output.
2. **Semantic Table of Contents**: Generate a descriptive table of contents based on the core topics of the merged documents, rather than just using raw filenames.
3. **Smart File Naming**: When saving a merged output, use the NLP engine to read the combined document and suggest a highly descriptive, context-aware filename (e.g., `Q3_Financial_Reports_and_Invoices.pdf` instead of `merged_output.pdf`).

## Implementation Considerations
- Must hook into `core/pdf_engine.py` and the main UI merging logic.
- The NLP processing must run in an isolated `QThread` to prevent blocking the main PyQt6 GUI during heavy summarization.
- Requires a robust text-chunking strategy (e.g., LangChain-style recursive splitters) to extract text from the source PDFs and fit it within the model's context window.
