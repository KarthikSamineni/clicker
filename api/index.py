import os
from flask import Flask, request, jsonify
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Do not raise at import time; create the Supabase client lazily so the
# function can load even if environment variables are not configured yet
# (e.g. during Vercel build). Handlers will return 500 if the vars are
# missing at runtime.
_SUPABASE_URL = os.environ.get("SUPABASE_URL")
_SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

_supabase_client = None

def get_supabase():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    if not _SUPABASE_URL or not _SUPABASE_KEY:
        return None
    _supabase_client = create_client(_SUPABASE_URL, _SUPABASE_KEY)
    return _supabase_client

app = Flask(__name__)


@app.route("/get_group", methods=["GET"])
def get_group():
    resp = supabase.table("catalog_group").select("id,name").execute()
    if getattr(resp, "error", None):
        # Debug: print error from Supabase
        print(f"get_group error: {resp.error}")
        return jsonify({"error": str(resp.error)}), 500
    return jsonify(resp.data), 200


@app.route("/get_sub_group", methods=["GET"])
def get_sub_group():
    group_id = request.args.get("group_id")
    if not group_id:
        return jsonify({"error": "group_id is required"}), 400
    supabase = get_supabase()
    if not supabase:
        return jsonify({"error": "SUPABASE_URL and SUPABASE_KEY are not configured"}), 500
    resp = supabase.table("catalog").select("id,name").eq("catalog_group_id", group_id).eq("is_active",True).execute()
    if getattr(resp, "error", None):
        return jsonify({"error": str(resp.error)}), 500
    data = sanitize(resp.data)
    # Debug: print number of rows returned for group
    print(f"get_sub_group returning {len(data) if isinstance(data, list) else 1} rows for group_id={group_id}")
    return jsonify(data), 200


def change_count(row_id, delta):
    # Perform an atomic increment/decrement on the DB side using a Postgres RPC.
    # This avoids a read-then-write race and requires a SQL function
    # (see README) named `increment_catalog_count(p_id, p_delta)`.
    # Debug: print RPC invocation (do not print secrets)
    print(f"RPC update_catalog_count called with id={row_id} delta={delta}")
    supabase = get_supabase()
    if not supabase:
        return None, "supabase_not_configured"
    resp = supabase.rpc("update_catalog_count", {"var_catalog_id": row_id, "delta": int(delta)}).execute()
    if getattr(resp, "error", None):
        # Debug: print RPC error
        print(f"RPC error: {resp.error}")
        return None, str(resp.error)
    # Debug: print RPC returned data
    print(f"RPC returned: {resp.data}")
    # Return the raw data from the RPC (caller will handle empty results).
    return resp.data, None


@app.route("/increase", methods=["POST"])
def increase():
    payload = request.get_json()
    row_id = payload.get("id")
    if row_id is None:
        return jsonify({"error": "id is required in JSON body"}), 400
    data, err = change_count(row_id, 1)
    if err:
        if err == "not_found":
            return jsonify({"error": "row not found"}), 404
        return jsonify({"error": err}), 500
    return jsonify({"updated": data}), 200


@app.route("/decrease", methods=["POST"])
def decrease():
    payload = request.get_json(silent=True) or {}
    row_id = payload.get("id")
    if row_id is None:
        return jsonify({"error": "id is required in JSON body"}), 400
    data, err = change_count(row_id, -1)
    if err:
        if err == "not_found":
            return jsonify({"error": "row not found"}), 404
        return jsonify({"error": err}), 500
    return jsonify({"updated": data}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)


def sanitize(data):
    # Minimal sanitizer: ensure list/dict structures are JSON-serializable
    return data
