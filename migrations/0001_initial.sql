-- Initial Layout
-- 
-- NB: New Additions must be nullable since it's not guaranteed that all data will populate it
-- TODO(kajo): this sucks. Versioning? 
-- 
-- New Additions:
-- cringe.author_id 
-- cum.created_at_ms 

CREATE TABLE guild_config (
    guild_id                INTEGER PRIMARY KEY,
    tplaylist               TEXT    NOT NULL DEFAULT 'PLb1JKHu_D4MTBXu-8MCFBJ855RpoUuYTf',
    koko_role_id            INTEGER,
    wood_threshold          INTEGER NOT NULL DEFAULT 5,
    wood_channel_id         INTEGER,
    cringe_threshold        INTEGER NOT NULL DEFAULT 5,
    cringe_channel_id       INTEGER,
    cringe_expire_s         INTEGER NOT NULL DEFAULT 1200,
    cringe_timeout_s        INTEGER NOT NULL DEFAULT 606,
    deleteguard_channel_id  INTEGER
) STRICT;

CREATE TABLE guild_emoji (
    guild_id  INTEGER PRIMARY KEY,
    play      TEXT NOT NULL DEFAULT '▶️',
    stop      TEXT NOT NULL DEFAULT '⏹️',
    queue     TEXT NOT NULL DEFAULT '📄',
    success   TEXT NOT NULL DEFAULT '☑️',
    repeat    TEXT NOT NULL DEFAULT '🔁',
    error     TEXT NOT NULL DEFAULT '❌',
    denpabot  TEXT NOT NULL DEFAULT ':satellite:',
    wood      TEXT NOT NULL DEFAULT '🪵',
    same      TEXT NOT NULL DEFAULT '🦈',
    take      TEXT NOT NULL DEFAULT '🎍',
    cat1      TEXT NOT NULL DEFAULT '<:cat1:856666094277361745>',
    uwu       TEXT NOT NULL DEFAULT '<:UwU:856664498094342205>',
    cunny     TEXT NOT NULL DEFAULT '<:Cunny:856666244006281256>',
    cringe    TEXT NOT NULL DEFAULT '🔴'
) STRICT;

CREATE TABLE wood (
    message_id  INTEGER PRIMARY KEY,
    guild_id    INTEGER NOT NULL
) STRICT;

CREATE TABLE cringe (
    message_id  INTEGER PRIMARY KEY,
    guild_id    INTEGER NOT NULL,
    author_id   INTEGER
) STRICT;

CREATE INDEX cringe_by_author ON cringe (guild_id, author_id);

CREATE TABLE deleteguard (
    guild_id  INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,
    PRIMARY KEY (guild_id, user_id)
) STRICT;

CREATE TABLE blacklist (
    role_id   INTEGER PRIMARY KEY,
    guild_id  INTEGER NOT NULL
) STRICT;

CREATE TABLE cum (
    id             INTEGER PRIMARY KEY,
    guild_id       INTEGER NOT NULL,
    cummer_id      INTEGER NOT NULL,
    cummed_on_id   INTEGER NOT NULL,
    created_at_ms  INTEGER
) STRICT;

CREATE INDEX cum_by_cummer    ON cum (guild_id, cummer_id);
CREATE INDEX cum_by_cummed_on ON cum (guild_id, cummed_on_id);

CREATE TABLE edit_config (
    guild_id           INTEGER PRIMARY KEY,
    enabled            INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    report_channel_id  INTEGER
) STRICT;

CREATE TABLE edit_rule (
    guild_id     INTEGER NOT NULL,
    threshold_s  INTEGER NOT NULL CHECK (threshold_s > 0),
    role_id      INTEGER NOT NULL,
    PRIMARY KEY (guild_id, threshold_s, role_id)
) STRICT;

CREATE TABLE edit_exempt_role (
    guild_id  INTEGER NOT NULL,
    role_id   INTEGER NOT NULL,
    PRIMARY KEY (guild_id, role_id)
) STRICT;

CREATE TABLE denparty (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	url TEXT NOT NULL,
	queued TEXT NOT NULL,
	video_id TEXT NOT NULL,
	caused_by TEXT,
	message_id INTEGER NOT NULL,
	"timestamp" INTEGER NOT NULL,
	was_played INTEGER NOT NULL,
	playlist TEXT
);

CREATE TABLE queue (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	url TEXT NOT NULL,
	requester TEXT
);
