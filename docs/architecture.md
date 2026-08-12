# Architecture: Notice Comparison Tool

## 1. Overview
The Notice Comparison Tool is implemented as a Python + Streamlit application that accepts uploaded notice documents, extracts structured notice fields automatically, compares the resulting notice data, and supports a human review workflow.

The architecture separates document extraction, comparison logic, and presentation so that each layer can be tested independently and reused outside the UI if needed.

## 2. Goals
- Accept uploaded PDF or JPEG documents through Streamlit, including notices, leases, and other text-based content.
- Extract arbitrary label/value pairs from document text without requiring a fixed field list up front.
- Normalize labels so OCR and minor formatting differences still align across documents.
- Compare two notice extraction results by the union of all labels found in both notices and highlight missing values explicitly.
- Add a second comparison path for full-document prose by splitting text into paragraphs and computing a paragraph-level diff.
- Support a human-readable side-by-side review experience for both structured fields and paragraph changes.
- Allow a reviewer to confirm match, mismatch, or request further review.
- Keep the extraction and comparison logic deterministic, explainable, and easy to evolve.

## 3. High-Level Solution
The application has four core responsibilities:

1. Ingestion of uploaded PDF or JPEG notice documents
2. Structured extraction via Claude and schema validation
3. Comparison and classification through a dedicated diff engine
4. Rendering and review through a Streamlit user interface

### Flow
1. The user uploads one or more PDF or JPEG documents through the Streamlit UI.
2. The app converts the uploaded file into text that can be scanned line by line for label/value patterns and full-document prose.
3. For PDF files, the extraction layer first inspects AcroForm widget values using PyMuPDF's form-field API. These are treated as the most reliable values because they come directly from the form data and do not depend on visible text extraction.
4. In parallel, the extraction layer also reads regular page text from the PDF via fitz for surrounding template/prose content, and it runs OCR on page images when needed, rather than treating text extraction and OCR as mutually exclusive choices.
5. The extraction result is normalized into a dictionary keyed by canonicalized labels so the same field can still match even if OCR output varies slightly.
6. The final raw text used for both structured parsing and the full-text diff is assembled from a combination of: form field values, page text, and OCR text. The form values are tagged as the highest-confidence source so they can be distinguished from surrounding template prose.
7. The diff engine compares the union of normalized labels across both notices and returns a structured diff result that includes missing/extra values.
8. A second text-diff layer splits the raw extracted text into paragraphs and compares them using Python difflib. This produces structured information about unchanged, changed, added, and removed paragraphs.
9. The UI renders both outputs in a single review workflow: structured field comparison and full-text paragraph diff.
10. The reviewer confirms the result, and the decision is stored with the comparison evidence.

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
- extracting direct PDF form-field values using PyMuPDF's widget/form API when present,
- extracting regular page text from PDFs with PyMuPDF (fitz) for surrounding template and narrative content,
- running OCR on page images or JPEG images when needed, rather than assuming one source is always enough,
- combining form field values, page text, and OCR text into a single raw-text view for both structured parsing and full-text comparison,
- scanning extracted text line by line for a generic label/value pattern: a label followed by a separator such as :, -, or multiple spaces, then a value,
- normalizing label text for comparison, including lowercasing, whitespace trimming, whitespace collapsing, and standardizing underscores/spaces,
- surfacing clear errors for failed extraction, low-confidence output, or OCR failures.

Primary module:
- src/extractor.py

This module should be isolated from the UI so it can be tested independently and reused in future automation flows.

The fixed regex-per-field design in field_rules.py is replaced by a generic parser that recognizes any label/value line rather than a small whitelist of expected notice fields.

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

### 5.4 Full-Text Diff Layer
Responsible for:
- taking the raw extracted text from both documents,
- splitting the text into paragraphs using double newlines when available and single newlines as a fallback,
- comparing paragraph lists with Python difflib,
- classifying paragraphs as unchanged, changed, added, or removed,
- preserving document order so a reviewer can follow narrative and clause changes in context,
- handling OCR-noisy documents by treating paragraph boundaries as approximate rather than exact.

Recommended function:
- compare_paragraphs(left_text: str, right_text: str) -> dict

This capability runs alongside the field-based diff and is not a replacement for label/value extraction. Both outputs are available to the UI in the same review workflow.

### 5.5 Data Models
Responsible for:
- defining the shape of notice extraction result input,
- defining the structure of the diff result,
- documenting expected field types and optional metadata,
- defining the paragraph-level diff result shape for prose and clause comparison.

Primary module:
- src/models.py

## 6. Data Shape for Extraction Results
The extraction pipeline should return a JSON-like dictionary keyed by the labels found in the document, without assuming a fixed schema in advance. The shape is intentionally open-ended so that notice-specific fields can be captured as they appear in the source document:

