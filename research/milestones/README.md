# research/milestones/

Raw exploration notes for each milestone in [`docs/implementation.md`](../../docs/implementation.md). This is the **R** of the Research-Plan-Implement (RPI) framework defined in [`CLAUDE.md §5`](../../CLAUDE.md).

## What lives here

Unstructured, throwaway-ish notes from investigating a milestone *before* you commit to a design:

- MCP smoke-test logs (what each tool returns, latency, failure modes)
- Schema dumps, API probes, fixture captures
- Decisions considered and rejected
- Open questions, unknowns
- Links to external references (upstream SHAs, docs, issues)

Investigation notes here are **inputs to the plan**, not the plan itself.

## Naming convention

One file per milestone:

```
Mn-investigation.md
```

Examples:

- `M0-investigation.md` — Wealthfolio schema dump, MCP smoke tests, philosophy YAML shape
- `M3-investigation.md` — ai-hedge-fund SHA pin rationale, persona module port notes
- `M14-investigation.md` — MCP coverage audit against Screener.in

For topics that span multiple milestones (e.g. a cross-cutting API exploration), use a descriptive kebab-case name: `mcp-india-coverage-audit.md`.

## Related directories

- [`../archive/`](../archive/) — historical exploration from pre-v1.2 design. Do not add to archive; it is frozen.
- [`../../plans/`](../../plans/) — the **P** of RPI: technical design docs distilled from investigation (one `plans/Mn/plan.md` per milestone).
- [`../../docs/implementation.md`](../../docs/implementation.md) — the milestone playbook (`§Mn` for each).
- [`../../docs/SPEC.md`](../../docs/SPEC.md) — the authoritative product spec. Investigation often cites specific `§` sections.

## Workflow for starting a milestone

**Investigate before decomposing.** The order below matters — subtasks created before investigation risk splitting work along the wrong seams.

```
1. bd show <Mn-epic-id>                       # Read acceptance criteria + risks
2. Read docs/implementation.md §Mn            # Deliverables list
3. Read SPEC.md sections referenced by §Mn    # Authoritative behavior
4. Write research/milestones/Mn-investigation.md  (← you are here)
   - Cover architectural unknowns
   - List candidate designs considered AND rejected
   - End with an Open Questions block
5. Resolve Open Questions with the user in one round
6. Decompose the epic into bd child tasks     # Only now — using findings
7. Per-subtask: plans/Mn/Mn.x-<slug>.md (or inline in bd for trivial ones)
8. Implement
```

**When to skip milestone-level R.** If `docs/implementation.md §Mn` is a flat list of independent pin/config/document deliverables with no architectural decisions (M0 is the canonical example), skip straight to decomposition and do per-subtask research inline in each plan.

**When a subtask surprises you mid-plan.** Do a mini-R inside that specific plan file, deviate, and record the deviation in the bd close note. Do not re-open `Mn-investigation.md` — it is a snapshot of pre-decomposition thinking.

Nothing here is considered authoritative. If a finding is important, promote it into the plan, the SPEC, or a bd issue comment.
