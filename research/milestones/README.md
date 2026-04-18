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

```
1. bd show <Mn-epic-id>                       # Read acceptance criteria + risks
2. Read docs/implementation.md §Mn            # Deliverables list
3. Read SPEC.md sections referenced by §Mn    # Authoritative behavior
4. Write research/milestones/Mn-investigation.md  (← you are here)
5. Write plans/Mn/plan.md                     # Or put plan inline in bd epic
6. Decompose deliverables into bd child tasks
7. Implement
```

Nothing here is considered authoritative. If a finding is important, promote it into the plan, the SPEC, or a bd issue comment.
