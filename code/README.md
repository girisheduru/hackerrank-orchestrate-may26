# Multi-Domain Support Triage Agent

A terminal-based AI agent that triages support tickets across **HackerRank**, **Claude**, and **Visa** product ecosystems. Responses are grounded exclusively in the provided local support corpus (`data/`). The Anthropic Claude API is the sole external dependency.

---

## Architecture

```
CLI (Typer + Rich)
      │
      ▼
Orchestrator Pipeline
  ├── io/csv_reader.py      — parse input CSV
  ├── agent/classifier.py   — infer company, classify product area
  ├── safety/gate.py        — pre/post escalation rules
  ├── retrieval/retriever.py— BM25 corpus search (domain-filtered)
  ├── agent/responder.py    — Claude API grounded response
  └── io/csv_writer.py      — write output CSV
         │
  telemetry/logger.py + store/persistence.py
```

**Key design decisions:**
- BM25 retrieval (rank-bm25) — deterministic, no vector DB, works offline
- Hard safety gate fires *before* the LLM — prevents Claude from attempting fraud/identity theft responses
- Domain-filtered retrieval — searches only the relevant company's corpus subset
- Rules-only fallback if `ANTHROPIC_API_KEY` is unset

---

## Quick Start

### 1. Setup

```bash
cd hackerrank-orchestrate-may26
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r code/requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY
```

### 3. Run

```bash
python code/main.py run \
  --input  support_tickets/support_tickets.csv \
  --output support_tickets/output.csv \
  --tail
```

**Common flags:**

| Flag | Description |
|------|-------------|
| `--tail` | Stream row-by-row progress |
| `--json` | Machine-readable JSON summary |
| `--limit N` | Process only first N tickets |
| `--seed INT` | Deterministic run |
| `--dry-run` | Validate pipeline, skip writing output |
| `--verbose` | Emit structured NDJSON logs to stderr |

### 4. Other commands

```bash
python code/main.py status          # show last run metadata
python code/main.py logs            # show run NDJSON logs
python code/main.py config --show   # show effective config
```

---

## Running Tests

```bash
# Unit tests only (no API key needed)
pytest -q code/tests/unit

# All tests (integration + e2e require ANTHROPIC_API_KEY)
pytest -q code/tests

# With coverage
pytest --cov=code --cov-report=term-missing code/tests
```

### Dashboard

```bash
./scripts/run_tests_and_build_dashboard.sh
open reports/dashboard/index.html
```

---

## Docker

```bash
# Copy and fill in .env first
docker compose up --build
```

---

## Output Format

`support_tickets/output.csv` — 8 columns:

| Column | Values |
|--------|--------|
| `issue` | Original issue text |
| `subject` | Original subject |
| `company` | Original company |
| `response` | User-facing reply grounded in corpus |
| `product_area` | e.g. `screen`, `privacy_and_legal`, `travel_support` |
| `status` | `replied` \| `escalated` |
| `request_type` | `product_issue` \| `feature_request` \| `bug` \| `invalid` |
| `justification` | Cites specific document(s) used |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | **Required** for LLM responses |
| `TRIAGE_LLM_MODEL` | `claude-sonnet-4-6` | Claude model to use |
| `TRIAGE_LLM_PROVIDER` | `anthropic` | `anthropic` or `rules` (fallback) |
| `TRIAGE_DATA_DIR` | `data` | Corpus directory |
| `TRIAGE_INPUT_CSV` | `support_tickets/support_tickets.csv` | Input path |
| `TRIAGE_OUTPUT_CSV` | `support_tickets/output.csv` | Output path |
| `TRIAGE_LOG_LEVEL` | `info` | `info` \| `debug` \| `warn` \| `error` |

---

## Evaluation Criteria Mapping

| Criterion | Implementation |
|-----------|---------------|
| Architectural clarity | Modular layout: cli/, agent/, retrieval/, safety/, store/, io/, telemetry/ |
| Corpus data reliance | All LLM prompts inject retrieved corpus chunks; no external knowledge used |
| Escalation protocols | `safety/gate.py` — regex rules + BM25 confidence threshold |
| Reproducibility | `--seed` flag, deterministic BM25, JSONL run logs in `~/hackerrank_orchestrate/runs/` |
| Engineering standards | `.env.example`, secrets via env vars only, no hardcoded credentials |
| No hallucination | System prompt enforces corpus-only; post-check validates confidence |
