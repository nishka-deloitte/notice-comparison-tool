# Notice Comparison Tool

The Notice Comparison Tool accepts uploaded notice or document files, extracts structured fields locally when possible, and compares two versions using two automatic review modes: structured field extraction and full-text paragraph diff for prose-heavy documents such as leases.

## Setup

1. Create and activate a Python virtual environment if you want an isolated setup.
2. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

   The app uses PyMuPDF and EasyOCR for local extraction (no API key required). See `requirements.txt` for the exact dependencies.

## Running the app

Start the Streamlit app locally:

```bash
streamlit run app.py
```

Or view the live deployment on Streamlit Cloud (replace with your app URL):

Live demo: (https://notice-comparison-tool-87km8pmrxzmtuuplsrshk3.streamlit.app/)

## Usage

The app now works from uploaded notice files rather than pasted JSON payloads.

1. Open the Streamlit UI in your browser (or visit the live demo URL above).
2. Upload a PDF or JPEG notice file using the built-in file uploader.
3. The app extracts fields locally using PyMuPDF (PDF text extraction) with an EasyOCR fallback for scanned pages. Unlike the earlier fixed-schema version, it does not assume a hard-coded set such as `notice_id`, `recipient`, `amount_due`, and `due_date`.
4. The parser looks for generic label/value patterns across the document, such as `Field Name: value`, `Field Name = value`, or other recognizable structured label/value lines. It normalizes labels to account for minor differences in spacing, punctuation, and casing.
5. Upload a second notice file and run the comparison workflow to inspect differences side-by-side.

### Comparison modes

The tool runs two comparison modes automatically on every comparison:

1. Structured field comparison
   - For documents with recognizable label/value pairs, it extracts and compares field names and values across both documents.
   - This is ideal for notices, invoices, and other semi-structured inputs where labels are clear.
   - When the two documents do not share the same fields, the comparison is based on the union of all labels found in either document.

2. Full-text paragraph comparison
   - For prose-heavy documents, especially leases and contracts, it splits the raw text into paragraphs and compares them paragraph by paragraph.
   - This mode catches wording changes, added clauses, and removed text even when the document does not use a rigid field schema.
   - It highlights changed wording inside a paragraph at the word level, while also showing added and removed paragraphs clearly.

### Assumption about document structure

The structured field extraction mode expects the document to contain recognizable label/value lines in some form. If the document is mostly narrative text, a scanned page with no usable field labels, or otherwise lacks a clear label/value pattern, the field-extraction portion will be limited or may return no structured fields rather than crashing.

The full-text paragraph diff still works on documents that are largely prose, even when they do not have structured labels.

### Comparing notices with different field sets

When the two notices do not share the same fields, the comparison is based on the union of all labels found in either document. A field is shown as:

- a match when both notices contain the same normalized label and same normalized value,
- a mismatch when both notices contain the same label but different values,
- missing when one notice contains the field and the other does not.

The comparison view displays the missing label explicitly, such as “Not present in Notice A” or “Not present in Notice B,” so the user can see that the difference is due to a field missing from one notice rather than a blank value.

If extraction fails, the app will surface an error message so the issue can be corrected before proceeding.

Known limitations: OCR accuracy depends heavily on image quality — skewed, low-resolution, or noisy scans may produce incorrect text that impacts field extraction. The full-text diff is also noisier on OCR-heavy documents because paragraph boundaries and wording are less precise than for text-based PDFs, but it still remains useful for review.
