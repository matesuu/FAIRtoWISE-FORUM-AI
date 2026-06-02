# HANDOFF

Date: 2026-06-02
Repo: `/Users/mateo/Desktop/f2wlocal`
Mode: caveman terse

---

## User Goal

Make KG-RAG CLI chat use CBORG like term extraction. Do not hardwire chat to Ollama. Make CBORG default. Fix dependency/env/runtime issues blocking CLI chat. Keep Open WebUI pointed at KG-RAG on `11435`.

---

## Completed This Session

### 1. CBORG connectivity fixed

- `CBORG_BASE_URL` in `.env` was pointing to `api-local.cborg.lbl.gov` (internal/VPN-only) — times out externally. Changed to `https://api.cborg.lbl.gov`.
- Model name `lbl/cborg-chat:latest` rejected by CBORG API. Correct name is `lbl/cborg-chat` (no `:latest`). Fixed in `.env`, `Dockerfile`, `scripts/.env.example`, and code default fallback in `kg_rag_ollama_api.py`.
- `load_dotenv()` → `load_dotenv(override=True)` in all three entry points so `.env` always wins over stale shell env vars:
  - `app/modules/kg_rag_ollama_api.py`
  - `app/modules/extract_terms.py`
  - `app/run_pipeline_cborg.py`

### 2. run_pipeline_cborg.py bad import fixed

```python
# was:
from modules.extract_terms_cborg import run_extraction
# fixed:
from modules.extract_terms import run_extraction
```

### 3. KG-RAG one-shot verified working

```bash
KG_RAG_CTX_CHARS=3000 python3 app/modules/kg_rag_ollama_api.py \
  --timeout 60 --question "What is P3HT?"
```

Output:
- KG loaded (15815 nodes, retrieval=lexical)
- 12 nodes selected
- CBORG responded with full grounded answer citing KG nodes
- No segfault, no PDF warnings, no timeout

### 4. KG-RAG API server running on 11435

```bash
python3 app/modules/kg_rag_ollama_api.py --api
```

- PID 20518 (as of 2026-06-02 session)
- `curl http://localhost:11435/api/tags` returns `kg-rag:latest`
- Open WebUI connected at `http://127.0.0.1:8080` (PID 20542)

### 5. scripts/analyze_kgs.py deduplicated

File had entire script body duplicated. First copy had incomplete 12-file list; second had complete 30-file list. Running unchanged would:
- Execute twice silently
- Write CSV/JSON twice (second overwrites first)
- First pass produce misleading partial comparative summary
Fixed by keeping only the complete second copy.

### 6. requirements.txt completed

All runtime deps added with `>=` version floors. Split into runtime/dev sections. `pip check` clean.

### 7. README rewritten

Full comprehensive setup guide:
- Prerequisites, clone, install, `.env` config
- ChEBI download note
- Full CLI arg + env var reference tables
- Open WebUI setup and troubleshooting table
- Docker steps (build, run, one-shot, pipeline, overrides, ChEBI mount, logs, stop)
- All `python` → `python3`, all `pip` → `pip3`

### 8. Dockerfile updated

- `KG_RAG_CBORG_MODEL=lbl/cborg-chat` (no `:latest`)
- Added `CBORG_BASE_URL=https://api.cborg.lbl.gov`
- Added `KG_RAG_CTX_CHARS=6000`
- `CMD python` → `CMD python3`
- `mkdir` now includes `storage/ontologies`

### 9. docs.md added (renamed from ref.md)

Repo reference document renamed `ref.md` → `docs.md`. All references in `HANDOFF.md` updated. Last updated note added.

### 10. Git committed (cd89460)

All changes committed to `main`. Push blocked by missing GitHub auth (HTTPS remote, no PAT/SSH configured). Commit is ready — just needs auth to push.

---

## Current State

### Services

| Service | PID | URL | Status |
|---|---|---|---|
| KG-RAG API | 20518 | `http://localhost:11435` | Running |
| Open WebUI | 20542 | `http://127.0.0.1:8080` | Running |

