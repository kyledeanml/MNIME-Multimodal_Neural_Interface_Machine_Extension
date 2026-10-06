# 03 - Enhanced "Smart" Bookmarking

## Goal
Upgrade the existing heuristic bookmarking engine (which relies on font sizes, bold flags, and layout positioning) to a semantic level using NLP.

## Key Features
1. **Contextual Section Titles**: If a document lacks explicit headers, the NLP engine can read a block of text and summarize it into a concise 3-4 word bookmark title to build an outline.
2. **Entity Extraction Bookmarks**: Automatically create bookmark hierarchies based on extracted entities (e.g., bookmarking every page where a specific person's name, company, or financial figure is mentioned).

## Implementation Considerations
- Identify blocks of text that likely represent the start of a new section (using the existing heuristic logic as a base) and pass them to the model for summarization.
- Implement structured JSON output from the local model to ensure entity extraction is easily parsable into a Qt `QTreeView` hierarchy.
- Must run lazily or in the background as the document is loaded to prevent slow document opening times.
