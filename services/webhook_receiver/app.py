from flask import Flask, request, jsonify

app = Flask(__name__)

processed_event_ids = set()

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

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
