# M1 — `claim-ctl` investigation

> **R** step of RPI for epic [ai-portfolio-manager-5bg](../../.beads/). Snapshot of the finalized design decisions feeding M1 decomposition. The authoritative behavior lives in [`docs/SPEC.md §6.7, §18.8, §10.3, §10.5, §10.6, §17, §19`](../../docs/SPEC.md) and [`docs/implementation.md §M1`](../../docs/implementation.md).

## Goal recap

Parallel Cursor/Claude sessions (Phase 2, 4, 5) each claim a disjoint batch of tickers from a shared directory, process them, and release them — with zero collisions and an automatic recovery path for crashed/killed sessions. Three separate claim namespaces (`claims/`, `scoring-claims/`, `persona-claims/`) mirror the three phases. The acceptance bar: 3 racing shells against 15 tickers produce a clean partition, and stale-reclaim unsticks zombie locks past a 30-minute threshold.

---

## 1. Lock primitive

Use `set -o noclobber` with a `.claimed` sentinel file inside a pre-created per-ticker directory, as SPEC §6.7 mandates. The per-ticker directory itself is created idempotently via `mkdir -p` by Phase 1 before any claim attempt (see M8 acceptance: *`claims/{TICKER}/` for every snapshot row*).

The primitive resolves to `open(O_CREAT|O_EXCL|O_WRONLY)` at the kernel layer — exactly-one-creator-wins, enforced by APFS. This holds in both execution venues that M1 must support:

- **Native host execution** — bash on macOS against APFS.
- **`bin/run-skill`** — Docker container writing through a VirtioFS bind mount. VirtioFS forwards `O_CREAT|O_EXCL` to host APFS, so the bind-mounted `.claimed` file is a host-side inode and two containers race on the same kernel inode.

NFS is forbidden by the project (documented in `skills/scripts/README.md`) so cross-host concurrency is out of scope.

---

## 2. Stale detection

**Mechanism:** mtime on `.claimed`. No heartbeat.

A claim goes stale when the claiming agent died (SIGKILL, container crash, user closed the Cursor tab) without writing `.done`. `reclaim-stale [<minutes>]` uses `find -mmin` / `stat` on the `.claimed` inode and removes entries older than the threshold (default 30 min per SPEC §10.3).

All mtimes are written and read on the host APFS regardless of which container wrote them — one clock, one filesystem, no skew.

**Budget constraint:** a single ticker must complete within the stale threshold. With 30 min and per-ticker Phase 2 work (one `fundamentals-fetch` MCP call + 2–5 web searches + compose), this is ample. Phase 4 / Phase 5 per-ticker work is lighter. Document the per-ticker budget in `skills/scripts/README.md` and in the Phase 2/4/5 prompts; the threshold stays user-configurable via the CLI arg.

---

## 3. Script layout — Option B (shared library + thin shims)

SPEC §18.8 names 13 commands; SPEC §17 pins three separate claim namespaces:

```
temp/research/claims/{TICKER}/         # Phase 2
temp/research/scoring-claims/{TICKER}/ # Phase 4
temp/research/persona-claims/{TICKER}/ # Phase 5
```

### What the variants differ on

| Dimension | Phase 2 | Phase 4 | Phase 5 |
|---|---|---|---|
| Claim root | `temp/research/claims/` | `temp/research/scoring-claims/` | `temp/research/persona-claims/` |
| `complete-*` validation | none (just write `.done`) | reject if stock file lacks `## Scoring` (SPEC §10.5) | reject if stock file lacks `## Persona Cross-Check` (header-only check) |
| `validate-prerequisites` check | N/A | `[Fund]` + `[Valu]` tags present | `## Scoring` block present |

Every other behavior (atomic `noclobber` claim, mtime reclaim, `.done` write, progress counting) is identical.

### Shape

- `skills/scripts/_claim-common.sh` — one library with the claim/release/reclaim/progress primitives, parameterized on `CLAIM_ROOT` and an optional completion-validation hook.
- 12 thin shims (`claim-stocks.sh`, `complete-stock.sh`, `claim-scoring.sh`, `complete-scoring.sh`, `check-scoring-progress.sh`, `reclaim-scoring-stale.sh`, `claim-persona.sh`, `complete-persona.sh`, `check-persona-progress.sh`, `reclaim-persona-stale.sh`, `check-progress.sh`, `reclaim-stale.sh`) — each sets phase-specific vars and calls the library entrypoint.
- `validate-prerequisites.sh` — separate script. It is a grep + existence check over stock files, not a claim-ctl operation, and does not source `_claim-common.sh`.

Sourced files get explicit `# shellcheck source=./_claim-common.sh` directives.

### `validate-prerequisites.sh` behavior

Per SPEC §18.8 `<phase-number>` argument:

- `validate-prerequisites 4` — every `temp/research/stocks/{TICKER}.md` must have `[Fund]` and `[Valu]` tag lines.
- `validate-prerequisites 5` — every stock file must have a `## Scoring` block.
- Exit non-zero on any missing prerequisite; print offending tickers to stderr.

