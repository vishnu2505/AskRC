# Gap Analysis: Implementation vs. Baseline Spec

**Date**: 2026-09-16
**Spec**: `spec.md` (001-baseline-rag-system)
**Constitution**: `.specify/memory/constitution.md` v1.0.0
**Scope**: All code on `main` as of commit at time of writing.

This document records where the existing implementation does not satisfy the retrofitted baseline
spec. Each gap cites the requirement it violates and the file that violates it. Gaps are ordered by
severity. Nothing here has been changed yet — this is the input to the next specs.

Severity key: **S1** breaks a core guarantee · **S2** degrades quality or operability · **S3**
maintainability and hygiene.

---

## S1 — Breaks a core guarantee

### G-01 · Pipeline is not idempotent; every run duplicates the entire corpus

**Violates**: FR-009, FR-031, Constitution III (idempotent tasks), II (stable identifiers)
**Files**: [src/data_pipeline/preprocess.py:117](src/data_pipeline/preprocess.py#L117),
[dags/datapipeline_airflow.py:55](dags/datapipeline_airflow.py#L55),
[src/data_pipeline/index_data.py](src/data_pipeline/index_data.py)

`preprocess_text_file` assigns `base_id = str(uuid.uuid4())` on every invocation. The same source
page therefore produces a different document ID and a different output filename on every pipeline
run. Consequences chain downstream:

- Blob upload names each file by its fresh UUID, so `overwrite=True` never actually overwrites — the
  container accumulates a full copy of the corpus per run.
- The indexing task walks *every* blob in the container and uploads each as a new document keyed by
  its unique ID, so the search index accumulates duplicates without bound.

The DAG runs `@daily`. After N days the index holds roughly N copies of every document. Retrieval
requests the top 8 results, so as duplicates accumulate the result set converges on 8 copies of the
same passage — effective context collapses toward a single document.

This is the highest-priority defect in the system: it silently degrades answer quality over time
and inflates storage and indexing cost linearly.

### G-02 · Generation failure is presented to the user as a relevance problem

**Violates**: FR-020, Edge Cases
**Files**: [src/model/get_model_response.py:52](src/model/get_model_response.py#L52),
[app.py:48](app.py#L48)

When retries are exhausted, `get_openai_response` returns the *string* `"Request failed after
multiple attempts due to rate limit or API issues."` rather than raising. That string flows into
bias screening and then into `key_concept_match`, which compares it against the retrieved context,
finds almost no overlap, and fails. The user is told **"The question lacks sufficient contextual
relevance."**

The user is told their question was bad when in fact the model API was unavailable. An alert fires
with the wrong category, so the outage is also misdiagnosed in monitoring.

### G-03 · Question screening rejects ordinary technical questions

**Violates**: FR-023, Constitution VI
**File**: [src/evaluation/user_question_bias.py:76](src/evaluation/user_question_bias.py#L76)

Two compounding faults:

1. Sentiment is scored **per word**. For a single-word input, VADER's negative ratio is `1.0` for
   any word carrying negative valence — including neutral-in-context words like "problem",
   "crash", "kill", "denied", "wrong". The `> 0.95` threshold therefore fires on a large fraction
   of genuine questions ("I have a *problem* submitting a job", "my job was *killed*").
2. The `technical_terms` exemption list is checked *after* the question is lowercased
   (`word_tokenize(modified_question.lower())`), but the set contains `"SSH"` and `"passwordless"`
   in original case. `"ssh"` never matches `"SSH"`, so the exemption for SSH silently does nothing.

Net effect: legitimate questions are refused with a rephrase suggestion and never reach retrieval.
This is a direct hit to the primary user story.

### G-04 · Alert dispatch can crash the request it is reporting on

**Violates**: FR-036
**File**: [src/model/alerts.py:12](src/model/alerts.py#L12)

`send_slack_alert` posts to `slack_webhook_url` with no guard. If `SLACK_WEBHOOK_URL` is unset,
`requests.post(None, ...)` raises `MissingSchema`. `app.py` calls this inside the answer flow
without a try/except, so a missing webhook turns a *successfully handled* quality warning into an
unhandled exception and a Streamlit traceback shown to the user.

### G-05 · Deployment dependency set is incompatible with the model code

**Violates**: FR-045 (local/deployed parity), Constitution: Technology Constraints
**Files**: [requirements.txt:9](requirements.txt#L9),
[minimal-requirements.txt](minimal-requirements.txt), [Dockerfile:28](Dockerfile#L28)

`requirements.txt` pins `openai==0.28`, which matches the code's use of `openai.ChatCompletion` and
`openai.error`. `minimal-requirements.txt` pins `openai==1.54.4`, where both of those were removed —
`import openai.error` raises `ModuleNotFoundError` at import time.

The Dockerfile installs `requirements.txt`, so the Airflow image is consistent. Any environment
built from `minimal-requirements.txt` — which its name and contents suggest is the Azure Web App
deployment — cannot import `src.model.get_model_response` at all. Two requirements files that
disagree on a breaking major version is a parity failure regardless of which one is currently in use.

---

## S2 — Degrades quality or operability

### G-06 · Preprocessing destroys the signal the retriever needs

**Violates**: SC-002 (implicitly); documented as FR-006/FR-007 but harmful as specified
**File**: [src/data_pipeline/preprocess.py:36](src/data_pipeline/preprocess.py#L36)

`clean_text` strips **all digits** (`[^a-zA-Z\s]`) and removes English stopwords from indexed
content. For HPC documentation this is severe: `--nodes=4`, `32GB`, `gpu-v100`, partition names,
version numbers, and flags are erased. Command syntax becomes unrecoverable.

Worse, the asymmetry: the **user's question is not cleaned the same way**. Questions keep their
stopwords, digits, and punctuation, while the index contains neither. Lexical search is matching
two different text distributions against each other.

The spec records this as current behavior (FR-006/FR-007), but it should be treated as a defect to
be revisited in a dedicated retrieval-quality spec, not as settled design.

### G-07 · No provenance; answers cannot be traced to a source page

**Violates**: FR-005, Constitution II
**File**: [src/data_pipeline/preprocess.py:113](src/data_pipeline/preprocess.py#L113)

Processed documents are written as `{"id", "content"}` only. The source URL is discarded during
preprocessing, so no indexed document can be traced back to the page it came from. The chatbot
therefore cannot cite sources, and a maintainer cannot verify a suspicious answer against the
documentation. For a RAG system whose entire value proposition is traceability, this is a
structural omission rather than a missing nicety.

### G-08 · Response bias screening is effectively inert

**Violates**: FR-024 (satisfied nominally, not in substance)
**File**: [src/evaluation/model_response_bias.py:79](src/evaluation/model_response_bias.py#L79)

Unlike the per-word question check, the response check scores the **entire response** and flags only
when `neg > 0.95`. A multi-sentence answer cannot realistically reach that ratio; VADER's negative
component is diluted across all tokens. The threshold is unreachable in practice, so the check
passes everything. The guardrail exists in the code and in the README but does not function.

Note also that `gender_neutral_map` maps `her → their` in the question path but `her → them` in the
response path, and the module defines `sia`, the map, and its imports **twice**.

### G-09 · Metrics logging writes through a shared module-global and can log the wrong data

**Violates**: FR-032, FR-033, Constitution V
**File**: [src/config/mlflow_config.py:13](src/config/mlflow_config.py#L13)

`add_metric` executes `global dict` and assigns the instance's metrics to a module-level name that
**shadows the `dict` builtin**. `log_all` then logs that global rather than `self.metrics`.

Four separate modules each instantiate their own `MetricsCollector`, but they all write to and read
from the one shared global. Whichever collector called `add_metric` last determines what
`log_all` sends to MLflow — metrics from other collectors are lost. If `log_all` runs before any
`add_metric`, the global is still the builtin type and `mlflow.log_metrics(dict)` raises a
`TypeError`, which the bare `except` swallows into a printed message.

The tracking URI is additionally hardcoded to `http://127.0.0.1:8080`, so no metric reaches a
tracking server in any deployed environment.

Practical result: the observability required to diagnose G-01 and G-06 is not actually working.

### G-10 · Empty retrieval results are passed to the model as an empty context

**Violates**: FR-017, FR-018, Edge Cases ("retrieval returns nothing")
**File**: [src/model/retrive_azure_index.py:22](src/model/retrive_azure_index.py#L22)

```python
context = "\n\n".join([...]) if results else "No relevant information found."
```

`results` is a `SearchItemPaged` object, which is always truthy — the fallback branch is
unreachable. When the search returns zero documents, the join produces `""` and the model receives a
prompt with an empty `<context>` block. The instruction not to guess is the only thing standing
between that and a fabricated answer.

There is also no exception handling around `search_client.search`, so a search outage surfaces as a
raw traceback in the UI rather than the error state the spec requires.

### G-11 · Continuous integration does not exist

**Violates**: FR (Test-Gated Changes), Constitution IV
**Evidence**: no `.github/` directory in the repository

`README.md` §5.5 states that "GitHub Actions automate the testing process." There is no workflow
file anywhere in the repo. The `Testing/` suite exists but nothing runs it on push or pull request,
so the constitutional gate "full suite MUST pass in CI before merge" is currently unenforceable.

### G-12 · Generation model is hardcoded

**Violates**: FR-021, Constitution: Technology Constraints
**File**: [src/model/get_model_response.py:34](src/model/get_model_response.py#L34)

`model="gpt-4-turbo"` is a literal at the call site. Changing models — for cost, latency, or
quality — requires a code edit and redeploy. `max_tokens=1024` and the retry parameters are
likewise fixed at the call site.

### G-13 · Thresholds are undocumented magic numbers

**Violates**: FR-027, Constitution VI
**Files**: [src/evaluation/answer_validation.py:27](src/evaluation/answer_validation.py#L27),
[src/evaluation/user_question_bias.py:80](src/evaluation/user_question_bias.py#L80),
[src/evaluation/model_response_bias.py:79](src/evaluation/model_response_bias.py#L79)

`threshold = 7` (key-concept overlap), `0.95` (question negativity), `0.95` (response negativity),
`MAX_TERM_SIZE = 20000`, `32766` (index-time size check), and `top=8` (retrieval depth) are all
inline literals. The overlap threshold carries the comment "Adjust this value based on
experimentation with the dataset," but no experiment is recorded. None of them are configurable and
none have a documented rationale.

Note that key-concept overlap counts **set intersection of tokens** — it scales with answer length,
so a long answer passes more easily than a short precise one, independent of correctness.

---

## S3 — Maintainability and hygiene

### G-14 · Inconsistent import strategy breaks module use outside Airflow

**Files**: [src/data_pipeline/azure_uploader.py:10](src/data_pipeline/azure_uploader.py#L10),
[src/data_pipeline/preprocess.py:9](src/data_pipeline/preprocess.py#L9)

`azure_uploader.py` does `from config.mlflow_config import *` — an absolute import that only
resolves when `/opt/airflow/src` is on `sys.path` (set by the DAG). Importing
`src.data_pipeline.azure_uploader` from the repository root fails. `preprocess.py` works around the
same class of problem with a `try/except ImportError` that substitutes a **mock uploader** in the
real code path — a test double living in production code, silently active whenever the import
layout is wrong.

Wildcard imports (`import *`) are used in four modules, obscuring what each actually depends on.

### G-15 · Container-only path hardcoded into a library module

**File**: [src/evaluation/user_question_bias.py:3](src/evaluation/user_question_bias.py#L3)

`nltk.data.path.append('/app/nltk_data')` and a later `nltk.download(..., download_dir='/app/nltk_data')`
hardcode a container path into an importable module. Locally this is a no-op at best and a
permission error at worst. NLTK resource bootstrapping is duplicated across three modules with
different resource lists.

### G-16 · Metrics are flushed on every Streamlit rerun

**File**: [app.py:65](app.py#L65)

`collector.log_all()` is called after `main()` returns. Streamlit re-executes the whole script on
every widget interaction, so `log_all` fires on reruns where no question was asked — creating empty
MLflow runs — and the `collector` in `app.py` is a *different instance* from the ones inside the
evaluation modules that actually recorded metrics (see G-09).

### G-17 · Dead and commented-out code carried in the repository

**Files**: [dags/response_generation_pipeline.py](dags/response_generation_pipeline.py) (entire file
commented out), [src/model/alerts.py:20](src/model/alerts.py#L20) (`main()` with a hardcoded sample
question), [src/data_pipeline/azure_uploader.py:30](src/data_pipeline/azure_uploader.py#L30),
[app.py:32](app.py#L32), duplicated blocks in `model_response_bias.py`.

`azure_uploader.py` also computes `blob_version` and records it as a metric on every upload, but the
value is never used for anything — blobs are still named by the caller-supplied filename.

### G-18 · Two scrapers, unclear ownership

**Files**: [src/data_pipeline/scrape.py](src/data_pipeline/scrape.py),
[src/data_pipeline/scraper.py](src/data_pipeline/scraper.py)

Both modules exist. The DAG imports `scraper`. The role of `scrape.py` is undocumented.

### G-19 · Week-based scraping schedule is coupled to a fixed start date

**File**: [src/data_pipeline/scraper.py:31](src/data_pipeline/scraper.py#L31)

Sections are scraped "up to the current week," computed from a hardcoded start date, and capped at
11. This was presumably a course-demo device to show incremental ingestion. In steady state it means
the corpus is permanently complete and the week calculation is vestigial — but it still runs, and its
behavior past week 11 (always scrape everything, daily) is the real schedule. Worth making explicit
rather than implicit.

---

### G-20 · README describes a system that was designed but not built

**Violates**: Constitution — documentation must not contradict the implementation
**Files**: [README.md](README.md) §2.2, §2.3, §5.5

Three claims in the README are not true of the code:

1. *"Data will be segmented, encoded into embeddings, and stored for efficient retrieval by the RAG
   model."* There are no embeddings anywhere in the repository. `data/embeddings/` contains only a
   `.gitkeep`. Retrieval is `search_text=query` — lexical keyword matching. No vector field, no
   embedding model, no embedding call.
2. *"Documents: HTML pages, PDF files, and other hosted resources."* The scraper handles HTML only.
   No PDF extraction exists.
3. *"Continuous Integration: GitHub Actions automate the testing process."* Covered separately as
   G-11 — no workflow file exists.

This matters beyond tidiness. Anyone reading the README — a reviewer, a collaborator, a future
maintainer — will reason about the system as a dense-retrieval RAG pipeline over mixed document
types, and every conclusion they draw will be wrong. The fix is to describe what exists and move the
rest to a roadmap section.

## Summary

| Severity | Count | IDs |
|----------|-------|-----|
| S1 | 5 | G-01 … G-05 |
| S2 | 8 | G-06 … G-13 |
| S3 | 7 | G-14 … G-20 |

**Requirements not met by current implementation**: FR-005, FR-009, FR-017, FR-018, FR-020, FR-021,
FR-023, FR-024, FR-027, FR-031, FR-032, FR-033, FR-036, FR-045.

**Constitution principles currently violated**: II (lineage, stable IDs), III (idempotency), IV (CI
gate), V (observability), VI (documented thresholds).

### Recommended spec sequence

1. **002 — Corpus idempotency and provenance** — fixes G-01 and G-07 together, since both hinge on
   replacing the random identifier with a content- or URL-derived stable ID. Highest value.
2. **003 — Honest failure modes** — G-02, G-04, G-10: distinguish API failure, retrieval failure,
   and genuine low relevance, and make alerting non-fatal.
3. **004 — Trustworthy screening and validation** — G-03, G-08, G-13: fix the false-positive
   question gate, make the response gate functional, and give every threshold a name and rationale.
4. **005 — Retrieval quality** — G-06: revisit preprocessing, align query and document processing,
   and establish an evaluation set (resolves the SC-002/SC-003 clarifications).
5. **006 — CI and working observability** — G-11, G-09, G-16: real GitHub Actions workflow and a
   metrics collector that records what it claims to.
6. **007 — Configuration and packaging hygiene** — G-05, G-12, G-14, G-15, G-17, G-18, G-19, G-20.
7. **008 — Modern retrieval** — structure-aware chunking, retrieval that works when question and
   page share no vocabulary, ordering by relevance, and an evaluation harness. Blocked on 002 (a
   chunking change needs stable identity and the processing-rules version) and on 005 (structure
   cannot be chunked once cleaning has destroyed it, and nothing here is measurable without the
   evaluation set). Spec: [008-modern-retrieval](../008-modern-retrieval/spec.md).
