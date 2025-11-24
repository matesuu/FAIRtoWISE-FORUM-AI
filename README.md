# From FAIR to WISE: Creating Knowledge Graphs from Research Papers

## LinkML "Core Model" Schema

An example of a core model for organic photovoltaics can be found in [storage/schema/matkg_schema.yaml](storage/schema/matkg_schema.yaml). You can use this as a starting point for defining a new schema for a different niche topic. The concept extraction uses this schema in the LLM call to help keep the results structured and relevant. 

## LLM Backend

The code in this repository is configured to allow users to pass LLM calls to [Ollama](https://ollama.com/) running locally, or, using [CBORG](https://cborg.lbl.gov/). 

## [Concept Extraction](app/modules/extract_terms.py)

The term extraction system employs parallel page-level processing through Python’s ThreadPoolExecutor, processing PDF pages concurrently with up to 50 workers to balance throughput with LLM latency. To ensure resilience against crashes during long-running extraction jobs, extracted terms and properties are persisted after every page via a lock-guarded \_save\_terms\_threadsafe method, providing thread-safe incremental saving that allows the system to resume from interruptions.

Schema-driven validation forms the core of the extraction accuracy. A SchemaHelper class loads the LinkML schema and performs fuzzy matching of classes and slots using RapidFuzz, enforcing domain/range constraints while auto-correcting invalid categories or relations. The system demonstrates robust fault tolerance by wrapping API calls and JSON parsing with an exponential backoff @retry\_on\_exception decorator, allowing recovery from transient Ollama or network errors without losing progress.

The chemical enrichment pipeline represents a sophisticated multi-stage process for handling chemical entities. The ChemicalFormulaValidator ensures valid chemical formulas and attempts repair through LLM prompts when invalid formulas are detected. Integration with the ChEBI ontology enriches recognized chemicals with additional data including formulas, SMILES notation, InChI identifiers, and charge information. Additionally, the PhysicalPropertyExtractor and PropertyNormalizer work in tandem to detect numerical properties in text and standardize their units and values on the fly, ensuring consistent representation across the knowledge graph.

Duplicate handling leverages LLM-guided semantic merging through a fuzzy merge function that prompts the LLM to determine whether a new term matches an existing one. This prevents duplicate nodes that might arise from variations in notation, such as “GIWAXS” versus “GI-WAXS”, while preserving genuinely distinct concepts. For provenance tracking, the system extracts 50-token snippets around each term mention, creating context-aware captures that link every knowledge graph node back to its source page and paper.

Quality assurance mechanisms include relation verification, where candidate edges are checked against schema domain/range constraints, with invalid ones downgraded to verified=false status. Terms receive post-run annotation with importance scores of high, medium, or low based on their frequency across pages and papers, helping prioritize validation and display. The system provides real-time feedback through a custom ANSI logger that streams color-highlighted progress and warnings, improving interpretability during large-scale runs.

The architecture maintains model-agnostic design, supporting configurable Ollama models such as Gemma 3, Qwen-3-235B, and Mistral, with temperature locked at 0.0 to minimize hallucinations and ensure consistent, deterministic outputs across extraction runs.

## [Convert to KG](app/modules/json2kg.py)

The graph construction module transforms the enriched terms produced by the extractor into a MatKG-compatible JSON-LD graph structure with explicit things (nodes) and associations (edges). Each term receives a stable canonical identifier through a precompiled regex-based cleaner (make\_id), prepending "matkg:" to cleaned term names to ensure reproducibility and compatibility across runs. This identifier system provides consistent node references throughout the knowledge graph lifecycle.

Full metadata preservation ensures downstream usability by retaining all extracted information within the graph structure. Nodes maintain complete records including formula data, formula validation results, extracted properties, and comprehensive provenance fields such as pages, source papers, and context snippets. The system handles incomplete data gracefully through automatic stubbing of unseen targets—when related terms are mentioned in edges but not yet defined as nodes, placeholder nodes are automatically created to prevent dangling edges in the graph.

Edge creation incorporates evidence awareness, carrying relation objects into the knowledge graph with optional evidence strings that make associations more interpretable and traceable. The system prevents duplicate edges by tracking (subject, predicate, object) signatures, ensuring each unique relationship appears only once in the final graph. Robustness is enhanced through utility functions like ensure\_list, which normalizes scalar and None values into lists, preventing schema violations in the graph output that could break downstream processing.

The module provides a configurable command-line interface enabling direct JSON to knowledge graph conversion with verbosity control through the --verbose flag, making it suitable for batch workflows and pipeline integration. Quality assurance comes through an integrated pytest test suite that validates ID generation, list normalization, node and edge field retention, and CLI behavior. This comprehensive testing ensures reproducibility and maintainability across different environments and use cases, providing confidence in the graph construction process.

## [KG-RAG LLM Chat](app/modules/kg_rag_ollama_api.py)

The knowledge graph retrieval-augmented generation system implements a hybrid retrieval strategy that combines semantic search using SentenceTransformer embeddings with a FAISS IVF-Flat index alongside weighted graph expansion through breadth-first search. This dual approach ensures retrieval balances vector similarity with relational structure, leveraging both the semantic understanding from embeddings and the structural knowledge encoded in graph relationships.

Evidence-aware ranking forms the core of result prioritization, where nodes are scored through a weighted combination of semantic similarity, graph depth, lexical overlap, and evidence count. This multi-factor scoring produces more interpretable and grounded answers by considering not just relevance but also the strength of supporting evidence. For each selected node, the system builds structured context blocks that include knowledge graph triples, chemical formulas, descriptions, and up to three PDF snippets with page-level caching for speed, all controlled by a configurable character budget to prevent context overflow.

Complex query handling is achieved through question decomposition and stepwise retrieval. The system decomposes multi-clause questions into sub-queries, performs retrieval for each component, and merges results to improve coverage on long or compound scientific questions. This approach ensures that queries touching multiple concepts or requiring multi-step reasoning receive comprehensive answers drawing from relevant graph regions.

The competency question evaluation loop automates batch evaluation of baseline versus KG-RAG answers using a curated set of materials science competency questions. Results are saved incrementally to JSON for traceability, allowing interrupted evaluations to resume and providing detailed comparison data between augmented and non-augmented responses. Knowledge gap tracking continuously logs missing or unsupported entities—such as queries with no knowledge graph evidence or LLM fallbacks flagged as domain knowledge—into JSONL files, enabling iterative knowledge graph improvement based on actual usage patterns.

FastAPI integration provides a proxy server for OpenWebUI, exposing endpoints including /api/chat, /api/tags, and /api/ps that serve KG-RAG answers as if they were a standard model. This allows seamless integration with existing chat interfaces while maintaining the enhanced capabilities of knowledge-grounded responses. Additionally, an interactive REPL mode supports live question-answering at the terminal, displaying baseline versus KG-RAG outputs side by side with color-coded logs for easy comparison during development and testing.

The system demonstrates GPU-aware optimization by auto-detecting CUDA devices and performing warm-up routines for faster inference, with graceful fallback to CPU if GPU embedding or FAISS indexing fails. Robust PDF caching through LRU mechanisms supports fast repeated lookups when the same papers are cited across multiple questions, significantly reducing latency for document-heavy queries. All key parameters—including model choice, graph file, context budgets, BFS hops, and penalties—can be overridden via environment variables, simplifying deployment across different HPC environments and enabling rapid experimentation without code changes.


This template includes common configuration and settings for ALS Computing projects.

<!-- TREE START -->
<pre>
.
├── _tests
│   └── test_example.py
├── app
│   ├── modules
│   │   ├── __init__.py
│   │   ├── agents
│   │   │   ├── __init__.py
│   │   │   ├── chebi.py
│   │   │   ├── chem_checker.py
│   │   │   └── properties.py
│   │   ├── extract_terms_cborg.py
│   │   ├── json2kg.py
│   │   ├── kg_rag_ollama_api.py
│   │   └── legacy
│   │       ├── build_onto.py
│   │       ├── extract_terms_linkml_jun3.py
│   │       ├── extract_terms_linkml.py
│   │       ├── extract_terms.py
│   │       ├── extracted_terms_json2kg_with_context.py
│   │       ├── json2kg.py
│   │       ├── kg_rag_ollama_nersc.py
│   │       └── kg_rag_ollama.py
│   └── run_pipeline_cborg.py
├── Dockerfile
├── mkdocs
│   ├── docs
│   │   ├── about.md
│   │   ├── assets
│   │   │   ├── als_style.css
│   │   │   └── images
│   │   │       ├── doe_logo.png
│   │   │       └── lbl_logo.png
│   │   ├── core_model.md
│   │   ├── index.md
│   │   ├── test.md
│   │   └── workflow.md
│   ├── mkdocs.yml
│   └── overrides
│       ├── assets
│       │   └── images
│       │       └── favicon.png
│       └── main.html
├── polymer_papers
│   ├── 10.1002adfm.201002014.md
│   ├── 10.1002adfm.201002014.pdf
│   ├── 10.1002adfm.201301121.pdf
│   ├── 10.1002adfm.201304216.pdf
│   ├── 10.1002adfm.201801874.pdf
│   ├── 10.1002adfm.201802895.pdf
│   ├── 10.1002adfm.201806262.pdf
│   ├── 10.1002adfm.201806977.pdf
│   ├── 10.1002adfm.201902238.pdf
│   ├── 10.1002adfm.201902478.pdf
│   ├── 10.1002adfm.201906855.pdf
│   ├── 10.1002adfm.202000489.pdf
│   ├── 10.1002adfm.202008699.pdf
│   ├── 10.1002adfm.202102522.pdf
│   ├── 10.1002adfm.202105304.pdf
│   ├── 10.1002adfm.202109271.pdf
│   ├── 10.1002adfm.202112511.pdf
│   ├── 10.1002adfm.202201150.pdf
│   ├── 10.1002adfm.202305611.pdf
│   ├── 10.1002adma.201102421.pdf
│   ├── 10.1002adma.201405913.pdf
│   ├── 10.1002adma.201505435.pdf
│   ├── 10.1002adma.201604603.pdf
│   ├── 10.1002adma.201606574.pdf
│   ├── 10.1002adma.201700144.pdf
│   ├── 10.1002adma.201703777.pdf
│   ├── 10.1002adma.201704713.pdf
│   ├── 10.1002adma.201705243.pdf
│   ├── 10.1002adma.201705485.pdf
│   ├── 10.1002adma.201801501.pdf
│   ├── 10.1002adma.201803045.pdf
│   ├── 10.1002adma.201806660.pdf
│   ├── 10.1002adma.201808279.pdf
│   ├── 10.1002adma.201902899.pdf
│   ├── 10.1002adma.202002784.pdf
│   ├── 10.1002adma.202005897.pdf
│   ├── 10.1002adma.202105707.pdf
│   ├── 10.1002adma.202107316.pdf
│   ├── 10.1002adma.202108317.pdf
│   ├── 10.1002adma.202108749.pdf
│   ├── 10.1002adma.202110155.pdf
│   ├── 10.1002adma.202202608.pdf
│   ├── 10.1002adma.202203379.pdf
│   ├── 10.1002adma.202205926.pdf
│   ├── 10.1002adma.202207020.pdf
│   ├── 10.1002adom.202300776.pdf
│   ├── 10.1002advs.201500095.pdf
│   ├── 10.1002advs.201500250.pdf
│   ├── 10.1002advs.201600032.pdf
│   ├── 10.1002advs.201600117.pdf
│   ├── 10.1002advs.201903419.pdf
│   ├── 10.1002advs.202000149.pdf
│   ├── 10.1002advs.202001986.pdf
│   ├── 10.1002advs.202104613.pdf
│   ├── 10.1002advs.202203513.pdf
│   ├── 10.1002advs.202302880.pdf
│   ├── 10.1002aelm.201800915.pdf
│   ├── 10.1002aelm.202300422.pdf
│   ├── 10.1002aenm.201601225.pdf
│   ├── 10.1002aenm.201700390.pdf
│   ├── 10.1002aenm.201700519.pdf
│   ├── 10.1002aenm.201701073.pdf
│   ├── 10.1002aenm.201701201.pdf
│   ├── 10.1002aenm.201701942.pdf
│   ├── 10.1002aenm.201702831.pdf
│   ├── 10.1002aenm.201702941.pdf
│   ├── 10.1002aenm.201703058.pdf
│   ├── 10.1002aenm.201800550.pdf
│   ├── 10.1002aenm.201802050.pdf
│   ├── 10.1002aenm.201901728.pdf
│   ├── 10.1002aenm.201903609.pdf
│   ├── 10.1002aenm.202001203.pdf
│   ├── 10.1002aenm.202001589.pdf
│   ├── 10.1002aenm.202003141.pdf
│   ├── 10.1002aenm.202102135.pdf
│   ├── 10.1002aenm.202200641.pdf
│   ├── 10.1002aenm.202300249.pdf
│   ├── 10.1002aenm.202300980.pdf
│   ├── 10.1002anie.201806354.pdf
│   ├── 10.1002anie.202115585.pdf
│   ├── 10.1002app.45399.pdf
│   ├── 10.1002asia.201100419.pdf
│   ├── 10.1002chem.202002632.pdf
│   ├── 10.1002cphc.200901023.pdf
│   └── s41563-024-02076-8.pdf
├── pytest.ini
├── README.md
├── requirements.txt
├── scripts
│   ├── analyze_kgs.py
│   ├── download_pdfs.py
│   ├── get_pdf_years.py
│   ├── test_chat_apis.py
│   └── update_readme_tree.py
└── storage
    ├── competency_questions
    │   └── thomas_f.txt
    ├── kg
    │   ├── matkg_deepseek-r1_14b_100_20250918_095748.json
    │   ├── matkg_deepseek-r1_14b_25_20250915_185643.json
    │   ├── matkg_deepseek-r1_14b_50_20250916_162508.json
    │   ├── matkg_deepseek-r1_14b_75_20250917_143348.json
    │   ├── matkg_deepseek-r1_32b_100_20250922_191851.json
    │   ├── matkg_deepseek-r1_32b_25_20250919_065133.json
    │   ├── matkg_deepseek-r1_32b_50_20250920_125000.json
    │   ├── matkg_deepseek-r1_32b_75_20250921_180642.json
    │   ├── matkg_deepseek-r1_70b_100_20250929_004942.json
    │   ├── matkg_deepseek-r1_70b_25_20250925_103657.json
    │   ├── matkg_deepseek-r1_70b_50_20250926_144206.json
    │   ├── matkg_deepseek-r1_70b_75_20250927_214641.json
    │   ├── matkg_google_gemini-flash-lite_100_20251008_230232.json
    │   ├── matkg_google_gemini-flash-lite_25_20251008_185312.json
    │   ├── matkg_google_gemini-flash-lite_50_20251008_200746.json
    │   ├── matkg_google_gemini-flash-lite_75_20251008_213611.json
    │   ├── matkg_gpt-oss_120b_100_20250925_002056.json
    │   ├── matkg_gpt-oss_120b_25_20250923_213915.json
    │   ├── matkg_gpt-oss_120b_50_20250924_042317.json
    │   ├── matkg_gpt-oss_120b_75_20250924_135625.json
    │   ├── matkg_gpt-oss_20b_100_20251001_115740.json
    │   ├── matkg_gpt-oss_20b_25_20250930_172105.json
    │   ├── matkg_gpt-oss_20b_50_20251001_025118.json
    │   ├── matkg_gpt-oss_20b_75_20251001_115100.json
    │   ├── matkg_lbl_cborg-chat_latest_100_20251008_010852.json
    │   ├── matkg_lbl_cborg-chat_latest_25_20251007_224848.json
    │   ├── matkg_lbl_cborg-chat_latest_50_20251007_232938.json
    │   ├── matkg_lbl_cborg-chat_latest_75_20251008_001702.json
    │   ├── matkg_qwen3_235b_100_20251004_054233.json
    │   ├── matkg_qwen3_235b_147papers.json
    │   ├── matkg_qwen3_235b_25_20251001_120436.json
    │   ├── matkg_qwen3_235b_257papers.json
    │   ├── matkg_qwen3_235b_333papers.json
    │   ├── matkg_qwen3_235b_361papers.json
    │   ├── matkg_qwen3_235b_444papers.json
    │   ├── matkg_qwen3_235b_50_20251002_095006.json
    │   ├── matkg_qwen3_235b_580papers.json
    │   ├── matkg_qwen3_235b_75_20251003_084431.json
    │   └── view_kg.html
    ├── schema
    │   └── matkg_schema.yaml
    └── terminology
        ├── extracted_terms_aug21_147papers.json
        ├── extracted_terms_aug21_257papers.json
        ├── extracted_terms_aug21_333papers.json
        ├── extracted_terms_aug21_361papers.json
        ├── extracted_terms_aug21_444papers.json
        ├── extracted_terms_aug21_580papers.json
        ├── extracted_terms_cp25_deepseek-r1_20250908_201314.json
        ├── extracted_terms_cp25_deepseek-r1_20250908_212738.json
        ├── extracted_terms_cp25_deepseek-r1_20250908_224024.json
        ├── extracted_terms_cp25_deepseek-r1_20250910_113328.json
        ├── extracted_terms_cp50_deepseek-r1_20250912_174500.json
        ├── extracted_terms_cp50_deepseek-r1_20250912_192346.json
        ├── extracted_terms_deepseek-r1_14b_100_20250918_095748.json
        ├── extracted_terms_deepseek-r1_14b_25_20250915_185643.json
        ├── extracted_terms_deepseek-r1_14b_50_20250916_162508.json
        ├── extracted_terms_deepseek-r1_14b_75_20250917_143348.json
        ├── extracted_terms_deepseek-r1_32b_100_20250922_191851.json
        ├── extracted_terms_deepseek-r1_32b_25_20250919_065133.json
        ├── extracted_terms_deepseek-r1_32b_50_20250920_125000.json
        ├── extracted_terms_deepseek-r1_32b_75_20250921_180642.json
        ├── extracted_terms_deepseek-r1_70b_100_20250929_004942.json
        ├── extracted_terms_deepseek-r1_70b_25_20250925_103657.json
        ├── extracted_terms_deepseek-r1_70b_50_20250926_144206.json
        ├── extracted_terms_deepseek-r1_70b_75_20250927_214641.json
        ├── extracted_terms_google_gemini-flash-lite_100_20251008_230232.json
        ├── extracted_terms_google_gemini-flash-lite_25_20251008_185312.json
        ├── extracted_terms_google_gemini-flash-lite_50_20251008_200746.json
        ├── extracted_terms_google_gemini-flash-lite_75_20251008_213611.json
        ├── extracted_terms_gpt-oss_120b_100_20250925_002056.json
        ├── extracted_terms_gpt-oss_120b_25_20250923_213915.json
        ├── extracted_terms_gpt-oss_120b_50_20250924_042317.json
        ├── extracted_terms_gpt-oss_120b_75_20250924_135625.json
        ├── extracted_terms_gpt-oss_20b_100_20250930_160658.json
        ├── extracted_terms_gpt-oss_20b_100_20251001_115740.json
        ├── extracted_terms_gpt-oss_20b_25_20250930_032030.json
        ├── extracted_terms_gpt-oss_20b_25_20250930_172105.json
        ├── extracted_terms_gpt-oss_20b_50_20250930_110510.json
        ├── extracted_terms_gpt-oss_20b_50_20251001_025118.json
        ├── extracted_terms_gpt-oss_20b_75_20250930_160006.json
        ├── extracted_terms_gpt-oss_20b_75_20251001_115100.json
        ├── extracted_terms_lbl_cborg-chat_latest_100_20251008_010852.json
        ├── extracted_terms_lbl_cborg-chat_latest_25_20251007_224848.json
        ├── extracted_terms_lbl_cborg-chat_latest_50_20251007_232938.json
        ├── extracted_terms_lbl_cborg-chat_latest_75_20251008_001702.json
        ├── extracted_terms_qwen3_235b_100_20251004_054233.json
        ├── extracted_terms_qwen3_235b_25_20251001_120436.json
        ├── extracted_terms_qwen3_235b_50_20251002_095006.json
        ├── extracted_terms_qwen3_235b_75_20251003_084431.json
        └── parse_terms.py

20 directories, 213 files
</pre>
<!-- TREE END -->


## Features

Included in this template are a number of helpful things to get you started on the ground running.

### GitHub Actions `.github/workflows/build-app.yml`

Automate linting, pytest, and mkdocs when you push changes to GitHub.

### MkDocs

Create nice documentation with MkDocs and deploy it directly in your repository (Note: Your repository must be set to `public`).

### `.gitignore`

Already configured with a number of common files to ignore.

### `requirements.txt`

List of Python dependencies, such as flake8, pytest, and mkdocs.

### flake8

Lint your Python code for errors with flake8.

### PyTest

Write unit tests with PyTest and they will run when you submit a push to GitHub.

## LBNL Software Disclosure and Distribution

[Here is the official lab policy regarding software disclosure and distribution,](https://commons.lbl.gov/display/rpm2/Software+Disclosure+and+Distribution#SoftwareDisclosureandDistribution--1898802862) and below you will find a summarized version. It is general good practice to keep your projects marked as `private` until you properly disclose your software through the lab.

- **Purpose:**  
  Ensure DOE compliance by reporting all software intended for external distribution to the Intellectual Property Office (IPO).

- **Who Must Comply:**  
  Berkeley Lab software developers and affiliates (employees, faculty, and on-site collaborators).

- **When to Report:**  
  - Before distributing any new or modified software.
  - Exemptions: Already disclosed or minor updates (<25% change without added functionality).

- **Key Requirements:**  
  - **Submission:** Complete a Software Disclosure form prior to external distribution.
  - **Licensing:**  
    - Obtain appropriate license agreements through IPO.
    - Prefer permissive licenses (BSD, MIT) over proprietary or viral open source licenses (e.g., GNU GPL).
  - **Documentation:**  
    - Record third-party licenses, contributor information, and funding sources.
  - **Tracking:**  
    - If distributed via personal repositories or websites, track and report download/licensing metrics annually.

- **IPO Responsibilities:**  
  Review disclosures, secure DOE approvals, manage licensing agreements, and maintain records.

- **Contact:**  
  For questions, reach out to the Licensing Manager at [ipo@lbl.gov](mailto:ipo@lbl.gov).

