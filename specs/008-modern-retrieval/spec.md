# Feature Specification: Modern Retrieval

**Feature Branch**: `008-modern-retrieval`

**Created**: 2026-09-29

**Status**: Draft — blocked, not ready for planning

**Input**: Close the gap between AskRC's keyword-only retrieval and current RAG practice: chunking that respects document structure, retrieval that finds relevant content when the question and the page share no vocabulary, ordering that puts the best material first, and tolerance for how real users phrase questions.

## Why This Feature Exists

AskRC retrieves with a single lexical query against a keyword index and passes the top results
straight to the model. If a researcher's wording differs from the documentation's wording, the right
page is not retrieved, the model is handed material that does not contain the answer, and the
grounding gate correctly withholds it. The user is told their question lacks context when the real
failure was retrieval.

Every downstream guardrail in this system is working as designed. The input to those guardrails is
the weak link.

## Scope Boundary Against Neighbouring Features

Three features touch retrieval. This one owns the retrieval strategy; the other two must land first.

| Feature | Owns |
|---|---|
| 002 Corpus Idempotency and Provenance | Stable document identity, source URLs, the processing-rules version, update and deletion handling |
| 005 Retrieval Quality | Stopping the destructive text cleaning (gap G-06), aligning how questions and documents are processed, and building the labeled evaluation set |
| **008 Modern Retrieval (this)** | **How documents are divided, how candidates are found, how they are ordered, and how question phrasing is handled** |

This feature revises the "documents are split" concern that
[002](../002-corpus-idempotency-provenance/spec.md) placed out of scope. It does not revisit text
cleaning, which stays with 005.

## Dependencies — This Feature Is Blocked

- **002 must ship first.** Changing how documents are split changes every document's identity.
  Without deterministic identity and the processing-rules version from 002, a chunking change leaves
  the corpus in a silent mixed state. With 002 in place, a chunking change is an ordinary
  redeployment: bump the rules version and the next ingestion run reprocesses everything.
- **005 must ship first.** Two reasons. Text that has had its digits and stopwords stripped cannot
  be chunked on structure, because the structure is already gone. And without the labeled evaluation
  set, no change in this feature can be shown to have helped — it would be guesswork dressed as
  engineering.

Attempting this feature before both is the most likely way to waste the effort.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Questions Find the Right Page Even When Worded Differently (Priority: P1)

A researcher asks "how do I stop my job from being killed for using too much memory?" The relevant
documentation page discusses memory limits, OOM termination and resource requests, and never uses
the phrase "stop my job from being killed." Today that page is not retrieved. It should be.

**Why this priority**: This is the single largest source of wrong behavior a user experiences. The
system looks like it does not know things it demonstrably does know, and the failure is invisible —
it surfaces as a refusal, so nobody can tell retrieval was at fault.

**Independent Test**: Take a set of questions deliberately worded differently from the documentation
that answers them. Measure how often the correct page appears in the retrieved results, before and
after.

**Acceptance Scenarios**:

1. **Given** a question whose wording does not overlap the answering page's wording, **When**
   retrieval runs, **Then** the answering page is among the retrieved results.
2. **Given** a question that uses the documentation's exact terminology, **When** retrieval runs,
   **Then** the answering page is still retrieved — improving paraphrase handling MUST NOT regress
   exact-term matching.
3. **Given** a question containing an exact identifier that appears verbatim in one page — a
   partition name, a command flag, an error string — **When** retrieval runs, **Then** that page is
   retrieved. Exact-token matching MUST remain reliable.
4. **Given** a question about something genuinely absent from the corpus, **When** retrieval runs,
   **Then** it MUST NOT manufacture loosely related results that would pass the grounding gate.

---

### User Story 2 - Retrieved Material Is Coherent and Complete (Priority: P1)

When a researcher asks how to submit a GPU job, the retrieved material contains the whole command
example — not the first four lines of it, with the rest in a chunk that was not retrieved.

**Why this priority**: A truncated command or a table split from its header is worse than no result.
The model receives something that looks like an answer, produces something that looks authoritative,
and the researcher runs a broken command. Chunking quality bounds the quality of everything
downstream.

**Independent Test**: Inspect chunks produced from pages containing code blocks, tables and nested
headings. Confirm no code block or table is split across chunks, and that each chunk indicates the
section it came from.

