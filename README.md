# Minimum Viable Factory

Ticket in, deployed web app out. The full SDLC — spec, architecture, code, review, tests, deploy — handled by Claude Code agents running in parallel. You approve at three gates.

**~1,500 lines of Python across 17 modules. 10 skills. 5 MCPs. You can read every file in one sitting.**

Right now this factory greenfields web apps from idea to production. You describe what you want, agents build and deploy it from scratch. Each app gets its own GitHub repo. Large tasks are automatically decomposed into subtasks and built in parallel. Brownfield support (existing codebases, new features, bug fixes) is next.

## What This Fork Changes

This is a fork of [ashtilawat/minimum-viable-factory](https://github.com/ashtilawat/minimum-viable-factory) by Ashalesh Tilawat. The pipeline, the Linear tracking, the human gates, and the review, test and deploy agents are his.

The problem this fork works on: the dev agents all write to one folder on one git branch at the same time, and the only thing keeping them out of each other's files was the subtask list in the architect's written plan. On bigger apps they overwrote each other and left subtasks unbuilt.

| Change | What it does | Where |
|---|---|---|
| **Decompose in the architect's session** | The decompose node continues the architect agent's own Claude Code session (Agent SDK `resume`) instead of running a regex over its written plan. The agent that designed the app decides how many dev agents to start (1 to 6) and which files each one owns. The regex parser is kept as the fallback. | `orchestrator/nodes/dev.py`, `orchestrator/agent_runner.py`, `.claude/skills/decompose/` |
| **Merge agent** | After the parallel dev agents finish, one more session compares the git log against the file ownership list, checks every file two agents touched, builds anything missing, and fixes the build before the PR is opened. | `orchestrator/nodes/dev.py`, `.claude/skills/merge-check/` |
| **Project-specific skill files** | After writing the spec, the PM agent writes a version of the architecture, coding, test and deploy skill files that fits this app. Agents load those in place of the fixed files. | `orchestrator/skills.py`, `orchestrator/nodes/agents.py`, `.claude/skills/skill-writing/` |
| **Security review agent** | A third QA agent runs next to code review and tests, with a fixed checklist: secrets, injection, row-level security, unguarded pages, values trusted from the browser, `npm audit`. | `orchestrator/graph.py`, `.claude/skills/security-review/` |
| **Skill files and parser** | Rewritten spec, architecture and coding skill files, and a subtask parser that accepts more than one list format. | `.claude/skills/`, `orchestrator/nodes/dev.py` |

Code review and security review always use their fixed skill files. They are left out of the list of stages the PM agent may write for, so their checks are the same for every app.

What this does not solve: file ownership is still an instruction, not something the code enforces. The agents still share one branch, so the merge agent can only repair a collision after it happens. Giving each dev agent its own branch and having the merge agent do real git merges is the next step.

## The 11 Primitives Every Software Factory Needs

We tried to figure out the smallest set of building blocks that turns a ticket into a deployed app. Every factory needs these — the specific tools are up to you:

| # | Primitive | What It Does | This Factory Uses |
|---|---|---|---|
| 1 | **Record** | Where work gets tracked | Linear (project: "software factory") |
| 2 | **Memory** | How agents share context | `memory/` — one markdown file per ticket, append-only |
| 3 | **Orchestrator** | What decides who runs next | LangGraph state machine in `orchestrator/` |
| 4 | **Execution Env** | Where agents actually run | Docker container |
| 5 | **Agent Runtime** | The brain behind each agent | Claude Code via `claude-agent-sdk` |
| 6 | **Integration Layer** | How agents talk to external tools | 5 MCPs: Linear, GitHub, Vercel, Supabase, Slack |
| 7 | **Quality Gates** | Where humans stay in the loop | LangGraph `interrupt()` + Slack notifications |
| 8 | **Delivery Target** | Where the app gets deployed | Vercel (frontend) + Supabase (database via Vercel Marketplace) |
| 9 | **Observability** | How you see what's happening | LangSmith traces + Linear sub-issue tracking |
| 10 | **Skills** | What each agent knows how to do | `.claude/skills/` — 10 markdown files, plus project-specific ones written per ticket |
| 11 | **Identity & Secrets** | How agents authenticate | `.env` file mounted into Docker |

Swap any of these out. Use Jira instead of Linear. Deploy to Railway instead of Vercel. The primitives are the pattern. The tools are interchangeable.

## How It Works

```
Ticket created in Linear
        |
Webhook fires --> orchestrator/api.py
        |
Create GitHub repo for the app
        |
Create 7 stage sub-issues in Linear (one per agent)
        |
PM Agent writes spec --> memory file
        |   🟢 Spec sub-issue checked off
        |
PM Agent (same session) writes project-specific skill files
        |
[GATE 1] 🟡 Waiting: "Move to In Arch to approve."
        |   🟢 Approved (or 🔴 Blocked)
        |
Architect Agent writes technical plan + subtasks
        |   🟢 Architecture sub-issue checked off
        |
[GATE 2] 🟡 Waiting: "Move to In Dev to approve."
        |   🟢 Approved (or 🔴 Blocked)
        |
Decompose: Architect Agent's session is resumed and splits the work
        |   (how many dev agents, which files each one owns)
        |
N × Dev Agents run in parallel (one per subtask, same branch, N ≤ 6)
        |   🟢 Progress posted per subtask
        |
Merge Agent checks collisions between dev agents and fixes the build
        |
Single PR opened with all changes
        |   🟢 Implementation sub-issue checked off
        |
Review Agent + Security Agent + Test Agent run in parallel
        |   🟢 Code Review + Security Review + Tests sub-issues checked off
        |
[GATE 3] 🟡 Waiting: "Move to In Deploy to approve."
        |   🟢 Approved (or 🔴 Blocked)
        |
Deploy Agent ships to Vercel + Supabase
        |   🟢 Deploy sub-issue checked off
        |
🟢 Done — final summary posted with repo link + deploy URL
```

Each agent is a Claude Code session running inside Docker. It reads the full memory file, follows its skill instructions, appends its output, and moves on. No agent-to-agent chatter. The memory file is the only shared state.

## Linear as a Dashboard

When a pipeline starts, the orchestrator:

1. Creates a new GitHub repo for the app
2. Creates 7 sub-issues under the parent ticket — one per agent stage
3. Posts a checklist comment on the parent ticket

As the pipeline runs, every event is posted to the Linear issue:

| Event | Comment |
|-------|---------|
| Pipeline start | ⚪ Pipeline started + stage checklist |
| Repo created | ⚪ Repository link |
| Agent starts | 🟡 "Spec — agent started" |
| Agent finishes | 🟢 "Spec — complete" + output excerpt |
| Gate waiting | 🟡 "Gate 1 — waiting for approval" |
| Gate approved | 🟢 "Gate 1 — approved" |
| Gate rejected | 🔴 "Gate 1 — rejected" |
| Subtask done | 🟢 "Subtask 2/5 done: Auth setup" |
| Error/timeout | 🔴 Error details + blocked reason |
| Pipeline done | 🟢 Final summary with repo + deploy URL |

Sub-issues are checked off as each agent completes. The parent issue becomes a complete record of the journey from idea to deployment.

## LangSmith Tracing

Every external call is traced as a nested span under the pipeline run:

- Linear GraphQL calls, sub-issue lifecycle
- Slack webhook posts
- Memory file reads and writes
- Each agent session, each parallel subtask
- Gate decisions, pipeline start/resume
- Webhook processing

## Try It

### What you need

- [Docker](https://docs.docker.com/get-docker/)
- [ngrok](https://ngrok.com/) (or any tunnel to expose port 8000)
- API keys for [Anthropic](https://console.anthropic.com/), [Linear](https://linear.app/), [GitHub](https://github.com/), [Vercel](https://vercel.com/), [Supabase](https://supabase.com/), [Slack](https://api.slack.com/)
- [LangSmith](https://smith.langchain.com/) (optional, for tracing)

### 1. Clone and add your keys

```bash
git clone https://github.com/gsverlov/App-factory.git
cd App-factory
cp .env.example .env
```

Fill in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
LINEAR_API_KEY=lin_api_...
LINEAR_WEBHOOK_SECRET=...
GITHUB_TOKEN=ghp_...
GITHUB_ORG=your-org-or-username
VERCEL_TOKEN=...
SUPABASE_TOKEN=...
SLACK_TOKEN=xoxb-...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
LANGCHAIN_API_KEY=lsv2_...          # optional
LANGCHAIN_PROJECT=your-project-name  # optional
LANGCHAIN_TRACING_V2=true            # optional
```

### 2. Set up Linear

Create these workflow states in your team settings (exact names matter):

```
Backlog --> In Spec --> In Arch --> In Dev --> In QA --> In Deploy --> Done --> Blocked
```

Create a project called **software factory** — all factory issues will live here.

Turn off all **Pull request automations** — the orchestrator handles state transitions.

### 3. Connect the webhook

```bash
ngrok http 8000
```

In Linear: **Settings > API > Webhooks > New webhook**
- URL: `https://your-ngrok-url.ngrok-free.app/webhook/linear`
- Resource types: Issues only

Copy the signing secret to `LINEAR_WEBHOOK_SECRET` in `.env`.

### 4. Set up Slack

Create an app at [api.slack.com/apps](https://api.slack.com/apps):
- Bot scopes: `chat:write`, `channels:read`
- Install to workspace, grab the bot token (`xoxb-...`) for `SLACK_TOKEN`
- Enable Incoming Webhooks, add one to your channel for `SLACK_WEBHOOK_URL`
- Invite the bot: `/invite @YourAppName`

### 5. Start the factory

```bash
docker compose build
docker compose up
```

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### 6. Create a ticket and watch it run

Write a Linear ticket describing what you want built. Move it to **In Spec**.

The factory creates a GitHub repo, then the PM Agent writes a spec and the project-specific skill files. You get a Slack message at Gate 1. Move to **In Arch**. The Architect plans the implementation. Move to **In Dev**. The Architect's session is resumed to split the work, and parallel Dev Agents build each subtask — progress is posted to the Linear issue. When all subtasks land, the Merge Agent checks the combined work and a single PR is opened. Review, security and test agents run on the combined PR. Move to **In Deploy**. The app deploys to Vercel (frontend) and Supabase (database, provisioned automatically via Vercel Marketplace). Done.

Every step is logged to the Linear issue. Open it to see the full journey.

## What's Inside

```
orchestrator/
  __init__.py                # Exports FastAPI app
  config.py                  # Env vars, paths, constants
  state.py                   # LangGraph state schema + Linear state map
  audit.py                   # Append-only audit logging
  memory.py                  # Memory file init and append
  linear.py                  # Linear GraphQL API + sub-issue lifecycle
  slack.py                   # Slack webhook posts
  agent_runner.py            # Core agent runner (claude-agent-sdk), session capture + resume
  skills.py                  # Picks the fixed or project-specific skill file
  graph.py                   # LangGraph DAG construction
  pipeline.py                # Pipeline start/resume + repo creation
  api.py                     # FastAPI endpoints
  nodes/
    __init__.py              # Re-exports all node functions
    agents.py                # PM (+ project skills), Architect, Review, Security, Test, Deploy nodes
    dev.py                   # Decompose + parallel dev execution + merge check
    gates.py                 # Human approval gates (interrupt/resume)
    terminal.py              # Done and blocked handlers
memory/
  _template.md               # Bootstrapped for each new ticket
  LIN-xxx.md                 # One file per ticket, append-only
.claude/
  CLAUDE.md                  # Master context for all agent sessions
  settings.json              # MCP server configuration
  skills/
    spec-writing/SKILL.md    # How to write a spec
    skill-writing/SKILL.md   # How the PM agent writes project-specific skill files
    architecture/SKILL.md    # How to plan implementation
    decompose/SKILL.md       # How the architect splits work between dev agents
    coding/SKILL.md          # How to write code and open a PR
    merge-check/SKILL.md     # How the merge agent checks the combined dev work
    code-review/SKILL.md     # How to review a PR (fixed for every app)
    security-review/SKILL.md # How to review security (fixed for every app)
    test-writing/SKILL.md    # How to write and run tests
    deploy-checklist/SKILL.md # How to deploy and verify
  skills-generated/
    LIN-xxx/                 # Project-specific skill files per ticket (gitignored)
audit/
  YYYY-MM-DD.log             # Every factory event, append-only
workspace/
  LIN-xxx/                   # Cloned app repo per ticket (gitignored)
Dockerfile
docker-compose.yml
```
