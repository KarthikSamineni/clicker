# Flask + Supabase API

This small Flask API exposes four endpoints backed by Supabase tables.

Environment variables (required):
- `SUPABASE_URL` - your Supabase project URL
- `SUPABASE_KEY` - your Supabase anon/service role key

Install:

```bash
pip install -r requirements.txt
```

Run (PowerShell example):

```powershell
$env:SUPABASE_URL = "https://your-project.supabase.co"
$env:SUPABASE_KEY = "your-service-key"
python app.py
```

Endpoints:
- `GET /get_group` — returns rows from `catalog_group`
- `GET /get_sub_group?group_id=<id>` — returns rows from `catalog` filtered by `group_id`
- `POST /increase` — body JSON `{ "id": <id> }` increments `count` in `calalog_count`
- `POST /decrease` — body JSON `{ "id": <id> }` decrements `count` in `calalog_count`

Notes:
- The code expects tables named exactly `catalog_group`, `catalog` and `calalog_count` (as provided). If your table names differ, update `app.py` accordingly.
- This implementation performs a read-then-update; for high concurrency you should implement a DB-side increment (e.g., an RPC) or use Postgres transactions.
