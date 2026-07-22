# Ava — Neurofive Sales Assistant

This repository contains a small FastAPI backend (main.py) and a static frontend (static/) that together implement "Ava", a sales-focused chat assistant.

Quick start

1. Create a virtualenv and install dependencies:

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate  # Windows (PowerShell)
   pip install -r requirements.txt

2. Set your OpenAI key (required):

   export OPENAI_API_KEY="sk-..."

3. (Optional) Configure sales handoff SMTP variables:

   export ENABLE_SALES_HANDOFF="true"
   export SALES_EMAIL="sales@neurofive.com"
   export SMTP_HOST="smtp.example.com"
   export SMTP_PORT="587"
   export SMTP_USER="noreply@example.com"
   export SMTP_PASS="smtppassword"

4. Run locally:

   uvicorn main:app --reload --host 0.0.0.0 --port 8000

5. Open http://localhost:8000/ in your browser.

Docker

Build and run the included Dockerfile:

   docker build -t ava-sales .
   docker run -e OPENAI_API_KEY="sk-..." -p 8000:8000 ava-sales

Notes
- Do not commit secrets (OpenAI key, SMTP creds) to the repository.
- For production, restrict CORS origins and use HTTPS.