---

## 4. Concurrent test design

### `tests/claim-ctl/concurrent.sh`

Runs natively on host (fastest, and the primitive proof is at the APFS layer anyway).

```
1. Fixture setup:
   - rm -rf temp/research/claims
   - mkdir -p temp/research/claims/T{01..15}    # 15 pre-seeded ticker dirs
2. Start 3 subshells in the background (&). Each runs
   `claim-stocks 5 agent-X` after a 0.1s settle.
3. wait for all 3 pids.
4. Assertions:
   - count of *.claimed files equals 15
   - union of claimed tickers has cardinality 15 (coverage)
   - no ticker has >1 claim (exclusivity — O_EXCL held)
   - agent IDs inside each .claimed are one of {A, B, C}
```

Assertions are outcome-based (coverage + exclusivity), not timing-based. A 7/4/4 partition is as valid as 5/5/5. If `O_EXCL` is broken, any amount of racing surfaces it.

A Docker/VirtioFS smoke test via `bin/run-skill` is a future nice-to-have, not part of M1 acceptance.

### `tests/claim-ctl/stale-reclaim.sh`

```
1. Seed 3 ticker dirs.
2. claim-stocks 3 agent-A → 3 .claimed files written, mtime = now.
3. touch -t <31 min ago> on one of the .claimed files.
4. reclaim-stale 30 → removes the aged .claimed, leaves the other two.
5. claim-stocks 3 agent-B → claims exactly the aged ticker.
```

Compute the past timestamp with `date -v-31M '+%Y%m%d%H%M.%S'` on BSD (macOS host) and `date -d '31 min ago' ...` on GNU (Debian container). Tests must handle both.

### Completion-validation tests

Added for M1 coverage of the `## Scoring` and `## Persona Cross-Check` guardrails:

- `tests/claim-ctl/complete-scoring-missing.sh` — stock file lacks `## Scoring`; `complete-scoring INFY.NS` exits non-zero, no `.done` written. (Already in epic acceptance.)
- `tests/claim-ctl/complete-scoring-ok.sh` — stock file has `## Scoring`; `complete-scoring INFY.NS` exits 0 and writes `.done`.
- `tests/claim-ctl/complete-persona-missing.sh` — stock file lacks `## Persona Cross-Check`; `complete-persona INFY.NS` exits non-zero, no `.done` written.
- `tests/claim-ctl/complete-persona-ok.sh` — stock file has `## Persona Cross-Check`; `complete-persona INFY.NS` exits 0 and writes `.done`.

---

## 5. SIGKILL recovery

No additional mechanism beyond `reclaim-stale`. A killed agent leaves only a `.claimed` sentinel (possibly empty if SIGKILLed between `open(O_EXCL)` and the `echo`); `reclaim-stale` only checks mtime, so empty payloads are handled cleanly. A re-claimer overwrites the sentinel with its own agent-id. `docker kill skills-env` follows the same path — bind-mounted `.claimed` files persist on the host.

Document in `skills/scripts/README.md` that `reclaim-stale <mins>` is the sole recovery command.

---

## 6. Behavior details

### 6.1 Ticker-pool source

`claim-stocks <batch-size> <agent-id>` scans `temp/research/claims/*/` for dirs without `.claimed`. Phase 1 (M7/M8) is responsible for seeding those dirs. The M1 concurrent-test fixture pre-creates 15 dirs manually.

All scripts resolve paths from the repository root, not from the caller's current directory. Implementation should derive `REPO_ROOT` from the script location (`skills/scripts/../..`) and allow tests to override it with an env var such as `CLAIM_CTL_ROOT` so fixtures can run in an isolated temp tree.

### 6.2 Iteration order

Sort candidate tickers lexicographically (`find ... -type d | sort`) so a specific race is reproducible.

### 6.3 `claim-stocks` output contract

- One ticker per line on stdout for each successfully claimed ticker.
- Exit 0 regardless of how many were claimed (including 0).
- Errors (bad args, missing claim root) exit non-zero with a message on stderr.

### 6.4 `check-progress` output

Human-readable by default. No JSON mode unless a downstream consumer appears. Counts files, does not parse `.claimed` contents (empty payloads after SIGKILL must not break progress reporting).

### 6.5 `complete-scoring` validation

```sh
grep -qE '^## Scoring[[:space:]]*$' "$STOCK_FILE"
```

Header presence only. Content validity is stock-linter / Phase 3 verifier territory.

### 6.6 `complete-persona` validation

Same shape against `^## Persona Cross-Check[[:space:]]*$`. Header presence only (ETF skip path still writes the header per SPEC §10.6). Keeps the guardrail cheap without coupling M1 to persona body content.

### 6.7 `.claimed` payload format

Human-readable key/value text:

```text
agent_id=agent-A
claimed_at_epoch=1766959200
model_id=gpt-5.2
```

- `claimed_at_epoch` is informational only; stale detection uses filesystem mtime.
- `model_id` is populated from the optional `CLAIM_MODEL_ID` env var when provided by the caller. CLI signatures stay as SPEC §18.8 defines them; no positional arg for model ID.
- Consumers must not depend on parsing the payload.

