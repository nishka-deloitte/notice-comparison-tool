# Architecture: Notice Comparison Tool

## 1. Overview
The Notice Comparison Tool is implemented as a Python + Streamlit application that accepts uploaded notice documents, extracts structured notice fields automatically, compares the resulting notice data, and supports a human review workflow.

The architecture separates document extraction, comparison logic, and presentation so that each layer can be tested independently and reused outside the UI if needed.

## 2. Goals
- Accept uploaded PDF or JPEG notice documents through Streamlit.
- Extract structured notice fields automatically using Claude via the Anthropic API.
- Produce a JSON object that matches the schema expected by the diff engine.
- Compare two notice extraction results and identify field-level differences clearly and consistently.
- Support a human-readable side-by-side review experience.
- Allow a reviewer to confirm match, mismatch, or request further review.
- Keep the extraction and comparison logic deterministic, explainable, and easy to evolve.

## 3. High-Level Solution
The application has four core responsibilities:

1. Ingestion of uploaded PDF or JPEG notice documents
2. Structured extraction via Claude and schema validation
3. Comparison and classification through a dedicated diff engine
4. Rendering and review through a Streamlit user interface

### Flow
1. The user uploads one or more PDF or JPEG notice files through the Streamlit UI.
2. The app converts the uploaded file into a base64-encoded content block appropriate for the Anthropic API.
3. The extraction service sends the document to Claude with a prompt that requires JSON output matching the notice schema.
4. The app parses and validates Claude’s response before passing it to the diff engine.
5. The diff engine compares the notices and returns a structured diff result.
6. The UI renders the comparison in a side-by-side view and enables review actions.
7. The reviewer confirms the result, and the decision is stored with the comparison evidence.

## 4. Recommended Project Structure
```text
app.py
src/
  __init__.py
  diff_engine.py
  extraction.py
  models.py
  ui_helpers.py
  audit.py
tests/
  test_diff_engine.py
  test_extraction.py
  test_ui_flow.py
```

## 5. Component Responsibilities

### 5.1 Streamlit UI Layer
Responsible for:
- collecting or loading the two notice inputs,
- storing them in Streamlit session state,
- invoking the diff engine,
- rendering the human-readable side-by-side view,
- exposing confirm actions for match / mismatch / needs review.

Primary entry point:
- app.py

### 5.2 Extraction Layer
Responsible for:
- accepting uploaded PDF or JPEG files from the Streamlit UI,
- extracting text from PDFs with PyMuPDF (fitz) and falling back to OCR for scanned pages,
- running EasyOCR on JPEG images and on scanned PDF pages rendered to images,
- applying field-parsing rules to recover notice_id, recipient, amount_due, due_date, and other relevant fields from the extracted text,
- surfacing clear errors for failed extraction, low-confidence output, or OCR failures.

Primary module:
- src/extractor.py

This module should be isolated from the UI so it can be tested independently and reused in future automation flows.

### 5.3 Diff Engine
Responsible for:
- traversing the structured notice data,
- comparing values recursively,
- detecting added, removed, changed, or unchanged fields,
- normalizing common formatting differences,
- producing a structured result with a recommended classification.

Primary module:
- src/diff_engine.py

This module should remain pure Python and should not import Streamlit. It should accept plain Python dictionaries and return a structured result object or dictionary.

### 5.4 Data Models
Responsible for:
- defining the shape of notice extraction result input,
- defining the structure of the diff result,
- documenting expected field types and optional metadata.

Primary module:
- src/models.py

## 6. Data Shape for Extraction Results
The extraction pipeline should return a JSON-like dictionary that the diff engine can compare directly. A recommended shape is a flat, schema-driven object so that the required fields remain explicit and easy to validate:

```python
{
  "notice_id": "notice-001",
  "recipient": "Acme Corp",
  "amount_due": 1500,
  "due_date": "2026-08-15",
  "metadata": {
    "source": "claude-api",
    "extracted_at": "2026-08-03T10:00:00Z",
    "confidence": 0.92
  }
}
```

### Notes
- The top-level object should be a dictionary.
- At minimum, the extractor should return fields such as notice_id, recipient, amount_due, and due_date.
- The extractor may include optional metadata and additional fields if they are present in the document.
- The diff engine should handle missing fields and partial extraction results gracefully.

## 7. Diff Result Shape
The diff engine should return a structured result such as:

