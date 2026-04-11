# System Evolution

**Usage:** `/evolve [--show|--apply|--reset]`

Trigger cross-project self-evolution to improve the system based on past runs.

- `--show`: Display accumulated lessons and fix effectiveness
- `--apply`: Generate fresh agent overlays from evolution log
- `--reset`: Clear evolution history (fresh start)

```bash
python3 -c "from tao.orchestrate import cli_evolve; print(cli_evolve('$ARGUMENTS' or '.'))"
```
