from __future__ import annotations

import json
import subprocess
from pathlib import Path

from langchain_core.tools import tool

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_ROOT = REPO_ROOT / "frontend"
SKILLS_ROOT = REPO_ROOT / "skills"


def build_structured_vitest_output(raw_json: str) -> str:
    """Turn Vitest JSON report into compact, deterministic routing context."""
    try:
        report = json.loads(raw_json)
    except Exception:
        return ""

    num_total = report.get("numTotalTests")
    num_passed = report.get("numPassedTests")
    num_failed = report.get("numFailedTests")
    success = report.get("success")
    suites = report.get("testResults") or []

    lines: list[str] = [
        "source: vitest-json-report",
        f"success: {success}",
        f"tests: total={num_total}, passed={num_passed}, failed={num_failed}",
    ]

    failed_items: list[dict[str, str]] = []
    unhandled_items: list[dict[str, str]] = []

    for suite in suites:
        file_path = suite.get("name") or "(unknown file)"
        assertion_results = suite.get("assertionResults") or []
        for case in assertion_results:
            if case.get("status") != "failed":
                continue
            title = " > ".join(case.get("ancestorTitles") or [])
            if title:
                title = f"{title} > {case.get('title', '(unnamed test)')}"
            else:
                title = case.get("title", "(unnamed test)")
            failure_msgs = case.get("failureMessages") or []
            first_msg = (failure_msgs[0] if failure_msgs else "").strip().splitlines()[0] if failure_msgs else ""
            failed_items.append(
                {
                    "file": str(file_path),
                    "test": title,
                    "message": first_msg or "(no failure message)",
                }
            )

        suite_errors = suite.get("errors") or []
        for err in suite_errors:
            msg = str(err).strip().splitlines()[0] if err else ""
            if msg:
                unhandled_items.append({"file": str(file_path), "message": msg})

    lines.append(f"failed_tests_count: {len(failed_items)}")
    for i, item in enumerate(failed_items[:8], start=1):
        lines.append(f"{i}. file={item['file']}")
        lines.append(f"   test={item['test']}")
        lines.append(f"   message={item['message']}")
    if len(failed_items) > 8:
        lines.append(f"... and {len(failed_items) - 8} more failed tests")

    lines.append(f"unhandled_errors_count: {len(unhandled_items)}")
    for i, item in enumerate(unhandled_items[:6], start=1):
        lines.append(f"{i}. file={item['file']}")
        lines.append(f"   message={item['message']}")
    if len(unhandled_items) > 6:
        lines.append(f"... and {len(unhandled_items) - 6} more unhandled errors")

    return "\n".join(lines)


def read_vitest_report_output() -> str:
    report_path = FRONTEND_ROOT / ".tmp" / "vitest.json"
    if not report_path.exists():
        return ""
    try:
        return build_structured_vitest_output(report_path.read_text(encoding="utf-8"))
    except Exception:
        return ""

@tool
def load_skill(skill_name: str) -> str:
    """Load a specialized skill prompt.
    Available: frontend-tech-stack
    """
    # Logic to read the SKILL.md file from a directory
    with open(f"./skills/{skill_name}/SKILL.md", "r") as f:
        return f.read()


def _format_cmd_result(
    label: str,
    exit_code: int | None,
    stdout: str,
    stderr: str,
    extra_note: str | None = None,
) -> str:
    """Always return a non-empty, LangSmith-friendly string for agent + tracing."""
    out = stdout or ""
    err = stderr or ""
    max_chars = 6000
    combined = out + err
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "\n... [truncated for length]"
    if not combined.strip():
        combined = "(no stdout/stderr captured — check exit code and note below)"
    parts = [
        f"command: {label}",
        f"exit_code: {exit_code if exit_code is not None else 'unknown'}",
    ]
    if extra_note:
        parts.append(f"note: {extra_note}")
    parts.append("--- output (stdout+stderr) ---")
    parts.append(combined)
    return "\n".join(parts)


@tool
def run_frontend_npm(command: str) -> str:
    """Run a restricted npm command in `frontend/`.

    Allowed commands:
    - npm install
    - npm run typecheck
    - npm run dev  (Vite is long-running; we stop after a short window and return startup output)

    The return value always includes exit_code and captured output so traces are never blank.
    """
    normalized = " ".join(command.strip().split())
    command_map: dict[str, list[str]] = {
        "npm install": ["npm", "install"],
        "npm run typecheck": ["npm", "run", "typecheck"],
        "npm run dev": ["npm", "run", "dev"],
        "npm run test": ["npm", "run", "test"],
    }

    if normalized not in command_map:
        allowed = ", ".join(command_map.keys())
        return (
            f"Rejected command: '{normalized}'. "
            f"Allowed commands only: {allowed}."
        )

    argv = command_map[normalized]
    # `npm run dev` runs Vite and does not exit — use a short timeout and treat timeout as OK if startup looks healthy.
    if normalized == "npm run dev":
        timeout_sec = 25
    elif normalized == "npm install":
        timeout_sec = 600
    else:
        timeout_sec = 180

    try:
        result = subprocess.run(
            argv,
            cwd=FRONTEND_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        out = result.stdout or ""
        err = result.stderr or ""
        return _format_cmd_result(normalized, result.returncode, out, err)
    except subprocess.TimeoutExpired as e:
        def _tx(val: object) -> str:
            if val is None:
                return ""
            if isinstance(val, str):
                return val
            if isinstance(val, (bytes, bytearray)):
                return bytes(val).decode(errors="replace")
            return str(val)

        out = _tx(e.stdout)
        err = _tx(e.stderr)
        note = (
            f"process timed out after {timeout_sec}s (expected for vite dev — startup output above)"
            if normalized == "npm run dev"
            else f"process timed out after {timeout_sec}s"
        )
        # Dev server: no meaningful exit code; use -1 so the model does not treat 0 vs non-0 as success.
        code: int | None = -1 if normalized == "npm run dev" else None
        return _format_cmd_result(normalized, code, out, err, extra_note=note)
    except Exception as e:
        return _format_cmd_result(normalized, None, "", "", extra_note=f"exception: {e!s}")
