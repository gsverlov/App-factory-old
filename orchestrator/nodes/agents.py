"""Thin wrappers that call run_agent with the correct skill file."""

from orchestrator.state import FactoryState
from orchestrator.audit import audit_log
from orchestrator.agent_runner import run_agent
from orchestrator.skills import project_skills_prompt, written_project_skills


async def pm_agent(state: FactoryState) -> FactoryState:
    state = await run_agent(
        state, "spec-writing/SKILL.md", "Spec", save_session_as="pm_session_id"
    )
    return await write_project_skills(state)


async def write_project_skills(state: FactoryState) -> FactoryState:
    """Have the PM agent write skill files tailored to this app.

    Continues the PM agent's own session, since it just wrote the spec and
    knows what this app needs. Later agents then load these files instead of
    the fixed ones (see orchestrator/skills.py). If this step fails, nothing
    is lost: every agent falls back to its fixed skill file.
    """
    ticket_id = state["ticket_id"]
    session_id = state.get("pm_session_id", "")
    if not session_id:
        return state
    try:
        state = await run_agent(
            state,
            "skill-writing/SKILL.md",
            "Project Skills",
            extra_prompt=project_skills_prompt(ticket_id),
            resume_session_id=session_id,
        )
    except Exception as e:
        audit_log(ticket_id, "project_skills_failed", str(e))
        return state
    written = written_project_skills(ticket_id)
    audit_log(ticket_id, "project_skills_written", ", ".join(written) or "none")
    return state


async def architect_agent(state: FactoryState) -> FactoryState:
    # Save the session ID: the decompose node continues this same session
    return await run_agent(
        state,
        "architecture/SKILL.md",
        "Architecture Decision",
        save_session_as="architect_session_id",
    )


async def review_agent(state: FactoryState) -> FactoryState:
    return await run_agent(state, "code-review/SKILL.md", "Code Review")


async def test_agent(state: FactoryState) -> FactoryState:
    return await run_agent(state, "test-writing/SKILL.md", "Test Results")


async def deploy_agent(state: FactoryState) -> FactoryState:
    return await run_agent(
        state, "deploy-checklist/SKILL.md", "Deploy Log", next_linear_state="Done"
    )
