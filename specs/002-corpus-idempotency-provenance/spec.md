# Feature Specification: Corpus Idempotency and Provenance

**Feature Branch**: `002-corpus-idempotency-provenance`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "Corpus idempotency and provenance — resolve gaps G-01 and G-07 from the baseline gap analysis: the ingestion pipeline duplicates the entire corpus on every run, and processed documents discard the source URL so no answer can be traced back to the page it came from."

## Why These Two Together

G-01 (duplication) and G-07 (no provenance) look unrelated but share one root cause: a processed
document's identity is randomly generated at processing time rather than derived from what the
document *is* and where it came from. Fixing identity fixes both. Splitting them into separate
features would mean changing the same identity scheme twice.

This feature extends [001-baseline-rag-system](../001-baseline-rag-system/spec.md). It does not
contradict it; it makes FR-005, FR-009, and FR-031 actually hold.

## Clarifications

### Session 2026-09-28

- Q: When clearing the existing duplicate backlog, is a short maintenance window acceptable? → A: Yes — the chatbot may be taken offline and the corpus rebuilt clean (Option A).
- Q: Should source references be shown to end users, or kept maintainer-facing only? → A: Shown to users — every answer displays a link to the documentation page it came from (Option A). Passage-level attribution remains out of scope.
- Q: When the text-processing rules change, should affected documents be reprocessed automatically? → A: Yes — each document records the processing-rules version that produced it, and a version change is treated as a content change (Option B).

### Session 2026-09-30

- Q: What should happen if a pipeline run is triggered while another is still in progress? → A: Only one run at a time — the second exits immediately reporting that a run is already in progress (Option A).
- Q: Should a run that would delete a large share of the corpus stop, or proceed and alert afterwards? → A: Stop and alert (Option A). No removals are applied, the corpus is left as it was, and a maintainer must review and explicitly authorise the removal before it can proceed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Repeated Ingestion Leaves the Corpus Unchanged (Priority: P1)

A maintainer lets the scheduled ingestion run every day, as designed. The documentation site has not
changed since yesterday. After today's run, the corpus is exactly what it was yesterday — same number
of documents, same content, no growth.

**Why this priority**: Today the opposite happens. Each run adds a complete second copy of the
corpus, so retrieval results fill up with duplicates of the same passage and the effective context
supplied to the model shrinks toward a single document. Every day this is not fixed, answer quality
degrades further and storage and indexing costs grow linearly. Nothing else in this feature matters
if this is not fixed first.

**Independent Test**: Run the full ingestion pipeline twice against an unchanged documentation
source. Count documents in the corpus after each run. The counts must be identical, and searching
for a distinctive phrase must return one document containing it, not two.

**Acceptance Scenarios**:

1. **Given** a corpus already ingested from unchanged source documentation, **When** the ingestion
   pipeline runs again, **Then** the number of stored and indexed documents is unchanged.
2. **Given** a corpus already ingested, **When** the pipeline runs again and a search is performed
   for a phrase appearing on exactly one documentation page, **Then** exactly one document
   containing that phrase is returned.
3. **Given** the same source page processed on two different days, **When** its identifier is
   examined both times, **Then** the identifier is the same.
4. **Given** the pipeline is interrupted partway through a run, **When** it is run again to
   completion, **Then** the resulting corpus is the same as if the first run had completed — no
   partial duplicates remain.
5. **Given** a source page whose content is split into multiple parts, **When** the page is
   reprocessed unchanged, **Then** the same number of parts is produced with the same identifiers.

---

### User Story 2 - Answers Show Where They Came From (Priority: P1)

A researcher receives an answer about requesting GPU resources. Alongside the answer, they can see
which documentation page or pages it was drawn from, and follow that reference to read the full
context themselves.

**Why this priority**: This is the core promise of retrieval-augmented generation — that answers are
traceable rather than merely fluent. Today the source URL is discarded during processing, so neither
the user nor a maintainer can verify any answer against the documentation. A researcher acting on
operational advice about cluster access needs to be able to confirm it. It also makes the system
self-correcting: a user who sees the source can tell when the retrieval picked the wrong page.

**Independent Test**: Ask a question answerable from a known documentation page. Confirm the response
identifies that page, and that following the reference reaches content consistent with the answer.

**Acceptance Scenarios**:

