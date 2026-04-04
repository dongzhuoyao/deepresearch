---
name: debug
description: Debug utilities for the research pipeline
allowed-tools: ["Bash", "Read", "Write"]
---

# Debug Utilities

**Usage:** `/deepresearch:debug <workspace_path>`

## Available Actions

1. **State inspection**: Show full workspace status, experiment state, GPU progress
2. **Error scan**: Run self-heal scan for fixable errors
3. **Log review**: Show recent events and iteration history
4. **Reset stage**: Manually set the pipeline stage (use with caution)
