"""
Build a new Toromi Database from the JS bot's existing data

Not Migrated:
- denparty_*.json, denparty_*_request.json, queue_*.json
    - I don't believe the schemas were ready and the music playback doesn't impl this currently anyways
- blacklist_*.json
    - We would need to map role names to IDs and I think its easier just do that via the command
- koko role
    wasn't per-server anyways. Can be set via the ;;config command
"""

import argparse
import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from models.cringe import CringeMessage
from models.cum import Cum
from models.delete_guard import GuardedUser
from models.wood import WoodMessage

# file names look like wood_856649672117583872.json
FILE_NAME = re.compile(r"(?P<kind>[a-z]+)_(?P<guild_id>\d+)\.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("backups", type=Path, help="folder holding the JS bot's JSON files")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(os.environ.get("TOROMI_DB_PATH", "persist/toromi.db")),
        help="database to create (default: $TOROMI_DB_PATH or persist/toromi.db)",
    )

    return parser.parse_args()


def snowflake(value) -> int | None:
    """discord IDs were stored as strings. the JS bot used "channel_id" as a placeholder for unset channels"""
    text = str(value)

    return int(text) if text.isdigit() else None


class Migration:
    def __init__(self):
        # imported here so TOROMI_DB_PATH is already pointing at the temporary file
        from base.config import Config
        from base.database import db
        from dao.cringe_dao import CringeDAO
        from dao.cum_dao import CumDAO
        from dao.deleteguard_dao import DeleteGuardDAO
        from dao.edit_cfg_dao import EditCfgDAO
        from dao.wood_dao import WoodDAO

        self.config = Config
        self.wood = WoodDAO(db)
        self.cringe = CringeDAO(db)
        self.deleteguard = DeleteGuardDAO(db)
        self.cum = CumDAO(db)
        self.edit = EditCfgDAO(db)

        self.handlers = {
            "wood": self.migrate_wood,
            "cringe": self.migrate_cringe,
            "deleteguard": self.migrate_deleteguard,
            "cum": self.migrate_cum,
            "editwindow": self.migrate_editwindow,
            "blacklist": self.skip_blacklist,
            "denparty": self.skip_music,
            "queue": self.skip_music,
        }

    async def set(self, guild_id: int, section: str | None, key: str, value):
        if value is not None:
            await self.config.update_db(guild_id, section, key, value)

    async def migrate_wood(self, guild_id: int, data: dict) -> str:
        await self.set(guild_id, "wood", "threshold", int(data["threshold"]))
        await self.set(guild_id, "wood", "channel_id", snowflake(data["channelId"]))

        added = [
            await self.wood.add(WoodMessage(int(message_id), guild_id))
            for message_id in data.get("messages", [])
        ]

        return f"{sum(added)} messages" + duplicates(added)

    async def migrate_cringe(self, guild_id: int, data: dict) -> str:
        await self.set(guild_id, "cringe", "threshold", int(data["threshold"]))
        await self.set(guild_id, "cringe", "channel_id", snowflake(data["channelId"]))
        # the JS bot stored minutes (and assumed 20 when missing), the python bot uses seconds
        await self.set(guild_id, "cringe", "expire_time", int(data.get("expireTime", 20)) * 60)
        if "timeoutTime" in data:
            await self.set(guild_id, "cringe", "timeout_time", int(data["timeoutTime"]))

        # the JS bot never recorded who wrote the message
        added = [
            await self.cringe.add(CringeMessage(int(message_id), None, guild_id))
            for message_id in data.get("messages", [])
        ]

        return f"{sum(added)} messages" + duplicates(added)

    async def migrate_deleteguard(self, guild_id: int, data: dict) -> str:
        await self.set(guild_id, "delete_guard", "channel_id", snowflake(data["channelId"]))

        added = [
            await self.deleteguard.add(GuardedUser(int(user_id), guild_id))
            for user_id in data.get("users", [])
        ]

        return f"{sum(added)} users" + duplicates(added)

    async def migrate_cum(self, guild_id: int, data: dict) -> str:
        # cummedOnUsers is the same data indexed the other way round, so only one side is read
        count = 0
        for cummer_id, sent in data["usersWhoCummed"].items():
            for cummee_id, pair in sent["users"].items():
                for _ in range(pair["numOccurences"]):
                    await self.cum.add(Cum(guild_id, int(cummer_id), int(cummee_id)))
                    count += 1

        if count != data["totalCums"]:
            raise ValueError(f"expected {data['totalCums']} events, found {count}")

        return f"{count} events"

    async def migrate_editwindow(self, guild_id: int, data: dict) -> str:
        await self.edit.set_config(guild_id, bool(data.get("enabled")), snowflake(data.get("channelId")))

        for rule in data.get("rules", []):
            for role_id in rule["roles"]:
                await self.edit.add_rule(guild_id, int(rule["threshold"]), int(role_id))

        for role_id in data.get("exempt", []):
            await self.edit.add_exempt_role(guild_id, int(role_id))

        return f"{len(data.get('rules', []))} rules, {len(data.get('exempt', []))} exempt roles"

    async def skip_blacklist(self, guild_id: int, data: list) -> str:
        return "SKIPPED, re-add these roles with ;;blacklist add: " + ", ".join(data)

    async def skip_music(self, guild_id: int, data) -> str:
        return "SKIPPED, music history isn't used by the python bot"

    async def run(self, backups: Path):
        from base.database import db

        db.setup()

        by_guild: dict[int, list[tuple[str, Path]]] = defaultdict(list)
        for path in sorted(backups.glob("*.json")):
            match = FILE_NAME.fullmatch(path.name)
            if match is None or match["kind"] not in self.handlers:
                print(f"  {path.name}: SKIPPED, not migrated (see the notes at the top of scripts/migrate_json.py)")
                continue

            by_guild[int(match["guild_id"])].append((match["kind"], path))

        for guild_id, files in by_guild.items():
            print(f"guild {guild_id}")
            await self.config.load(guild_id)  # creates the settings rows with their defaults

            for kind, path in files:
                data = json.loads(path.read_text(encoding="utf-8"))
                summary = await self.handlers[kind](guild_id, data)
                print(f"  {path.name}: {summary}")

        print("\nrows per table")
        for (table,) in db.con.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name;"
        ).fetchall():
            (count,) = db.con.execute(f'SELECT COUNT(*) FROM "{table}";').fetchone()
            print(f"  {table}: {count}")


def duplicates(added: list[bool]) -> str:
    skipped = len(added) - sum(added)

    return f" ({skipped} duplicates skipped)" if skipped else ""


def main():
    args = parse_args()

    if not args.backups.is_dir():
        sys.exit(f"{args.backups} is not a folder")

    target: Path = args.db
    if target.exists():
        sys.exit(f"{target} already exists. move or delete it first, this script only builds new databases")

    building = target.with_name(target.name + ".migrating")
    building.unlink(missing_ok=True)  # left over from a crashed run
    os.environ["TOROMI_DB_PATH"] = str(building)

    from base.database import db

    db.con.execute("PRAGMA synchronous = OFF;")  # safe, the file is thrown away if anything fails

    try:
        asyncio.run(Migration().run(args.backups))
    except BaseException:
        db.con.close()
        building.unlink(missing_ok=True)
        raise

    db.con.close()
    building.replace(target)
    print(f"\nwrote {target}")


if __name__ == "__main__":
    main()
