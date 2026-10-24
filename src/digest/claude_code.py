"""Run a prompt through the Claude Code CLI so usage is billed to your Claude subscription.

Requires `claude` on PATH (or CLAUDE_BIN) and a subscription login: either run
`claude` once and log in, or set CLAUDE_CODE_OAUTH_TOKEN from `claude setup-token`
(the way to do it in CI).
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

URL = re.compile(r"https?://[^\s\"'<>\\)\]]+")
TIMEOUT_SECONDS = 20 * 60


@dataclass
class Run:
    text: str
    structured: dict | None = None
    search_urls: list[str] = field(default_factory=list)
    cost_usd: float | None = None


def run(prompt: str, *, system: str, tools: list[str], model: str | None = None, schema: dict | None = None) -> Run:
    cmd = [
        _binary(), "-p",
        "--output-format", "stream-json", "--verbose",
        "--system-prompt", system,
        # Only the tools we name, no MCP servers, nothing that needs a human to approve.
        "--tools", ",".join(tools),
        "--strict-mcp-config",
        "--permission-mode", "dontAsk",
        "--no-session-persistence",
    ]
    if tools:
        cmd += ["--allowedTools", ",".join(tools)]
    if model:
        cmd += ["--model", model]
    if schema:
        cmd += ["--json-schema", json.dumps(schema)]

    # An API key in the environment would take precedence over the subscription login.
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    # Run from an empty folder so no project CLAUDE.md, hooks or settings get loaded.
    with tempfile.TemporaryDirectory() as cwd:
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, env=env, cwd=cwd, timeout=TIMEOUT_SECONDS
        )

    result, urls = None, []
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "user":
            for block in _blocks(event):
                if block.get("type") == "tool_result":
                    urls += URL.findall(_text(block.get("content")))
        elif event.get("type") == "result":
            result = event

    if result is None:
        raise RuntimeError(f"Claude Code exited with {proc.returncode} and no result: {proc.stderr.strip()[:500]}")
    if result.get("is_error"):
        raise RuntimeError(f"Claude Code failed ({result.get('subtype')}): {str(result.get('result'))[:500]}")
    return Run(
        text=result.get("result") or "",
        structured=result.get("structured_output"),
        search_urls=urls,
        cost_usd=result.get("total_cost_usd"),
    )


def _binary() -> str:
    path = os.environ.get("CLAUDE_BIN") or shutil.which("claude")
    if not path:
        raise RuntimeError(
            "Claude Code CLI not found. Install it (https://code.claude.com/docs/en/setup), "
            "log in by running `claude` once, or set CLAUDE_BIN to its path."
        )
    return path


def _blocks(event: dict) -> list[dict]:
    content = (event.get("message") or {}).get("content")
    return content if isinstance(content, list) else []


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_text(c.get("text") or c.get("content")) for c in content if isinstance(c, dict))
    return json.dumps(content) if content else ""
