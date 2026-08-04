# Notice Comparison Tool

The Notice Comparison Tool accepts uploaded notice documents, extracts structured fields automatically with Claude, and compares two notice versions to highlight material differences.

## Setup

1. Create and activate a Python virtual environment if you want an isolated setup.
2. Install the required packages:

   ```bash
   pip install -r requirements.txt
   pip install anthropic python-dotenv
   ```

3. Create a `.env` file in the project root and add your Anthropic API key:

   ```dotenv
   ANTHROPIC_API_KEY=your_api_key_here
   ```

   The application uses `python-dotenv` to load this value automatically at startup.

## Running the app

Start the Streamlit app:

```bash
streamlit run app.py
```

## Usage

The app now works from uploaded notice files rather than pasted JSON payloads.

1. Open the Streamlit UI in your browser.
2. Upload a PDF or JPEG notice file.
3. The app sends the document to Claude automatically and extracts notice fields such as `notice_id`, `recipient`, `amount_due`, and `due_date`.
4. Upload a second notice file and run the comparison workflow to inspect differences.

If extraction fails, the app will surface a clear error message so the issue can be corrected before comparison proceeds.
