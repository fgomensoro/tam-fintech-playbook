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
    postman collection run "postman/Fintech Integration Starter Kit.postman_collection.json" \
      --environment postman/local.postman_environment.json