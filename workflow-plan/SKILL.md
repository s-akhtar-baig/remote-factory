---
name: workflow-plan
description: "Plan-only workflow — truncated design workflow (triggered via --mode design --just-plan). Prior plan check + research + strategy + single approval gate, with NO implementation. Checks for prior plans on GitHub issues (plan label) and local archive before researching. Produces a phased plan at .factory/strategy/current.md. Single approval gate: 'Keep this plan?' — approval auto-publishes to GitHub and seeds backlog. RELOOP re-runs Strategist with feedback. HALT exits without publishing. Terminal — does not chain to build or improve."
disable-model-invocation: true
argument-hint: "<project_path> --mode design --just-plan [--focus <topic>]"
---

# Plan Workflow

The user wants: **$ARGUMENTS**

### Gate — Has Factory (Automated)

**MANDATORY:** Wait for the preceding agent to finish, then run this check BEFORE spawning the next agent. Do NOT run agents in parallel across this gate.

```bash
python3 -c "from pathlib import Path; exists = Path("$PROJECT_PATH/.factory/config.json").exists(); print("PROCEED" if exists else "HALT")"
```

- **PROCEED** (exit 0 / no FAIL in output) → continue to `graph_update`
- **HALT** (exit non-zero / FAIL in output) → continue to `discover` instead.

## Step: Discover

```bash
factory discover $PROJECT_PATH
```

## Step: Eval Test

```bash
cd $PROJECT_PATH && python eval/score.py
```

### CEO Review — Eval

Apply the CEO Review Gate protocol:
1. Read the agent output for the preceding step
2. Read artifacts: `.factory/reviews/eval-test-latest.md`
3. Assess: Check eval output. Did all dimensions pass? If any dimension failed, dispatch the Builder to fix it (install missing tool, adjust command, remove broken dimension). PROCEED only when all dimensions produce valid scores.
4. Write verdict to `.factory/reviews/ceo-verdict-eval.md`
5. **PROCEED** → continue to next step
6. **REDIRECT** → re-invoke the preceding agent with corrections (max 2)
7. **ABORT** → log failure and skip to archival

*On RELOOP: return to `eval_test` (max 3 iterations)*

## Step: Mark Reviewed

Mark the eval profile as human-reviewed by setting the human_reviewed flag.

```bash
python3 -c "import json; from pathlib import Path; p = Path('$PROJECT_PATH/.factory/eval_profile.json'); d = json.loads(p.read_text()); d['human_reviewed'] = True; p.write_text(json.dumps(d, indent=2))"
```

## Phase 1: Ceo — Create Factory Md

```bash
factory agent ceo --task "Create factory.md from template. Copy the factory config template to the project root. Fill in: Goal, Scope, Guards, Eval command, Threshold, and Smoke Test. If .factory/eval_spec.json exists, populate the Eval Spec section. If .factory/strategy/current.md has a Research Configuration section, populate research sections (Research Target, Mutable/Fixed Surfaces, etc.).
Read: .factory/eval_profile.json
Write output to: factory.md" --project "$PROJECT_PATH" --timeout 3600
```

```bash
# Artifact verification: create_factory_md
_vfail=0
_f="$PROJECT_PATH/factory.md"
[ ! -f "$_f" ] && echo "VERIFY FAIL: create_factory_md: factory.md missing" && _vfail=1
[ -f "$_f" ] && [ ! -s "$_f" ] && echo "VERIFY FAIL: create_factory_md: factory.md is empty" && _vfail=1
[ "$_vfail" -ne 0 ] && echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) VERIFY_FAIL node=create_factory_md" >> "$PROJECT_PATH/.factory/hooks/hook-log.txt" && exit 1
echo "VERIFY OK: create_factory_md artifacts validated"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) VERIFY_OK node=create_factory_md" >> "$PROJECT_PATH/.factory/hooks/hook-log.txt"
```
*(harness verification — DO NOT SKIP)*

## Step: Factory Init

Parse factory.md and generate .factory/config.json. Must run after factory.md is created.

```bash
factory init $PROJECT_PATH
```

## Step: Graph Update

Extract or incrementally update the code knowledge graph before study.

```bash
factory graph update $PROJECT_PATH
```

## Phase 2: Observe

Run local study to gather observations:

```bash
factory study $PROJECT_PATH
```

Writes observations to `.factory/strategy/observations.md`.

If your task includes a focus directive or focus topic, pass it to the study command:
`factory study $PROJECT_PATH --focus "<your focus topic>"`

