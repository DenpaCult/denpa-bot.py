# denpa-bot.py
porting the denpa bot to python

# modifying the db
do so as as a modification to the existing schema in `migrations/`

# migration

Point the script at the JS bot's `backups` folder. 

```sh
uv run python -m scripts.migrate_json path/to/denpa-bot/backups --db persist/toromi.db 
```
