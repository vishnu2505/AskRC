# Feature Specification: AskRC Baseline RAG System

**Feature Branch**: `001-baseline-rag-system`

**Created**: 2026-09-16

**Status**: Draft (retrofit of existing implementation)

**Input**: Baseline specification for the existing AskRC RAG chatbot: scrape, preprocess, index, retrieve, generate, validate.

## Context

This specification is a *retrofit*. AskRC already exists as working code on `main`. This document
states, as verifiable requirements, the behavior that implementation is meant to deliver. It serves
three purposes:

1. It becomes the reference for judging whether the current code is correct.
2. It anchors every future feature spec, which may extend but not silently contradict it.
3. It surfaces where the current behavior is underspecified — marked `[NEEDS CLARIFICATION]` and
   resolved via `/speckit-clarify` before any plan depends on them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Researcher Gets a Grounded Answer (Priority: P1)

A researcher at Northeastern needs to know how to do something on the research computing cluster —
request GPU resources, transfer data, submit a Slurm job. Instead of browsing documentation or
opening a support ticket, they type the question into AskRC and receive a direct answer drawn from
the official Research Computing documentation.

**Why this priority**: This is the product. Every other story exists to make this one trustworthy.
Without it there is no value delivered at all.

**Independent Test**: With a populated search index, submit a question whose answer appears in the
documentation and confirm the response is relevant, factually consistent with the source material,
and returned in a single interaction.

**Acceptance Scenarios**:

1. **Given** a populated index and a question answerable from the documentation, **When** the user
   submits the question, **Then** the system returns an answer grounded in retrieved documentation
   content.
2. **Given** a question with no supporting content in the corpus, **When** the user submits it,
   **Then** the system tells the user the question lacks sufficient contextual relevance rather
   than producing a speculative answer.
3. **Given** a submitted question, **When** the system is working, **Then** the user sees a
   progress indicator until the answer or the refusal is displayed.
4. **Given** the retrieval service is unreachable, **When** the user submits a question, **Then**
   the user is shown an error state and no answer is fabricated.

---

### User Story 2 - Answers Stay Current With the Documentation (Priority: P1)

The Research Computing documentation site changes as services change. A maintainer needs the
chatbot's knowledge to track those updates automatically, without anyone running scripts by hand.

**Why this priority**: A RAG system over stale content gives confidently wrong operational advice.
Freshness is a correctness requirement, not a convenience.

**Independent Test**: Trigger the ingestion pipeline end to end and verify that content published on
the documentation site becomes retrievable through the chatbot without manual intervention.

**Acceptance Scenarios**:

1. **Given** the scheduled pipeline run, **When** it executes, **Then** documentation content is
   scraped, cleaned, stored, and indexed in that order, each stage running only after the previous
   one succeeds.
2. **Given** a pipeline run over content already ingested by a previous run, **When** it completes,
   **Then** the index contains no duplicate documents for that content.
3. **Given** a stage of the pipeline fails, **When** the failure occurs, **Then** downstream stages
   do not run and the team is alerted.
4. **Given** a single source document is malformed, **When** the pipeline processes the batch,
   **Then** that document is skipped and counted, and the remaining documents are still processed.

---

### User Story 3 - Unsupported Answers Are Withheld (Priority: P1)

Before any answer reaches the user, the system checks that the answer is actually supported by the
retrieved documentation. Answers that are not sufficiently grounded are withheld and the team is
alerted.

**Why this priority**: This is the guardrail that makes Story 1 safe to ship. It is the difference
between an assistant and a plausible-sounding liability.

**Independent Test**: Feed the validation component an answer that shares little substance with its
retrieved context and confirm the answer is rejected; feed it a well-grounded answer and confirm
it passes.

**Acceptance Scenarios**:

1. **Given** a generated answer whose key concepts substantially overlap the retrieved context,
   **When** validation runs, **Then** the answer is released to the user.
2. **Given** a generated answer whose key concepts do not sufficiently overlap the retrieved
   context, **When** validation runs, **Then** the answer is withheld, the user is told the
   question lacks contextual relevance, and an alert is raised.
3. **Given** any validation decision, **When** it is made, **Then** both the measured value and the
   threshold it was compared against are recorded for later review.

---

