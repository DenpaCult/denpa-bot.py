SCHEMA = """
CREATE TABLE IF NOT EXISTS editcfg (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    time_limit_h INTEGER NOT NULL,
    report_channel_id INTEGER NOT NULL,
    mention_list TEXT,
    ignore_roles TEXT
);
"""
