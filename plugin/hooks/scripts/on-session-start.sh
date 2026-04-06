#!/bin/bash
# Session start hook — restore pending work and restart daemons

echo "Tao Research System — session initialized"

# Check for active workspaces
if [ -d "workspaces" ]; then
    ACTIVE=$(find workspaces -name "status.json" -maxdepth 2 2>/dev/null | head -5)
    if [ -n "$ACTIVE" ]; then
        echo "Active workspaces found:"
        echo "$ACTIVE"
    fi
fi