### User Story 4 - Biased or Hostile Language Is Screened (Priority: P2)

Questions are screened before retrieval and responses are screened before display. Gendered terms
are normalized to neutral equivalents, and strongly negative language is flagged.

**Why this priority**: Required for responsible deployment on university infrastructure, but the
system still delivers its core value if screening is tuned rather than absent.

**Independent Test**: Submit a question containing gendered pronouns and confirm they are
normalized; submit strongly hostile phrasing and confirm the user receives a rephrase suggestion
instead of an answer.

**Acceptance Scenarios**:

1. **Given** a question containing gendered pronouns, **When** it is screened, **Then** the
   pronouns are replaced with neutral equivalents before retrieval.
2. **Given** a question flagged as strongly negative, **When** it is screened, **Then** the user
   receives a suggestion to rephrase and no retrieval or generation occurs.
3. **Given** a model response flagged for bias, **When** it is screened, **Then** the user is shown
   a warning alongside the answer and an alert is raised to the team.
4. **Given** a question containing technical vocabulary that reads as negative in ordinary English
   — "error", "failed", "issue" — **When** it is screened, **Then** it is NOT flagged.

---

### User Story 5 - Maintainers Can Diagnose Quality Regressions (Priority: P2)

When answer quality degrades, a maintainer needs to determine what changed — retrieval returning
less context, validation thresholds rejecting more answers, a pipeline run that indexed fewer
documents — without reproducing the user's session.

**Why this priority**: Operability. The system can run without it, but cannot be improved without it.

**Independent Test**: Exercise the question-answering path and confirm that retrieval size,
validation measurements, thresholds, and bias scores are queryable afterward from the tracking
system.

**Acceptance Scenarios**:

1. **Given** a completed question-answering interaction, **When** a maintainer inspects the
   tracking system, **Then** they find the metrics recorded for that interaction.
2. **Given** a pipeline task failure, **When** it occurs, **Then** an email alert is dispatched to
   the configured recipients.
3. **Given** a bias flag or a context-relevance failure, **When** it occurs, **Then** an alert is
   dispatched to the team channel identifying the alert type and the triggering detail.

---

### User Story 6 - Corpus State Is Reproducible (Priority: P3)

A maintainer investigating a regression can reconstruct exactly which corpus produced a given
answer, by checking out a commit and restoring the matching data revision.

**Why this priority**: Valuable for debugging and required for defensible evaluation, but the
system serves users without it.

**Independent Test**: From a clean checkout at a past commit, restore the tracked data and confirm
the raw and processed corpora match what that commit referenced.

**Acceptance Scenarios**:

1. **Given** a commit, **When** a maintainer restores tracked data at that revision, **Then** the
   raw and processed data match the state referenced by that commit.
2. **Given** the same source document processed twice, **When** preprocessing runs, **Then** the
   cleaned text and chunk boundaries are identical both times.

---

### Edge Cases

- **Empty question**: user submits with an empty input field. [NEEDS CLARIFICATION: current
  behavior is unspecified — should the system reject with a prompt, or attempt retrieval?]
- **Oversized document**: a cleaned document exceeds the search backend's term-size limit. It MUST
  be split upstream during preprocessing so that no content is silently dropped at index time.
- **Empty stored document**: a stored file contains no content. It MUST be skipped with a warning
  and MUST NOT halt the indexing stage.
- **Generation service rate-limited**: the answer request is retried with backoff; if retries are
  exhausted, the user MUST be shown a failure state distinguishable from a low-relevance refusal.
  [NEEDS CLARIFICATION: current implementation returns a failure string that flows into validation
  as if it were an answer.]
- **Retrieval returns nothing**: no documents match the question. The system MUST treat this as
  insufficient context rather than prompting the generator with an empty context block.
- **Documentation site unreachable during scraping**: the scrape stage fails and downstream stages
  MUST NOT run against a partial corpus.
- **Concurrent users**: multiple people ask questions simultaneously. [NEEDS CLARIFICATION: metrics
  are collected in a process-level collector; per-user attribution under concurrency is
  unspecified.]

## Requirements *(mandatory)*

### Functional Requirements

#### Data Acquisition

- **FR-001**: System MUST scrape content from the Northeastern Research Computing public
  documentation site, covering the defined documentation sections.
