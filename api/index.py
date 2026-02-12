import os
from flask import Flask, request, jsonify
from supabase import create_client
from dotenv import load_dotenv
import serverless_wsgi

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY environment variables")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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


def handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)