**Acceptance Scenarios**:

1. **Given** a documentation page containing a code block, **When** it is divided, **Then** the code
   block is contained whole within one chunk.
2. **Given** a page containing a table, **When** it is divided, **Then** the table and the header row
   it depends on stay together.
3. **Given** a page with nested headings, **When** it is divided, **Then** chunk boundaries fall at
   section boundaries wherever the size budget allows.
4. **Given** any chunk, **When** it is retrieved, **Then** it carries enough context to be
   interpretable on its own — at minimum which page and which section it came from.
5. **Given** a passage whose meaning depends on the sentences immediately preceding it, **When**
   chunks are produced, **Then** adjacent chunks overlap sufficiently that the passage is not
   orphaned.
6. **Given** a single element larger than the size budget — an unusually long table or code block —
   **When** it is divided, **Then** the split is reported rather than performed silently.

---

### User Story 3 - The Best Material Appears First (Priority: P2)

Of the candidates retrieval finds, the ones most likely to answer the question are the ones the
model actually receives.

**Why this priority**: Real, but second-order. Retrieving the right page at all (Story 1) matters
more than its position. Becomes important once the candidate pool is larger and more diverse.

**Independent Test**: For evaluation questions with a known answering page, measure that page's
position in the final ordering, before and after.

**Acceptance Scenarios**:

1. **Given** a set of retrieved candidates, **When** they are ordered, **Then** the material most
   relevant to the question is placed earliest in the context given to the model.
2. **Given** the ordering step is unavailable, **When** a question is asked, **Then** retrieval still
   returns results in a sensible default order rather than failing the request.
3. **Given** several retrieved chunks from the same page, **When** the final set is assembled,
   **Then** near-identical material does not consume multiple slots.

---

### User Story 4 - A Maintainer Can Prove a Retrieval Change Helped (Priority: P1)

Before any change to chunking, retrieval or ordering is deployed, a maintainer can see its effect on
the evaluation set, as a comparison against the current behavior.

**Why this priority**: Without this, every subsequent change to this subsystem is a guess, and
regressions are invisible until a user reports a bad answer. This is the requirement that makes the
rest of the feature honest.

**Independent Test**: Run the evaluation against the current configuration, change one parameter,
run it again, and confirm the two results are directly comparable.

**Acceptance Scenarios**:

1. **Given** a proposed retrieval change, **When** the evaluation is run, **Then** it reports how
   often the correct page was retrieved and how highly it was ranked, for both configurations.
2. **Given** an evaluation run, **When** it completes, **Then** the configuration that produced it is
   recorded alongside the result.
3. **Given** a change that improves overall performance but regresses a subset of questions, **When**
   results are reported, **Then** the regressed questions are identifiable individually, not hidden
   in an average.
4. **Given** a retrieval change, **When** it is proposed for deployment, **Then** it MUST NOT ship
   without an evaluation result demonstrating it does not regress the current behavior.

---

### User Story 5 - Everyday Phrasing Is Handled (Priority: P3)

A researcher types a terse fragment, a misspelling, or an acronym. Retrieval copes.

**Why this priority**: Genuine, but the cheapest wins come from Stories 1 and 2. Deliberately last —
it is also the easiest place to add complexity that sounds impressive and changes nothing measurable.

**Independent Test**: Submit terse, misspelled and acronym-bearing variants of evaluation questions
and compare retrieval against the well-formed original.

**Acceptance Scenarios**:

1. **Given** a question containing a common misspelling of a technical term, **When** retrieval runs,
   **Then** the correct material is still found.
2. **Given** a question using an acronym where the documentation spells the term out, or the reverse,
   **When** retrieval runs, **Then** the correct material is found.
3. **Given** any transformation applied to a question before retrieval, **When** it is applied,
   **Then** it is recorded, so a bad retrieval can be traced to the transformed query rather than the
   original.
4. **Given** a transformation would change the meaning of the question, **When** retrieval runs,
   **Then** the original question's results are not discarded in favour of the transformed one's.

---

### Edge Cases

- **A page too short to chunk meaningfully** — a stub or a redirect. Must not produce an empty or
  near-empty chunk that pollutes results.
