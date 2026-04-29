"""
Async worker for processing webhook events.

Polls the SQLite queue, claims pending events atomically,
processes them, and stores the result in business_events.

Run separately from Flask: python services/webhook_receiver/worker.py
Or use: just worker
"""
import os
import time
import json
import sqlite3
import socket
import traceback
from datetime import datetime

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = os.environ.get("DB_PATH", "webhook_events.db")
WORKER_ID = os.environ.get("WORKER_ID", f"{socket.gethostname()}-{os.getpid()}")
POLL_INTERVAL_SEC = 1
CLAIM_TIMEOUT_MIN = 5  # reclaim events stuck in 'processing' after 5 min


# ---------------------------------------------------------------------------
# Initialize business_events table (worker's "output" table)
# ---------------------------------------------------------------------------
def init_business_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS business_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            origin TEXT NOT NULL,
            payload TEXT NOT NULL,
            worker_id TEXT,
            attempts INTEGER DEFAULT 1,
            last_error TEXT,
            processing_duration_ms INTEGER,
            processed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Claim next pending event atomically
# ---------------------------------------------------------------------------
def claim_next_event():
    """
    Atomically claim a pending event for this worker.
    
    Returns the event dict if successfully claimed, None if no events available.
    Uses UPDATE ... WHERE status='pending' to ensure only one worker wins.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        # Find one event to try to claim
        cursor = conn.execute("""
            SELECT event_id, event_type, raw_body, attempts
            FROM processed_events
            WHERE status = 'pending'
               OR (status = 'processing' 
                   AND claimed_at < datetime('now', '-5 minutes'))
            ORDER BY received_at ASC
            LIMIT 1
        """)
        row = cursor.fetchone()
        
        if not row:
            return None
        
        event_id, event_type, raw_body, attempts = row
        
        # Try to claim it atomically
        cursor = conn.execute("""
            UPDATE processed_events
            SET status = 'processing',
                claimed_at = datetime('now'),
                attempts = attempts + 1
            WHERE event_id = ?
              AND (status = 'pending' 
                   OR (status = 'processing' 
                       AND claimed_at < datetime('now', '-5 minutes')))
        """, (event_id,))
        conn.commit()
        
        # Si rowcount = 0, otro worker se lo llevó primero
        if cursor.rowcount == 0:
            return None
        
        return {
            "event_id": event_id,
            "event_type": event_type,
            "raw_body": raw_body,
            "attempts": attempts + 1
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Process event: simulate business logic by inserting into business_events
# ---------------------------------------------------------------------------
def process_event(event):
    """
    Simulates processing a webhook event.
    
    In a real system this would update business state, send emails,
    call external APIs, etc. Here we just record the processing in
    a separate table to demonstrate the receiver/worker split.
    """
    start = time.time()
    
    # Simulate some processing time (50-200ms)
    time.sleep(0.1)
    
    duration_ms = int((time.time() - start) * 1000)
    
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT OR IGNORE INTO business_events 
            (event_id, origin, payload, worker_id, 
             processing_duration_ms, processed_at, attempts)
            VALUES (?, 'stripe', ?, ?, ?, datetime('now'), ?)
        """, (
            event["event_id"],
            event["raw_body"],
            WORKER_ID,
            duration_ms,
            event["attempts"]
        ))
        conn.commit()
    finally:
        conn.close()
    
    return duration_ms


# ---------------------------------------------------------------------------
# Mark event as processed in queue
# ---------------------------------------------------------------------------
def mark_processed(event_id):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            UPDATE processed_events
            SET status = 'processed',
                processed_at = datetime('now')
            WHERE event_id = ?
        """, (event_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Mark event as failed (worker keeps it in 'pending' for retry)
# ---------------------------------------------------------------------------
def mark_failed(event_id, error):
    conn = sqlite3.connect(DB_PATH)
    try:
        # Volvemos a 'pending' para que se reintente
        conn.execute("""
            UPDATE processed_events
            SET status = 'pending',
                last_error = ?,
                claimed_at = NULL
            WHERE event_id = ?
        """, (str(error)[:500], event_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main():
    print(f"[worker {WORKER_ID}] starting, polling every {POLL_INTERVAL_SEC}s")
    init_business_table()
    
    while True:
        try:
            event = claim_next_event()
            
            if event is None:
                # Queue vacía, esperamos
                time.sleep(POLL_INTERVAL_SEC)
                continue
            
            print(f"[worker {WORKER_ID}] processing {event['event_id']} "
                  f"(attempt {event['attempts']})")
            
            try:
                duration_ms = process_event(event)
                mark_processed(event["event_id"])
                print(f"[worker {WORKER_ID}] processed {event['event_id']} "
                      f"in {duration_ms}ms")
            except Exception as e:
                print(f"[worker {WORKER_ID}] FAILED {event['event_id']}: {e}")
                traceback.print_exc()
                mark_failed(event["event_id"], e)
        
        except KeyboardInterrupt:
            print(f"[worker {WORKER_ID}] shutting down")
            break
        except Exception as e:
            # Error inesperado en el loop principal — no morimos, dormimos y reintentamos
            print(f"[worker {WORKER_ID}] loop error: {e}")
            traceback.print_exc()
            time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()