## Phase 3: Researcher — Graph Explorer

```bash
factory agent researcher --task "Explore the project's code knowledge graph to build structural understanding. Read .factory/strategy/observations.md for focus context.

**Step 0 — detect graph availability:** Your working directory is already the project root. The graph file lives at `$PROJECT_PATH/graph.json` (NOT inside `.factory/`). Run this smoke check FIRST — use a relative path since your CWD is the project root: `test -f graph.json && echo 'GRAPH AVAILABLE' || echo 'NO GRAPH'` — if the output says GRAPH AVAILABLE, proceed with the graph commands below. If the output says NO GRAPH, skip to the fallback section.

**If the graph IS available:**
1. Run `factory graph query "$PROJECT_PATH" "<focus from observations>" --depth 2` to find relevant nodes
2. Run `factory graph explain "$PROJECT_PATH" "<key node>"` on the most important nodes to understand their connections and dependencies
3. Run `factory graph path "$PROJECT_PATH" "<A>" "<B>"` to trace dependency paths between key components
4. Write structured findings to .factory/strategy/graph-context.md covering: key modules and their relationships, dependency paths, architectural layers, entry points and hotspots

**If the graph is NOT available**, fall back to direct file exploration:
1. Use `find . -name '*.py' | head -50` to discover source files
2. Use `grep -rn 'class \|def ' --include='*.py' | head -100` to map functions and classes
3. Use `grep -rn 'import ' --include='*.py' | head -100` to trace dependencies
4. Write the same structured findings to .factory/strategy/graph-context.md
Read: .factory/strategy/observations.md
Write output to: .factory/strategy/graph-context.md" --project "$PROJECT_PATH" --timeout 600
```

```bash
# Artifact verification: graph_explorer
_vfail=0
_f="$PROJECT_PATH/.factory/strategy/graph-context.md"
[ ! -f "$_f" ] && echo "VERIFY FAIL: graph_explorer: .factory/strategy/graph-context.md missing" && _vfail=1
[ -f "$_f" ] && [ ! -s "$_f" ] && echo "VERIFY FAIL: graph_explorer: .factory/strategy/graph-context.md is empty" && _vfail=1
[ "$_vfail" -ne 0 ] && echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) VERIFY_FAIL node=graph_explorer" >> "$PROJECT_PATH/.factory/hooks/hook-log.txt" && exit 1
echo "VERIFY OK: graph_explorer artifacts validated"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) VERIFY_OK node=graph_explorer" >> "$PROJECT_PATH/.factory/hooks/hook-log.txt"
```
*(harness verification — DO NOT SKIP)*

## Step: Concat Study

```bash
cat $PROJECT_PATH/.factory/strategy/observations.md $PROJECT_PATH/.factory/strategy/graph-context.md > $PROJECT_PATH/.factory/strategy/study-combined.md
```

### Gate — Check Prior Plans (Automated)

**MANDATORY:** Wait for the preceding agent to finish, then run this check BEFORE spawning the next agent. Do NOT run agents in parallel across this gate.

```bash
: > "$PROJECT_PATH/.factory/strategy/prior-plans.md"; if [ -n "$FOCUS" ]; then   if gh auth status >/dev/null 2>&1 && git remote -v 2>/dev/null | grep -q .; then     gh issue list --label plan --search "$FOCUS" --json number,title,url       --jq ".[] | \"#\(.number) \(.title) — \(.url)\""       > "$PROJECT_PATH/.factory/strategy/prior-plans.md" 2>/dev/null || true;   fi;   if [ ! -s "$PROJECT_PATH/.factory/strategy/prior-plans.md" ]; then     grep -Frl "$FOCUS" "$PROJECT_PATH/.factory/archive/" --include="plan-*.md"       >> "$PROJECT_PATH/.factory/strategy/prior-plans.md" 2>/dev/null || true;   fi; fi; [ -s "$PROJECT_PATH/.factory/strategy/prior-plans.md" ]
```

- **PROCEED** (exit 0 / no FAIL in output) → continue to `gate_prior_plans`
- **HALT** (exit non-zero / FAIL in output) → continue to `fork_research` instead.

### Steering Point — Prior Plans (User Approval)

**This is a USER approval gate, NOT a CEO review gate. Do NOT self-approve.**

Present the strategy/findings to the user by summarizing key points in your output.
Then explicitly ask the user: "Do you approve this plan, or do you have feedback?"

