"""LangGraph state schema and Linear state mapping."""

from typing import TypedDict, Annotated


def _last(a: str, b: str) -> str:
    """Reducer: keep the last non-empty value. Allows parallel branches to merge."""
    return b if b else a


def _last_list(a: list, b: list) -> list:
    """Reducer: keep the last non-empty list."""
    return b if b else a


def _last_dict(a: dict, b: dict) -> dict:
    """Reducer: keep the last non-empty dict."""
    return b if b else a


class FactoryState(TypedDict):
    ticket_id: Annotated[str, _last]
    title: Annotated[str, _last]
    current_state: Annotated[str, _last]
    error: Annotated[str, _last]
    parent_issue_id: Annotated[str, _last]
    subtasks: Annotated[list[dict], _last_list]
    stage_sub_issues: Annotated[dict[str, str], _last_dict]
    repo_name: Annotated[str, _last]       # e.g. "ashtilawat/my-cool-app"
    workspace_path: Annotated[str, _last]  # e.g. "/app/workspace/LIN-42"
    # Claude Code session IDs, saved so a later step can continue that session:
    # the PM agent's (to write project-specific skill files) and the architect
    # agent's (so the decompose node can continue it after Gate 2).
    pm_session_id: Annotated[str, _last]
    architect_session_id: Annotated[str, _last]


# Linear state name -> graph entry node
STATE_MAP: dict[str, str] = {
    "In Spec": "pm_agent",
    "In Arch": "architect_agent",
    "In Dev": "decompose",
    "In QA": "qa_fanout",
    "In Deploy": "deploy_agent",
}
