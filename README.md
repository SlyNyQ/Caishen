# Caishen

Caishen is a plain-English stock and investment-analysis assistant for non-expert retail investors. It combines current and historical market data, user-supplied public sources, deterministic calculations, retrieval-grounded educational notes, and multiple server-side LLM providers.

Caishen is read-only. It does not connect to brokerage accounts, execute trades, guarantee outcomes, or issue personalized buy/sell instructions.

## Product

The working product lives in [`Software_Project_Template/03_Product`](Software_Project_Template/03_Product).

- FastAPI backend with `GET /health`, `GET /ready`, and `POST /chat`
- `yfinance` market snapshots, return comparisons, and annualized volatility
- Guarded public URL summarization with private-network blocking and content limits
- OpenAI, Anthropic, Google, Bedrock, and deterministic mock provider adapters
- Local Markdown RAG notes for investment basics, risk, methods, freshness, and safety
- Responsive Next.js research workspace with context controls and structured insights
- AWS Lambda, API Gateway, S3, and CloudFront Terraform stack

## Local Start

```powershell
cd Software_Project_Template\03_Product
uv venv .venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r backend\requirements.dev.txt
.\.venv\Scripts\python.exe scripts\kb_build.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

In a second terminal:

```powershell
cd Software_Project_Template\03_Product\frontend
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

## Verification

```powershell
cd Software_Project_Template\03_Product
.\.venv\Scripts\python.exe -m pytest backend -q
.\.venv\Scripts\python.exe scripts\eval_run_rag.py --require-citations
cd frontend
npm test
npm run build
npm run test:e2e
```

Provider credentials belong only in an ignored `backend/.env`; use the sanitized examples as a starting point.
