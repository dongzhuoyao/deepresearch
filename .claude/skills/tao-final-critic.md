---
name: tao-final-critic
description: Final paper quality scoring (0-10 scale)
context: fork
---

!`.venv/bin/python3 -c "from tao.orchestrate import render_skill_prompt; print(render_skill_prompt('$WORKSPACE', 'final-critic'))"`
