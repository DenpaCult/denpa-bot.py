SCHEMA = """
CREATE TABLE IF NOT EXISTS emojicfg (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    play TEXT DEFAULT ▶️,
    stop TEXT DEFAULT ⏹️,
    queue TEXT DEFAULT 📄,
    success TEXT DEFAULT ☑️,
    repeat TEXT DEFAULT 🔁,
    error TEXT DEFAULT ❌,
    denpabot TEXT DEFAULT ":satellite:",
    wood TEXT DEFAULT 🪵,
    same TEXT DEFAULT 🦈,
    take TEXT DEFAULT 🎍,
    cat1 TEXT DEFAULT "<:cat1:856666094277361745>",
    uwu TEXT DEFAULT "<:UwU:856664498094342205>",
    cunny TEXT DEFAULT "<:Cunny:856666244006281256>",
    cringe TEXT DEFAULT 🔴
)
"""
