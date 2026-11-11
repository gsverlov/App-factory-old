---
name: decompose
description: Split the architecture you just wrote into subtasks for parallel dev agents, so that no file is owned by two agents
---

# Decompose Skill

You are still the Architect Agent. This is the same session in which you wrote the architecture, so you remember the reasoning behind it, including the details you left out of the written document. Use that now.

Dev agents will build this app in parallel. They all work in the same folder, on the same git branch, at the same time, and they cannot talk to each other. If two of them edit the same file, one silently overwrites the other. Your split is what prevents that.

## What to decide

1. How many dev agents to start: between 1 and 6. Use fewer for a small app. Do not split work just to reach a number.
2. Exactly what each agent builds.
3. Exactly which files each agent owns.

## Rules for the split

- Every file in the project structure is owned by exactly one subtask. No file path may appear in two subtasks.
- Shared files belong to subtask 1, Project Setup: `package.json`, the Vite/Tailwind/TypeScript config, `src/main.tsx`, `src/App.tsx` with the router, the central types file, the Supabase client, global stores, and reusable UI primitives.
- Subtask 1 must write those shared files complete, including every route, type, and dependency the other subtasks will need, because no other agent is allowed to edit them. If a later subtask needs something in a shared file, put it in subtask 1's description.
- Each subtask description says what it may import from another subtask but must not create (for example: "imports `Button` from `src/components/ui/Button.tsx`, owned by subtask 1").
- Split by feature, so each agent's files sit in their own folders wherever possible.
- Every file from the architecture's project structure must be assigned to someone. Unassigned files do not get built.

## Output format

The orchestrator parses your reply, so the format matters. Reply with ONLY the two sections below. Use `###` headings exactly as shown and no other headings.

### Agents

One line: how many dev agents, and one sentence on why that number.

### Subtasks

1. **Project Setup**: What to build, in 2-5 sentences. What the other subtasks will import from it. Files: `path/one.ts`, `path/two.tsx`, ...
2. **Next Subtask Title**: What to build, in 2-5 sentences. What it imports from other subtasks. Files: `path/three.tsx`, ...

A numbered list, each item with a bold title, a colon, a description, and a `Files:` list. No tables, no bullet points, no checkboxes.

## Before you reply, check

- Does any file path appear under two subtasks? Move it to one.
- Does any subtask need to edit a file it does not own? Move that work to the owner.
- Is every file in the project structure assigned?