1. **Given** a processed document in the corpus, **When** it is inspected, **Then** it carries the
   URL of the documentation page it was derived from.
2. **Given** a question answered from retrieved documentation, **When** the answer is displayed,
   **Then** the user can see the source page reference for the retrieved material.
3. **Given** a document split into several parts, **When** any part is retrieved, **Then** it
   reports the same source page as every other part of that document.
4. **Given** a displayed source reference, **When** the user follows it, **Then** it resolves to a
   live, publicly reachable documentation page.
5. **Given** an answer that is withheld for insufficient relevance, **When** the refusal is shown,
   **Then** no misleading source reference is attached to it.

---

### User Story 3 - Updated Documentation Replaces Stale Content (Priority: P1)

The Research Computing team edits a documentation page — a partition is renamed, a policy changes.
After the next ingestion run, the chatbot answers from the *new* text. The old version is gone, not
sitting alongside the new one competing for retrieval.

**Why this priority**: Idempotency without update handling would be a corpus that never changes,
which is just as wrong as one that duplicates. Superseded operational guidance is actively
dangerous — a researcher following a renamed partition or a withdrawn policy will fail, or worse,
succeed at something they shouldn't.

**Independent Test**: Ingest a page, modify its source content, re-ingest, then search for a phrase
unique to the old version and a phrase unique to the new version. Only the new phrase should be
found.

**Acceptance Scenarios**:

1. **Given** a page already in the corpus, **When** its source content changes and ingestion runs,
   **Then** the corpus reflects the new content.
2. **Given** a page whose content changed, **When** ingestion completes, **Then** no document
   containing only the superseded content remains retrievable.
3. **Given** a page that changed such that it now splits into a different number of parts, **When**
   ingestion completes, **Then** no orphaned parts from the previous version remain.
4. **Given** a page that has not changed, **When** ingestion runs, **Then** it is not needlessly
   rewritten or reindexed. *(Efficiency expectation, not a correctness requirement.)*

---

### User Story 4 - The Existing Duplicate Backlog Is Cleared (Priority: P1)

A maintainer needs the corpus that exists *today* — already carrying many accumulated copies from
past daily runs — brought to a clean state, once, as part of adopting this feature.

**Why this priority**: The fix prevents *future* duplication but does nothing about duplicates
already in the index. Without remediation, retrieval stays degraded and the feature delivers no
observable improvement to users. Shipping the fix without the cleanup would be shipping a change
nobody can see.

**Independent Test**: After remediation, search for a phrase appearing on exactly one documentation
page and confirm a single document is returned. Compare the total document count against the number
of source pages and parts, and confirm they are consistent.

**Acceptance Scenarios**:

1. **Given** a corpus containing accumulated duplicates, **When** remediation completes, **Then**
   each distinct piece of source content is represented exactly once.
2. **Given** remediation has completed, **When** the document count is compared to the expected
   count derived from the source documentation, **Then** the two agree.
3. **Given** remediation is in progress, **When** a user visits the chatbot, **Then** they are shown
   a maintenance message rather than a question form, and no answer is ever produced from a
   partially rebuilt corpus.
4. **Given** remediation has failed partway, **When** a maintainer inspects the system, **Then** the
   chatbot remains in the maintenance state rather than returning to service on an incomplete
   corpus.
5. **Given** remediation completes, **When** the chatbot is returned to service and the next
   scheduled ingestion runs, **Then** the corpus remains stable (User Story 1 holds from that point
   onward).

---

### User Story 5 - Withdrawn Pages Leave the Corpus (Priority: P2)

A documentation page is deleted or moved upstream. Within one ingestion cycle, the chatbot stops
answering from it.

**Why this priority**: Real, but lower frequency than the others and the system remains broadly
useful in the interim. Deferred behind the P1 stories deliberately.

**Independent Test**: Ingest a set of pages, remove one from the source set, re-ingest, and confirm
content unique to the removed page is no longer retrievable.

**Acceptance Scenarios**:

1. **Given** a page previously ingested, **When** it is no longer present at the documentation
   source and ingestion runs, **Then** its content is no longer retrievable.
2. **Given** a documentation source that is temporarily unreachable, **When** ingestion runs,
   **Then** existing content is NOT removed — an outage must not be mistaken for deletion.

---

### Edge Cases

- **Two pages with identical content**: distinct source URLs, same text. Each must retain its own
  source reference; identity must not collapse them into one document such that one page's
  provenance is lost.