**You MUST wait for the user's response before proceeding.**
- The user says "approve", "yes", "looks good", or similar → proceed to next step
- The user provides feedback or corrections → re-run the previous step incorporating their feedback
- Do NOT write a verdict file and auto-proceed — this gate requires human input

## Phase 4: Research (Parallel)

Spawn 3 agents in parallel:

```bash
factory agent researcher --review-tag similar --task "Similar projects research. Read .factory/strategy/study-combined.md for project context (observations + structural graph analysis). Search the web for similar projects, existing solutions, and prior art. Analyze their strengths, weaknesses, and market positioning. Check .factory/archive/ for prior knowledge on similar builds. Write findings to .factory/strategy/research-similar.md covering: similar projects found (with links), what they do well and what's missing, differentiation opportunities.
Read: .factory/strategy/study-combined.md
Write output to: .factory/strategy/research-similar.md" --project "$PROJECT_PATH" --timeout 600 &
```

```bash
factory agent researcher --review-tag techstack --task "Tech stack research. Read .factory/strategy/study-combined.md for project context (observations + structural graph analysis). Identify the best technology stack for this type of project. Find architecture patterns and best practices. Evaluate framework/library options with trade-offs. Write findings to .factory/strategy/research-techstack.md covering: recommended tech stack with rationale, architecture patterns, framework comparisons.
Read: .factory/strategy/study-combined.md
Write output to: .factory/strategy/research-techstack.md" --project "$PROJECT_PATH" --timeout 600 &
```

```bash
factory agent researcher --review-tag pitfalls --task "Pitfalls and scope research. Read .factory/strategy/study-combined.md for project context (observations + structural graph analysis). Identify potential pitfalls and common mistakes for this type of project. Research MVP scope best practices. Check .factory/archive/ for lessons from past builds. Write findings to .factory/strategy/research-pitfalls.md covering: potential pitfalls to avoid, MVP scope recommendation, lessons from similar past builds.
Read: .factory/strategy/study-combined.md
Write output to: .factory/strategy/research-pitfalls.md" --project "$PROJECT_PATH" --timeout 600 &
```

```bash
wait
```

**Important:** Run ALL commands above in a **single** Bash tool call with timeout set to at least 600 seconds.

```bash
# Artifact verification: researcher_similar
_vfail=0
_f="$PROJECT_PATH/.factory/strategy/research-similar.md"
[ ! -f "$_f" ] && echo "VERIFY FAIL: researcher_similar: .factory/strategy/research-similar.md missing" && _vfail=1
[ -f "$_f" ] && [ ! -s "$_f" ] && echo "VERIFY FAIL: researcher_similar: .factory/strategy/research-similar.md is empty" && _vfail=1
[ -f "$_f" ] && [ "$(wc -c < "$_f")" -lt 50 ] && echo "VERIFY FAIL: researcher_similar: .factory/strategy/research-similar.md smaller than 50 bytes" && _vfail=1
[ "$_vfail" -ne 0 ] && echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) VERIFY_FAIL node=researcher_similar" >> "$PROJECT_PATH/.factory/hooks/hook-log.txt" && exit 1
echo "VERIFY OK: researcher_similar artifacts validated"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) VERIFY_OK node=researcher_similar" >> "$PROJECT_PATH/.factory/hooks/hook-log.txt"

# Artifact verification: researcher_techstack
_vfail=0
_f="$PROJECT_PATH/.factory/strategy/research-techstack.md"
[ ! -f "$_f" ] && echo "VERIFY FAIL: researcher_techstack: .factory/strategy/research-techstack.md missing" && _vfail=1
[ -f "$_f" ] && [ ! -s "$_f" ] && echo "VERIFY FAIL: researcher_techstack: .factory/strategy/research-techstack.md is empty" && _vfail=1
[ -f "$_f" ] && [ "$(wc -c < "$_f")" -lt 50 ] && echo "VERIFY FAIL: researcher_techstack: .factory/strategy/research-techstack.md smaller than 50 bytes" && _vfail=1
[ "$_vfail" -ne 0 ] && echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) VERIFY_FAIL node=researcher_techstack" >> "$PROJECT_PATH/.factory/hooks/hook-log.txt" && exit 1
echo "VERIFY OK: researcher_techstack artifacts validated"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) VERIFY_OK node=researcher_techstack" >> "$PROJECT_PATH/.factory/hooks/hook-log.txt"

# Artifact verification: researcher_pitfalls
_vfail=0
_f="$PROJECT_PATH/.factory/strategy/research-pitfalls.md"
[ ! -f "$_f" ] && echo "VERIFY FAIL: researcher_pitfalls: .factory/strategy/research-pitfalls.md missing" && _vfail=1
[ -f "$_f" ] && [ ! -s "$_f" ] && echo "VERIFY FAIL: researcher_pitfalls: .factory/strategy/research-pitfalls.md is empty" && _vfail=1
[ -f "$_f" ] && [ "$(wc -c < "$_f")" -lt 50 ] && echo "VERIFY FAIL: researcher_pitfalls: .factory/strategy/research-pitfalls.md smaller than 50 bytes" && _vfail=1
[ "$_vfail" -ne 0 ] && echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) VERIFY_FAIL node=researcher_pitfalls" >> "$PROJECT_PATH/.factory/hooks/hook-log.txt" && exit 1
echo "VERIFY OK: researcher_pitfalls artifacts validated"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) VERIFY_OK node=researcher_pitfalls" >> "$PROJECT_PATH/.factory/hooks/hook-log.txt"
```
*(post-barrier harness verification — DO NOT SKIP)*

