from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)

def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"ok": False, "error": "missing_bearer_token"}), 401
        token = auth.removeprefix("Bearer ").strip()
        if token != "token_admin":
            return jsonify({"ok": False, "error": "insufficient_scope"}), 403
        return f(*args, **kwargs)
    return wrapper

processed_event_ids = set()
items = {}
next_id = 1


@app.post("/webhook")
def webhook():
    raw_body = request.get_data(as_text=False)

    auth = request.headers.get("Authorization", "")

    # Simple auth simulation:
    # - Missing/invalid token => 401
    # - Valid token but insufficient scope => 403
    if not auth.startswith("Bearer "):
        return jsonify({"ok": False, "error": "missing_bearer_token"}), 401

    token = auth.removeprefix("Bearer ").strip()

    if token != "token_admin":
        return jsonify({"ok": False, "error": "insufficient_scope"}), 403
    
    # Idempotency simulation (in-memory)
    data = request.get_json(silent=True) or {}
    event_id = data.get("event_id")
    print(raw_body)
    if not event_id:
        return jsonify({"ok": False, "error": "missing_event_id"}), 422

    if event_id in processed_event_ids:
        return jsonify({"ok": False, "error": "duplicate_event"}), 409

    processed_event_ids.add(event_id)
    
    app.logger.info("Webhook received: content_length=%s content_type=%s",
                    request.content_length, request.content_type)

    return jsonify({"ok": True, "received_bytes": len(raw_body)}), 200


@app.get("/items")
@require_admin
def list_items():
    return jsonify({"items": list(items.values())}), 200


@app.get("/items/<int:item_id>")
@require_admin
def get_item(item_id: int):
    item = items.get(item_id)
    if not item:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify(item), 200


@app.post("/items")
@require_admin
def create_item():
    global next_id
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    name = data.get("name")
    if not name or not isinstance(name, str):
        return jsonify({"ok": False, "error": "name_required"}), 422

    item = {"id": next_id, "name": name}
    items[next_id] = item
    next_id += 1

    return jsonify(item), 201


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
