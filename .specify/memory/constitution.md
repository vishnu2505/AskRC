# AskRC Constitution

AskRC is a Retrieval-Augmented Generation assistant over Northeastern University Research
Computing's public documentation. This constitution governs every change to the data pipeline,
the retrieval and generation path, the evaluation layer, and the deployed application.

## Core Principles

### I. Grounded Answers Only (NON-NEGOTIABLE)

Every answer shown to a user MUST be derived from documents retrieved from the indexed corpus.

- The generation step MUST receive retrieved context and MUST be instructed to decline rather
  than guess when the context does not contain the answer.
- An answer that fails the relevance gate MUST NOT be presented as an authoritative answer; the
  user MUST be told the question lacks sufficient context.
- The model MUST NOT be given the user's raw question without retrieval, and retrieval MUST NOT
  be silently skipped on error — a retrieval failure is a user-visible failure, not an
  unretrieved answer.
- Any change that weakens or bypasses the relevance gate is a breaking change and requires an
  explicit amendment to this section.

Rationale: users are researchers making operational decisions about cluster access, storage,
and job submission. A fluent wrong answer costs more than a refusal.

### II. Reproducible Data Lineage

Raw and processed data MUST be reproducible from a commit plus a DVC revision.

- `data/raw` and `data/processed` MUST remain DVC-tracked. Data files MUST NOT be committed to
  git directly.
- Preprocessing MUST be deterministic given the same input: the same source document MUST yield
  the same cleaned text and the same chunk boundaries.
- Every indexed document MUST carry a stable identifier and MUST be traceable back to the source
  URL it was scraped from.
- Schema or chunking changes MUST be versioned; a change to chunking requires a full reindex, not
  an in-place partial update.

Rationale: retrieval quality regressions are untraceable unless the corpus that produced them can
be reconstructed exactly.

### III. Pipeline-First Automation

Ingestion work MUST run as orchestrated, idempotent Airflow tasks — never as manual scripts.

- The pipeline stages are scrape → preprocess → upload → index, in that order, with explicit task
  dependencies.
- Every task MUST be idempotent: re-running it on unchanged input MUST NOT duplicate documents in
  blob storage or the search index.
- A task MUST fail loudly. Catching an exception to `print()` and continuing is permitted only for
  per-document skips that are counted and reported; it is forbidden for stage-level failures.
- Any operation a developer performs by hand more than twice MUST be promoted into the DAG.

Rationale: the corpus tracks a live documentation site. Freshness depends on unattended runs.

### IV. Test-Gated Changes

No change merges without automated verification proportional to its risk.

- New modules in `src/` MUST ship with `pytest` tests in `Testing/`.
- Tests MUST NOT require live Azure or OpenAI credentials; external services MUST be mocked at the
  client boundary so the suite runs in CI and offline.
- Retrieval, validation, and bias logic MUST have tests covering the negative case, not only the
  happy path.
- The full suite MUST pass in CI before merge. A failing test is fixed or explicitly quarantined
  with a linked issue — never deleted to make CI green.

### V. Observability and Alerting

The system MUST be diagnosable after the fact, without reproducing the user's session.

- Per-request signals (retrieval size, validation scores, thresholds, bias scores) MUST be logged
  to MLflow under the project experiment.
- Every threshold that gates user-visible behavior MUST be logged alongside the value it gated, so
  a decision can be explained later.
- Failures that degrade answer quality — pipeline task failures, bias flags, and context-relevance
  failures — MUST raise an alert to the team channel or on-call email.
- Alerts MUST be actionable: type, message, and enough context to locate the triggering run.

### VI. Secure and Responsible by Default

- Secrets MUST come from environment variables or a managed secret store. Credentials, keys,
  endpoints, and webhook URLs MUST NEVER be committed, logged, or embedded in prompts.
- Scraping MUST stay within the public Research Computing documentation domain, respect crawl
  depth limits, and collect no personal or student data. FERPA compliance is mandatory.
- User questions and model responses MUST pass bias screening before use and display
  respectively; gendered terms are normalized to neutral forms.
- Bias and validation thresholds MUST be named constants with a documented rationale, not
  unexplained literals scattered through the code.

## Technology and Infrastructure Constraints

The following are fixed for this project. Deviating requires a constitution amendment.

- **Language**: Python 3.10+.
- **Retrieval**: Azure Cognitive Search (index `askrcindex`). Documents MUST respect the Azure
  Search term-size limit; oversized content is split upstream, never truncated at index time.
- **Storage**: Azure Blob Storage (container `preprocessed-data`), authenticated via Entra ID
  service principal credentials.
- **Generation**: OpenAI chat completions. The model identifier MUST be configurable, not
  hardcoded at the call site.
- **Orchestration**: Apache Airflow, daily schedule, with retries and failure email configured.
- **Experiment tracking**: MLflow.
- **Data versioning**: DVC.
- **Interface**: Streamlit, deployed to Azure Web App.
- **Packaging**: Docker / docker-compose for local and deployed parity.

## Development Workflow and Quality Gates

All work follows Spec-Driven Development using Spec Kit:

1. `/speckit-specify` — write the feature specification (WHAT and WHY, never HOW).
2. `/speckit-clarify` — resolve ambiguities before planning.
3. `/speckit-plan` — produce the technical plan, checked against this constitution.
4. `/speckit-tasks` — break the plan into ordered, verifiable tasks.
5. `/speckit-analyze` — confirm spec, plan, and tasks agree.
6. `/speckit-implement` — execute the tasks.

Gates:

- A plan that violates a principle MUST document the violation and its justification in the plan's
  Complexity Tracking section, or be revised. Silent violations are rejected in review.
- Specs MUST contain no implementation detail. Plans MUST contain no unspecified requirements.
- Every functional requirement MUST be independently testable and MUST have at least one acceptance
  scenario.
- `[NEEDS CLARIFICATION]` markers MUST be resolved before implementation begins.

## Governance

- This constitution supersedes ad-hoc practice and prior convention in the repository.
- Amendments require: a written rationale, a version bump per the policy below, and an update to
  any spec, plan, or template that the amendment invalidates.
- Versioning policy: **MAJOR** for removing or redefining a principle in a backward-incompatible
  way; **MINOR** for adding a principle or materially expanding guidance; **PATCH** for
  clarifications and wording that do not change meaning.
- All pull requests MUST be reviewed for compliance with these principles. Added complexity MUST
  be justified against the simpler alternative that was rejected.
- Agent-specific runtime guidance lives in `CLAUDE.md`; it elaborates on this constitution and
  MUST NOT contradict it.

**Version**: 1.0.0 | **Ratified**: 2026-09-16 | **Last Amended**: 2026-09-16
