# claim-ctl

Concurrency control for parallel research agents. Provides an atomic locking primitive based on filesystem `O_EXCL` via `set -o noclobber`.

## 1. Local Filesystem Caveat

**CRITICAL**: `claim-ctl` must run from a local filesystem. **NFS is strictly forbidden.**
macOS `O_EXCL` atomicity guarantees do not hold over network filesystems. Running this on an NFS mount will result in broken exclusivity and duplicate work.

## 2. Per-Ticker Time Budget

A single ticker must complete processing within the stale threshold (default **30 minutes**).
If a script takes longer, its claim will age out, and another agent running `reclaim-stale` might claim it while the original agent is still working, resulting in duplicate work. Ensure the combined time of MCP fetches, web searches, and model synthesis for a single ticker fits safely within 30 minutes.

## 3. SIGKILL Recovery

If an agent crashes, is killed (e.g., `docker kill` or user closes tab), or gets stuck, it will leave behind a `.claimed` sentinel file. 
`reclaim-stale <mins>` is the **sole recovery command**. 
The reclaim command checks the mtime of the `.claimed` sentinel file. If it's older than the specified threshold, the claim is released (deleted) so another agent can pick it up.

## 4. Command Summary

| Command | Signature | Description |
|---|---|---|
| Phase 2 | `claim-stocks <batch-size> <agent-id>` | Claims a batch of tickers for Phase 2 research. |
| Phase 2 | `complete-stock <ticker> [<ticker>...]` | Marks Phase 2 complete (writes `.done`). |
| Phase 2 | `check-progress` | Prints a single-line summary of Phase 2 progress. |
| Phase 2 | `reclaim-stale [<minutes>]` | Releases Phase 2 claims older than `<minutes>` (default 30). |
| Phase 4 | `claim-scoring <batch-size> <agent-id>` | Claims a batch for Phase 4 scoring. |
| Phase 4 | `complete-scoring <ticker> [...]` | Marks Phase 4 complete; rejects if `## Scoring` is missing. |
| Phase 4 | `check-scoring-progress` | Prints a single-line summary of Phase 4 progress. |
| Phase 4 | `reclaim-scoring-stale [<minutes>]` | Releases Phase 4 claims older than `<minutes>`. |
| Phase 5 | `claim-persona <batch-size> <agent-id>` | Claims a batch for Phase 5 persona cross-check. |
| Phase 5 | `complete-persona <ticker> [...]` | Marks Phase 5 complete; rejects if `## Persona Cross-Check` is missing. |
| Phase 5 | `check-persona-progress` | Prints a single-line summary of Phase 5 progress. |
| Phase 5 | `reclaim-persona-stale [<minutes>]` | Releases Phase 5 claims older than `<minutes>`. |
| Utility | `validate-prerequisites <phase-number>` | Validates that stock files meet preconditions for a phase. |

*(Note: The `claim-ctl` prefix is used in documentation for the tool category, but the physical scripts in `skills/scripts/` are invoked directly by name, e.g., `skills/scripts/claim-stocks.sh`)*

## 5. Execution Venues

Scripts can run in two venues:
- **Native**: Directly on the host OS (`skills/scripts/<cmd>.sh args`).
- **Container**: Via the skill runner (`bin/run-skill skills/scripts/<cmd>.sh args`). The VirtioFS bind mount forwards `O_EXCL` back to the host APFS, so containers race safely on the same underlying host kernel inode.

## 6. Payload Format

`.claimed` and `.done` files contain human-readable key/value text:

```text
agent_id=agent-A
claimed_at_epoch=1766959200
model_id=gpt-5.2
```

- `claimed_at_epoch` / `completed_at_epoch` are informational; `reclaim-stale` uses filesystem mtime.
- `model_id` is automatically populated if the optional `CLAIM_MODEL_ID` environment variable is set. Consumers must not depend on parsing this payload.

## 7. Agent ID Convention

The `agent-id` argument must be a URL-safe string.
- No whitespace
- No `=` characters

*(e.g., `agent-1`, `Cursor-Phase2-A`)*. Violating this will corrupt the key/value payload format inside `.claimed`, though it won't break the atomicity of the lock.
