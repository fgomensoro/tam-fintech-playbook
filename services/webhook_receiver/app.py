from flask import Flask, request, jsonify

app = Flask(__name__)

@app.post("/webhook")
def webhook():
    raw_body = request.get_data(cache=False, as_text=False)

    auth = request.headers.get("Authorization", "")

    # Simple auth simulation:
    # - Missing/invalid token => 401
    # - Valid token but insufficient scope => 403
    if not auth.startswith("Bearer "):
        return jsonify({"ok": False, "error": "missing_bearer_token"}), 401

    token = auth.removeprefix("Bearer ").strip()

    if token != "token_admin":
        return jsonify({"ok": False, "error": "insufficient_scope"}), 403

    app.logger.info("Webhook received: content_length=%s content_type=%s",
                    request.content_length, request.content_type)

    return jsonify({"ok": True, "received_bytes": len(raw_body)}), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
