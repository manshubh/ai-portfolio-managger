# THIRD_PARTY.md

> Single source of truth for external-dependency pins. Each entry below names one upstream artifact, its exact pin, why it is pinned that way, and — where redistribution is in play — the full license text at pin time. Produced by [M0.4](plans/M0/M0.4-third-party.md); consumed by M3 (the `skills/scoring-engine/` port) and revisited whenever a new upstream source is pinned per [docs/implementation.md §3.3](docs/implementation.md).

## 1. Taxonomy and update protocol

Two axes determine how an upstream shows up here:

- **Vendored vs invoked.** Code we copy into `skills/` (§2) carries license obligations because we redistribute it. Code we run as a black box via MCP, `uvx`, `npx`, or shell (§3, §4) carries version pins so behavior is reproducible but no redistribution surface.
- **Code vs data.** Software whose *data* we read but whose *code* we never touch or redistribute is listed separately (§5) with a version pin and an upstream license link, but no inlined license body.

Update protocol is defined in §6. The revision log at §7 records every edit to this file since M0.4 initial write.

## 2. Ported source code (vendored under `skills/`)

### 2.1 `virattt/ai-hedge-fund` @ `0f6ac48…`

**Pin.** Consumed by M3's `skills/scoring-engine/` port per [SPEC §6.3](docs/SPEC.md).

| Field | Value |
|---|---|
| Upstream | <https://github.com/virattt/ai-hedge-fund> |
| Pinned SHA | `0f6ac487986f7eb80749ed42bd26fb8330c450db` |
| Short SHA | `0f6ac48` |
| Commit date (UTC) | `2026-04-17T21:29:41Z` |
| Commit URL | <https://github.com/virattt/ai-hedge-fund/commit/0f6ac487986f7eb80749ed42bd26fb8330c450db> |
| Pin date | `2026-04-21` |

**Rationale.** Pinned at the SHA verified during M0.2: all 10 port-target files return HTTP 200 at this SHA, and the immutable SHA insulates this file from any future upstream relicense or force-push. Full manifest: [research/ai-hedge-fund-pin-0f6ac48.md](research/ai-hedge-fund-pin-0f6ac48.md).

**License status.** `README: claims MIT · LICENSE file: missing · GitHub API license field: null`

**Disclosure.** The upstream repository `virattt/ai-hedge-fund` at SHA `0f6ac487986f7eb80749ed42bd26fb8330c450db` does **not** ship a `LICENSE` file, and GitHub's API reports the repository's license field as `null`. The README prose asserts MIT. We proceed under that asserted MIT grant and capture the canonical MIT template below with a reconstructed copyright line (`Copyright (c) 2024 virattt`) in lieu of a named author from a LICENSE artifact. If upstream publishes a LICENSE file with different text or a different copyright line, this manifest becomes historical and `THIRD_PARTY.md` is updated to match the authoritative artifact.

**Captured license text (standard MIT template, reconstructed copyright line):**

```
MIT License

Copyright (c) 2024 virattt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**Port targets.** M3 copies these 10 files. `Ported?` is `pending` at M0.4 close; M3 flips each cell to `ported <short-sha>` when the corresponding file lands under `skills/scoring-engine/`. `Local path` is the proposed destination per [docs/implementation.md §M3](docs/implementation.md); M3 may rename at port time and rewrite the cell.

| Upstream path | Raw blob at pinned SHA | Ported? | Local path |
|---|---|---|---|
| `src/agents/fundamentals.py` | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/fundamentals.py) | pending | `skills/scoring-engine/fundamentals.py` |
| `src/agents/phil_fisher.py` | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/phil_fisher.py) | pending | `skills/scoring-engine/phil_fisher.py` |
| `src/agents/risk_manager.py` | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/risk_manager.py) | pending | `skills/scoring-engine/risk_manager.py` |
| `src/agents/ben_graham.py` | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/ben_graham.py) | pending | `skills/scoring-engine/personas/graham.py` |
| `src/agents/warren_buffett.py` | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/warren_buffett.py) | ported `0f6ac48` | `skills/scoring_engine/personas/buffett.py` |
| `src/agents/charlie_munger.py` | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/charlie_munger.py) | pending | `skills/scoring-engine/personas/munger.py` |
| `src/agents/mohnish_pabrai.py` | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/mohnish_pabrai.py) | pending | `skills/scoring-engine/personas/pabrai.py` |
| `src/agents/rakesh_jhunjhunwala.py` | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/rakesh_jhunjhunwala.py) | ported `0f6ac48` | `skills/scoring_engine/personas/jhunjhunwala.py` |
| `src/agents/aswath_damodaran.py` | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/aswath_damodaran.py) | pending | `skills/scoring-engine/personas/damodaran.py` |
| `src/agents/peter_lynch.py` | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/peter_lynch.py) | pending | `skills/scoring-engine/personas/lynch.py` |

## 3. Invoked external tools (no source vendored)

Install and registration prose is owned by [config/mcp-servers.md](config/mcp-servers.md); entries below carry only the pin, license, and one-line rationale.

### 3.1 `finstack-mcp` 0.10.0

- **Pin.** `finstack-mcp` 0.10.0 (PyPI). Invoked via `uvx finstack-mcp@0.10.0` per [config/mcp-servers.md §Per-MCP table](config/mcp-servers.md).
- **Upstream.** <https://github.com/finstacklabs/finstack-mcp>
- **Rationale.** Primary fundamentals + SEC + India FII/DII MCP per [research/mcp-gaps.md §1](research/mcp-gaps.md); pinned to the latest published release at M0.3 smoke-test time.
- **License.** MIT. Text captured from the PyPI sdist `finstack_mcp-0.10.0.tar.gz` (fetched from `files.pythonhosted.org` 2026-04-23; upstream ships no git tag matching the PyPI version, so the sdist artifact is the pin-time authoritative source).

```
MIT License