## Barrier: Research

Wait for all parallel agents to complete: `researcher_similar`, `researcher_techstack`, `researcher_pitfalls`

### CEO Review — Research

Apply the CEO Review Gate protocol:
1. Read the agent output for the preceding step
2. Read artifacts: `.factory/strategy/research-pitfalls.md`, `.factory/strategy/research-similar.md`, `.factory/strategy/research-techstack.md`
3. Assess: Is the research relevant? Does it cover the technology landscape adequately? Check for gaps in similar projects, tech stack analysis, and pitfall coverage.
4. Write verdict to `.factory/reviews/ceo-verdict-research.md`
5. **PROCEED** → continue to next step
6. **REDIRECT** → re-invoke the preceding agent with corrections (max 2)
7. **ABORT** → log failure and skip to archival

*On RELOOP: return to `fork_research` (max 3 iterations)*

## Phase 5: Strategist

```bash
factory agent strategist --task "Synthesize a project specification from study and research. If .factory/strategy/study-combined.md exists, read it for project observations and structural graph analysis. Read ALL research files at .factory/strategy/research-similar.md, research-techstack.md, and research-pitfalls.md. Produce a complete phased build plan. Phase 1 must be project scaffold + eval harness. Every Phase must have substantive What/Why/Expected impact fields. Build EVERYTHING in this pass. Only defer items requiring human intervention. Write the plan to .factory/strategy/current.md.
Read: .factory/strategy/research-pitfalls.md, .factory/strategy/research-similar.md, .factory/strategy/research-techstack.md, .factory/strategy/study-combined.md
Write output to: .factory/strategy/current.md" --project "$PROJECT_PATH" --timeout 600
```

```bash
# Artifact verification: strategist
_vfail=0
_f="$PROJECT_PATH/.factory/strategy/current.md"
[ ! -f "$_f" ] && echo "VERIFY FAIL: strategist: .factory/strategy/current.md missing" && _vfail=1
[ -f "$_f" ] && [ ! -s "$_f" ] && echo "VERIFY FAIL: strategist: .factory/strategy/current.md is empty" && _vfail=1
[ -f "$_f" ] && [ "$(wc -c < "$_f")" -lt 200 ] && echo "VERIFY FAIL: strategist: .factory/strategy/current.md smaller than 200 bytes" && _vfail=1
[ -f "$_f" ] && ! grep -qE '\#\#\#\ Phase\ 1|\#\#\#\ Architecture' "$_f" && echo "VERIFY FAIL: strategist: .factory/strategy/current.md missing required sentinel (### Phase 1, ### Architecture)" && _vfail=1
[ "$_vfail" -ne 0 ] && echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) VERIFY_FAIL node=strategist" >> "$PROJECT_PATH/.factory/hooks/hook-log.txt" && exit 1
echo "VERIFY OK: strategist artifacts validated"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) VERIFY_OK node=strategist" >> "$PROJECT_PATH/.factory/hooks/hook-log.txt"
```
*(harness verification — DO NOT SKIP)*

### Steering Point — Strategy (User Approval)

**This is a USER approval gate, NOT a CEO review gate. Do NOT self-approve.**

Present the strategy/findings to the user by summarizing key points in your output.
Then explicitly ask the user: "Do you approve this plan, or do you have feedback?"

**You MUST wait for the user's response before proceeding.**
- The user says "approve", "yes", "looks good", or similar → proceed to next step
- The user provides feedback or corrections → re-run the previous step incorporating their feedback
- Do NOT write a verdict file and auto-proceed — this gate requires human input

