#!/bin/bash
# Stop hook — clean up PID files for stopped projects

WORKSPACE="$1"
if [ -d "$WORKSPACE/exp" ]; then
    echo "Cleaning up experiment PID files..."
    find "$WORKSPACE/exp" -name "*.pid" -delete 2>/dev/null
fi
