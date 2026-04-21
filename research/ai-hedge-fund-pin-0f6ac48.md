# ai-hedge-fund — pin manifest (`0f6ac48`)

> Authoritative pin manifest for `virattt/ai-hedge-fund`. Produced by M0.2 per
> [plans/M0/M0.2-ai-hedge-fund-pin.md](../plans/M0/M0.2-ai-hedge-fund-pin.md).
> Consumed by M0.4 (`THIRD_PARTY.md`) and M3 (scoring-engine port).

## 1. Pin metadata

| Field | Value |
|---|---|
| Upstream repo | [`virattt/ai-hedge-fund`](https://github.com/virattt/ai-hedge-fund) |
| Pinned SHA | `0f6ac487986f7eb80749ed42bd26fb8330c450db` |
| Short SHA | `0f6ac48` |
| Commit date (UTC) | `2026-04-17T21:29:41Z` |
| Commit message (first line) | `Create initial data layer` |
| Pin date | `2026-04-21` |
| Commit URL | <https://github.com/virattt/ai-hedge-fund/commit/0f6ac487986f7eb80749ed42bd26fb8330c450db> |

## 2. Re-query log

Re-run at pin time (2026-04-21), per the selection rule in the plan.

**HEAD query:**

```bash
curl -sS -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/virattt/ai-hedge-fund/commits/main \
  | jq -r '.sha, .commit.author.date, .commit.message'
```

```
0f6ac487986f7eb80749ed42bd26fb8330c450db
2026-04-17T21:29:41Z
Create initial data layer
```

**Compare vs research SHA (`0f6ac48...`):**

```bash
curl -sS -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/virattt/ai-hedge-fund/compare/0f6ac487986f7eb80749ed42bd26fb8330c450db...main \
  | jq '{status, ahead_by, behind_by, total_commits}'
```

```json
{
  "status": "identical",
  "ahead_by": 0,
  "behind_by": 0,
  "total_commits": 0
}
```

**Selection rule applied:** `ahead_by == 0` and `behind_by == 0` ⇒ HEAD equals the
research SHA. Per the plan's selection rule branch 1, pin the research SHA
unchanged: `0f6ac487986f7eb80749ed42bd26fb8330c450db`.

## 3. Rationale

- **Reproducible.** HEAD is identical to the SHA surfaced during M0-investigation
  on 2026-04-18; no drift in the 3-day window between research and pin.
- **Port targets intact.** All 10 files SPEC §6.3 names for the M3 scoring-engine
  port resolve to HTTP 200 at this SHA (see §4). The pin is safe against
  file-rename / deletion surprises at port time.
- **Proxy for "green main."** Upstream has no CI badge and no release tags, so
  we cannot mechanically verify main is green. The 10-file HTTP-200 check is
  our proxy — the files we need exist and are syntactically retrievable.
  Deeper verification (importability, test-passing) is an M3 concern.
- **No behavioral regressions to consider.** The compare is empty, so the
  plan's "inspect diffs of touched port-list files" branch does not apply.
- **Immutable anchor for licensing posture.** SHA-pinning insulates us from
  a future upstream relicense or force-push: our `THIRD_PARTY.md` entry
  cites the commit, not the branch.

## 4. Port targets at this SHA

Files the M3 scoring-engine port will read, per SPEC §6.3. Verified 2026-04-21
via `curl -sS -o /dev/null -w '%{http_code}'` against the raw blob URL:

| File | HTTP | Raw blob at pinned SHA |
|---|---|---|
| `src/agents/fundamentals.py` | 200 | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/fundamentals.py) |
| `src/agents/phil_fisher.py` | 200 | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/phil_fisher.py) |
| `src/agents/risk_manager.py` | 200 | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/risk_manager.py) |
| `src/agents/ben_graham.py` | 200 | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/ben_graham.py) |
| `src/agents/warren_buffett.py` | 200 | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/warren_buffett.py) |
| `src/agents/charlie_munger.py` | 200 | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/charlie_munger.py) |
| `src/agents/mohnish_pabrai.py` | 200 | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/mohnish_pabrai.py) |
| `src/agents/rakesh_jhunjhunwala.py` | 200 | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/rakesh_jhunjhunwala.py) |
| `src/agents/aswath_damodaran.py` | 200 | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/aswath_damodaran.py) |
| `src/agents/peter_lynch.py` | 200 | [raw](https://raw.githubusercontent.com/virattt/ai-hedge-fund/0f6ac487986f7eb80749ed42bd26fb8330c450db/src/agents/peter_lynch.py) |

## 5. License

### Status

`README: claims MIT · LICENSE file: missing · GitHub API license field: null`

Verified 2026-04-21:

- `GET /repos/virattt/ai-hedge-fund/contents/LICENSE` → `404`.
- `GET /repos/virattt/ai-hedge-fund` → `.license == null`.
- `README.md` prose: *"This project is licensed under the MIT License — see the LICENSE file for details."*

### Captured license text (standard MIT template, reconstructed copyright line)

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

### Disclosure paragraph (to copy verbatim into `THIRD_PARTY.md`)

The upstream repository `virattt/ai-hedge-fund` at SHA
`0f6ac487986f7eb80749ed42bd26fb8330c450db` does **not** ship a `LICENSE` file,
and GitHub's API reports the repository's license field as `null`. The README
prose asserts MIT. We proceed under that asserted MIT grant and capture the
canonical MIT template above with a reconstructed copyright line
(`Copyright (c) 2024 virattt`) in lieu of a named author from a LICENSE
artifact. If upstream publishes a LICENSE file with different text or a
different copyright line, this manifest becomes historical and `THIRD_PARTY.md`
is updated to match the authoritative artifact.

## 6. Consumer map

Downstream milestones that read this manifest:

- **M0.4** (`THIRD_PARTY.md`) — consumes §1 (SHA + URL), §4 (files-of-interest
  list), §5 (license status line, MIT text, disclosure paragraph), and
  compresses §3 into a one-line rationale per SPEC §19.9.
- **M3** (scoring-engine port under `skills/scoring-engine/**`) — consumes the
  SHA from §1 and the file list from §4 to drive the `git clone` at port time
  per SPEC §6.3.

No other consumers. No format coupling beyond these fields — M0.4 and M3 are
free to restructure.
