SCHEMA = """
CREATE TABLE IF NOT EXISTS denparty (
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
"""
