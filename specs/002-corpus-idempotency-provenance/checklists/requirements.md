# Specification Quality Checklist: Corpus Idempotency and Provenance

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Validation Notes

**Iteration 1 — 2026-09-22**

Passing 15 of 16. Detail on the judgement calls:

- *No implementation details*: The spec deliberately does not state how identity is derived. It
  requires only that the identifier be deterministic (FR-101, FR-102) and collision-free across
  source pages (FR-103). Content hashing, URL slugs, and composite keys all remain open for
  `/speckit-plan` to choose. FR-104 ("valid for use as keys ... without further transformation") is
  a constraint on the outcome, not a prescription of mechanism.
- *Success criteria technology-agnostic*: All nine are stated as observable outcomes — document
  counts, duplicate-free results, resolvable references, cycle latency. None names a service.
- *Scope bounded*: An explicit **Out of Scope** section keeps text cleaning and chunking (G-06) and
  the metrics-collector defects (G-09) in their own future features, preventing this one from
  absorbing the whole gap analysis.

**Iteration 2 — 2026-09-30 (after clarification sessions)**

All 16 items now pass. Five clarifications were resolved across two sessions and integrated:

| # | Decision | Effect on the spec |
|---|---|---|
| 1 | Maintenance window acceptable during remediation | FR-121a, FR-122; User Story 4 scenarios 3–5 |
| 2 | Source links shown to end users | FR-108 rewritten, FR-108a added |
| 3 | Processing-rules version recorded per document | FR-110a, FR-120a, FR-120b; new entity |
| 4 | One ingestion run at a time | FR-114a, FR-114b; SC-112; two edge cases |
| 5 | Large deletions are withheld pending review | FR-128 to FR-128d; FR-119a, FR-119b; SC-110, SC-110a, SC-111; new entity |

Note on decision 5: this was first answered as "proceed and alert", then revised to "stop and alert"
before planning began. The revision added two things the first answer did not need:

- **An authorisation path (FR-128c).** Withholding removals only works if a legitimate large-scale
  restructure can still get through. A safety check with no override eventually becomes an obstacle
  someone disables.
- **Repeat detection (FR-128d).** Without it, a subsequent run could silently resume the deletions
  the previous run refused, defeating the check.

FR-119a and FR-119b were introduced under the earlier answer and are retained. They sit upstream of
the threshold: a failed or empty crawl produces no deletions to evaluate in the first place, and an
error page served with a success status is not evidence of withdrawal. They are now defence in depth
rather than the sole safeguard.

The FR-128 threshold value is intentionally not specified. The requirement fixes that it must be
configurable; choosing the starting number is tuning, not product definition.

**Status**: Ready for `/speckit-plan`.
