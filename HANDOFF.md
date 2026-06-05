# HANDOFF

Date: 2026-06-05
Repo: `/Users/mateo/Desktop/f2wlocal`

---

## User Goal

Make KG-RAG CLI chat use CBORG as default backend. Fix all dependency/env/runtime issues blocking CLI chat. Keep Open WebUI pointed at KG-RAG on port `11435`. Extend the pipeline to extract x-ray scattering peak-finding code snippets from PDFs and build a dedicated xray KG. Ensure both code snippets AND publication/domain terms are correctly retrieved in chat.

---

## Completed

### Backend & Connectivity
- Fixed `CBORG_BASE_URL` from internal `api-local.cborg.lbl.gov` → `https://api.cborg.lbl.gov`
- Removed invalid `:latest` suffix from model name — `lbl/cborg-chat` everywhere
- `load_dotenv()` → `load_dotenv(override=True)` in all three entry points so `.env` always wins over stale shell env vars: `kg_rag_api.py`, `extract_terms.py`, `run_pipeline_cborg.py`

### Bug Fixes
- Fixed bad import in `run_pipeline_cborg.py`: `extract_terms_cborg` → `extract_terms`
- Deduplicated `scripts/analyze_kgs.py` — double execution would have silently produced misleading partial results
- Renamed `kg_rag_ollama_api.py` → `kg_rag_api.py` — all references updated
- Fixed `chebi.py`: missing OBO file now raises catchable `FileNotFoundError` instead of `sys.exit(1)`

### Schema Extensions (`storage/schema/matkg_schema.yaml`)
- Added `CodeSnippet` class (`is_a: Thing`) with slots: `code_snippet`, `code_language`, `code_description`, `function_name`, `code_domain`
- Added `has_code_snippet` slot (range: `CodeSnippet`) and `code_domain` slot
- Added `XRayScatteringAnalysis` class (subclass of `ExperimentalTechnique`) with slots: `scattering_technique`, `peak_positions`, `d_spacing`, `peak_assignments`, `has_code_snippet`
  - Code fields removed from `XRayScatteringAnalysis` — now live on `CodeSnippet`
- Added 10 publication metadata slots to `Thing` base class: `paper_title`, `authors`, `institutions`, `doi`, `journal`, `volume`, `issue`, `pages_range`, `abstract_text`, `keywords`
- Added `publication_year` slot (`integer`, `dcterms:date`) to `Thing` — all entities inherit it

### Term Extraction (`app/modules/extract_terms.py`)

#### Code Snippet Extraction
- Added `extract_xray_code_snippets()` — LLM-based extraction of peak-finding code blocks per page
- Added `_collect_xray_code_snippets()` — dedup + thread-safe save, called every page
- Snippets stamped with full pub metadata: `paper_title`, `doi`, `paper_authors`, `publication_year`, `source_paper`, `page`
- `function_name` extracted: LLM value → regex `def`/`class` fallback → first called function
- `publication_year` explicitly stamped onto each snippet from `pub_meta` so recency boost fires

#### Regex Fallback
- Post-LLM pass after every LLM call — finds named `def`/`class` blocks missed by LLM
- Only adds what LLM missed (compares against `llm_fn_names`)
- Tags recovered snippets: `"(recovered via regex fallback)"` in `code_description`

#### Publication Metadata
- `_extract_pub_metadata()` with 4-priority year extraction
- Both `paper_authors` (from pub_meta) and `authors` (library attribution from LLM) kept separate

### KG Conversion (`app/modules/json2kg.py`)
- `make_xray_node()` builds `XRayScatteringAnalysis` KG nodes
- `make_code_snippet_node()` builds `CodeSnippet` KG nodes; MD5 hash of code body in ID prevents collisions
- `build_graph()` wires `rel:has_code_snippet` edge between `XRayScatteringAnalysis` → `CodeSnippet`
- Fragment filter: snippets with `len(code) < 150` or no `def`/`class`/`import` anchor are skipped — prevents math formulas, bare function names, partial captures from entering KG
- Ghost node guard: terms mis-categorized as `CodeSnippet` by LLM are **demoted to `Unknown`** (not dropped) so their relations are preserved; real `CodeSnippet` nodes come exclusively from `xray_code_snippets`
- All 10 pub metadata fields + `publication_year` carried into all KG nodes

