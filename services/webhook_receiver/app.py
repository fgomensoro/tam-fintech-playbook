import os
import secrets
import time
import jwt
from functools import wraps

from flask import Flask, request, jsonify

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Flask(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
rate_window_sec = 10
rate_limit_max_requests = 3

SECRET_KEY = os.environ.get("JWT_SECRET", "dev-secret-key")
OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "test-client")
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "test-secret")

# ---------------------------------------------------------------------------
# State  (in-memory, resets on restart)
# ---------------------------------------------------------------------------
processed_event_ids = set()
items = {}
next_id = 1
rate_state = {}    # key -> (window_start_ts, count)
oauth_tokens = {}  # token -> scope

# ---------------------------------------------------------------------------
# Middleware / helpers
# ---------------------------------------------------------------------------
def require_scope(required_scope):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return jsonify({"ok": False, "error": "missing_bearer_token"}), 401
            token = auth.removeprefix("Bearer ").strip()
            if token == "token_admin":
                return f(*args, **kwargs)
            if token not in oauth_tokens:
                return jsonify({"ok": False, "error": "insufficient_scope"}), 403
            if oauth_tokens[token] not in required_scope:
                return jsonify({"ok": False, "error": "insufficient_scope"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

def rate_limit(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", "")
        key = token or "anonymous"

        now = int(time.time())
        window_start, count = rate_state.get(key, (now, 0))

        if now - window_start >= rate_window_sec:
            window_start, count = now, 0

        count += 1
        rate_state[key] = (window_start, count)

        if count > rate_limit_max_requests:
            retry_after = rate_window_sec - (now - window_start)
            return jsonify({"ok": False, "error": "rate_limited"}), 429, {
                "Retry-After": str(max(retry_after, 1))
            }

        return f(*args, **kwargs)
    return wrapper


def paginate(all_items: list, page: int, limit: int) -> tuple[list, int | None]:
    start = (page - 1) * limit
    end = start + limit
    page_items = all_items[start:end]
    next_page = page + 1 if end < len(all_items) else None
    return page_items, next_page


def log_request(event: str):
    req_id = request.headers.get("X-Request-Id", "-")
    app.logger.info("%s request_id=%s method=%s path=%s",
                    event, req_id, request.method, request.path)


# ---------------------------------------------------------------------------
# Routes — webhook
# ---------------------------------------------------------------------------
@app.post("/webhook")
def webhook():
    auth = request.headers.get("Authorization", "")

    # Simple auth simulation:
    # - Missing/invalid token => 401
    # - Valid token but insufficient scope => 403
    if not auth.startswith("Bearer "):
        return jsonify({"ok": False, "error": "missing_bearer_token"}), 401

    token = auth.removeprefix("Bearer ").strip()

    if token != "token_admin":
        return jsonify({"ok": False, "error": "insufficient_scope"}), 403

    raw_body = request.get_data(as_text=False)

    # Idempotency simulation (in-memory)
    data = request.get_json(silent=True) or {}
    event_id = data.get("event_id")
    if not event_id:
        return jsonify({"ok": False, "error": "missing_event_id"}), 422

    if event_id in processed_event_ids:
        return jsonify({"ok": False, "error": "duplicate_event"}), 409

    processed_event_ids.add(event_id)

    app.logger.info("Webhook received: content_length=%s content_type=%s",
                    request.content_length, request.content_type)

    log_request("webhook_processed")

    return jsonify({"ok": True, "received_bytes": len(raw_body)}), 200


@app.route("/reset", methods=["POST"])
def reset():
    processed_event_ids.clear()
    return jsonify({"ok": True, "reset": True}), 200


# ---------------------------------------------------------------------------
# Routes — items (CRUD)
# ---------------------------------------------------------------------------
@app.get("/items")
@require_scope(["read:items"])
@rate_limit
def list_items():
    log_request("items_list")

    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=2, type=int)

    if page < 1 or limit < 1 or limit > 100:
        return jsonify({"ok": False, "error": "invalid_pagination"}), 422

    all_items = list(items.values())
    page_items, next_page = paginate(all_items, page, limit)

    return jsonify({
        "items": page_items,
        "page": page,
        "limit": limit,
        "next_page": next_page,
    }), 200


@app.get("/items/<int:item_id>")
@require_scope(["read:items"])
def get_item(item_id: int):
    log_request("items_get")

    item = items.get(item_id)
    if not item:
        return jsonify({"ok": False, "error": "not_found"}), 404

    return jsonify(item), 200


@app.post("/items")
@require_scope(["write:items"])
def create_item():
    log_request("items_create")

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


# ---------------------------------------------------------------------------
# Routes — OAuth
# ---------------------------------------------------------------------------
@app.post("/oauth/token")
def oauth_token():
    grant_type = request.form.get("grant_type")
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")
    scope = request.form.get("scope", "read:items")

    if not grant_type:
        return jsonify({"error": "missing_grant_type"}), 400

    if grant_type != "client_credentials":
        return jsonify({"error": "unsupported_grant_type"}), 400

    if client_id != OAUTH_CLIENT_ID or client_secret != OAUTH_CLIENT_SECRET:
        return jsonify({"error": "invalid_client"}), 401

    payload = {
        "sub": client_id,
        "scope": scope,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    oauth_tokens[token] = scope

    return jsonify({
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": scope
    }), 200
    

@app.post("/oauth/userinfo-token")
def oauth_userinfo_token():
    grant_type = request.form.get("grant_type")
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")
    scope = request.form.get("scope", "openid read:items")

    if not grant_type:
        return jsonify({"error": "missing_grant_type"}), 400

    if grant_type != "client_credentials":
        return jsonify({"error": "unsupported_grant_type"}), 400

    if client_id != OAUTH_CLIENT_ID or client_secret != OAUTH_CLIENT_SECRET:
        return jsonify({"error": "invalid_client"}), 401

    now = int(time.time())

    access_payload = {
        "sub": client_id,
        "scope": scope,
        "iat": now,
        "exp": now + 3600,
    }

    id_payload = {
        "sub": client_id,
        "email": "test@example.com",
        "name": "Test User",
        "auth_time": now,
        "iat": now,
        "exp": now + 3600,
    }

    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm="HS256")
    id_token = jwt.encode(id_payload, SECRET_KEY, algorithm="HS256")

    oauth_tokens[access_token] = scope

    return jsonify({
        "access_token": access_token,
        "id_token": id_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": scope
    }), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
