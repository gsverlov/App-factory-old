"""Decomposition, parallel dev agent execution, and the merge check."""

import re
import asyncio

from langsmith import traceable

from orchestrator.config import MEMORY_DIR, MAX_DEV_AGENTS, logger
from orchestrator.state import FactoryState
from orchestrator.audit import audit_log
from orchestrator.memory import append_memory, read_memory_section
from orchestrator.slack import post_slack
from orchestrator.linear import (
    get_issue_id,
    comment_on_issue,
    update_linear_state,
    update_stage_progress,
)
from orchestrator.agent_runner import run_agent


# ---------------------------------------------------------------------------
# Subtask parser
# ---------------------------------------------------------------------------


def parse_subtasks(memory_text: str) -> list[dict]:
    """Parse subtasks from the architecture decision in memory.
    Aggressively matches any reasonable subtask format."""
    
    # Find ANY section with "subtask" in the heading (case-insensitive)
    match = re.search(r'#+\s+.*?[Ss]ubtask.*?\n(.*?)(?=\n##[^#]|\n# |\Z)', memory_text, re.DOTALL)
    if not match:
        return []
    section = match.group(1).strip()
    subtasks = []

    # Strategy 1: Numbered list with bold titles and ANY separator
    for m in re.finditer(r'\d+\.\s+\*\*(.+?)\*\*\s*[^a-zA-Z\n]*(.+?)(?=\n\d+\.|\Z)', section, re.DOTALL):
        subtasks.append({
            "title": m.group(1).strip(),
            "description": m.group(2).strip(),
        })
    
    # Strategy 2: Markdown table rows
    if not subtasks:
        for m in re.finditer(r'\|\s*\d+\s*\|\s*\*?\*?(.+?)\*?\*?\s*\|\s*(.+?)\s*\|', section):
            title = m.group(1).strip().strip('*').strip()
            description = m.group(2).strip()
            if title and title != 'Subtask' and not title.startswith('--'):
                subtasks.append({"title": title, "description": description})

    # Strategy 3: Any numbered line with recognizable content
    if not subtasks:
        for m in re.finditer(r'\d+\.\s+(.+?)(?=\n\d+\.|\Z)', section, re.DOTALL):
            line = m.group(1).strip()
            if len(line) > 10:
                parts = re.split(r'\s*[\-\—\–:]\s*', line, maxsplit=1)
                title = parts[0].strip().strip('*')
                description = parts[1].strip() if len(parts) > 1 else line
                subtasks.append({"title": title, "description": description})

    # Deduplicate by title
    seen = set()
    return [st for st in subtasks if st["title"] not in seen and not seen.add(st["title"])]

    # Format 3: ## Subtask N: Name headers
    for m in re.finditer(r'##\s+Subtask\s+\d+[:\s]+(.+?)\n(.*?)(?=\n##\s+Subtask|\n## [^S]|\Z)', section, re.DOTALL):
        subtasks.append({
            "title": m.group(1).strip(),
            "description": m.group(2).strip(),
        })
    if subtasks:
        seen = set()
        return [st for st in subtasks if st["title"] not in seen and not seen.add(st["title"])]

    # Format 4: Numbered list without bold
    for m in re.finditer(r'\d+\.\s+([^:*\n]+):\s*(.+?)(?=\n\d+\.|\Z)', section, re.DOTALL):
        subtasks.append({
            "title": m.group(1).strip(),
            "description": m.group(2).strip(),
        })
    
    seen = set()
    return [st for st in subtasks if st["title"] not in seen and not seen.add(st["title"])]


# ---------------------------------------------------------------------------
# Decompose node
# ---------------------------------------------------------------------------


def cap_subtasks(subtasks: list[dict], limit: int = MAX_DEV_AGENTS) -> list[dict]:
    """Never start more than `limit` dev agents.

    Extra subtasks are folded into the last kept one, so no work is dropped.
    """
    if len(subtasks) <= limit:
        return subtasks
    kept, extra = subtasks[:limit], subtasks[limit:]
    folded = "\n".join(f"- {st['title']}: {st['description']}" for st in extra)
    kept[-1] = {
        "title": kept[-1]["title"],
        "description": f"{kept[-1]['description']}\n\nAlso build:\n{folded}",
    }
    return kept


