"""Run the compiled LangGraph locally with async stream (no LangGraph dev server)."""
# ruff: noqa: T201, D103, E402

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

DEFAULT_RAW_SPEC = """
1. Display a list of cars fetched via Apollo Client from a mock GraphQL API (GetCars query) served by MSW
2. Show responsive car images — render the appropriate image based on viewport width:
◦ ≤ 640px → mobile
◦ 641px – 1023px → tablet
◦ ≥ 1024px → desktop
3. Use Material UI cards to present each car (make, model, year, color, image)
4. Include an "Add Car" form that submits via a GraphQL mutation (AddCar)
5. Implement sorting and search — a search bar to filter by model, plus sorting by year or make
6. Extract GraphQL logic into a useCars() custom hook
7. Include unit tests for key components
8. A GetCar query to fetch individual cars
9. A year filter (multi-filter support alongside model search)
10. A reusable useCarFilters() hook combining all filter logic
"""


def _initial_state(raw_specifications: str) -> dict[str, Any]:
    return {
        "raw_specifications": raw_specifications.strip(),
        "detailed_specifications": "",
        "repo_context": "",
        "design": "",
        "approach": "",
        "task": [],
        "plan_approved": False,
        "feedback_of_plan": "",
        "human_feedback_of_plan": "",
        "feedback_of_code": "",
        "feedback_of_test_case": "",
        "human_feedback_of_code": "",
    }


def _updates_dict(event: Any) -> dict[str, Any]:
    """With subgraphs=True, events are (namespace, updates); otherwise plain updates dict."""
    if isinstance(event, tuple) and len(event) == 2 and isinstance(event[0], tuple):
        _, data = event
        return data if isinstance(data, dict) else {}
    return event if isinstance(event, dict) else {}


def _is_real_stage(node_name: str) -> bool:
    """Filter out middleware/model/tooling updates; keep graph node stages only."""
    if not node_name:
        return False
    if node_name in {"model", "tools"}:
        return False
    if "Middleware" in node_name:
        return False
    if node_name.endswith(".before_model") or node_name.endswith(".after_model"):
        return False
    return True


class _DotsSpinner:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._label = "Running"

    def start(self, label: str = "Running") -> None:
        self.stop()
        self._stop.clear()
        self._label = label

        def run() -> None:
            i = 0
            dots = (".", "..", "...")
            while not self._stop.is_set():
                sys.stdout.write(f"\r{self._label}{dots[i % 3]}")
                sys.stdout.flush()
                i += 1
                time.sleep(0.2)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


async def amain(agent: Any) -> None:
    parser = argparse.ArgumentParser(description="Stream the code agent graph locally.")
    parser.add_argument(
        "--spec-file",
        type=Path,
        help="Path to a text file containing raw specifications (overrides default).",
    )
    args = parser.parse_args()

    raw = (
        args.spec_file.read_text(encoding="utf-8")
        if args.spec_file is not None
        else DEFAULT_RAW_SPEC
    )
    state = _initial_state(raw)
    thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
    spinner = _DotsSpinner()
    spinner.start()

    try:
        async for event in agent.astream(
            state,
            thread,
            stream_mode="updates",
            subgraphs=True,
        ):
            data = _updates_dict(event)
            if not data:
                continue

            node_name = next(iter(data.keys()))
            if not _is_real_stage(node_name):
                continue

            spinner.stop()
            print(f"Stage: {node_name}")
            print("Updates:")
            print(json.dumps(data[node_name], indent=2, ensure_ascii=False, default=str))
            print()
            spinner.start()
    except KeyboardInterrupt:
        spinner.stop()
        print("\nInterrupted.")
    finally:
        spinner.stop()


def main() -> None:
    """Load `.env` from the repo root, then import the graph (LLM reads the API key at import time)."""
    import os

    repo_root = Path(__file__).resolve().parent
    load_dotenv(repo_root / ".env")
    if not (os.getenv("OPENAI_API_KEY") or "").strip() and (os.getenv("OPEN_API_KEY") or "").strip():
        os.environ["OPENAI_API_KEY"] = (os.getenv("OPEN_API_KEY") or "").strip()

    from my_agent.agent import agent as compiled_agent

    asyncio.run(amain(compiled_agent))


if __name__ == "__main__":
    main()