```python
{
  "status": "materially_different",
  "summary": "The notices differ in date and obligation text.",
  "differences": [
    {
      "path": "data.effective_date",
      "change_type": "changed",
      "before": "2026-08-01",
      "after": "2026-08-15"
    }
  ],
  "classification": {
    "label": "materially_different",
    "confidence": 0.92,
    "reason": "Critical date changed"
  }
}
```

## 8. Streamlit Session State
Streamlit session state should hold all data needed to render the comparison view and support the review flow.

### Recommended state entries
```python
st.session_state["notice_a"] = notice_a
st.session_state["notice_b"] = notice_b
st.session_state["comparison_result"] = comparison_result
st.session_state["review_decision"] = None
st.session_state["review_comment"] = ""
st.session_state["review_submitted"] = False
st.session_state["extraction_error"] = None
st.session_state["extraction_confidence"] = None
```

### Why this works
- The UI can re-render without reloading the notices from the backend.
- The comparison result remains available while the reviewer inspects the side-by-side view.
- Confirm actions can update the state without losing the evidence already produced.

## 9. Extraction Pipeline Design
The extraction flow should follow a predictable sequence:

1. The Streamlit UI accepts a PDF or JPEG upload and stores the file bytes plus MIME type.
2. The extraction module inspects the uploaded file and chooses the appropriate processing path:
   - PDF: use PyMuPDF (fitz) to extract embedded text directly; for pages with little or no text, render the page to an image and run EasyOCR on that image.
   - JPEG: run EasyOCR directly on the image bytes.
3. The extracted text is normalized and passed through regex/keyword rules that recover notice_id, recipient, amount_due, due_date, and other relevant fields.
4. The parsed fields are assembled into a notice dictionary matching the schema expected by the diff engine.
5. The validated notice object is passed to compare_notices().
6. Failures such as unreadable files, OCR errors, or insufficient extracted content should be surfaced to the UI as actionable errors rather than silently failing.

### Suggested implementation responsibilities
- src/extractor.py: process PDFs and JPEGs, run OCR when needed, and parse notice fields from text.
- app.py: orchestrate upload, call the extractor, and display any extraction errors.
- src/models.py: define the expected schema and validation helpers.

## 10. UI Rendering Approach
The Streamlit UI should render:
- a header with both notices and comparison status,
- a side-by-side comparison pane,
- highlighted rows for added, removed, and changed values,
- action buttons for match / mismatch / needs review,
- extraction error messaging when validation or API calls fail.

The UI should use the diff result to decide how each row is styled and labeled.

## 11. Architectural Decisions (ADRs)

### ADR-1: Separate diff logic from UI
Decision: The comparison logic will live in a dedicated Python module, not inside the Streamlit app.

Rationale:
- Improves testability
- Enables reuse in non-UI workflows
- Keeps the UI focused on rendering and review

### ADR-2: Use JSON-like nested dictionaries as the canonical input format
Decision: Notices will be represented as nested dictionaries and lists that resemble JSON.

Rationale:
- Matches common extraction outputs
- Supports flexible schemas
- Makes recursive comparison straightforward

### ADR-3: Use Streamlit session state for multi-step review state
Decision: Session state will hold both notices, the diff result, and the reviewer decision.

Rationale:
- Aligns with Streamlit’s execution model
- Avoids unnecessary persistence for MVP
- Makes the review flow simple and stateful

### ADR-4: Treat materiality as heuristic-driven with human override
Decision: The diff engine will provide a recommended classification, but the human reviewer will remain the final authority.

Rationale:
- Recognizes that some differences are ambiguous
- Supports explainability
- Avoids overclaiming certainty from automated logic

### ADR-5: Validate extraction output before it reaches the diff engine
Decision: Extracted text will be parsed into structured fields through deterministic rules before compare_notices() is called.

Rationale:
- Prevents malformed or low-confidence data from polluting comparisons
- Makes failures explicit and easier to debug
- Preserves a consistent schema for downstream comparison logic
- Avoids dependency on external OCR or model services that are unavailable in this environment

## 12. Testing Strategy
- Unit tests for the diff engine should cover added, removed, changed, and nested structures.
- UI tests should verify that the Streamlit app renders comparison results and handles confirm actions.
- Edge cases should include missing fields, empty lists, formatting differences, and partial extraction results.

## 13. Open Questions
- Should the MVP persist comparisons to a local file or database?
- Should the diff classification rules be configurable by business rule set?
- Should the UI support upload of JSON files directly in the first iteration?
- Should low-confidence extractions be retried automatically or require manual review?
