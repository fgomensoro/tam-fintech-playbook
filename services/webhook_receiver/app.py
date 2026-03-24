from flask import Flask, request, jsonify

app = Flask(__name__)

@app.post("/webhook")
def webhook():
    # Raw body bytes (useful for signature verification later)
    raw_body = request.get_data(cache=False, as_text=False)

    # Minimal logging (safe: no secrets)
    app.logger.info("Webhook received: content_length=%s content_type=%s",
                    request.content_length, request.content_type)

    return jsonify({
        "ok": True,
        "received_bytes": len(raw_body),
    }), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
