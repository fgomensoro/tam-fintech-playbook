set dotenv-load := true

receiver:
    python services/webhook_receiver/app.py

worker:
    python services/webhook_receiver/worker.py

dev:
    #!/usr/bin/env bash
    trap 'kill 0' EXIT
    just receiver &
    just worker &
    wait

test:
    @if [ -z "$STRIPE_SECRET_KEY" ] || [ "$STRIPE_SECRET_KEY" = "PASTE_YOUR_KEY_HERE" ]; then echo "WARNING: STRIPE_SECRET_KEY not configured in .env - Stripe API tests will fail with 401"; fi
    postman collection run "postman/Fintech Integration Starter Kit.postman_collection.json" \
      --environment postman/local.postman_environment.json \
      --env-var "base_url=$BASE_URL" \
      --env-var "bearer_token_admin=$BEARER_TOKEN_ADMIN" \
      --env-var "bearer_token_user=$BEARER_TOKEN_USER" \
      --env-var "stripe_secret_key=$STRIPE_SECRET_KEY"