*On RELOOP: return to `strategist` (max 3 iterations)*

## Step: Publish Github

Publishes the approved plan to a GitHub issue. If no git remote exists, auto-creates a public GitHub repository via 'gh repo create --public --source=. --remote=origin --push'. If the repo name already exists on GitHub, links it as a remote instead. After ensuring a remote exists, publishes the plan: if --focus is an issue number, posts as a comment; otherwise creates a new issue titled 'Plan: <focus>'. Writes the issue number to github-issue-ref.txt for downstream use by seed_backlog. Graceful degradation: if gh is not authenticated, not in a git repo, or repo creation fails, writes 'none' and exits cleanly.

```bash
bash -c 'set -e; echo "none" > "$PROJECT_PATH/.factory/strategy/github-issue-ref.txt"; if ! gh auth status >/dev/null 2>&1; then   echo "SKIP: gh not authenticated — plan saved locally only"; exit 0; fi; if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then   echo "SKIP: not inside a git repository"; exit 0; fi; if ! git remote -v 2>/dev/null | grep -q .; then   SLUG=$(basename "$PROJECT_PATH");   echo "Creating GitHub repository: $SLUG...";   if gh repo create "$SLUG" --public --source=. --remote=origin --push 2>&1; then     REPO_URL=$(gh repo view "$SLUG" --json url -q .url 2>/dev/null || echo "");     echo "GitHub repository created: ${REPO_URL:-$SLUG}";   elif gh repo view "$SLUG" >/dev/null 2>&1; then     echo "Repository $SLUG already exists on GitHub, linking as remote...";     REMOTE_URL=$(gh repo view "$SLUG" --json sshUrl -q .sshUrl 2>/dev/null ||       gh repo view "$SLUG" --json url -q .url);     git remote add origin "$REMOTE_URL" 2>/dev/null || true;     git push -u origin HEAD 2>/dev/null || true;   else     echo "SKIP: could not create GitHub repo — plan saved locally only"; exit 0;   fi; fi; gh label create plan --description "Approved plan" --color 0366d6 --force 2>/dev/null || true; FOCUS="${FOCUS:-}"; ISSUE_NUM=""; if echo "$FOCUS" | grep -qE "^[0-9]+$"; then   ISSUE_NUM="$FOCUS"; elif echo "$FOCUS" | grep -qoE "#([0-9]+)"; then   ISSUE_NUM=$(echo "$FOCUS" | grep -oE "[0-9]+" | tail -1); fi; if [ -n "$ISSUE_NUM" ]; then   gh issue comment "$ISSUE_NUM" --body-file "$PROJECT_PATH/.factory/strategy/current.md";   gh issue edit "$ISSUE_NUM" --add-label plan;   echo "$ISSUE_NUM" > "$PROJECT_PATH/.factory/strategy/github-issue-ref.txt";   echo "Plan posted to issue #$ISSUE_NUM"; else   TITLE="Plan: ${FOCUS:-project}";   ISSUE_URL=$(gh issue create --title "$TITLE" --body-file "$PROJECT_PATH/.factory/strategy/current.md" --label plan);   ISSUE_NUM=$(echo "$ISSUE_URL" | grep -oE "[0-9]+$");   echo "$ISSUE_NUM" > "$PROJECT_PATH/.factory/strategy/github-issue-ref.txt";   echo "Created plan issue: $ISSUE_URL"; fi'
```

## Step: Seed Backlog

Extracts phase headers from the approved plan at current.md and appends them as backlog items to backlog.md. References GitHub issue number if publish_github ran (reads github-issue-ref.txt), otherwise references current.md. Example: '- [ ] Phase 1: Set up auth middleware (see #42)'

```bash
python3 -c "import re, os; project = '$PROJECT_PATH'; plan = open(f'{project}/.factory/strategy/current.md').read(); ref_file = f'{project}/.factory/strategy/github-issue-ref.txt'; issue_num = open(ref_file).read().strip() if os.path.exists(ref_file) else 'none'; ref = f'(see #{issue_num})' if issue_num != 'none' else '(see .factory/strategy/current.md)'; phases = re.findall(r'### Phase \d+:.*', plan); backlog_path = f'{project}/.factory/strategy/backlog.md'; items = '\n'.join(f'- [ ] {p[4:]} {ref}' for p in phases); open(backlog_path, 'a').write('\n' + items + '\n') if items else None; print(f'Seeded {len(phases)} backlog items from plan')"
```