```python
{
  "notice_id": "notice-001",
  "recipient": "Acme Corp",
  "amount_due": 1500,
  "due_date": "2026-08-15",
  "tax_id": "12-3456789",
  "metadata": {
    "source": "ocr+parser",
    "extracted_at": "2026-08-03T10:00:00Z",
    "confidence": 0.92
  }
}
```

### Notes
- The top-level object should be a dictionary.
- The extractor should not depend on a fixed four-field schema or a whitelist of known labels.
- Labels should be normalized before comparison so variants such as Amount Due and amount due map to the same canonical field name.
- The diff engine should handle missing fields, partial extraction, and document-specific fields gracefully.

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

The full-text paragraph diff should return a parallel result such as:

```python
{
  "status": "materially_different",
  "summary": "3 paragraphs changed and 2 were added.",
  "paragraphs": [
    {
      "index": 4,
      "status": "changed",
      "before": "The tenant shall pay rent on the first day of each month.",
      "after": "The tenant shall pay rent on the fifth day of each month."
    },
    {
      "index": 6,
      "status": "added",
      "text": "A late fee of $50 will apply after a 10-day grace period."
    },
    {
      "index": 7,
      "status": "removed",
      "text": "Utilities remain the responsibility of the landlord."
    }
  ],
  "classification": {
    "label": "materially_different",
    "confidence": 0.8,
    "reason": "Narrative clause-level differences detected."
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
   - PDF: first read any AcroForm widget values directly through PyMuPDF's form-field API. These values are treated as the most reliable source for filled-in field data.
   - PDF: also extract normal page text via fitz for surrounding template or prose content.
   - PDF: for pages that are mostly scanned images or that have little embedded text, render the page to an image and run EasyOCR; do not skip OCR solely because page text exceeds a short threshold.
   - JPEG: run EasyOCR directly on the image bytes.
3. The extracted data is aggregated across all sources for a given document: form field values, regular page text, and OCR output. The final raw text is the concatenation or merged union of these sources, with a clear distinction between direct form-field values and surrounding template text.
4. The combined raw text is normalized and scanned line by line for generic label/value pairs.
5. A parser recognizes a label followed by a separator such as :, -, or multiple spaces and then a value; OCR noise is tolerated by allowing non-alphanumeric separator variants as part of the generic pattern.
6. Labels are canonicalized for comparison by lowercasing, trimming whitespace, collapsing repeated spaces, and converting underscores/spaces to a common form.
7. The parsed fields are assembled into a notice dictionary keyed by the canonicalized labels, without requiring a fixed whitelist.
8. The validated notice object is passed to compare_notices().
9. Independently, the raw extracted text is also passed to a paragraph diff function that splits the document into paragraph units and compares them with difflib.
10. Failures such as unreadable files, OCR errors, or insufficient extracted content should be surfaced to the UI as actionable errors rather than silently failing.

### Suggested implementation responsibilities
- src/extractor.py: process PDFs and JPEGs, extract widget values, run OCR when needed, merge page text and OCR output, and parse generic label/value entries from the final extracted text.
- src/text_diff.py (or a similar helper module): split the raw extracted text into paragraphs and compute paragraph-level diffs with difflib.
- app.py: orchestrate upload, call the extractor, call the text diff helper, and display both outputs.
- src/models.py: define the expected result structure and validation helpers for arbitrary field names and paragraph diff results.

### Constraint / limitation
This approach assumes the document contains recognizable label/value structure such as a line like “Field Name: value” or other consistent key/value formatting. Narrative-only text without discernible field labels is outside the supported input pattern for structured extraction, but it can still be compared through the paragraph-level text diff path. For OCR’d content, paragraph boundaries will be noisier than text-based PDFs, but the diff remains useful and should degrade gracefully rather than fail.

### PDF form-specific note
Lease PDFs are often fillable forms, with some pages containing native form widgets and other pages containing scanned image content. The implementation should therefore prefer form field values whenever available, while still extracting regular page text and OCR output for the surrounding template or prose. The final document-level raw text should merge those sources without dropping form values simply because the page also contains visible template text.

## 10. UI Rendering Approach
The Streamlit UI should render:
- a header with both documents and comparison status,
- a structured field comparison pane,
- a paragraph-level text diff pane for full-document prose changes,
- highlighted rows for added, removed, and changed values,
- action buttons for match / mismatch / needs review,
- extraction error messaging when validation or API calls fail.

The UI should use both the structured diff result and the paragraph diff result to decide how each section is styled and labeled.

The paragraph diff should be displayed beneath or adjacent to the structured field comparison so that a reviewer can inspect the extracted fields and the narrative/contractual differences in the same workflow.

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
Decision: Extracted text will be parsed into structured fields through a generic line-based key/value parser before compare_notices() is called.

Rationale:
- Prevents malformed or low-confidence data from polluting comparisons
- Makes failures explicit and easier to debug
- Supports arbitrary labels instead of a fixed schema
- Keeps the extraction logic aligned with OCR noise handling and normalized label matching
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
