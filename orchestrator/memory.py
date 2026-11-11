"""Memory file helpers — init and append-only writes."""

import re
from datetime import datetime, timezone
from pathlib import Path

from langsmith import traceable

from orchestrator.config import MEMORY_DIR, TEMPLATE_PATH
from orchestrator.audit import audit_log


@traceable(run_type="tool", name="init_memory")
def init_memory(ticket_id: str, title: str) -> Path:
    path = MEMORY_DIR / f"{ticket_id}.md"
    if path.exists():
        return path
    MEMORY_DIR.mkdir(exist_ok=True)
    template = TEMPLATE_PATH.read_text()
    content = template.replace("{{TICKET_ID}}", ticket_id).replace("{{TICKET_TITLE}}", title)
    path.write_text(content)
    audit_log(ticket_id, "memory_init", str(path))
    return path


@traceable(run_type="tool", name="append_memory")
def append_memory(ticket_id: str, section: str, content: str) -> None:
    path = MEMORY_DIR / f"{ticket_id}.md"
    ts = datetime.now(timezone.utc).isoformat()
    text = path.read_text()
    marker = f"## {section}"
    if marker in text:
        text = text.replace(
            f"{marker}\n_pending_",
            f"{marker}\n_{ts}_\n\n{content}",
        )
        path.write_text(text)
    else:
        with path.open("a") as f:
            f.write(f"\n{marker}\n_{ts}_\n\n{content}\n")
    audit_log(ticket_id, f"memory_append:{section}", f"{len(content)} chars")


def read_memory_section(ticket_id: str, section: str) -> str:
    """Return the text of one section of a ticket's memory file ('' if absent).

    A section runs from its `## Section` heading to the next heading that is
    in the template. Only template headings end a section, because agents
    often write `## ` headings of their own inside their output.
    """
    text = (MEMORY_DIR / f"{ticket_id}.md").read_text()
    headings = re.findall(r"^## (.+?)[ \t]*$", TEMPLATE_PATH.read_text(), re.MULTILINE)
    start = re.search(rf"^## {re.escape(section)}[ \t]*$", text, re.MULTILINE)
    if not start:
        return ""
    end = len(text)
    for other in headings:
        if other == section:
            continue
        nxt = re.search(rf"^## {re.escape(other)}[ \t]*$", text[start.end():], re.MULTILINE)
        if nxt:
            end = min(end, start.end() + nxt.start())
    return text[start.end():end].strip()
