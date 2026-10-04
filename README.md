# FixPune local prototype

FastAPI backend and a single-file Streamlit UI for an artisan/customer marketplace MVP.

## Setup

1. Create and activate a virtual environment, then install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`. Profile generation and
   job classification require a valid Google AI Studio Gemini API key; the API
   returns an explicit error if it is missing or Gemini is unavailable. The
   workspace enables `python.terminal.useEnvFile` so the Python extension loads
   `.env` values into new terminals; restart existing terminals after changing
   `.env`.

3. Start the API and UI in separate terminals from the project directory:

   ```powershell
   uvicorn app.main:app --reload
   ```

   ```powershell
   streamlit run streamlit_app/app.py
   ```

   The API docs are at <http://127.0.0.1:8000/docs>. Set `API_BASE_URL` if the
   Streamlit UI needs a different API address.

## Demo behavior

- SQLite creates `handyman.db` in this project directory and seeds mock, verified
  artisans on first startup. New artisan profiles remain pending verification.
- The trade dropdown and price validation use only trades/services present in
  `price_lookup.json`; the model cannot set prices outside those published bands.
- Phone OTP, image storage, verification, and payment holds/releases/disputes are
  simulated. No payment processor or actual payout is connected.
- To accept or decline a customer-created booking, switch to the artisan feed.
  An artisan can also accept a still-open matching job directly from the feed.
