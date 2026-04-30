# Wealthfolio — install, DB path, and Docker mount contract

> Version pinned: **v3.2.1** (bundle build `20260301.1`). See [THIRD_PARTY.md](../THIRD_PARTY.md) (M0.4) for the canonical pin list. Upgrades are a separate `bd` ticket per [SPEC §19.14](../docs/SPEC.md).

## 1. What Wealthfolio is

Wealthfolio is a local-first desktop investment tracker built on Tauri (Rust + web UI) with a SQLite backend. It stores holdings, activities, valuations, and corporate-action data on the user's machine; no cloud sync is required. Upstream: <https://github.com/afadil/wealthfolio>.

In this project Wealthfolio is the **canonical tracker** (SPEC §5.1). The agent treats it as a strictly read-only data source: the macOS GUI is the only writer; Python and shell skills running in the M0.9 container open the DB with `-readonly` and consume a small set of named queries defined in M0.7.

## 2. Maintenance mode: holdings-only

The user maintains **current positions and cost basis only**. Entering transaction history, dividends, and corporate-action rows is **optional** — the tracker is kept current enough to answer "what do I own, what did it cost, where does it sit" and nothing more.

Consequences the rest of the system absorbs (see [SPEC §5.3](../docs/SPEC.md)):

- **Phase 1 snapshot** derives holdings from the current `holdings_snapshots` / `assets` / `accounts` view, not by replaying `activities`.
- **M5 long-window alpha / TWR** is degraded or unavailable when activity history is sparse; reports should mark those metrics N/A rather than fabricate them (SPEC §19.1 invariant 1).
- **Corp-actions reconciliation** is informational only; there is no recorded-activity baseline to diff against in holdings-only mode (SPEC §19.2 invariant 18).

If the user later elects to backfill full transaction history, the SQL queries in M0.7 will transparently pick up the richer data — nothing in this contract needs to change.

## 3. Install

Install via Homebrew Cask:

```bash
HOMEBREW_NO_AUTO_UPDATE=1 brew install --cask wealthfolio
```

Verify the installed version matches the pin:

```bash
defaults read /Applications/Wealthfolio.app/Contents/Info.plist CFBundleShortVersionString
# expected: 3.2.1

defaults read /Applications/Wealthfolio.app/Contents/Info.plist CFBundleVersion
# expected: 20260301.1
```

The Wealthfolio bundle does **not** ship a CLI — `wealthfolio --version` fails, and version can only be read from `Info.plist`.

## 4. First launch and DB initialization

Wealthfolio's SQLite file is created by Diesel migrations the first time the app is opened. Until then, `app.db` does not exist.

1. Launch `Wealthfolio.app` from Finder or Spotlight.
2. Step past any first-run onboarding. If the UI blocks until an account exists, create a throwaway account (name: `init`, any broker / currency); no transactions or holdings are required for migrations to complete.
3. Quit the app (⌘Q / File → Quit) so the WAL checkpoints cleanly.
4. Confirm the DB materialized:

   ```bash
   ls -la "$HOME/Library/Application Support/com.teymz.wealthfolio/app.db"
   ```

   File should exist and be non-empty (expect a few hundred KB at minimum).

## 5. DB path and override

**Default path (macOS):**

```
$HOME/Library/Application Support/com.teymz.wealthfolio/app.db
```

**Canonical env var:** `WEALTHFOLIO_DB`. All tooling (M0.7 SQL skill, M0.9 container) reads the path from this variable. Default resolution in scripts:

```bash
export WEALTHFOLIO_DB="${WEALTHFOLIO_DB:-$HOME/Library/Application Support/com.teymz.wealthfolio/app.db}"
```

Inside the container (see §6) the same variable points at the bind-mount target (`/wealthfolio/app.db`).

**Read-only open, always.** Per [SPEC §19.2 invariant 11](../docs/SPEC.md) the agent never writes the Wealthfolio DB. Use `-readonly` on every `sqlite3` invocation:

```bash
sqlite3 -readonly "$WEALTHFOLIO_DB" '.schema' | head
```

## 6. Docker mount (Option A)

Wealthfolio is a Tauri desktop app and cannot be containerized. The topology chosen for this project:

- Wealthfolio runs **natively on macOS**.
- All Python / shell skill code runs inside the container built in M0.9.
- The container bind-mounts the host Wealthfolio app-support directory **read-only**.

Fragment that M0.9's `docker-compose.yml` must honor:

```yaml
services:
  skills:
    volumes:
      - type: bind
        source: ${WEALTHFOLIO_DB_DIR:-${HOME}/Library/Application Support/com.teymz.wealthfolio}
        target: /wealthfolio
        read_only: true
    environment:
      - WEALTHFOLIO_DB=/wealthfolio/app.db
```

On the host, override the source directory by setting `WEALTHFOLIO_DB_DIR`; inside the container, scripts continue to read `WEALTHFOLIO_DB=/wealthfolio/app.db`.

### Caveats

1. **Mount the directory, not the file.** SQLite with WAL journaling keeps two sidecars next to the main DB: `app.db-wal` and `app.db-shm`. A read-only open must be able to see both; mounting only `app.db` will silently return stale or empty query results. Always bind the enclosing directory.
2. **Quit Wealthfolio before any agent run.** `-readonly` opens tolerate a dirty WAL (they simply cannot checkpoint it), but if the GUI is actively writing while the container reads, the agent can see a momentarily-inconsistent snapshot. This is enforced by convention, not by a lock — see §7.
3. **VirtioFS is fine.** macOS Docker bind mounts use VirtioFS by default; read-heavy SQLite access does not need additional tuning for M0.1. Revisit if query latency ever becomes a concern.

Alternatives B (snapshot-copy), C (host-native Python), and D (export-import) were considered in planning and rejected — Option A is the simplest contract M0.7/M0.9 have to honor, and the DB is rarely written during scan runs.

## 7. Quit-before-scans discipline

Before running any agent scan or skill that reads the Wealthfolio DB:

- Use **File → Quit** (or ⌘Q). Do **not** force-quit from Activity Monitor — it skips the clean WAL checkpoint and the last-committed transaction may be invisible to the next `-readonly` open.
- Confirm the app is down: `pgrep -lf -i wealthfolio` should print nothing.
- Run the scan. Relaunch Wealthfolio afterwards if you need the GUI.

## 8. Version pin

| Field | Value |
|---|---|
| Version (`CFBundleShortVersionString`) | `3.2.1` |
| Build (`CFBundleVersion`) | `20260301.1` |
| Schema dump | [`research/wealthfolio-schema-v3.2.1.txt`](../research/wealthfolio-schema-v3.2.1.txt) |
| Bundle ID | `com.teymz.wealthfolio` |
| Upstream | <https://github.com/afadil/wealthfolio> |

Upgrading Wealthfolio requires a separate `bd` ticket per [SPEC §19.14](../docs/SPEC.md) (schema-drift policy): the new version's `.schema` must be dumped, diffed against the committed one, and any affected queries in `skills/sql/wealthfolio-queries.sql` reviewed before the pin is advanced.