### KG-RAG Retrieval (`app/modules/kg_rag_api.py`)
- `NodeInfo` gains `publication_year` and `category` fields
- `score_prp` applies recency boost: up to +0.1 for recent papers, decaying over 10 years
- `CodeSnippet` score bonus: +0.15 added to `score_prp` — ensures code nodes rank above their `XRayScatteringAnalysis` parents when both are in result set, preventing code from being crowded out
- `retrieve_nodes()` injects linked `CodeSnippet` nodes after top-K ranking — guarantees code always reaches context even if parent fills the K budget
- `build_context()` renders `CodeSnippet` nodes: `Function`, `Domain`, `Library_Authors`, `Paper_Authors`, full fenced code block; skips nodes with empty `code_snippet`
- `build_context()` renders for ALL nodes: `Paper_Title`, `Publication_Year`, `DOI`, `Authors`, `Journal`, `Source_Papers`
- `RAG_SYSTEM` prompt guideline: rank by relevance then recency; include year in citations; include title/authors/year/DOI when available

### Build Script (`scripts/build_kg.sh`)
- Safe rebuild: writes to `.tmp` files, promotes on success only, backs up as `.bak`
- `trap cleanup EXIT`, `set -euo pipefail`

### Verified Extraction Results (2026-06-05, latest run)
- **118 unique terms**, 7 PDFs, 36 pages, 34 pages with terms
- **25 code snippets** in KG (13 fragments/noise filtered out)
- **197 total nodes** (33 `XRayScatteringAnalysis`, 25 `CodeSnippet`, remainder materials/terms/techniques)
- **160 edges**
- 0 orphan `CodeSnippet` nodes, 0 empty code nodes

### Fragment Filter — What Gets Dropped
Skipped at KG-build time (not extracted to KG):
- Math formulas: `q = 4π/λ sin(θ)`, loss equations, scattering vector components
- Bare identifiers: `XGBClassifier`, `RandomForestClassifier`, `scipy.signal.find_peaks`
- Partial captures: argument lists without function definition, incomplete code blocks

---

## Current State

### Services
```bash
# Restart API
cd /Users/mateo/Desktop/f2wlocal
python3 app/modules/kg_rag_api.py --api &

# Verify
curl http://localhost:11435/api/tags
```

Last run: API PID 11436, started 2026-06-05 ~14:50

### Active KG
```
storage/kg/matkg_xray_papers_cborg_chat.json
197 nodes | 160 edges | 25 CodeSnippet | 33 XRayScatteringAnalysis
```

### .env (current values, no secrets)
```env
CBORG_BASE_URL=https://api.cborg.lbl.gov
KG_RAG_BACKEND=cborg
KG_RAG_CBORG_MODEL=lbl/cborg-chat
KG_RAG_GRAPH=storage/kg/matkg_xray_papers_cborg_chat.json
KG_RAG_RETRIEVAL_BACKEND=lexical
KG_RAG_LLM_TIMEOUT=120
KG_RAG_SHOW_BASELINE=0
PYSTOW_HOME=.cache/pystow
```

### Git state
```
branch: main
last commit: 1964c82
push: pending — no PAT or SSH key configured
```

---

## Remaining Issues

| # | Issue | Priority |
|---|---|---|
| 1 | `KG_RAG_CTX_CHARS` not in `.env` | Low — add `KG_RAG_CTX_CHARS=6000` |
| 2 | ChEBI `.obo` missing | Low — enrichment silently disabled; ~500MB download to enable |
| 3 | Test coverage shallow | Low — `_tests/` only has dummy `add()` test |
| 4 | GitHub push blocked | Medium — needs PAT or SSH key |
| 5 | Ctrl+C on API server throws error | Low — wrap `uvicorn.run()` in `try/except KeyboardInterrupt: sys.exit(0)` |
| 6 | Regex-recovered snippets lack real `code_description` | Low — second-pass LLM call on regex-only entries to fill description/authors/technique |
| 7 | `MP_API_KEY` placeholder in `.env` causes silent formula validation failures | Non-critical |

---

## Key Files

| File | Role |
|---|---|
| `app/modules/kg_rag_api.py` | API server, retrieval, context builder, LLM chat |
| `app/modules/extract_terms.py` | PDF → terms + code snippets via LLM + regex |
| `app/modules/json2kg.py` | terms JSON → KG graph JSON |
| `storage/schema/matkg_schema.yaml` | Schema: 19 classes, 60 slots |
| `storage/kg/matkg_xray_papers_cborg_chat.json` | Active KG |
| `storage/terminology/extracted_terms_xray_papers_cborg_chat.json` | Latest extraction output |
| `xray_papers/` | Source PDFs: MISC_DOCS, PYFAI_DOCS, SCIPY_DOCS, XRAY_MISC1, XRAY1, XRAY2, XRAY3 |
| `scripts/build_kg.sh` | Safe extract + rebuild script |
| `docs.md` | Full repo reference |