- **A page that is almost entirely one code block** — the structural rule and the size budget
  conflict directly; the resolution must be explicit, not incidental.
- **A question in which every term is a stopword** ("how do I do it?") — must degrade to a clear
  refusal, not to arbitrary results.
- **Two chunks with near-identical content** from different pages, e.g. a repeated boilerplate
  warning. Both should not occupy final slots.
- **The semantic component of retrieval is unavailable** — the system must still answer using what
  remains, and the degradation must be recorded, not silent.
- **The evaluation set becomes stale** because the documentation changed underneath it — must be
  detectable, so a measured "regression" is not really an upstream edit.
- **A question mixing an exact identifier with natural language** ("why does `--mem=4G` fail on
  short partition?") — both the exact-token and the conceptual parts must contribute.

## Requirements *(mandatory)*

### Chunking

- **FR-801**: Documents MUST be divided along their structural boundaries — sections and headings —
  in preference to arbitrary positions.
- **FR-802**: A code block MUST NOT be divided across chunks.
- **FR-803**: A table MUST NOT be separated from the header row required to interpret it.
- **FR-804**: Every chunk MUST carry an indication of its position in the document's structure,
  sufficient to interpret the chunk without the rest of the page.
- **FR-805**: Adjacent chunks MUST overlap sufficiently that a passage spanning a boundary remains
  retrievable.
- **FR-806**: Where a single indivisible element exceeds the size budget, the division MUST be
  reported and counted, never performed silently.
- **FR-807**: Chunk boundaries MUST be deterministic for identical input (extends baseline FR-010).
- **FR-808**: A change to the chunking strategy MUST bump the processing-rules version defined in
  [002](../002-corpus-idempotency-provenance/spec.md) (FR-110a), so affected documents are
  reprocessed automatically.

### Retrieval

- **FR-809**: Retrieval MUST find relevant material when the question and the answering page share
  little or no vocabulary.
- **FR-810**: Retrieval MUST continue to match exact identifiers — command flags, partition names,
  error strings — reliably.
- **FR-811**: Retrieval MUST combine its conceptual and exact-match capabilities into a single
  ranked candidate set, rather than requiring the caller to choose between them.
- **FR-812**: The number of candidates considered and the number finally supplied to the model MUST
  be independently configurable.
- **FR-813**: If one retrieval capability is unavailable, the system MUST continue using the
  remainder, and MUST record that it operated in a degraded state.
- **FR-814**: Retrieval MUST NOT return results below a relevance floor merely to fill the requested
  number of slots.

### Ordering and Assembly

- **FR-815**: Candidates MUST be ordered by likely relevance to the question before the final set is
  selected.
- **FR-816**: Near-duplicate material MUST NOT occupy multiple slots in the final set.
- **FR-817**: If the ordering step is unavailable, retrieval MUST fall back to its underlying order
  rather than failing the request.
- **FR-818**: The assembled context MUST preserve each chunk's provenance (002 FR-107), so citations
  remain correct.

### Query Handling

- **FR-819**: Questions MUST be processed consistently with the way document text is processed
  (established in 005), so query and index are comparable.
- **FR-820**: Any transformation applied to a question before retrieval MUST be recorded alongside
  the original.
- **FR-821**: A transformation MUST NOT cause the original question's results to be discarded.

### Evaluation and Safety

- **FR-822**: The system MUST be able to report, over the evaluation set, how often the correct
  material was retrieved and how highly it was ranked.
- **FR-823**: Evaluation results MUST identify individually regressed questions, not only aggregate
  scores.
- **FR-824**: Every evaluation result MUST record the configuration that produced it.
- **FR-825**: A retrieval change MUST NOT be deployed without an evaluation result showing it does
  not regress current behavior.
- **FR-826**: The system MUST be able to detect that the evaluation set no longer matches the current
  documentation.

### Observability

- **FR-827**: Each retrieval MUST record how many candidates each capability contributed, how many
  survived ordering, and how many reached the model.
- **FR-828**: Each retrieval MUST record whether it operated in a degraded state and which capability
  was unavailable.
- **FR-829**: Added retrieval stages MUST NOT push response time beyond the interactive bound set in
  the baseline (SC-008).

### Constraints Carried Forward

- **FR-830**: All chunks MUST continue to respect the retrieval system's maximum term size (baseline
  FR-008).