async def decompose_in_architect_session(state: FactoryState) -> list[dict]:
    """Ask the architect agent itself to split the work.

    Continues the architect's own Claude Code session (SDK `resume`), so the
    agent that designed the app, and still remembers the reasoning it left out
    of the written architecture, decides how many dev agents to start and
    which files each one owns. Its answer is written to the memory file under
    `## Decomposition`, where every dev agent will read it.

    Returns [] if there is no session to continue or it produced no usable
    split; the caller then falls back to the architect's written plan.
    """
    ticket_id = state["ticket_id"]
    session_id = state.get("architect_session_id", "")
    if not session_id:
        return []
    try:
        await run_agent(
            state, "decompose/SKILL.md", "Decomposition", resume_session_id=session_id
        )
    except Exception as e:
        # e.g. the session's files are gone because the container was rebuilt
        audit_log(ticket_id, "decompose_resume_failed", str(e))
        return []
    return parse_subtasks(read_memory_section(ticket_id, "Decomposition"))


@traceable(run_type="chain", name="decompose")
async def decompose(state: FactoryState) -> FactoryState:
    """Decide the subtasks for parallel dev: one dev agent per subtask."""
    ticket_id = state["ticket_id"]

    # Preferred: the architect's own session makes the split
    subtasks = await decompose_in_architect_session(state)

    # Fallback: parse the subtask list the architect wrote in its document
    if not subtasks:
        audit_log(ticket_id, "decompose_fallback", "parsing subtasks from the architecture text")
        memory_text = (MEMORY_DIR / f"{ticket_id}.md").read_text()
        subtasks = parse_subtasks(memory_text)

    subtasks = cap_subtasks(subtasks)

    if not subtasks:
        audit_log(ticket_id, "decompose_fallback", "no subtasks found, running single dev agent")
        return {**state, "subtasks": [], "parent_issue_id": ""}

    # Resolve parent issue ID
    issue_info = await get_issue_id(ticket_id)
    parent_id = issue_info["id"] if issue_info else ""

    # Post decomposition summary on parent ticket
    if parent_id:
        lines = [f"⚪ **Decomposed into {len(subtasks)} subtasks:**"]
        for i, st in enumerate(subtasks, 1):
            lines.append(f"{i}. {st['title']}")
        await comment_on_issue(parent_id, "\n".join(lines))

    # Post to the Implementation stage sub-issue
    stage_subs = state.get("stage_sub_issues", {})
    impl_sub = stage_subs.get("Implementation", "")
    if impl_sub:
        await update_stage_progress(
            ticket_id, "Implementation", impl_sub,
            f"Decomposed into {len(subtasks)} subtasks:\n"
            + "\n".join(f"- {st['title']}" for st in subtasks),
        )

    audit_log(ticket_id, "decompose_done", f"{len(subtasks)} subtasks")
    await post_slack(
        f":white_circle: `{ticket_id}` decomposed into {len(subtasks)} subtasks. "
        f"Dev agents starting in parallel."
    )
    return {**state, "subtasks": subtasks, "parent_issue_id": parent_id}


# ---------------------------------------------------------------------------
# Parallel dev node
# ---------------------------------------------------------------------------