- **One page whose content changes only in whitespace or markup**: must be treated as unchanged, so
  trivial upstream edits do not churn the corpus.
- **Source URL changes but content does not** (page moved): treated as a new page plus a withdrawn
  page. The stale reference must not persist.
- **Interrupted remediation**: remediation is itself re-runnable; a failed attempt must not leave
  the corpus in a state worse than before it started.
- **Page content that produces zero usable text** after processing: must not be stored as an empty
  document, and must be counted and reported rather than silently skipped.
- **A page whose part count shrinks between runs**: previously created trailing parts must be
  removed, not left orphaned.
- **Concurrent ingestion runs**: a manual trigger during the scheduled run must exit immediately
  without touching the corpus, reporting that a run is already in progress. A skipped run is
  acceptable; ingestion is idempotent and runs daily.
- **A run killed mid-flight** (process crash, worker eviction): must not block the next run from
  starting. Recovering from an abandoned run must not require manual intervention.
- **A crawl that succeeds but returns far fewer pages than usual** — a partial outage, a changed site
  structure, a redirect loop. No removals are applied, the run is marked failed, and an alert is
  raised (FR-128). The corpus keeps serving the content it already has.
- **A genuine large-scale documentation restructure** — the department really does retire a third of
  its pages. The first run halts and alerts; a maintainer confirms the removal is correct and
  authorises it (FR-128c). The pipeline must not be permanently stuck in this state.
- **A documentation page that serves an error page with a success status code** — must be recognised
  as a non-content response, not ingested as content and not treated as evidence of withdrawal.

## Requirements *(mandatory)*

### Document Identity

- **FR-101**: Every processed document MUST have an identifier that is derived deterministically
  from its source page and its position within that page.
- **FR-102**: Processing the same source content MUST produce the same identifier on every run,
  across machines, and across process restarts.
- **FR-103**: Two different source pages MUST NOT produce the same document identifier, even when
  their content is identical.
- **FR-104**: Identifiers MUST remain valid for use as keys in the storage and retrieval systems
  without further transformation.

### Provenance

- **FR-105**: Every processed document MUST record the URL of the source documentation page it was
  derived from.
- **FR-106**: Every processed document MUST record its position among the parts derived from that
  page, and the total number of such parts.
- **FR-107**: Provenance MUST survive storage and indexing — it MUST be retrievable alongside
  content at query time, not only present at processing time.
- **FR-108**: The user interface MUST display, alongside every answer, a followable link to each
  documentation page the answer's retrieved material came from.
- **FR-108a**: Where several retrieved documents share one source page, that page MUST be listed
  once rather than repeated.
- **FR-109**: Source references MUST NOT be attached to refusals or error states.
- **FR-110**: Every processed document MUST record when it was last derived from its source.
- **FR-110a**: Every processed document MUST record the version of the text-processing rules that
  produced it.

### Idempotency

- **FR-111**: Running the ingestion pipeline over unchanged source documentation MUST NOT change the
  number of stored or indexed documents.
- **FR-112**: Running the ingestion pipeline over unchanged source documentation MUST NOT change the
  content of any stored or indexed document.
- **FR-113**: Re-running an interrupted pipeline run MUST converge to the same corpus state as an
  uninterrupted run.
- **FR-114**: Each stage of the pipeline MUST be independently re-runnable without duplicating the
  work of prior runs.
- **FR-114a**: Only one ingestion run MAY be in progress at a time. A run started while another is
  in progress MUST exit immediately without modifying the corpus, and MUST report that it did so and
  why.
- **FR-114b**: A run that ends abnormally MUST NOT leave behind a condition that prevents the next
  run from starting.

### Update and Deletion

- **FR-115**: When source content changes, the corpus MUST reflect the new content after the next
  ingestion run.
- **FR-116**: When source content changes, no document representing only the superseded content MAY
  remain retrievable.
- **FR-117**: When a page's content splits into fewer parts than a previous run produced, the surplus
  parts from the previous run MUST be removed.
- **FR-118**: When a page is no longer present at the documentation source, its documents MUST be
  removed from the corpus within one ingestion cycle.
- **FR-119**: The system MUST distinguish a page that is genuinely absent from a source that is
  temporarily unreachable, and MUST NOT delete content on the basis of an unreachable source.
