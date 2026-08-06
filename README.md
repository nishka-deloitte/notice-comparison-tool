# Notice Comparison Tool

The Notice Comparison Tool accepts uploaded notice documents, extracts structured fields locally, and compares two notice versions to highlight material differences.

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
3. The app extracts fields locally using PyMuPDF (PDF text extraction) with an EasyOCR fallback for scanned pages, producing `notice_id`, `recipient`, `amount_due`, and `due_date`.
4. The field parser is tolerant to common OCR noise (misplaced/missing separators, mixed quotes, extra punctuation) and uses robust regex-based extraction.
5. Upload a second notice file and run the comparison workflow to inspect differences side-by-side.

If extraction fails, the app will surface an error message so the issue can be corrected before proceeding.

Known limitation: OCR accuracy depends heavily on image quality — skewed, low-resolution, or noisy scans may produce incorrect text that impacts field extraction.
