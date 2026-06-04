# Caishen Folder And Architecture Strategy

Caishen separates source knowledge, deterministic market tools, model generation, user interface, and infrastructure so each can be tested and changed independently.

## Product Layout

```text
03_Product/
|-- backend/
|   |-- app/
|   |   |-- api/              # FastAPI contracts and routes
|   |   |-- llm/              # Validated provider adapters
|   |   |-- orchestrator/     # Intent, refusal, analysis, workflow
|   |   |-- rag/              # Lexical retrieval and citations
|   |   |-- telemetry/        # Logging
|   |   `-- tools/            # Market data, public sources, scenarios
|   |-- kb/raw_docs/          # Curated Markdown research notes
|   `-- tests/                # Unit and API integration tests
|-- frontend/
|   |-- app/                  # Next.js routes and global visual system
|   |-- components/           # Research workspace, context, insights
|   |-- lib/                  # Typed API client and contracts
|   `-- e2e/                  # Playwright flows
|-- scripts/                  # KB build, evaluation, deployment helpers
|-- terraform/
|   |-- bootstrap/            # Optional shared state/ECR/KB resources
|   `-- modules/              # Lambda API and CloudFront frontend
|-- api/                      # Human-readable API specification
`-- documentation/            # Setup notes
```

## Runtime Boundaries

- `api/schemas.py` is the shared backend contract. The frontend mirrors it in `frontend/lib/types.ts`.
- `tools/market_data.py` owns ticker parsing and calculations. It returns unavailable states instead of invented values.
- `tools/web_sources.py` owns URL validation, private-network blocking, redirects, timeouts, size limits, and sanitization.
- `orchestrator/workflow_engine.py` is the only end-to-end request workflow.
- `llm/providers.py` validates provider/model allowlists and keeps credentials server-side.
- `rag/` retrieves only curated educational Markdown. It never stores customer portfolios or brokerage data.

## Generated And Local-Only Material

The following are intentionally not retained:

- virtual environments, dependency folders, build outputs, coverage, and caches
- real `.env` files and local Terraform values/state
- generated KB chunks and manifests
- evaluation output and test results

Regenerate the KB with `python scripts/kb_build.py`, the frontend with `npm run build`, and test results with the documented verification commands.

## Safety Model

Caishen is read-only and educational. Market snapshots and public-source summaries are evidence inputs, not trade instructions. Refusal logic blocks trade execution, guaranteed outcomes, manipulation, and personalized buy/sell directives while offering safer educational alternatives.
