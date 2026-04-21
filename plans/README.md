# plans/

Technical design documents for each milestone in [`../docs/implementation.md`](../docs/implementation.md). This is the **P** of the Research-Plan-Implement (RPI) framework defined in [`CLAUDE.md §5`](../CLAUDE.md).

## What lives here

One subdirectory per milestone, with **one plan file per subtask**. Plans are committed *before* any implementation code is written. A plan is the answer to: *"Given the deliverable for this subtask and the behavior in `SPEC.md`, how exactly are we going to build this?"*

A good plan covers:

- **Scope.** Which `implementation.md §Mn` deliverables are in / out.
- **Approach.** The chosen design, with 1–2 sentences on each rejected alternative.
- **File layout.** Exact paths for new code, tests, fixtures, configs.
- **SPEC references.** Every section of [`../docs/SPEC.md`](../docs/SPEC.md) this milestone must honor, by section number.
- **Dependencies on other milestones.** Which bd epics must be complete; which artifacts they produce that this plan consumes.
- **Task decomposition.** The bd child tasks to create under the epic. Each task should map to one deliverable bullet in `implementation.md §Mn`.
- **Verification.** How the acceptance criteria in the bd epic body get checked.
- **Known risks / open questions.** Cross-link to bd issues or human decisions.

Plans are **living** until the milestone closes. Once the epic is closed, the plan is historical but stays in place.

## Directory layout

One subdirectory per milestone, named `Mn/`. Inside, one plan file per subtask, named `Mn.x-<slug>.md` where `Mn.x` matches the bd task and `<slug>` is a short kebab-case name. Additional artifacts (diagrams, scratch notes, sub-designs) live alongside as needed.

```
plans/
├── README.md                    ← you are here
├── M0/
│   ├── M0.1-wealthfolio.md      ← plan for the M0.1 bd task
│   ├── M0.2-ai-hedge-fund-pin.md
│   ├── ...
│   └── <optional artifacts>     ← diagrams, tables, sub-design notes
├── M1/
│   ├── M1.1-claim-ctl-phase2.md
│   └── ...
├── ...
└── M15/
    └── M15.1-....md
```

Cross-cutting designs that span multiple milestones can sit at the top level with a descriptive kebab-case name: `plans/prompt-versioning-strategy.md`. A milestone that is genuinely atomic (single deliverable) can use `plans/Mn/plan.md` instead of the per-subtask naming.

## When to skip the file

[`CLAUDE.md §5`](../CLAUDE.md) permits putting the plan directly in the `bd` issue (via `--design` or `--append-notes`) instead of here. Use the bd-inline form when:

- The subtask is a single deliverable with no architectural decisions.
- The plan is short enough to fit in one `bd show` screen.
- There's no diagram, table, or long code block that would be awkward in a bd issue body.

Prefer a file in `plans/Mn/Mn.x-<slug>.md` when the plan needs review, diffing, or references from multiple bd issues.

## Related directories

- [`../research/milestones/`](../research/milestones/) — the **R** of RPI: raw investigation notes that fed a plan.
- [`../docs/implementation.md`](../docs/implementation.md) — the milestone playbook.
- [`../docs/SPEC.md`](../docs/SPEC.md) — the authoritative product spec.
- [`../.beads/`](../.beads/) — epic IDs and acceptance criteria live in `bd`, not here.

## Workflow for writing a plan

```
1. Claim the subtask:          bd update <Mn.x-id> --claim
2. Finish R (if needed):       research/milestones/Mn-investigation.md
3. Draft this file:            plans/Mn/Mn.x-<slug>.md
4. Review against SPEC:        every acceptance criterion traces to a section
5. Link the plan to bd:        bd update <Mn.x-id> --notes "See plans/Mn/Mn.x-<slug>.md"
6. Start implementing.
```
