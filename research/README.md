# research/

External-world evidence for this project — schema dumps, upstream pin manifests, API probes, investigation notes. Organised into three tiers by **authority and lifecycle**.

## Tiers

### Tier 1 — Authoritative artifacts (top of `research/`)

Version-stamped, immutable-ish records that downstream milestones depend on by exact path. These are **outputs of the RPI "P" or "I" step**, not raw exploration. Readers (humans or agents) cite them from plans, `bd` issues, and `docs/*.md`.

Naming convention: `<topic>-<version-or-shortsha>.<ext>`.

Examples present today:

- [`wealthfolio-schema-v3.2.1.txt`](./wealthfolio-schema-v3.2.1.txt) — Diesel schema dump. Produced by [M0.1](../plans/M0/M0.1-wealthfolio.md). Consumed by M0.7 (SQL stub) and M0.4 (`THIRD_PARTY.md`).
- [`ai-hedge-fund-pin-0f6ac48.md`](./ai-hedge-fund-pin-0f6ac48.md) — Upstream SHA pin manifest with license snapshot and port-target verification. Produced by [M0.2](../plans/M0/M0.2-ai-hedge-fund-pin.md). Consumed by M0.4 (`THIRD_PARTY.md`) and M3 (scoring-engine port).

A file belongs in Tier 1 when:

1. Another milestone reads it by exact path, **or**
2. It is a version-stamped snapshot of an external thing (upstream SHA, library release, schema dump) that we want to be able to cite deterministically.

Every Tier 1 artifact should be linked from the plan that produced it and from the bd issue(s) that consume it. If nothing points at it, it isn't really Tier 1 — either promote the pointers or move it into `milestones/`.

### Tier 2 — Milestone investigation notes ([`milestones/`](./milestones/))

The **R** of RPI: throwaway-ish pre-plan exploration, one file per milestone (`Mn-investigation.md`). See [`milestones/README.md`](./milestones/README.md) for the full policy. Nothing in there is considered authoritative; findings are promoted into Tier 1, a plan, the SPEC, or a `bd` issue.

### Tier 3 — Archive ([`archive/`](./archive/))

Frozen historical exploration from pre-v1.2 design. Read-only. Do not add to archive — it is a snapshot, not an active directory.

## When to add a new top-level file

Add a Tier 1 file when:

- A milestone plan explicitly names `research/<path>` as a deliverable (see `plans/Mn/Mn.x-*.md` "File layout" sections).
- You need a stable, version-stamped reference that downstream code, plans, or `THIRD_PARTY.md` will cite.

Prefer `milestones/Mn-investigation.md` when:

- You're still deciding. The file captures notes, rejected options, open questions.
- The finding may never be referenced by another milestone.

If a tier-2 finding later becomes load-bearing (e.g. a config field, a schema detail, a pin), promote the durable part into a tier-1 file with a pointer from the investigation note.

## Cross-linking discipline

Every Tier 1 artifact should be discoverable from **both directions**:

- **Producer:** the `plans/Mn/Mn.x-*.md` that created it has a `Produces:` header line.
- **Consumers:** the `bd` issue(s) that read it have `--append-notes` pointing at the path, and downstream plans name the file in their "File layout" section.
- **Reverse:** the artifact itself has a "consumer map" section (see `ai-hedge-fund-pin-0f6ac48.md §6` for the canonical shape).

An orphaned Tier 1 file is a bug — fix the links, don't leave it for the next agent to rediscover.

## Related directories

- [`../plans/`](../plans/) — the **P** of RPI. Plans declare which `research/<path>` files they produce and consume.
- [`../docs/implementation.md`](../docs/implementation.md) — milestone playbook. Top-level deliverables sometimes name `research/<path>` directly.
- [`../docs/SPEC.md`](../docs/SPEC.md) — authoritative product spec.