### 6.8 `shellcheck`

M1 acceptance #4: `shellcheck skills/scripts/*.sh` clean, including `_claim-common.sh`. Write with `set -euo pipefail`, quoted variables, `[[ ]]` over `[ ]`, and `# shellcheck source=...` directives on shims.

---

## 7. Operational contract

### 7.1 `.done` sentinel

- **Path.** Same per-ticker directory as `.claimed`, file named `.done`.
- **Payload.** Same human-readable key/value shape as `.claimed` (`agent_id=...`, `completed_at_epoch=...`, optional `model_id=...`). Consumers must not depend on parsing it; the existence of the file is the signal.
- **Availability rule.** A ticker dir is "available to claim" iff it contains **neither `.claimed` nor `.done`**. `claim-stocks` skips dirs that have either.
- **`reclaim-stale` scope.** Operates on `.claimed` only. A completed ticker (has `.done`) stays completed — reclaim restores claimability for abandoned work, not for finished work.

### 7.2 `complete-*` semantics

Applies uniformly to `complete-stock`, `complete-scoring`, `complete-persona`.

- **Prerequisite check.** `.claimed` must exist in the ticker's dir. If it doesn't, exit non-zero with a message on stderr. No "complete without claim".
- **Agent-id enforcement.** None. `agent_id` in `.claimed` is metadata only; any invoker may complete any claimed ticker. (Useful for recovery flows where a different session finishes the work.)
- **Idempotency.** If `.done` already exists, log a notice on stderr and exit 0 (no-op success). Do not rewrite `.done`.
- **Header validation** (scoring/persona variants). Runs after the prerequisite check; on failure, no `.done` is written and exit is non-zero.
- **Multi-arg partial-failure behavior** (`complete-stock A B C`). Not pinned here — decide at implementation time based on what reads best. A reasonable default is "continue past failures, exit non-zero if any ticker failed, summarize on stderr", but leave room to change.

### 7.3 `check-progress` output

Single-line summary. Suggested shape:

```
total=15 available=3 claimed=8 completed=4 stale=0
```

- `total` — count of ticker dirs under the phase's claim root.
- `available` — dirs with neither `.claimed` nor `.done`.
- `claimed` — dirs with `.claimed` and no `.done`.
- `completed` — dirs with `.done`.
- `stale` — dirs with `.claimed` and mtime older than the default 30-min threshold.

One-liner keeps parsing trivial for Phase-2/4/5 prompts; human reads it fine too.

### 7.4 `claim-stocks` edge cases

- `batch-size <= 0` — exit non-zero with a usage message on stderr.
- `batch-size > available` — claim what's available, exit 0. Zero claims is a valid no-op (nothing left to do).

### 7.5 `agent-id` format

Documented as a URL-safe string with no whitespace and no `=`. Not validated by the scripts; caller's responsibility. Violations corrupt the `.claimed` payload but don't affect correctness of the atomic claim itself.

### 7.6 `skills/scripts/README.md` outline

- Filesystem caveat — must run from a local filesystem; NFS forbidden.
- Per-ticker time budget — single ticker must complete within the stale threshold (default 30 min); document consequences of exceeding it.
- SIGKILL recovery — `reclaim-stale <mins>` is the sole recovery command; a killed agent leaves only a `.claimed` sentinel.
- Command summary — one-line description per subcommand with its SPEC §18.8 signature.
- Execution venues — works both natively (`skills/scripts/<cmd>.sh args`) and via `bin/run-skill skills/scripts/<cmd>.sh args`.
- `.claimed` / `.done` payload format and the `CLAIM_MODEL_ID` env var for optional model-ID metadata.
- Agent-id convention — URL-safe string, no whitespace, no `=`.

---

## 8. Final decisions / no remaining blockers

- Script layout: **Option B** — shared `_claim-common.sh` plus thin phase-specific shims.
- Phase-5 completion validation: **yes** — `complete-persona.sh` requires a `## Persona Cross-Check` header before writing `.done`.
- Test venue: native host for M1 acceptance; Docker/VirtioFS smoke coverage is optional future work.
- Stale detection: `.claimed` mtime only; no heartbeat.
- Progress output: single-line human-readable key/value summary; no JSON mode.
- Metadata: `.claimed` and `.done` are human-readable key/value files; optional `model_id` comes from `CLAIM_MODEL_ID`.

Nothing else blocks decomposition. The remaining details above are implementation-level choices with clear defaults.

---

## What's not in scope for M1

- **Snapshot seeding** (`temp/research/claims/{TICKER}/` dir creation) — M7/M8.
- **Phase 2/4/5 prompts** invoking claim-ctl — M7.
- **Stock-file linter** verifying `[Tag]` lines and period annotations — M9.
- **`scoring-engine` integration** — M3/M10.
- **Docker-in-Docker or multi-host concurrency** — forbidden by SPEC (no-NFS) and by the `skills/scripts/README.md` deliverable.
