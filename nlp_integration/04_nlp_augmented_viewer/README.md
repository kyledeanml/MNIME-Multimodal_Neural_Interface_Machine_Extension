# 04 - NLP-Augmented Document Viewer

## Goal
Deeply integrate the NLP engine directly into the document reading experience (`ui/reader_dialog.py` or similar), moving away from a separate, isolated NLP view.

## Key Features
1. **Context Menu Actions**: Allow users to highlight text directly in the Document Viewer and right-click to trigger immediate NLP actions:
   - *Summarize this selection*
   - *Explain this concept*
   - *Extract key data points*
2. **Semantic Highlighting**: Allow the user to ask the NLP a question (e.g., "Where are the termination clauses?"), and have the engine return bounding boxes to visually highlight the relevant paragraphs in the PDF viewer.

## Implementation Considerations
- Add a custom context menu to the PyMuPDF/QPainter text selection logic in the viewer component.
- NLP responses should render in a non-intrusive floating widget or a collapsible side-pane within the reader, maintaining reading context.
- Semantic highlighting requires mapping NLP text responses back to precise PyMuPDF bounding boxes (`fitz.Rect`) for drawing visual highlights on the rendered page canvas.
