# DSI v1 capability-to-evidence matrix

The mandatory first gate of the v1 product-boundary website pack. Every positive capability
claim on the published site must trace to a row here. A claim without a row is cut.

Built from the frozen v1 contract, not from the website's prior copy:

- `D:\DSI-V1\docs\MEASUREMENT_CONTRACT.md` @ `7f80654` — authorised under the owner's
  forward reconciliation of the CORE-1D closure (`DSI_CORE_1D_CLOSED_PASS`). The record's
  `TRUNCATION_FLAG` remains truthful evidence that an earlier message was truncated; its
  "NOT yet authorised" next-action field was superseded by the later explicit authorisation.
  The historical record is not rewritten.
- `D:\DSI-V1\docs\CLAIM_BOUNDARIES.md` @ `978dfcf`

## The two artefacts the site must keep distinct

| | v0.2.1 evaluation build | DSI v1 |
|---|---|---|
| Availability | supplied by request | **forthcoming — not released, not downloadable** |
| Lineage | `dsi-product` | inherits the measurand of `dsi-product @ e0ad514`, and none of its status |
| Status | research implementation, private evaluation access | **unqualified; makes no measurement claim** |

No v1 capability may be presented as belonging to v0.2.1, and no "forthcoming" wording may
imply availability.

## Capability rows

| Capability | v0.2.1 | v1 | Evidence / limitation |
|---|---|---|---|
| Audit a supplied response against a governed reference | yes | **implemented, unqualified** | v1: 23 tests, 3 predecessor goldens MUST_MATCH. `CLAIM_BOUNDARIES`: "an implemented contract is not a qualified instrument" |
| Governed status partition (§4) | yes | yes | The single authority for trajectory status |
| Coverage over the applicable counted population | yes | yes | §5. **Not** "required coverage" — never present a figure without its denominator and applicability legend |
| `omitted_safety_critical` finding | yes | yes | §6. Orthogonal to coverage; a finding, not a percentage. Not a safety or regulatory conclusion |
| Regression comparison between runs | yes | **no** | v1 `compare` unimplemented; comparability §9 defined not built |
| Evidence generation, fingerprints, provenance, replay | yes | **no** | v1 identity §7 and evidence unimplemented |
| Comparability determination | yes | **no** | `COMPARABILITY_UNKNOWN` is not a soft yes |
| Local, stateless operation; readiness checks | yes | **no** | v1 CLI unimplemented |
| Handoff integrity · retrieval/RAG integrity | no | **no** | Never implemented. Removed from the site |
| Revision, recovery, remediation, intervention | no | **no** | `CLAIM_BOUNDARIES`: deliberately unsupported |
| Pluraxis · GATE · integrated operation | no | **no** | `CLAIM_BOUNDARIES`: deliberately unsupported |

## The frozen findings vocabulary (§4)

The site must use this exact vocabulary. It is richer than any short substitute, and
"loss · addition · distortion" is not it — `addition` and `distortion` are not governed
statuses, and "general relational distortion" is on the deliberately-unsupported list.

```text
COVERAGE_POSITIVE      surfaced · partially_surfaced
COVERAGE_NEGATIVE      omitted · discouraged · negated · collapsed_into_other
NON_COUNTING_POLICY    warning_required_missing
```

`surfaced_with_warning` is a **label**, not a status. `abstained` and structural preclusion
are deliberately absent from v1; adopting either is a successor instrument (§11).

## The strongest permissible revision wording

DSI performs no revision and establishes no improvement. The site may say only:

> DSI audits a supplied output. If the operator independently revises that output, DSI can
> re-audit it under the same instrument and report the resulting delta.

## What the site may still disclose

The boundary is **contextual, not lexical**. Pluraxis and GATE carry no promotion, no
navigation, no application profile and no v1-capability claim — but they remain permitted in
bounded evidence and programme-history disclosures, because deleting a negative finding would
itself be a claim.

Specifically preserved:

- **Deliberation-loop efficacy: not established** — evidence register and homepage.
- The programme-history section on `/research`, which states that the wider work is preserved
  in the governed repositories and excluded from v1. `/pluraxis` redirects there.
- No R-EGA reference is added; none exists today, and completeness is not a reason to create one.

## Version identity — RESOLVED (option 2, owner-authorised)

The site publishes **two** identities, and `0.3.0` is not one of them:

- **`v0.2.1`** — the evaluation build, supplied by request. Every subordinate page
  (installation, deployment, security, release notes, worked example) documents *this*.
- **`DSI v1`** — separately lineaged, unqualified, not released and not downloadable.

`0.3.0` is removed from published copy entirely. It was an internal predecessor development
line, **not** the lineage that becomes v1, and publishing it beside v1 invited exactly the
lineage inference recorded below. The contract now rejects `0.3.0` in published copy, a v-prefixed form of it
anywhere, availability wording inside the v1 entry, and any wording implying 0.3.0 becomes v1.

### Why it needed a ruling

The two were different artefacts, and their relationship was not establishable from evidence:

| Artefact | Version | Lineage |
|---|---|---|
| `dsi-product` — the site's "current development line" | `0.3.0` | head of the predecessor product |
| `D:\DSI-V1` — DSI v1 | `0.0.0` | inherits the measurand at `e0ad514`, and none of its status |

`e0ad514` is the CORE-1A baseline, not `0.3.0`'s head, so v1 is not a continuation of the
`0.3.0` line. Publishing them side by side would have asserted a lineage nothing supported.
**Option 2 was authorised and is implemented**: name `v0.2.1` and `v1`, retire `0.3.0`.

## Surface classes

The v1 boundary is enforced structurally, by what a page is for, not by lexical proximity:

| Class | Pages | Rule |
|---|---|---|
| **v1 surfaces** | `/`, `/dsi`, `/applications` | The withheld capabilities must not appear in **visible copy or metadata** — title, description, OG, Twitter and image alt text are all scanned, because stripping tags discards exactly the place a claim can hide. `/dsi` must positively carry the four authorised capabilities and the seven statuses. **`/dsi` and `/applications` get no exemption of any kind.** |
| **v0.2.1 surfaces** | `/audit`, `/getting-started`, `/deployment`, `/security`, `/release-notes`, `/example-audit` | Withheld capabilities are legitimate, but the page must carry the verbatim scope marker. |
| **disclosure surfaces** | `/evidence`, `/research` | Permitted as evidence and programme history; the not-established and history rules apply. |

Withheld from v1: regression, evidence bundles, fingerprints, provenance, replay,
comparability, readiness, stateless operation, revision, intervention, remediation.

### The one exception, and why it is this narrow

The homepage carries a bounded evidence-status disclosure — including
*"measurement integrity, comparability … not established"* — which must survive, because
deleting a negative finding is itself a claim. That exemption is keyed to **one explicitly
identified section**, `index.html#evidence-status`, and to nothing else.

Two earlier versions were broader and each hid a real escape that reached a pushed head:

| Exception as written | What it hid |
|---|---|
| whole `<section>` containing an `ev-*` chip | a capability promoted into a heading beside an unrelated badge |
| any card or row containing an `ev-*` chip | *"a reproducible fingerprint"* in the `/applications` AI-summary card, which also carried an application-validity badge |

An exception scoped by "contains a chip" is scoped by coincidence. This one is scoped by
identity.

`source evidence` is **not** one of v1's four authorised capabilities, so the application
profiles state the governed reference and the status partition instead of promising evidence
the contract does not authorise.

## Corrections made against the frozen contract

Two owner-supplied phrasings were corrected against the frozen contract and
are recorded here rather than silently adopted: the "loss · addition · distortion" triplet
(replaced by §4), and "configured classifiers and scorers" — v1 has no scorer, and coverage is
produced once by the canonical counting authority inside `build_observed_map`.