- **FR-002**: System MUST follow links recursively within the documentation domain up to a bounded
  depth, and MUST NOT follow links outside that domain.
- **FR-003**: System MUST NOT revisit a URL it has already visited within a single scrape run.
- **FR-004**: System MUST organize scraped content into a structured directory layout that
  preserves which section each document came from.
- **FR-005**: System MUST record the source URL for each scraped document so any indexed content
  can be traced back to its origin.

#### Preprocessing

- **FR-006**: System MUST normalize scraped text by lowercasing, removing markup, removing
  non-alphabetic characters, and collapsing whitespace.
- **FR-007**: System MUST remove common English stopwords from document text.
- **FR-008**: System MUST split any cleaned document that exceeds the maximum permitted term size
  into parts that each fall within the limit.
- **FR-009**: System MUST assign every processed document a unique, stable identifier; split parts
  of one source document MUST share a common base identifier and be individually addressable.
- **FR-010**: System MUST produce identical output for identical input across runs.

#### Storage and Indexing

- **FR-011**: System MUST upload processed documents to the configured object-storage container
  using service-principal credentials supplied through the environment.
- **FR-012**: System MUST index stored documents into the configured search index.
- **FR-013**: System MUST skip and warn on empty documents, documents with invalid structure, and
  documents whose content exceeds the search backend's term-size limit, without aborting the run.
- **FR-014**: System MUST report, per document, whether indexing succeeded or failed and why.
- **FR-015**: System MUST fail the indexing stage loudly if required credentials are absent.

#### Retrieval and Generation

- **FR-016**: System MUST retrieve the most relevant documents for a user question from the search
  index, bounded to a fixed number of results.
- **FR-017**: System MUST assemble retrieved document content into a single context block supplied
  to the generation step.
- **FR-018**: System MUST instruct the generation model to answer only from the supplied context
  and to avoid guessing when the context is insufficient.
- **FR-019**: System MUST retry generation on rate-limit errors with a delay between attempts, up
  to a bounded number of attempts.
- **FR-020**: System MUST surface generation failure to the user as a failure, distinguishable from
  a low-relevance refusal.
- **FR-021**: The generation model identifier MUST be configurable without a code change.

#### Validation and Screening

- **FR-022**: System MUST screen every user question for biased or hostile language before
  retrieval, normalizing gendered terms and flagging strongly negative language.
- **FR-023**: System MUST NOT flag recognized technical vocabulary as negative language.
- **FR-024**: System MUST screen every generated response for biased language before display.
- **FR-025**: System MUST validate that a generated answer's key concepts are sufficiently present
  in the retrieved context before displaying it as an answer.
- **FR-026**: System MUST withhold answers that fail validation and inform the user the question
  lacks sufficient contextual relevance.
- **FR-027**: All screening and validation thresholds MUST be named, documented constants.

#### Orchestration

- **FR-028**: System MUST run the ingestion pipeline on a daily schedule without manual
  intervention.
- **FR-029**: Pipeline stages MUST execute in dependency order: scrape → preprocess → upload →
  index.
- **FR-030**: Pipeline tasks MUST retry on failure a bounded number of times before being marked
  failed.
- **FR-031**: Pipeline tasks MUST be idempotent: re-running over unchanged input MUST NOT create
  duplicate stored or indexed documents.

#### Observability

- **FR-032**: System MUST record per-interaction metrics — retrieved context size, validation
  measurements, applied thresholds, and bias scores — to the experiment-tracking system.
- **FR-033**: System MUST record the threshold alongside every measurement that gated user-visible
  behavior.
- **FR-034**: System MUST dispatch an alert to the team channel when a response is flagged for bias
  or fails the context-relevance check.
- **FR-035**: System MUST dispatch an email alert to configured recipients when a pipeline task
  fails.
- **FR-036**: Alert dispatch failures MUST NOT crash the request or pipeline task that triggered
  them.

#### Security and Compliance

- **FR-037**: All credentials, endpoints, and webhook URLs MUST be read from the environment and
  MUST NEVER appear in source control, logs, or prompts.
- **FR-038**: System MUST collect no personal, student, or otherwise sensitive data during
  scraping.
