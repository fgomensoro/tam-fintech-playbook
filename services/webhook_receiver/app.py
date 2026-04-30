import os, secrets, time, jwt, hashlib, base64, hmac, sqlite3
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
REGISTERED_REDIRECT_URI = "https://app.example.com/callback"
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "whsec_test_secret")
BEARER_TOKEN_ADMIN = os.environ.get("BEARER_TOKEN_ADMIN", "token_admin")
BEARER_TOKEN_USER = os.environ.get("BEARER_TOKEN_USER", "token_user")


# ---------------------------------------------------------------------------
# Database — SQLite for webhook event deduplication
# ---------------------------------------------------------------------------
DB_PATH = os.environ.get("DB_PATH", "webhook_events.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT,
            raw_body TEXT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            claimed_at TIMESTAMP,
            processed_at TIMESTAMP,
            attempts INTEGER DEFAULT 0,
            last_error TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ---------------------------------------------------------------------------
# State  (in-memory, resets on restart)
# ---------------------------------------------------------------------------
processed_event_ids = set()
items = {}
next_id = 1
rate_state = {}    # key -> (window_start_ts, count)
oauth_tokens = {}  # token -> scope
auth_codes = {}    # code -> { scope, redirect_uri, code_challenge, code_challenge_method }

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
            if token == BEARER_TOKEN_ADMIN:
                return f(*args, **kwargs)

            # Validate JWT first (checks exp automatically)
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                return jsonify({"ok": False, "error": "token_expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"ok": False, "error": "invalid_token"}), 401

            # Then check scope
            token_scope = payload.get("scope", "")
            if not any(s in token_scope.split() for s in required_scope):
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

@app.post("/webhook/stripe")
def webhook_stripe():
    # ============================================================
    # PASO 1: Read raw body BEFORE anything else
    # ============================================================
    # Lo guardamos en bytes (as_text=False) porque la firma HMAC
    # se calcula sobre los bytes exactos. Si Flask parsea el JSON
    # primero, los bytes cambian (whitespace, orden de keys) y la
    # firma nunca matchea.
    raw_body = request.get_data(as_text=False)
    
    # ============================================================
    # PASO 2: Verify signature exists and is well-formed
    # ============================================================
    # Rechazos baratos primero — si no hay header, no hay nada
    # que verificar. 401 porque es un problema de autenticación.
    sig_header = request.headers.get("Stripe-Signature", "")
    if not sig_header:
        return jsonify({"ok": False, "error": "missing_signature"}), 401

    # Stripe-Signature: t=1234567890,v1=abc123...
    # Parseamos los pares key=value separados por coma.
    sig_parts = {}
    for part in sig_header.split(","):
        key, _, value = part.partition("=")
        sig_parts[key.strip()] = value.strip()

    timestamp = sig_parts.get("t", "")
    received_sig = sig_parts.get("v1", "")

    if not timestamp or not received_sig:
        return jsonify({"ok": False, "error": "invalid_signature_format"}), 401

    # ============================================================
    # PASO 3: Timestamp tolerance check (anti-replay)
    # ============================================================
    # Aunque la firma sea válida, si el timestamp es viejo es un
    # replay attack. 5 minutos (300 seg) es el estándar de Stripe.
    # Lo hacemos ANTES de calcular HMAC porque es más barato.
    try:
        ts = int(timestamp)
    except ValueError:
        return jsonify({"ok": False, "error": "invalid_timestamp"}), 401

    if abs(int(time.time()) - ts) > 300:
        return jsonify({"ok": False, "error": "timestamp_too_old", "tolerance_seconds": 300}), 401

    # ============================================================
    # PASO 4: Verify HMAC signature
    # ============================================================
    # Recalculamos la firma con nuestro secret y la comparamos.
    # signed_payload = "timestamp.body" — el "." es literal.
    signed_payload = f"{timestamp}.".encode() + raw_body
    expected_sig = hmac.new(
        WEBHOOK_SECRET.encode(),
        signed_payload,
        hashlib.sha256
    ).hexdigest()

    # compare_digest evita timing attacks: tarda lo mismo aunque
    # los strings difieran en el primer caracter o en el último.
    if not hmac.compare_digest(expected_sig, received_sig):
        return jsonify({"ok": False, "error": "signature_mismatch"}), 401

    # ============================================================
    # PASO 5: Parse JSON only AFTER signature verified
    # ============================================================
    # Ahora que confirmamos que el body es legítimo, podemos
    # parsearlo sin riesgo. Antes de este punto, los bytes
    # podrían venir de un atacante.
    data = request.get_json(silent=True) or {}
    event_id = data.get("event_id")
    event_type = data.get("type", "unknown")
    
    if not event_id:
        return jsonify({"ok": False, "error": "missing_event_id"}), 422

    # ============================================================
    # PASO 6: Persist to queue (status='pending')
    # ============================================================
    # GOLDEN ARCHITECTURE: el receiver NO procesa. Solo guarda.
    # INSERT OR IGNORE = si event_id ya existe, no hace nada
    # (race-safe deduplication a nivel DB).
    # status='pending' = el worker lo va a tomar después.
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO processed_events 
               (event_id, event_type, raw_body, status) 
               VALUES (?, ?, ?, 'pending')""",
            (event_id, event_type, raw_body.decode('utf-8'))
        )
        conn.commit()
        # rowcount=0 significa que el INSERT fue ignorado
        # → ya existía → es un duplicado
        is_duplicate = cursor.rowcount == 0
    finally:
        conn.close()

    # ============================================================
    # PASO 7: Return 200 IMMEDIATELY (always 2xx)
    # ============================================================
    # Stripe ya cumplió su trabajo. Si es duplicado, también 200
    # (NO 409 — eso dispararía retries). El procesamiento real
    # pasa después en el worker, en otro proceso.
    if is_duplicate:
        return jsonify({
            "ok": True,
            "duplicate": True,
            "event_id": event_id,
            "message": "already in queue or processed"
        }), 200

    return jsonify({
        "ok": True,
        "event_id": event_id,
        "queued": True,
        "message": "event queued for async processing"
    }), 200  
    
    
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

    if not grant_type:
        return jsonify({"error": "missing_grant_type"}), 400

    if grant_type not in ("client_credentials", "authorization_code"):
        return jsonify({"error": "unsupported_grant_type"}), 400

    if client_id != OAUTH_CLIENT_ID or client_secret != OAUTH_CLIENT_SECRET:
        return jsonify({"error": "invalid_client"}), 401

    # --- Authorization Code grant (with PKCE) ---
    if grant_type == "authorization_code":
        code = request.form.get("code")
        code_verifier = request.form.get("code_verifier")
        redirect_uri = request.form.get("redirect_uri")

        if not code or code not in auth_codes:
            return jsonify({"error": "invalid_grant", "detail": "invalid or expired code"}), 400

        stored = auth_codes.pop(code)  # single-use

        if redirect_uri != stored["redirect_uri"]:
            return jsonify({"error": "invalid_grant", "detail": "redirect_uri mismatch"}), 400

        # PKCE verification
        if stored["code_challenge"]:
            if not code_verifier:
                return jsonify({"error": "invalid_grant", "detail": "code_verifier required"}), 400

            if stored["code_challenge_method"] == "S256":
                expected = base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                ).rstrip(b"=").decode()
            else:  # plain
                expected = code_verifier

            if expected != stored["code_challenge"]:
                return jsonify({"error": "invalid_grant", "detail": "code_verifier mismatch"}), 400

        scope = stored["scope"]

    # --- Client Credentials grant ---
    else:
        scope = request.form.get("scope", "read:items")

    now = int(time.time())

    access_payload = {
        "sub": client_id,
        "scope": scope,
        "iat": now,
        "exp": now + 3600,
    }
    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm="HS256")
    oauth_tokens[access_token] = scope

    response = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": scope
    }

    # OIDC: if scope includes "openid", add id_token with identity claims
    if "openid" in scope.split():
        id_payload = {
            "sub": client_id,
            "email": "test@example.com",
            "name": "Test User",
            "auth_time": now,
            "iat": now,
            "exp": now + 3600,
        }
        response["id_token"] = jwt.encode(id_payload, SECRET_KEY, algorithm="HS256")

    return jsonify(response), 200

 
@app.get("/oauth/authorize")
def oauth_authorize():
    client_id = request.args.get("client_id")
    redirect_uri = request.args.get("redirect_uri")
    response_type = request.args.get("response_type")
    scope = request.args.get("scope", "openid read:items")
    code_challenge = request.args.get("code_challenge")
    code_challenge_method = request.args.get("code_challenge_method", "S256")

    if not client_id or client_id != OAUTH_CLIENT_ID:
        return jsonify({"error": "invalid_client"}), 401

    if response_type != "code":
        return jsonify({"error": "unsupported_response_type"}), 400

    if not redirect_uri or redirect_uri != REGISTERED_REDIRECT_URI:
        return jsonify({
            "error": "redirect_uri_mismatch",
            "received": redirect_uri
        }), 400

    if code_challenge_method not in ("S256", "plain"):
        return jsonify({"error": "invalid_request", "detail": "unsupported code_challenge_method"}), 400

    auth_code = secrets.token_hex(8)

    auth_codes[auth_code] = {
        "scope": scope,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }

    return jsonify({
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "scope": scope
    }), 200
    

# ---------------------------------------------------------------------------
# Debug endpoints — simulate failure modes for testing
# ---------------------------------------------------------------------------

@app.post("/webhook/stripe/simulate-500")
def webhook_simulate_500():
    """Simulates endpoint crash — returns 500 every time."""
    return jsonify({"ok": False, "error": "simulated_server_error"}), 500


@app.post("/webhook/stripe/simulate-slow")
def webhook_simulate_slow():
    """Simulates slow endpoint — sleeps 12 seconds before responding.
    Stripe timeout is ~10s, so this triggers a timeout retry."""
    time.sleep(12)
    return jsonify({"ok": True, "slow": True}), 200


@app.post("/webhook/stripe/simulate-wrong-secret")
def webhook_simulate_wrong_secret():
    """Simulates wrong signing secret — verifies with a different secret,
    so all real Stripe-signed requests fail."""
    raw_body = request.get_data(as_text=False)
    sig_header = request.headers.get("Stripe-Signature", "")
    
    if not sig_header:
        return jsonify({"ok": False, "error": "missing_signature"}), 401

    sig_parts = {}
    for part in sig_header.split(","):
        key, _, value = part.partition("=")
        sig_parts[key.strip()] = value.strip()

    timestamp = sig_parts.get("t", "")
    received_sig = sig_parts.get("v1", "")

    # Use WRONG secret on purpose
    wrong_secret = "whsec_WRONG_SECRET_FOR_SIMULATION"
    
    signed_payload = f"{timestamp}.".encode() + raw_body
    expected_sig = hmac.new(
        wrong_secret.encode(),
        signed_payload,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, received_sig):
        return jsonify({
            "ok": False,
            "error": "signature_mismatch",
            "hint": "endpoint is verifying with wrong secret"
        }), 401

    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
