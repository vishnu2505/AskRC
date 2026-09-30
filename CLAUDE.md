# AskRC — Agent Guidance

RAG assistant over Northeastern Research Computing's public documentation.

**Read [`.specify/memory/constitution.md`](.specify/memory/constitution.md) before any change.** It
governs this repository and supersedes habit or convention found in existing code.

## Workflow: Spec-Driven Development

All work goes through Spec Kit. Do not write implementation code before a spec and plan exist.

| Step | Command | Output |
|------|---------|--------|
| 1 | `/speckit-specify` | `specs/NNN-name/spec.md` — WHAT and WHY only |
| 2 | `/speckit-clarify` | resolved `[NEEDS CLARIFICATION]` markers |
| 3 | `/speckit-plan` | `plan.md` — HOW, checked against the constitution |
| 4 | `/speckit-tasks` | `tasks.md` — ordered, verifiable work items |
| 5 | `/speckit-analyze` | consistency report across the three |
| 6 | `/speckit-implement` | code |

Specs contain no implementation detail. Plans introduce no unspecified requirements.

## Current state

- [`specs/001-baseline-rag-system/spec.md`](specs/001-baseline-rag-system/spec.md) — retrofitted
  baseline describing what the existing system is meant to do.
- [`specs/001-baseline-rag-system/gap-analysis.md`](specs/001-baseline-rag-system/gap-analysis.md) —
  20 recorded gaps between that spec and the code on `main`, with a recommended spec sequence.
- [`specs/002-corpus-idempotency-provenance/spec.md`](specs/002-corpus-idempotency-provenance/spec.md) —
  **active feature.** Spec written, 3 of 5 clarifications resolved. Needs `/speckit-clarify` to
  finish, then `/speckit-plan`.
- [`specs/008-modern-retrieval/spec.md`](specs/008-modern-retrieval/spec.md) — written ahead of its
  turn for roadmap purposes. **Blocked on 002 and 005.** Do not plan or implement it before both
  have shipped.

`.specify/feature.json` points at the active feature (currently 002). Downstream Spec Kit commands
read it, so re-point it deliberately rather than by accident.

New specs must not contradict the baseline. Extending it is expected; changing it requires editing
the baseline in the same change.

## Architecture

```
rc-docs.northeastern.edu
   └─ scrape (src/data_pipeline/scraper.py, get_all_url.py)
        └─ preprocess (preprocess.py) → clean, stopword-strip, chunk, JSON
             └─ upload (azure_uploader.py) → Azure Blob "preprocessed-data"
                  └─ index (index_data.py) → Azure Cognitive Search "askrcindex"

user question (app.py, Streamlit)
   └─ screen question (evaluation/user_question_bias.py)
        └─ retrieve (model/retrive_azure_index.py, top 8)
             └─ prompt (model/system_prompt.py)
                  └─ generate (model/get_model_response.py)
                       └─ screen response (evaluation/model_response_bias.py)
                            └─ validate grounding (evaluation/answer_validation.py)
                                 └─ display, or refuse + alert (model/alerts.py)
```

Ingestion runs daily via Airflow: [`dags/datapipeline_airflow.py`](dags/datapipeline_airflow.py),
tasks `scrape → preprocess → blob_storage → index`.

## Stack

Python 3.10+ · Azure Blob Storage + Azure Cognitive Search · OpenAI (pinned `openai==0.28`, legacy
API — see gap G-05) · Airflow 2.7 · MLflow · DVC · Streamlit · Docker.

## Rules that are easy to get wrong here

- **Never commit data.** `data/raw` and `data/processed` are DVC-tracked.
- **Never commit secrets.** Everything comes from the environment. Check before staging.
- **Tests must run without cloud or model credentials.** Mock at the client boundary.
- **Never weaken the grounding gate** in `answer_validation.py` to make an answer appear. Withholding
  is the correct behavior — a fluent wrong answer about cluster operations is worse than a refusal.
- **Thresholds get names and rationales**, not inline literals.
- **Per-document skips may be logged and counted; stage-level failures must raise.**
- The repository contains known defects catalogued in the gap analysis. Do not imitate existing
  patterns without checking whether that pattern is one of them.

## Commands

```bash
pytest Testing/                          # test suite
streamlit run app.py                     # UI locally
docker-compose up                        # Airflow + services
python -m src.data_pipeline.main         # scrape only
dvc pull                                 # restore tracked data
```