@traceable(run_type="chain", name="dev_parallel")
async def dev_parallel(state: FactoryState) -> FactoryState:
    """Run N dev agents in parallel, one per subtask, all on the same branch."""
    ticket_id = state["ticket_id"]
    subtasks = state.get("subtasks", [])
    parent_id = state.get("parent_issue_id", "")
    stage_subs = state.get("stage_sub_issues", {})
    impl_sub = stage_subs.get("Implementation", "")

    # Fallback: no subtasks means run a single dev agent
    if not subtasks:
        return await run_agent(
            state, "coding/SKILL.md", "Implementation", next_linear_state="In QA"
        )

    # Create the branch once before spawning parallel agents
    branch_name = f"{ticket_id}/implementation"
    workspace_path = state.get("workspace_path", "/app")
    try:
        from claude_agent_sdk import query as claude_query, ClaudeAgentOptions

        options = ClaudeAgentOptions(
            cwd=workspace_path,
            permission_mode="bypassPermissions",
            allowed_tools=["Bash"],
        )
        branch_prompt = (
            f"Run these git commands to set up the branch:\n"
            f"git checkout -b {branch_name} 2>/dev/null || git checkout {branch_name}\n"
            f"Just run the commands and confirm the branch is ready."
        )
        async for _ in claude_query(prompt=branch_prompt, options=options):
            pass
    except ImportError:
        logger.warning("claude-agent-sdk not available for branch creation")

    audit_log(ticket_id, "dev_parallel_start", f"{len(subtasks)} subtasks")

    @traceable(run_type="chain", name="dev_subtask")
    async def run_subtask(index: int, subtask: dict) -> str:
        subtask_title = subtask["title"]
        subtask_desc = subtask["description"]
        extra = (
            f"## Subtask Scope\n\n"
            f"You are implementing subtask {index + 1} of {len(subtasks)}.\n\n"
            f"**Title**: {subtask_title}\n"
            f"**Scope**: {subtask_desc}\n\n"
            f"**Branch**: `{branch_name}` (already created — just check it out and pull)\n\n"
            f"Implement ONLY the files described in this subtask. "
            f"The `## Decomposition` section of the memory file lists which files every "
            f"agent owns. The other agents are writing theirs right now, in this same "
            f"folder: do not create or edit a file that belongs to another subtask.\n\n"
            f"Commit with message: `{ticket_id}: {subtask_title}`"
        )
        result = await run_agent(state, "coding/SKILL.md", "Implementation", extra_prompt=extra)

        # Post progress to parent and stage sub-issue
        if parent_id:
            await comment_on_issue(
                parent_id,
                f"🟢 Subtask {index + 1}/{len(subtasks)} done: **{subtask_title}**",
            )
        if impl_sub:
            await update_stage_progress(
                ticket_id, "Implementation", impl_sub,
                f"Subtask {index + 1}/{len(subtasks)} complete: **{subtask_title}**",
            )

        audit_log(ticket_id, f"subtask_done:{index + 1}", subtask_title)
        return subtask_title

    # Run all subtasks concurrently
    tasks = [run_subtask(i, st) for i, st in enumerate(subtasks)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Check for failures
    failures = [r for r in results if isinstance(r, Exception)]
    if failures:
        error_msg = f"{len(failures)}/{len(subtasks)} subtasks failed: {failures[0]}"
        audit_log(ticket_id, "dev_parallel_error", error_msg)
        return {**state, "current_state": "Blocked", "error": error_msg}

    audit_log(ticket_id, "dev_parallel_done", f"all {len(subtasks)} subtasks complete")

    # Merge agent: the dev agents shared one folder and one branch, so before
    # the PR is opened one more session checks where their work collided and
    # makes the combined app build.
    await run_agent(
        state,
        "merge-check/SKILL.md",
        "Merge Check",
        extra_prompt=(
            f"**Branch**: `{branch_name}`\n"
            f"**Subtasks that just ran in parallel**: "
            + "; ".join(f"{i + 1}. {st['title']}" for i, st in enumerate(subtasks))
        ),
    )

    # Open a single PR with all changes
    try:
        from claude_agent_sdk import query as claude_query, ClaudeAgentOptions

        options = ClaudeAgentOptions(
            cwd=workspace_path,
            permission_mode="bypassPermissions",
            allowed_tools=["Bash", "Read", "Glob", "mcp__github__*", "mcp__linear__*"],
        )
        pr_prompt = (
            f"You are working on ticket {ticket_id}: {state['title']}\n\n"
            f"All {len(subtasks)} subtasks have been committed to branch `{branch_name}`.\n\n"
            f"1. Push the branch to origin\n"
            f"2. Open a single PR via GitHub MCP targeting `main` with:\n"
            f"   - Title: `{ticket_id}: {state['title']}`\n"
            f"   - Body summarizing all subtasks that were implemented\n"
            f"3. Post the PR link as a comment on the Linear ticket\n\n"
            f"Return the PR URL."
        )
        pr_output = []
        async for message in claude_query(prompt=pr_prompt, options=options):
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        pr_output.append(block.text)
        pr_text = "\n".join(pr_output)
        append_memory(ticket_id, "Implementation", f"### PR\n{pr_text}")
    except ImportError:
        logger.warning("claude-agent-sdk not available for PR creation")

    await update_linear_state(ticket_id, "In QA")
    if parent_id:
        await comment_on_issue(
            parent_id,
            f"🟢 All {len(subtasks)} subtasks complete. PR opened, moving to QA.",
        )
    if impl_sub:
        await update_stage_progress(
            ticket_id, "Implementation", impl_sub,
            f"All {len(subtasks)} subtasks complete. PR opened.",
        )

    return {**state, "current_state": "Implementation"}