Copyright (c) 2026 SpawnAgent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 3.2 `nsekit-mcp` 0.0.22

- **Pin.** `nsekit-mcp` 0.0.22 (PyPI). Invoked via `uvx nsekit-mcp@0.0.22` per [config/mcp-servers.md §Per-MCP table](config/mcp-servers.md).
- **Upstream.** <https://github.com/Prasad1612/NseKit-MCP>
- **Rationale.** India-specific price history + corporate actions MCP per [research/mcp-gaps.md §1](research/mcp-gaps.md); pinned at smoke-test time despite the missing-license posture because the `corporate_actions` tool is the only Tier-A path for India corp-actions per [SPEC §6.2](docs/SPEC.md).
- **License status.** No `LICENSE` file, no license declared in `pyproject.toml`, GitHub repo metadata field is null. Proceed with risk awareness — do not redistribute; confine use to local tool invocation. Revisit if usage extends beyond local Phase 1 corp-actions queries. (Source: [config/mcp-servers.md §5](config/mcp-servers.md), reproduced here verbatim as the canonical license disclosure.)
- **Disclosure.** NseKit-MCP at 0.0.22 ships no license artifact and no upstream license declaration. We do not vendor any of its source; we only invoke it locally as an MCP tool under `uvx`. No redistribution surface exists in this project. If NseKit becomes a distribution blocker later (e.g., this project is published as a product), a fork-or-replace `bd` ticket is filed and this entry is rewritten to match the resolved license posture.

### 3.3 `nse-bse-mcp` 0.1.5

- **Pin.** `nse-bse-mcp` 0.1.5 (npm). Invoked via `npx -y nse-bse-mcp@0.1.5` + `npx -y mcp-remote@latest http://localhost:3000/mcp --allow-http` per [config/mcp-servers.md §4](config/mcp-servers.md).
- **Upstream.** <https://github.com/bshada/nse-bse-mcp>
- **Rationale.** India EOD live-quote fallback per [research/mcp-gaps.md §1](research/mcp-gaps.md); flagged as drop-candidate at M9 kickoff per [research/mcp-gaps.md §4](research/mcp-gaps.md) (1/59 tool utilization; subsumed by nsekit `equity_price_history(period="1D")`).
- **License.** MIT. Text captured from the npm tarball `nse-bse-mcp-0.1.5.tgz` (fetched from `registry.npmjs.org` 2026-04-23; upstream ships no git tags at all, so the npm tarball is the pin-time authoritative source).