- **FR-831**: Provenance and identity guarantees from 002 MUST hold for chunks produced under the new
  strategy.
- **FR-832**: The grounding gate MUST continue to apply. Better retrieval reduces how often it fires;
  it does not license removing it (Constitution, Principle I).

### Key Entities

- **Chunk**: Supersedes the baseline Processed Document as the unit of retrieval. Adds structural
  position, overlap with neighbours, and the chunking strategy version that produced it.
- **Candidate Set**: The material retrieval finds for one question, before ordering and selection.
- **Retrieval Capability**: One means of finding candidates — conceptual or exact-match. Each
  contributes to the candidate set and can independently be unavailable.
- **Final Context**: The ordered, deduplicated material actually supplied to the model, carrying
  provenance.
- **Evaluation Set**: Questions with known answering pages, from 005, including deliberately
  out-of-corpus questions.
- **Evaluation Result**: Retrieval performance over the evaluation set for one configuration, with
  per-question detail.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-801**: For evaluation questions worded differently from their answering page, the correct page
  is retrieved measurably more often than under the current keyword-only behavior.
- **SC-802**: For evaluation questions using the documentation's own terminology, retrieval
  performance does not regress.
- **SC-803**: No code block or table in the corpus is divided across chunk boundaries.
- **SC-804**: Every chunk is interpretable on its own — a reader can tell what page and section it
  came from without further context.
- **SC-805**: For questions with a known answering page, that page appears earlier in the final
  ordering than it does today.
- **SC-806**: No two items in a final context set contain near-identical material.
- **SC-807**: Refusals attributable to retrieval failure rather than genuine absence of content
  decrease measurably.
- **SC-808**: Any retrieval configuration change can be compared against the previous one on the
  evaluation set, with per-question detail, before deployment.
- **SC-809**: Response time stays within the interactive bound; added stages do not make the system
  feel slower to users.
- **SC-810**: When a retrieval capability is unavailable, users still receive answers, and the
  degradation is visible to maintainers afterward.

## Assumptions

- The evaluation set from 005 exists, covers the documentation's major sections, and includes both
  answerable and deliberately unanswerable questions.
- The corpus stays small enough that reprocessing it entirely after a chunking change is affordable.
- Retrieval remains single-turn; no conversational context carries across questions.
- English only.
- The retrieval platform already in use can support these capabilities through configuration; no
  migration to a different system is assumed.
- Cost per question may rise somewhat; the improvement in answer quality is expected to justify it.
  Cost is tracked, not ignored.

## Out of Scope

- Text cleaning and normalisation (gap G-06 — owned by 005).
- Fine-tuning or training any model.
- Multi-hop reasoning across documents, entity graphs, or corpus-wide summarisation. The corpus is
  a single coherent documentation site of modest size; graph-based retrieval solves problems it does
  not have.
- Optical character recognition, layout parsing or image handling. The corpus is HTML. If PDFs are
  ever genuinely ingested (see gap G-20), that is a separate feature.
- Conversational memory or follow-up questions.
- Access control over retrieval results — the corpus is entirely public.
- Response streaming.

## Anticipated Direction *(non-normative)*

This section is context for planning, not requirements. `/speckit-plan` chooses the approach and may
depart from this entirely.

The retrieval platform in use provides vector fields, hybrid queries that fuse lexical and vector
results with reciprocal rank fusion, and a semantic reranking stage — meaning FR-809 through FR-815
may be substantially satisfied by configuration rather than new retrieval code. If that holds, the
real engineering in this feature is chunking (FR-801 to FR-808) and the evaluation harness (FR-822 to
FR-826), not the retrieval mechanics.

Planning should verify that before assuming it.

## Deferred Clarifications

1. **Evaluation set size and composition** — how many questions, and what proportion deliberately
   unanswerable. Determines whether measured differences are meaningful or noise. Likely resolved
   within 005.
2. **Acceptable cost increase per question** — conceptual retrieval and reranking both add cost. No
   budget has been stated.
3. **Interactive latency bound** — inherited unresolved from baseline SC-008, and this feature adds
   stages to the request path, so it can no longer be deferred indefinitely.
