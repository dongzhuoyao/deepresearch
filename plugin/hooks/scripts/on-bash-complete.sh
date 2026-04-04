#!/bin/bash
# Post-bash hook — detect sync requests and launch background tasks
# Called by Claude Code after every Bash tool execution

OUTPUT="$1"

# Check for sync_requested marker
if echo "$OUTPUT" | grep -q "sync_requested"; then
    echo "Sync requested — launching background sync..."
fi
