---
name: tao-experimenter
description: Run experiments on GPU
context: fork
---

!`.venv/bin/python3 -c "from tao.orchestrate import render_skill_prompt; print(render_skill_prompt('$WORKSPACE', 'experimenter'))"`