- **FR-039**: System MUST restrict scraping to publicly accessible Research Computing documentation
  pages.

#### Data Versioning

- **FR-040**: Raw and processed data MUST be tracked by the data-versioning system and MUST NOT be
  committed directly to source control.
- **FR-041**: A given commit MUST be resolvable to the exact corpus revision it was built against.

#### Interface and Deployment

- **FR-042**: Users MUST be able to submit a question and receive an answer through a web interface
  requiring no installation.
- **FR-043**: The interface MUST show progress while a question is being processed.
- **FR-044**: The interface MUST visually distinguish a successful answer, a warning, and a refusal.
- **FR-045**: The application MUST be deployable as a container to the hosting platform, with local
  and deployed environments built from the same image definition.

### Key Entities

- **Documentation Section**: A top-level area of the Research Computing documentation (connecting
  to the cluster, running jobs, GPUs, data management, software, Slurm, classroom, containers, best
  practices, glossary, FAQs). Each section is the root of a crawl.
- **Raw Document**: Text extracted from a single documentation page, associated with its source URL
  and section.
- **Processed Document**: A cleaned, stopword-filtered, size-bounded chunk of a raw document. Has a
  unique identifier, a content body, and a traceable link to its raw source. This is the unit that
  is stored and indexed.
- **Search Index**: The retrievable collection of processed documents, queried by user question.
- **User Question**: Free-text input from a researcher; exists in raw and screened/normalized form.
- **Retrieved Context**: The concatenation of processed-document content returned for a question;
  the sole factual basis for the answer.
- **Generated Answer**: The model's response to the context and question; exists in raw, screened,
  and validated states, and reaches the user only in the validated state.
- **Interaction Metrics**: The measurements and thresholds recorded for one question-answer cycle.
- **Alert**: A typed, message-bearing notification dispatched to the team on quality or pipeline
  failure.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A researcher can go from question to grounded answer in a single interaction, with no
  documentation browsing required.
- **SC-002**: For questions answerable from the documentation, the system returns an answer rather
  than a refusal in at least 90% of cases. [NEEDS CLARIFICATION: no labeled evaluation set exists
  yet to measure this against.]
- **SC-003**: For questions not answerable from the documentation, the system refuses rather than
  fabricating in at least 95% of cases.
- **SC-004**: Documentation content published upstream is retrievable through the chatbot within
  one scheduled pipeline cycle.
- **SC-005**: A pipeline stage failure produces an alert to the team within the same run.
- **SC-006**: Every user-visible answer decision can be reconstructed afterward from recorded
  metrics without reproducing the session.
- **SC-007**: The automated test suite runs to completion with no live cloud or model credentials.
- **SC-008**: Median time from question submission to displayed answer stays within an acceptable
  interactive bound. [NEEDS CLARIFICATION: no latency target has been set.]
- **SC-009**: Measurable reduction in support tickets for questions the documentation already
  answers. [NEEDS CLARIFICATION: no baseline ticket volume has been captured.]

## Assumptions

- The Research Computing documentation site remains publicly accessible and structurally stable
  enough for section-rooted crawling.
- All content on that site is eligible for educational use under Northeastern's data policies.
- Users are Northeastern researchers, staff, and students who are comfortable with technical
  computing vocabulary.
- English is the only supported language for questions and answers.
- The chatbot answers from documentation only; it has no access to user accounts, job state,
  cluster telemetry, or ticketing systems.
- Interactions are single-turn: each question is answered independently, with no conversational
  memory across questions.
- Cloud infrastructure (object storage, search, hosting) and model API access remain provisioned
  and funded.
- Question volume stays within a scale where per-request retrieval and generation costs are
  acceptable without caching.

## Deferred Clarifications

These must be resolved via `/speckit-clarify` before any plan depends on them:

1. Behavior on empty question submission (Edge Cases).
2. Whether generation failure is distinguishable from low-relevance refusal in the current flow
   (FR-020, Edge Cases).
3. Per-user metric attribution under concurrent usage (Edge Cases, FR-032).
4. Evaluation set and target for answer-rate and refusal-rate measurement (SC-002, SC-003).
5. Latency target for interactive response (SC-008).
6. Baseline support-ticket volume for measuring deflection (SC-009).
