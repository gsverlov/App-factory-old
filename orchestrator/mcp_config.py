"""MCP servers the agents connect to: Linear, GitHub, Vercel, Supabase, Slack.

create_app_infra writes this list into each ticket's workspace folder as
`.mcp.json`. Every time an agent is started in that folder, the code reads
the file and passes its servers to the Claude Code session.
"""

import json
import os
from pathlib import Path

MCP_FILE_NAME = ".mcp.json"

# "${NAME}" means: the environment variable NAME, which docker-compose loads
# from .env. It is filled in only when an agent starts, so the .mcp.json
# file on disk never contains a real key.
MCP_SERVERS: dict[str, dict] = {
    "linear": {
        "command": "npx",
        "args": ["-y", "linear-mcp-server"],
        "env": {"LINEAR_API_KEY": "${LINEAR_API_KEY}"},
    },
    "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"},
    },
    "vercel": {
        "command": "npx",
        "args": ["-y", "@vercel/mcp"],
        "env": {"VERCEL_API_TOKEN": "${VERCEL_TOKEN}"},
    },
    "supabase": {
        "command": "npx",
        "args": ["-y", "@supabase/mcp-server-supabase"],
        "env": {"SUPABASE_ACCESS_TOKEN": "${SUPABASE_TOKEN}"},
    },
    "slack": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-slack"],
        "env": {"SLACK_BOT_TOKEN": "${SLACK_TOKEN}"},
    },
}


def write_mcp_json(workspace: Path) -> Path:
    """Write `.mcp.json` into a ticket's workspace folder.

    The workspace is the app's git repo, so the file is also added to that
    repo's local ignore list (.git/info/exclude), so no agent commits it.
    """
    path = Path(workspace) / MCP_FILE_NAME
    path.write_text(json.dumps({"mcpServers": MCP_SERVERS}, indent=2) + "\n")

    exclude = Path(workspace) / ".git" / "info" / "exclude"
    if exclude.parent.is_dir():
        lines = exclude.read_text().splitlines() if exclude.exists() else []
        if MCP_FILE_NAME not in lines:
            with exclude.open("a") as f:
                f.write(f"\n{MCP_FILE_NAME}\n")
    return path


def load_mcp_servers(workspace: str | Path) -> dict[str, dict]:
    """Read the workspace's `.mcp.json` and fill in the keys from the environment.

    Uses MCP_SERVERS if the file doesn't exist yet (for example, during
    create_app_infra, before the file has been written).
    """
    path = Path(workspace) / MCP_FILE_NAME
    if path.exists():
        servers = json.loads(path.read_text()).get("mcpServers", {})
    else:
        servers = MCP_SERVERS
    return _fill_in_env(servers)


def _fill_in_env(value):
    """Replace every "${NAME}" in strings with the environment variable NAME."""
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _fill_in_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill_in_env(v) for v in value]
    return value