- **FR-119a**: Deletions MUST only be computed from a crawl that completed successfully. A crawl that
  failed, was interrupted, or returned no pages MUST NOT be treated as evidence that pages were
  withdrawn, and MUST cause the deletion step to be skipped for that run.
- **FR-119b**: A page that returns an error or a non-content response — an authentication wall, a
  server error, an error page served with a success status — MUST NOT be treated as withdrawn.
- **FR-120**: Changes limited to whitespace or markup MUST NOT be treated as content changes.
- **FR-120a**: A change to the text-processing rules version MUST be treated as a content change:
  every document produced under a superseded version MUST be reprocessed on the next ingestion run.
- **FR-120b**: The corpus MUST NOT be left in a mixed state, where some documents were produced
  under a superseded processing-rules version and others under the current one, beyond the
  ingestion run that performs the changeover.

### Remediation of Existing State

- **FR-121**: The system MUST provide a repeatable operation that brings an already-duplicated
  corpus to a clean state.
- **FR-121a**: For the duration of remediation the chatbot MUST be placed in a maintenance state
  that tells users it is temporarily unavailable, and MUST NOT serve answers from a partially
  rebuilt corpus.
- **FR-122**: Remediation MUST be safe to re-run after a failure. A failed attempt MUST leave the
  chatbot in the maintenance state rather than returning it to service on an incomplete corpus.
- **FR-123**: Remediation MUST report what it changed — documents removed, documents retained, and
  the resulting count.
- **FR-124**: After remediation, each distinct piece of source content MUST be represented exactly
  once in the corpus.

### Observability

- **FR-125**: Each ingestion run MUST record how many documents were added, updated, left unchanged,
  removed, and reprocessed because the processing-rules version changed.
- **FR-126**: A run in which no source content changed MUST be distinguishable, from its recorded
  metrics alone, from a run that changed content.
- **FR-127**: Documents skipped for any reason MUST be counted and reported, never silently dropped.
- **FR-128**: An ingestion run that would remove more than a configurable proportion of the corpus
  MUST NOT perform any removals. It MUST halt the deletion step, be recorded as failed, and raise an
  alert identifying how many documents would have been removed and which source pages they belonged
  to.
- **FR-128a**: The alert MUST be raised as part of the run that detected the condition, not deferred
  to a later report.
- **FR-128b**: Content added or updated earlier in the same run MUST be retained. Only removals are
  withheld — blocking additions would leave the corpus stale for no safety benefit.
- **FR-128c**: A maintainer MUST be able to review the withheld removals and explicitly authorise
  them, without editing code, so that a genuine large-scale documentation change can proceed.
- **FR-128d**: Until the removal is authorised or the source returns to its previous state, each
  subsequent run MUST re-detect the condition and re-alert rather than silently resuming deletions.

### Constraints Carried Forward

- **FR-129**: Provenance data MUST NOT include personal, student, or otherwise sensitive
  information (baseline FR-038).
- **FR-130**: Documents MUST continue to respect the retrieval system's maximum term size (baseline
  FR-008); identity and provenance changes MUST NOT push any document over that limit.
- **FR-131**: The corpus MUST remain reproducible from a commit plus a data revision (baseline
  FR-041).

### Key Entities

- **Source Page**: A single documentation page at the upstream site, identified by its URL. The unit
  of provenance and of deletion.
- **Document Identity**: The deterministic identifier of one processed part, derived from its source
  page and its position within that page. Stable across runs.
- **Processed Document**: Extends the baseline entity with source URL, part position, total part
  count, last-derived timestamp, and the processing-rules version that produced it. Remains the unit
  of storage and retrieval.
- **Processing Rules Version**: An identifier for the text cleaning and splitting behavior in force
  when a document was produced. Changing it obsoletes every document produced under the prior
  version.
- **Corpus State**: The set of processed documents currently stored and indexed, with its document
  count and per-source-page part counts.
- **Ingestion Run Summary**: Counts of documents added, updated, unchanged, removed, reprocessed and
  skipped for a single run, plus whether removals were withheld pending review.
- **Withheld Removal**: A set of deletions a run declined to apply because they exceeded the safety
  proportion, retained with the run that detected them so a maintainer can review and authorise it.
- **Remediation Operation**: The one-time, re-runnable cleanup that brings an existing duplicated
  corpus to a clean state, and its report.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-101**: Running ingestion twice in succession over unchanged documentation leaves the document
  count identical — 0% growth, verified by comparing counts before and after.
