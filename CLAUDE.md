# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project (ai-portfolio-manager).

---

## Behavioral Guidelines

Behavioral guardrails to reduce common LLM coding mistakes. These bias toward caution over speed — for trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

### 5. Research-Plan-Implement (RPI) Framework

When executing work against the milestones in `docs/implementation.md`, follow this order — **investigate before decomposing**:

1. **R — milestone-level investigation.** Write `research/milestones/Mn-investigation.md` covering the architectural unknowns, candidate designs considered and rejected, and an **Open Questions** block. This is the "R" step. Keep it throwaway-ish; nothing here is authoritative.
2. **Resolve open questions with the user in one round.** Do not interleave with decomposition.
3. **Decompose into `bd` subtasks.** Create the epic's child tasks *after* R, using investigation findings to pick the seams. Do not blindly map `implementation.md` deliverable bullets → tasks if the investigation shows a different shape.
4. **P — per-subtask plan.** Write `plans/Mn/Mn.x-<slug>.md` (or put the plan inline in the `bd` issue via `--design` / `--notes` for trivial subtasks — see `plans/README.md`).
5. **I — implement.** Execute the plan into `skills/`, `.agents/`, etc. based tightly on `docs/SPEC.md`. Tier-1 artifacts produced here live at `research/<topic>-<version>.{md,txt}`.

**Exceptions.**
- If `implementation.md §Mn` already reads like a flat list of independent pin/config/document deliverables (e.g. M0), you may skip milestone-level R and do per-subtask research inline.
- If a subtask discovers its own architectural surprise mid-plan, do a mini-R inside that plan, deviate, and record the deviation in the `bd` close note. Do not re-open the milestone-level investigation file.

**Anti-patterns to avoid.**
- Creating `bd` subtasks from `implementation.md` bullets before any investigation — risks splitting work along seams that don't exist yet.
- Running R and writing subtasks simultaneously — open questions get resolved during planning, not before decomposition.

---

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, complete the steps below. The user handles pushing to the remote — do NOT run `git push` or `bd dolt push` yourself.

**WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Stage/commit local changes only if the user asked** - Never push to the remote
5. **Hand off** - Summarize what changed, what's left, and remind the user to push when they're ready

**CRITICAL RULES:**
- NEVER run `git push`, `git push --force`, or `bd dolt push` — the user pushes themselves
- Do not create commits unless the user explicitly asks
- If a push would normally be required to unblock something, say so and stop — don't do it
<!-- END BEADS INTEGRATION -->

---
