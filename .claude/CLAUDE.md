# Software Factory — Agent Context

You are an agent inside a software factory. The factory turns Linear tickets into deployed web apps. An orchestrator moves tickets through a pipeline of specialized agents — you are one of them. Your job is defined by the skill file loaded for this session.

## Memory

Your memory file is `memory/{ticket_id}.md`. Read it in full at the start of every session. It contains the cumulative output of every agent that has worked on this ticket before you.

When you finish your work, append your output under the correct section header (defined by your skill). Never overwrite or edit existing sections. Always prepend your output with an ISO 8601 timestamp.

## MCP Connections

You have five MCP connections available:

- **Linear** (`mcp__linear__*`) — read ticket details, update ticket state, post comments. Use this to pull the full ticket description and to move the ticket forward when your work is done.
- **GitHub** (`mcp__github__*`) — create branches, commit code, open PRs, post review comments, merge. Each app gets its own repo under the `ashtilawat` org.
- **Vercel** (`mcp__vercel__*`) — deploy frontend apps, check deploy status, manage projects. Use this for frontend deployment and post-deploy verification.
- **Supabase** (`mcp__supabase__*`) — manage databases, run migrations, check project status. Use this for database operations and schema management.
- **Slack** (`mcp__slack__*`) — post messages to channels. Use this only when your skill instructions tell you to.

## The App

Each app gets its own GitHub repo, created automatically at pipeline start. The repo is cloned to a workspace directory that is passed to you via the prompt. Stack: Next.js, TypeScript, Tailwind CSS. All code changes go in the workspace root.

## Skills

Each agent session loads one skill file from `.claude/skills/`:

| Skill | Agent | Purpose |
|-------|-------|---------|
| `spec-writing/SKILL.md` | PM Agent | Turn a raw ticket into a structured spec |
| `skill-writing/SKILL.md` | PM Agent (same session) | Write project-specific skill files for later agents |
| `architecture/SKILL.md` | Architect Agent | Produce a technical architecture decision |
| `decompose/SKILL.md` | Architect Agent (same session) | Split the work between parallel dev agents, one owner per file |
| `coding/SKILL.md` | Dev Agent | Write code for one subtask |
| `merge-check/SKILL.md` | Merge Agent | Check where dev agents collided and fix the build |
| `code-review/SKILL.md` | Review Agent | Review the PR for correctness and security |
| `security-review/SKILL.md` | Security Agent | Review the PR for security problems only |
| `test-writing/SKILL.md` | Test Agent | Write and run tests |
| `deploy-checklist/SKILL.md` | Deploy Agent | Deploy to Vercel + Supabase and verify |

For the architecture, coding, test-writing and deploy-checklist stages, the PM Agent writes a project-specific version of the skill file per ticket (`.claude/skills-generated/{ticket_id}/`), and that version is loaded in place of the fixed one. Code review and security review always use the fixed files above.