- **SC-102**: After remediation, a search for a phrase occurring on exactly one documentation page
  returns exactly one document containing it.
- **SC-103**: 100% of documents in the corpus carry a source URL that resolves to a reachable
  documentation page.
- **SC-104**: 100% of answers displayed to users are accompanied by at least one source reference.
- **SC-105**: A content change made at the documentation source is reflected in the chatbot's answers
  within one ingestion cycle, with no answer drawn from the superseded text afterward.
- **SC-106**: Retrieved results for a question contain no duplicate passages, so all retrieval slots
  carry distinct content.
- **SC-107**: Total corpus storage stops growing on runs where source documentation has not changed.
- **SC-108**: A maintainer can determine, from a single run summary, whether that run changed the
  corpus and how — without inspecting the corpus itself.
- **SC-109**: Given any answer, a maintainer can reach the exact source page it was drawn from in one
  step.
- **SC-110**: A run that would remove an unusually large share of the corpus removes nothing, and
  produces an alert during that same run naming the count and the affected source pages.
- **SC-110a**: A maintainer who confirms a large removal is legitimate can let it through without a
  code change or a redeploy.
- **SC-111**: A failed or empty crawl never results in documents being removed from the corpus.
- **SC-112**: Two ingestion runs never overlap; a run started during another exits without modifying
  the corpus.

## Assumptions

- Source page URLs are stable enough to serve as the basis of identity; page moves are uncommon and
  are acceptably handled as a deletion plus an addition.
- The documentation corpus is small enough that a full comparison against source content on each run
  is affordable within the daily schedule.
- The corpus is fully regenerable from the upstream documentation site; no processed document holds
  information that cannot be recovered by re-ingesting.
- Users benefit from seeing source references and will not find them noise — consistent with the
  constitutional principle that answers must be traceable.
- Showing a source reference is not a claim that every sentence of the answer appears on that page;
  it identifies the material the answer was built from.
- The upstream documentation site remains publicly reachable without authentication, so source
  references are followable by any user.
- Remediation is a one-time operation for the existing backlog, not an ongoing scheduled task.
- A short, announced maintenance window is acceptable to this user base. Because the corpus is fully
  regenerable from the upstream site, rebuilding it clean is preferred over reconciling the live
  corpus in place.
- A wrongful mass deletion would leave the chatbot unable to answer until someone noticed and
  rebuilt the corpus. Since real documentation sites rarely lose a large share of their pages
  overnight, a run attempting it is far more likely to be broken than correct — so removals are
  withheld pending review (FR-128) rather than applied and reported afterwards.
- Large-scale documentation restructures do happen occasionally, so withholding removals requires an
  explicit authorisation path (FR-128c). Without one, the safety check would eventually become an
  obstacle that gets disabled.
- Ingestion runs daily, so a run skipped because another was in progress (FR-114a) costs at most one
  cycle of freshness.
- No change to the chunking or text-cleaning strategy is in scope here; that is deferred to the
  planned retrieval-quality feature (gap G-06).

## Out of Scope

- Changing how text is cleaned (gap G-06 — deferred to feature 005) or how documents are split
  (deferred to feature [008](../008-modern-retrieval/spec.md)). This feature establishes the
  processing-rules versioning that makes both changes safe to deploy; it does not alter the rules
  themselves.
- Changing the retrieval ranking, result count, or query processing.
- Per-sentence or per-claim attribution within an answer; provenance here is per retrieved document.
- Displaying document excerpts or snippets alongside references.
- Fixing the metrics collector defects (gap G-09) — this feature specifies *what* must be recorded;
  making the recording mechanism reliable is feature 006.

## Dependencies

- Baseline spec [001-baseline-rag-system](../001-baseline-rag-system/spec.md) — this feature makes
  FR-005, FR-009, and FR-031 hold.
- Requires write access to the existing corpus to perform remediation.

## Deferred Clarifications

None outstanding. All five open decisions were resolved across the 2026-09-28 and 2026-09-30
clarification sessions — see [Clarifications](#clarifications).

One item is deliberately left to planning rather than specification: the exact proportion at which a
removal counts as "large" for FR-128. The requirement states it MUST be configurable; the starting
value is a tuning decision, not a product decision.
