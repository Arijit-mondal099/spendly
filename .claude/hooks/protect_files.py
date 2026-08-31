#!/usr/bin/env python
import sys
import json
import re

PROTECTED = ["expense_tracker", ".env", "migrations/"]
DANGEROUS_PATTERNS = [
    r"\brm\b",
    r"\bunlink\b",
    r"\btruncate\b",
    r"\brmdir\b",
    r"\bdel\b",
    r"\bRemove-Item\b",
]


def is_protected_path(text):
    if not text:
        return None
    # Normalize separators for cross-platform matching
    norm = text.replace("\\", "/")
    for p in PROTECTED:
        if p in norm:
            return p
    return None


def is_dangerous_command(cmd):
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return True
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        # No valid JSON on stdin -> let normal permission flow continue
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    hit = None
    reason = None

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        if is_dangerous_command(cmd):
            hit = is_protected_path(cmd)
            if hit:
                reason = f"Blocked: destructive command targets protected path '{hit}'."

    elif tool_name in ("Edit", "Write", "NotebookEdit"):
        # These tools use file_path; also check path/filePath variants
        file_path = (
            tool_input.get("file_path")
            or tool_input.get("filePath")
            or tool_input.get("path")
            or ""
        )
        hit = is_protected_path(file_path)
        if hit:
            reason = f"Blocked: write to protected path '{hit}' denied."

    else:
        # Fallback: if any tool carries a file_path that is protected and
        # looks like a write, block it
        file_path = tool_input.get("file_path", "")
        if file_path:
            hit = is_protected_path(file_path)
            # Only block for write-like tools; reads are safe
            if hit and tool_name in ("Edit", "Write"):
                reason = f"Blocked: write to protected path '{hit}' denied."

    if reason:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )
    # No output when clean -> normal permission flow continues unaffected

    sys.exit(0)


if __name__ == "__main__":
    main()
