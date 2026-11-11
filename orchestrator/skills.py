"""Skill file loading — fixed skill files plus project-specific ones written per ticket."""

from pathlib import Path

from orchestrator.config import SKILLS_DIR, GENERATED_SKILLS_DIR

# Stages the PM agent writes a project-specific skill file for.
# Code review and security review are deliberately not in this list: their
# checks must be the same for every app, so they always load the fixed file.
GENERATED_STAGES = ("architecture", "coding", "test-writing", "deploy-checklist")


def generated_skill_path(ticket_id: str, skill_file: str) -> Path:
    """Where the project-specific version of a skill file lives for one ticket."""
    return GENERATED_SKILLS_DIR / ticket_id / skill_file


def load_skill(ticket_id: str, skill_file: str) -> str:
    """Return the skill instructions an agent should get for this ticket.

    Uses the project-specific file the PM agent wrote for this ticket if the
    stage allows one and the file exists; otherwise the fixed file.
    """
    stage = skill_file.split("/")[0]
    if stage in GENERATED_STAGES:
        generated = generated_skill_path(ticket_id, skill_file)
        if generated.exists() and generated.read_text().strip():
            return generated.read_text()
    return (SKILLS_DIR / skill_file).read_text()


def project_skills_prompt(ticket_id: str) -> str:
    """List, for the PM agent, each base skill file and where to write its project version."""
    lines = ["## Files to write\n"]
    for stage in GENERATED_STAGES:
        skill_file = f"{stage}/SKILL.md"
        base = (SKILLS_DIR / skill_file).resolve()
        target = generated_skill_path(ticket_id, skill_file).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        lines.append(f"- **{stage}**: read `{base}`, write `{target}`")
    return "\n".join(lines)


def written_project_skills(ticket_id: str) -> list[str]:
    """Stages that now have a non-empty project-specific skill file."""
    return [
        stage
        for stage in GENERATED_STAGES
        if (path := generated_skill_path(ticket_id, f"{stage}/SKILL.md")).exists()
        and path.read_text().strip()
    ]
