---
name: init-workspace
description: Start a new submission from a call-for-paper URL (defaults to NeurIPS)
allowed-tools: ["Bash", "Read", "Write"]
---

# Initialize Submission Workspace from Call-for-Paper

**Usage:**
- `/deepresearch:init-workspace` — defaults to NeurIPS (latest)
- `/deepresearch:init-workspace <cfp-url>` — scrape the provided CFP

Creates a Tao workspace tailored to a target venue. Scrapes the CFP for
venue constraints (deadline, page limit, template, anonymity, topics), asks
the user for the research topic, synthesizes a structured `spec.md`, and
calls the existing `cli_init_from_spec` to create the workspace.

## Flow

### Step 1 — Resolve CFP URL

- If `$ARGUMENTS` is empty, use the NeurIPS default:
  `https://neurips.cc/Conferences/2026/CallForPapers`
- Otherwise use `$ARGUMENTS` as the URL.

### Step 2 — Scrape the CFP

Use `WebFetch` on the CFP URL with this extraction prompt:

> Extract the following fields from this Call-for-Paper page. Return each
> field on its own line as `FIELD: value` or `FIELD: MISSING` if not stated
> on the page. Do NOT guess. Do NOT infer from prior knowledge.
>
> - VENUE (conference name + year, e.g. "NeurIPS 2026")
> - SUBMISSION_DEADLINE (absolute date incl. timezone, e.g. "2026-05-15 AoE")
> - ABSTRACT_DEADLINE (absolute date, or MISSING if same as submission)
> - NOTIFICATION_DATE (absolute date)
> - REBUTTAL_WINDOW (start — end absolute dates)
> - SUBMISSION_SITE_URL
> - MAIN_PAGE_LIMIT (integer, e.g. 9)
> - REFERENCES_LIMIT ("unlimited" or integer)
> - APPENDIX_LIMIT ("unlimited", "separate file", or integer)
> - TEMPLATE_URL (link to LaTeX style files)
> - ANONYMITY ("double-blind" | "single-blind" | "open")
> - SUPPLEMENTARY_POLICY (one-line summary)
> - TOPICS_OF_INTEREST (bullet list of topic areas; MISSING if none listed)

Parse the response into a dict keyed by field name.

### Step 3 — Fill missing fields with NeurIPS defaults

Apply defaults ONLY for non-date fields. Dates that scrape as `MISSING`
stay as `TBD` — never guess a deadline.

NeurIPS defaults (fallback only):
- `VENUE`: `NeurIPS 2026`
- `MAIN_PAGE_LIMIT`: `9`
- `REFERENCES_LIMIT`: `unlimited`
- `APPENDIX_LIMIT`: `unlimited (same PDF)`
- `TEMPLATE_URL`: `https://neurips.cc/Conferences/2026/PaperInformation/StyleFiles`
- `ANONYMITY`: `double-blind`
- `SUPPLEMENTARY_POLICY`: `allowed, separate upload`

Track which fields were defaulted — they will appear in the spec's
"Fields defaulted" line and in the final summary. No silent fallbacks.

### Step 4 — Ask user for the research topic

Use `AskUserQuestion`. If `TOPICS_OF_INTEREST` was scraped, include the
list in the question text as suggestions. Ask:

> What research topic for this submission? (One sentence. You can pick
> from the venue's topics of interest above, or propose your own.)

Store the answer as `TOPIC`.

### Step 5 — Synthesize spec.md

Write to `/tmp/tao_spec_$(date +%s).md` using this exact template. The H1
is the topic (first-line-is-topic contract in `cli_init_from_spec`).

```markdown
# {TOPIC}

## Venue
- **Conference:** {VENUE}
- **Submission deadline:** {SUBMISSION_DEADLINE}
- **Abstract deadline:** {ABSTRACT_DEADLINE}
- **Notification:** {NOTIFICATION_DATE}
- **Submission site:** {SUBMISSION_SITE_URL}

## Format Constraints
- **Main paper:** {MAIN_PAGE_LIMIT} pages
- **References:** {REFERENCES_LIMIT}
- **Appendix:** {APPENDIX_LIMIT}
- **Template:** {TEMPLATE_URL}
- **Anonymity:** {ANONYMITY}
- **Supplementary:** {SUPPLEMENTARY_POLICY}

## Topics of Interest
{TOPICS_OF_INTEREST as bullet list, or "- (not listed on CFP page)"}

## Review Timeline
- Rebuttal: {REBUTTAL_WINDOW}
- Final decision: {NOTIFICATION_DATE}

## CFP Source
- URL: {cfp-url}
- Scraped at: {ISO-8601 UTC timestamp}
- Fields defaulted (scrape gaps): {comma-separated list, or "none"}
```

### Step 6 — Ask user to name the workspace folder

Use `AskUserQuestion`. Suggest a default derived from the topic (first ~5
words, lowercased, underscores, ASCII-only), e.g. `diffusion_few_step_distill`.
Ask:

> What folder name for this workspace? (letters / digits / underscores;
> defaults to `{suggested}` if you press enter)

If the user's answer is empty, use `{suggested}`. Store the result as
`WS_NAME`. The name will be sanitized by `_sanitize_workspace_name` (lowercase,
spaces/hyphens → `_`, other chars stripped, capped at 80 chars). If the
sanitized name collides with an existing workspace under the configured
workspaces directory, append `_2`, `_3`, … until unique.

### Step 7 — Create the workspace

```bash
.venv/bin/python3 -c "from tao.orchestrate import cli_init_from_spec; print(cli_init_from_spec('/tmp/tao_spec_<ts>.md', workspace_name='<WS_NAME>'))"
```

Capture the returned workspace path as `WS_PATH`.

### Step 8 — Download the LaTeX template

Stage the venue's style files into the workspace so the `writing_latex`
stage can compile directly. **Never skip this silently** — if the download
fails or the CFP did not expose a template URL, record it clearly in the
final summary.

Target directories:
- `{WS_PATH}/paper_template/` — pristine copy of whatever was downloaded
  (kept as-is for future reference).
- `{WS_PATH}/writing/latex/` — working directory; copy the style/cls/bst
  files here so `paper.tex` can `\documentclass{...}` them later.

Procedure:

1. If `TEMPLATE_URL` is `MISSING` or empty, print
   `WARNING: no LaTeX template URL — add one to writing/latex/ manually before writing_latex`
   and skip the rest of this step.
2. Create both target directories:
   ```bash
   mkdir -p "{WS_PATH}/paper_template" "{WS_PATH}/writing/latex"
   ```
3. **Direct asset** — if `TEMPLATE_URL` ends in `.zip`, `.tar.gz`, `.tgz`,
   `.tar`, `.sty`, `.cls`, `.bst`, `.tex`, or `.pdf`, fetch it directly:
   ```bash
   curl -fL --noproxy '*' -o "{WS_PATH}/paper_template/$(basename <TEMPLATE_URL>)" "<TEMPLATE_URL>"
   ```
   Unpack archives in place:
   ```bash
   cd "{WS_PATH}/paper_template" && \
     (unzip -o *.zip 2>/dev/null || tar -xf *.tar.gz 2>/dev/null || tar -xf *.tgz 2>/dev/null || true)
   ```
4. **Landing page** — otherwise (e.g. NeurIPS `StyleFiles` HTML page), use
   `WebFetch` on `TEMPLATE_URL` with this extraction prompt:
   > List every absolute URL on this page whose pathname ends in one of:
   > `.zip`, `.tar.gz`, `.tgz`, `.sty`, `.cls`, `.bst`, `.tex`, `.pdf`.
   > Return one URL per line, nothing else. If none found, return the
   > single word `NONE`.

   If the response is `NONE`, warn
   `WARNING: could not locate style files at {TEMPLATE_URL}. Download manually into writing/latex/.`
   and skip to step 6. Otherwise `curl -fL --noproxy '*' -o …` each URL into
   `{WS_PATH}/paper_template/`, then unpack archives as in step 3.
5. Copy the pristine files into the working directory, preserving
   subfolders:
   ```bash
   cp -R "{WS_PATH}/paper_template/." "{WS_PATH}/writing/latex/"
   ```
6. Record the outcome for the summary step:
   - `TEMPLATE_STATUS`: one of `ok`, `warn-no-url`, `warn-no-assets`,
     `warn-download-failed`.
   - `TEMPLATE_FILES`: list of basenames placed under `writing/latex/`
     (for the summary line).

Any `curl` non-zero exit flips `TEMPLATE_STATUS` to `warn-download-failed`
and the summary must surface the specific URL that failed. No silent
fallbacks — the user must know whether the template landed.

### Step 9 — Ask whether the project needs GPU compute

Use `AskUserQuestion`:

> Does this project need GPU experiments on RunPod?
> - yes (default) — will run experiments on paid RunPod pods
> - no — theory / survey / analysis paper, skip the experiment cycle

Store as `NEEDS_GPU` (bool). Write a minimal override to
`{WS_PATH}/config.yaml` (merge with existing if the file exists):

```yaml
runpod_enabled: {NEEDS_GPU}
```

If `NEEDS_GPU` is `no`, note in the final summary that the experiment cycle
will be skipped; Tao's state machine will advance idea → writing without
the experiment stages.

### Step 10 — Print summary

Show the user:
1. Workspace path
2. Venue + deadline (or `TBD` flag if defaulted)
3. Page limits
4. GPU: `yes` or `no (theory/survey mode)`
5. LaTeX template: `TEMPLATE_STATUS` + basename list (e.g.
   `ok — neurips_2026.sty, neurips_2026.bst`). For any `warn-*` status,
   print the specific remediation (missing URL, no assets on page, or the
   failing URL for download failures).
6. A one-line warning if any CFP field was defaulted:
   `WARNING: scrape gaps — {fields}. Review spec.md before starting.`

### Step 11 — Offer to start the pipeline

Ask via `AskUserQuestion`:
> Start the autonomous research pipeline now on topic "{TOPIC}"?
> - yes (default) — begin the orchestration loop immediately
> - no — I'll review spec.md / config.yaml first and start manually

If **yes**: execute the same steps as `plugin/commands/start.md` with
`$ARGUMENTS` = `{WS_PATH}`. That is, call `cli_status` then enter the
`cli_next` / `cli_record` loop until the stage reaches `done`.

If **no**: print `To start later: /deepresearch:start {WS_PATH}`.
