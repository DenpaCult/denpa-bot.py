"""
Creates a snapshot of toromi.db, and prunes old snapshots.

Meant to run from cron every 6 hours, e.g.

    0 */6 * * * cd /app && mkdir -p persist/backups && flock -n persist/backups/.lock python -m scripts.backup_db --db persist/toromi.db

- uses VACUUM INTO, which takes a consistent snapshot even while the bot is writing
- snapshots are named toromi-YYYY-MM-DDTHHMMZ.db (UTC)
- snapshots are written as temp files before being integrity-checked and then renamed
- pruning goes by the timestamp in the file name, and only runs after a successful backup
"""

import argparse
import logging
import os
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

PREFIX = "toromi-"
SUFFIX = ".db"
TIMESTAMP = "%Y-%m-%dT%H%MZ"

logger = logging.getLogger("backup_db")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(os.environ.get("TOROMI_DB_PATH", "persist/toromi.db")),
        help="database to back up (default: $TOROMI_DB_PATH or persist/toromi.db)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="folder for snapshots (default: a backups/ folder next to the database)",
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=30,
        help="delete snapshots older than this many days (default: 30)",
    )
    return parser.parse_args()


def _connect_ro(path: Path) -> sqlite3.Connection:
    """read-only: can't write to the db, and a typo'd path errors instead of creating one"""

    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def snapshot(db: Path, out: Path, now: datetime) -> Path:
    """write a checked snapshot of db into out, returning its path"""

    final = out / f"{PREFIX}{now.strftime(TIMESTAMP)}{SUFFIX}"
    if final.exists():
        raise FileExistsError(f"{final} already exists, refusing to overwrite it")

    partial = final.with_name(final.name + ".partial")
    partial.unlink(missing_ok=True)  # leftover from a crashed run

    try:
        con = _connect_ro(db)
        try:
            con.execute("VACUUM INTO ?", (str(partial),))
        finally:
            con.close()

        check = _connect_ro(partial)
        try:
            result = check.execute("PRAGMA integrity_check;").fetchone()[0]
        finally:
            check.close()

        if result != "ok":
            raise RuntimeError(f"integrity check failed on the snapshot: {result}")

        partial.rename(final)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    return final


def prune(out: Path, keep_days: int, now: datetime) -> list[Path]:
    """delete snapshots whose name says they're older than keep_days and all partials"""

    cutoff = now - timedelta(days=keep_days)
    deleted: list[Path] = []

    for file in out.glob(f"{PREFIX}*{SUFFIX}"):
        stamp = file.name.removeprefix(PREFIX).removesuffix(SUFFIX)

        try:
            taken = datetime.strptime(stamp, TIMESTAMP).replace(tzinfo=UTC)
        except ValueError:
            continue  # e.g. old toromi-YYYY-MM-DD.db backups, not ours to prune

        if taken < cutoff:
            file.unlink()
            deleted.append(file)

    # SAFETY: we assume `flock` is being used, so we can delete every partial as we know we are the only
    # backup script being run
    for file in out.glob(f"{PREFIX}*{SUFFIX}.partial"):
        file.unlink()
        deleted.append(file)

    return deleted


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args = parse_args()

    db: Path = args.db
    out: Path = args.out or db.parent / "backups"
    now = datetime.now(tz=UTC)

    if not db.is_file():
        logger.error(f"database {db} doesn't exist")
        return 1

    out.mkdir(parents=True, exist_ok=True)

    try:
        path = snapshot(db, out, now)
    except Exception:
        logger.exception("backup failed")  # nothing is pruned in this case
        return 1

    logger.info(f"wrote {path} ({path.stat().st_size / 1024:.0f} KiB)")

    for file in prune(out, args.keep_days, now):
        logger.info(f"pruned {file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