```
MIT License

Copyright (c) 2025 NSE-BSE MCP Server

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 4. Runtime prerequisites

### 4.1 `uv` (provides `uvx`)

- **Pin policy.** Latest stable upstream release; no exact version pin. The host machine must have a working `uvx` on `PATH` before any `uvx`-launched MCP (§3.1, §3.2) will start. Install: `brew install uv` per [config/mcp-servers.md §3](config/mcp-servers.md).
- **Upstream.** <https://github.com/astral-sh/uv>
- **Rationale.** Runtime prerequisite for `uvx`-launched MCPs (finstack, nsekit); carried here per the [M0.3 plan's](plans/M0/M0.3-mcp-servers.md) explicit hand-off.
- **License.** Dual `Apache-2.0 OR MIT`. Both `LICENSE-APACHE` and `LICENSE-MIT` exist in upstream at `main` (verified 2026-04-23); the GitHub API reports `Apache-2.0` as the primary. No body inlined — we do not redistribute `uv`'s source, so the upstream link is the audit trail.

## 5. External data consumers

### 5.1 Wealthfolio v3.3.0 (consumed-but-not-vendored)

We read the Wealthfolio SQLite database read-only via `sqlite3 -readonly` and consume a small set of named queries defined in `skills/sql/wealthfolio-queries.sql`. We do **not** vendor, modify, or redistribute any Wealthfolio source code, UI assets, or migrations — this project's relationship to Wealthfolio is strictly that of a passive consumer of the locally-installed app's on-disk state. The pinned consumer-side artifact is the schema dump at [research/wealthfolio-schema-v3.3.0.txt](research/wealthfolio-schema-v3.3.0.txt), not Wealthfolio's own source.

| Field | Value |
|---|---|
| Product | Wealthfolio (Tauri desktop app, macOS bundle) |
| Version (`CFBundleShortVersionString`) | `3.3.0` |
| Build (`CFBundleVersion`) | `20260301.1` |
| Upstream | <https://github.com/afadil/wealthfolio> |
| Upstream LICENSE | <https://github.com/afadil/wealthfolio/blob/main/LICENSE> |
| Install + DB-mount contract | [config/wealthfolio.md](config/wealthfolio.md) |

No license body is inlined here: we have no redistribution surface. Upgrading Wealthfolio is a separate `bd` ticket per [SPEC §19.14](docs/SPEC.md); that ticket also refreshes §7's revision log.

## 6. Update protocol

Who owns what, and when entries change:

- **§2.1 port-target rows — M3.** M3 flips each `Ported?` cell from `pending` to `ported <commit-sha>` when the corresponding file lands under `skills/scoring-engine/`. M3 may also rewrite the `Local path` column if the port uses a different filename. Each M3 port commit is one row edit; no other §2.1 field changes.
- **§2.1 SHA — frozen.** The pinned SHA does not change. If upstream relicenses or force-pushes, M3 and/or a follow-up `bd` ticket decide whether to re-pin at a new SHA; that is a new revision-log row, not an edit in place.
- **§3.x MCP pins — dependency-bump `bd` ticket.** Version bumps are a dedicated `bd` ticket of type `dependency-bump` per [SPEC §19.14](docs/SPEC.md). The ticket is responsible for: (a) updating the pin line, (b) re-fetching the LICENSE body from the new release artifact (for §3.1 and §3.3), (c) re-verifying the license-status block (for §3.2), and (d) appending a row to §7.
- **§3.2 NseKit license wording — mirror of `config/mcp-servers.md §5`.** The authoritative source is `config/mcp-servers.md`. If that wording changes, this section is re-synced in the same commit; drift is a lint failure (see the [M0.4 plan's](plans/M0/M0.4-third-party.md) verification table).
- **§4 `uv` — bumped only on breakage.** If MCP install instructions stop working with the host's `uv`, the entry is revisited. Not on a schedule.
- **§5.1 Wealthfolio — schema-drift `bd` ticket.** Per [SPEC §19.14](docs/SPEC.md), any Wealthfolio upgrade requires dumping `.schema`, diffing against the committed dump, and reviewing `skills/sql/wealthfolio-queries.sql`. The same ticket bumps the version cell above and appends a row to §7.

## 7. Revision log

| Date | Section | Change |
|---|---|---|
| 2026-04-23 | All | Initial write. Five pins (§2.1 ai-hedge-fund @ `0f6ac48`; §3.1 finstack-mcp 0.10.0; §3.2 nsekit-mcp 0.0.22; §3.3 nse-bse-mcp 0.1.5; §5.1 Wealthfolio v3.2.1) plus §4.1 `uv` runtime prerequisite. MIT bodies for §2.1, §3.1, §3.3 captured; §3.2 no-license disclosure mirrors `config/mcp-servers.md §5`; §5.1 no license body inlined (consumed-but-not-vendored). Produced by [plans/M0/M0.4-third-party.md](plans/M0/M0.4-third-party.md). |
| 2026-05-05 | §5.1 | Wealthfolio upgrade v3.2.1 → v3.3.0 (build `20260301.1` unchanged). Schema drift confined to `goals` / `goals_allocation` / `goal_plans` (new) / `sync_entity_metadata.last_op` (new column); none of these are read by `skills/sql/wealthfolio-queries.sql`, so no query edits needed. Schema dump renamed `research/wealthfolio-schema-v3.2.1.txt` → `wealthfolio-schema-v3.3.0.txt`. Position JSON shape pin carried forward unchanged (live re-verification deferred to M2.14). Produced by bd `ai-portfolio-manager-wjw` (M2.13). |