### .env (current values, no secrets)

```env
CBORG_BASE_URL=https://api.cborg.lbl.gov
KG_RAG_BACKEND=cborg
KG_RAG_CBORG_MODEL=lbl/cborg-chat
KG_RAG_GRAPH=storage/kg/matkg_qwen3_235b_580papers.json
KG_RAG_RETRIEVAL_BACKEND=lexical
KG_RAG_LLM_TIMEOUT=120
KG_RAG_SHOW_BASELINE=0
PYSTOW_HOME=.cache/pystow
```

> Note: `KG_RAG_CTX_CHARS` not yet in `.env` — set via shell or add manually. Recommend `6000`.

### Git state

```
branch: main
last commit: cd89460
push: pending (no GitHub auth configured)
```

Untracked (not committed, not ignored):
- `.venv-open-webui/` — Open WebUI venv, large, should stay untracked
- `instructions.md` — local doc
- `schema.md` — local doc
- `storage/knowledge_gaps/` — generated artifacts

---

## Remaining Issues

| # | Issue | Priority |
|---|---|---|
| 1 | `KG_RAG_CTX_CHARS` not in `.env` | Low — add `KG_RAG_CTX_CHARS=6000` |
| 2 | ChEBI `.obo` missing | Low — enrichment silently disabled; download ~500MB if needed |
| 3 | Test coverage shallow | Low — `_tests/` only has dummy `add()` test |
| 4 | GitHub push blocked | Medium — needs PAT or SSH key configured |

---

## CLI Usage

Default CBORG one-shot:
```bash
python3 app/modules/kg_rag_ollama_api.py --question "What is P3HT?"
```

Interactive REPL:
```bash
python3 app/modules/kg_rag_ollama_api.py
```

Reduced context (faster):
```bash
KG_RAG_CTX_CHARS=3000 python3 app/modules/kg_rag_ollama_api.py \
  --timeout 60 --question "What is P3HT?"
```

Ollama override:
```bash
python3 app/modules/kg_rag_ollama_api.py \
  --backend ollama --model llama3.1:8b \
  --question "What is P3HT?"
```

Baseline + KG-RAG:
```bash
python3 app/modules/kg_rag_ollama_api.py \
  --show-baseline --question "What is P3HT?"
```

Start API server:
```bash
python3 app/modules/kg_rag_ollama_api.py --api
```

Term extraction pipeline:
```bash
python3 app/run_pipeline_cborg.py
```

---

## Restart Services (if terminals closed)

```bash
cd /Users/mateo/Desktop/f2wlocal

# KG-RAG API
python3 app/modules/kg_rag_ollama_api.py --api &

# Open WebUI (installed at system Python 3.12)
/Users/mateo/Library/Python/3.12/bin/open-webui serve --host 127.0.0.1 --port 8080 &
```

Verify:
```bash
curl http://localhost:11435/api/tags
```

---

## Files Changed This Session

| File | Change |
|---|---|
| `app/modules/kg_rag_ollama_api.py` | `load_dotenv(override=True)`, model default fixed, code default fixed |
| `app/modules/extract_terms.py` | `load_dotenv(override=True)` |
| `app/run_pipeline_cborg.py` | Bad import fixed, `load_dotenv(override=True)` |
| `scripts/analyze_kgs.py` | Duplicate body removed |
| `requirements.txt` | All runtime deps added with version floors |
| `README.md` | Full rewrite — comprehensive setup, CLI/env tables, Docker, ChEBI |
| `Dockerfile` | Model name, base URL, CTX_CHARS, python3, storage/ontologies |
| `.env` | CBORG_BASE_URL and KG_RAG_CBORG_MODEL corrected |
| `scripts/.env.example` | Model name fixed, KG_RAG_CTX_CHARS added |
| `.env.example` | Root copy synced with scripts/.env.example |
| `.gitignore` | Added `.webui_secret_key` |
| `.dockerignore` | New file |
| `docs.md` | New file (renamed from ref.md) |
