#!/bin/bash
set -e

# Define file to store server identity
IDENTITY_FILE="server_identity.json"

if [ ! -f "$IDENTITY_FILE" ]; then
    echo "Initializing new Cloud-X Backend Node..."
    # Generate UUID
    SERVER_ID=$(python3 -c 'import uuid; print(str(uuid.uuid4()))')
    echo "{\"server_id\": \"$SERVER_ID\", \"created_at\": \"$(date -Iseconds)\"}" > "$IDENTITY_FILE"
    echo "Generated new Server ID: $SERVER_ID"
else
    SERVER_ID=$(python3 -c "import json; print(json.load(open('$IDENTITY_FILE'))['server_id'])")
    echo "Loaded existing Server ID: $SERVER_ID"
fi

# Export as env var for app to use
export SERVER_ID=$SERVER_ID

# Start Application
exec python app.py
