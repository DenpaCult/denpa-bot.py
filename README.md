# denpa-bot.py
porting the denpa bot to python

# modifying the db

add a new `migrations/NNNN_description.sql` (next number up). never edit one that's already on main, see `base/database.py`

# migration

Point `scripts/migrate_json.py` at the JS bot's `backups` folder. 

# update yt-dlp

1. run `uv lock --upgrade-package yt-dlp`
2. commit `uv.lock`

TODO: dependabot?

```sh
uv run python -m scripts.migrate_json path/to/denpa-bot/backups --db persist/toromi.db 
```
# TODOs

- move the music queue to database
- idk someone add more todos
