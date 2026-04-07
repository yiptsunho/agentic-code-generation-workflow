from pathlib import Path
import re
from typing import Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.constants import END

from my_agent.utils.state import (
    CodeAgentState,
    DetailedSpecifications,
    ImplementationSummaryResponse,
    ImplementationValidationResponse,
    PlannerResponse,
    ReviewImplementationResponse,
    ReviewPlanResponse,
    TestFailureRoutingResponse,
)
from langchain_skills import SkillTool
from my_agent.utils.tools import FRONTEND_ROOT, load_skill, read_vitest_report_output, run_frontend_npm

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

convert_detailed_specification_prompt = """You are an agent responsible for converting product specifications into detailed specifications.
The original specifications may be vague, so your job is to list out every detail of the specifications that developers would use for implementation.

Original specifications: {raw_specifications}
"""

explore_prompt = """You are a senior frontend architect exploring a codebase.
Use `list_directory` and `read_file` only as needed to understand layout and the files relevant to the specifications.
Rules:
- Prefer listing one directory, then reading a few key files — do not crawl the whole tree.
- Do not write, copy, move, or delete files.
- When you have enough context, **stop calling tools** and send one final assistant message summarizing what you learned (paths, patterns, styling) so a developer could implement the spec. Your final message must not include tool calls.
"""

final_plan_prompt = """You are a senior frontend architect.
Given the detailed specifications and the repository exploration transcript, produce repo_context, design, approach, and task.

If a previous plan and reviewer feedback are included in the user message:
- Treat that plan as the draft to revise (preserve what already satisfies the spec and transcript).
- Address every reviewer point explicitly in the updated design, approach, and/or task list.
- Do not return an unchanged plan when feedback asks for changes.

If there is no previous plan section (first draft), produce a complete plan from the spec and transcript alone.

Rules:
- repo_context: concise notes grounded in what the transcript shows (paths read, patterns, styling).
- design, approach, task: concrete plan for implementing the specifications. Only need to write tests for components.
- Do not invent file contents or paths that are not supported by the transcript.
"""

review_plan_system_prompt = """You are a pragmatic implementation-plan reviewer for a frontend codebase. Prefer approving plans that a competent developer could reasonably follow; do not demand perfection.

You will receive:
- Detailed specifications: what must be implemented.
- Proposed plan fields:
  - design: UI/UX and structural decisions.
  - approach: how the work fits the existing codebase (patterns, layers, libraries).
  - task: an ordered checklist of concrete implementation steps.

Your job:
1) Coverage (light touch): the plan should address the main goals and constraints from the detailed specifications. Minor gaps, implied details, or reasonable implementation leeway are OK.
2) Consistency: design, approach, and task should not clearly contradict each other. Small ambiguities a developer could resolve are fine.
3) Feasibility: tasks should be concrete enough to start work (sensible order, not only vague phrases). Exact file paths are optional unless the spec or repo_context makes a location critical.
4) Grounding: only push back on specific files, paths, or code claims that are clearly wrong or invented when repo_context contradicts them. If repo_context is thin, allow reasonable assumptions.

Approval bar:
- Set plan_approved to true if the plan is directionally correct, covers the spec well enough to implement, and has no blocking contradictions or obvious bad claims.
- Set plan_approved to false only for serious problems: large missing areas vs the spec, hard contradictions, or specific assertions that are very likely false given the context.

Output (structured):
- plan_approved: boolean as above.
- feedback_of_plan:
  - If plan_approved is false: short numbered bullets on blocking fixes only.
  - If plan_approved is true: a brief confirmation (2–4 sentences). Optional minor suggestions are fine; keep approval true unless something is truly blocking.
"""

EXPLORE_RUN_TOOL_LIMIT = 12
EXPLORE_MODEL_CALL_LIMIT = 22
EXPLORER_RECURSION_LIMIT = 120

IMPLEMENT_RUN_TOOL_LIMIT = 100
IMPLEMENT_MODEL_CALL_LIMIT = 100
IMPLEMENT_RECURSION_LIMIT = 220

implement_system_prompt = """Implement frontend tasks with high signal and minimal turns.

Core constraints:
- Follow detailed specs + design + approach + ordered task checklist + project skills.
- Keep edits focused; avoid unrelated refactors.
- Use `src/main.tsx` and `src/App.tsx` as entry points unless asked otherwise.
- Only use dependencies already in `package.json` unless explicitly asked to add new ones.
- Do not edit files in `src/mocks`.
- When writing tests files, explicitly import { describe, it, expect } from "vitest"

Tool usage:
- Batch same-kind tool calls in one turn whenever possible (group `list_directory`, then grouped reads, then grouped writes).
- Prefer `file_search` and targeted reads over repeatedly listing directories.
- If multiple files need edits, complete them in one pass before validation.
- Do not call `list_directory` (or other file-browsing tools) on `node_modules` or any path under it.

Validation and fix loop (mandatory):
1) Run `run_frontend_npm("npm install")`, then `run_frontend_npm("npm run typecheck")`.
2) After each result, briefly interpret `exit_code` and key log lines.
3) If typecheck fails, treat diagnostics as source of truth and fix them before anything else:
   - Extract failing file/code/message.
   - Edit only implicated files (+ directly related config/setup) first.
   - Re-run `npm run typecheck`, compare with previous errors, and continue until clean.
   - Switch strategy if errors are unchanged after 2 iterations.
4) Heuristics:
   - TS6133 unused React in TSX: remove unused default `React` import when not referenced.
   - Missing `describe`/`it`/`expect` in `*.test.tsx`: first add explicit imports at the top of each failing test file:
     `import { describe, it, expect } from "vitest"`.
     If errors persist across many test files, then fix test typing globally via Vitest types config. Do not add Jest types or `@jest/globals` in this repo.
5) `npm run dev` may timeout (Vite is long-running); use startup logs to judge success.

Do not stop with a failure report only. Finish with one assistant message (no tool calls) including:
- checklist status
- files changed
- final typecheck result (must be clean unless truly blocked)
- dev sanity check
- remaining risks/blockers (if any).
"""

def parse_specifications(state: CodeAgentState):

    raw_specifications = state["raw_specifications"]
    structured_llm = llm.with_structured_output(DetailedSpecifications)
    response = structured_llm.invoke([
        SystemMessage(content=convert_detailed_specification_prompt.format(raw_specifications=raw_specifications))
    ])

    return {
        "detailed_specifications": response.detailed_specifications
    }

explore_tool_kit = FileManagementToolkit(
    root_dir=str(Path("./frontend").resolve()),
    selected_tools=["read_file", "list_directory"],
)

explorer_middleware = [
    ToolCallLimitMiddleware(
        run_limit=EXPLORE_RUN_TOOL_LIMIT,
        exit_behavior="continue",
    ),
    ModelCallLimitMiddleware(
        run_limit=EXPLORE_MODEL_CALL_LIMIT,
        exit_behavior="end",
    ),
]

repo_explorer = create_agent(
    model="gpt-4o-mini",
    tools=explore_tool_kit.get_tools(),
    system_prompt=explore_prompt,
    middleware=explorer_middleware,
)


def _format_exploration_transcript(
    messages: Sequence[BaseMessage],
    *,
    tool_body_limit: int = 4000,
) -> str:
    """Compress agent message list into text for the final structured planner."""
    parts: list[str] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            parts.append(f"User:\n{m.content}")
        elif isinstance(m, AIMessage):
            if m.tool_calls:
                names = ", ".join(tc["name"] for tc in m.tool_calls)
                parts.append(f"Assistant (requested tools): {names}")
            if m.content:
                parts.append(f"Assistant:\n{m.content}")
        elif isinstance(m, ToolMessage):
            body = m.content
            if len(body) > tool_body_limit:
                body = body[:tool_body_limit] + "\n... [truncated]"
            parts.append(f"Tool {m.name}:\n{body}")
    return "\n\n---\n\n".join(parts)


def _format_task_list(task: list[str]) -> str:
    if not task:
        return "(none)"
    return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(task))


def plan(state: CodeAgentState):
    detailed_specifications = state["detailed_specifications"]
    feedback_of_plan = (state.get("feedback_of_plan") or "").strip()
    revising = bool(feedback_of_plan)

    explore_parts = [
        "Detailed specifications to implement:\n\n",
        detailed_specifications,
    ]
    if revising:
        explore_parts.append(
            "\n\nFocus hints from the last plan review (optional; use only if they suggest files or areas to inspect):\n\n"
        )
        explore_parts.append(feedback_of_plan)

    explore = repo_explorer.invoke(
        {
            "messages": [
                HumanMessage(content="".join(explore_parts)),
            ],
        },
        config={"recursion_limit": EXPLORER_RECURSION_LIMIT},
    )
    transcript = _format_exploration_transcript(explore["messages"])

    planner_user_parts = [
        "Detailed specifications:\n\n",
        detailed_specifications,
        "\n\nRepository exploration transcript:\n\n",
        transcript,
    ]
    if revising:
        prev_design = (state.get("design") or "").strip() or "(none)"
        prev_approach = (state.get("approach") or "").strip() or "(none)"
        prev_task = state.get("task") or []
        planner_user_parts.append(
            "\n\n---\n\nPrevious plan (revise this draft; keep what is already valid):\n\n"
            f"design:\n{prev_design}\n\n"
            f"approach:\n{prev_approach}\n\n"
            f"task:\n{_format_task_list(prev_task)}\n\n"
            "---\n\nReviewer feedback (address every point):\n\n"
            f"{feedback_of_plan}"
        )

    structured_llm = llm.with_structured_output(PlannerResponse)
    response = structured_llm.invoke(
        [
            SystemMessage(content=final_plan_prompt),
            HumanMessage(content="".join(planner_user_parts)),
        ]
    )

    return {
        "repo_context": response.repo_context,
        "design": response.design,
        "approach": response.approach,
        "task": response.task,
    }

def review_plan(state: CodeAgentState):
    detailed_specifications = state["detailed_specifications"]
    repo_context = state.get("repo_context") or ""
    design = state.get("design") or ""
    approach = state.get("approach") or ""
    task = state.get("task") or []

    human_message = HumanMessage(
        content="""
        Detailed specifications:
        {detailed_specifications}
        
        Repo context (from exploration; may be empty):
        {repo_context}
        
        Proposed plan:
        
        design:
        {design}
        
        approach:
        {approach}
        
        task:
        {task}
        """.format(
                detailed_specifications=detailed_specifications,
                repo_context=repo_context,
                design=design,
                approach=approach,
                task=_format_task_list(task),
            )
        )

    structured_llm = llm.with_structured_output(ReviewPlanResponse)
    response = structured_llm.invoke([SystemMessage(content=review_plan_system_prompt), human_message])

    return {
        "plan_approved": response.plan_approved,
        "feedback_of_plan": response.feedback_of_plan,
    }



def should_start_implement(state: CodeAgentState):
    plan_approved = state["plan_approved"]

    if plan_approved:
        return "implement"

    return "plan"


def should_continue_to_tests(state: CodeAgentState):
    if state.get("implementation_typecheck_passed", False):
        return "implement_tests"
    return "implement_app"


def should_finish_implementation(state: CodeAgentState):
    if state.get("implementation_typecheck_passed", False):
        return "run_test"
    return "implement_tests"

implement_tool_kit = FileManagementToolkit(
    root_dir=str(Path("./frontend").resolve()),
    selected_tools=["copy_file", "file_search", "move_file", "write_file", "read_file", "list_directory"],
).get_tools()

implement_middleware = [
    ToolCallLimitMiddleware(
        run_limit=IMPLEMENT_RUN_TOOL_LIMIT,
        exit_behavior="continue",
    ),
    ModelCallLimitMiddleware(
        run_limit=IMPLEMENT_MODEL_CALL_LIMIT,
        exit_behavior="end",
    ),
]

skill_tool = SkillTool(directories="./skills")

implement_tools = implement_tool_kit + [load_skill, run_frontend_npm]

repo_coder = create_agent(
    model="gpt-5.4-mini",
    tools=implement_tools,
    system_prompt=implement_system_prompt,
    middleware=implement_middleware,
)


def _split_tasks(task: list[str]) -> tuple[list[str], list[str]]:
    """Split plan tasks into app tasks and test tasks."""
    test_keywords = re.compile(r"\b(test|tests|testing|vitest|unit test|integration test)\b", re.IGNORECASE)
    app_tasks: list[str] = []
    test_tasks: list[str] = []
    for item in task:
        if test_keywords.search(item):
            test_tasks.append(item)
        else:
            app_tasks.append(item)
    return app_tasks, test_tasks


def _run_implementation_phase(state: CodeAgentState, *, phase: str) -> dict:
    detailed_specifications = state["detailed_specifications"]
    repo_context = (state.get("repo_context") or "").strip()
    design = (state.get("design") or "").strip()
    approach = (state.get("approach") or "").strip()
    full_task = state.get("task") or []
    feedback_of_code = (state.get("feedback_of_code") or "").strip()
    feedback_of_test_case = (state.get("feedback_of_test_case") or "").strip()
    test_output = (state.get("test_output") or "").strip()
    test_passed = state.get("test_passed")
    test_failure_category = (state.get("test_failure_category") or "").strip()
    app_tasks, test_tasks = _split_tasks(full_task)
    phase_task = app_tasks if phase == "app" else test_tasks

    if phase == "app":
        phase_header = (
            "Phase: application implementation only (exclude writing/updating tests). "
            "Do not create or edit test files in this phase.\n\n"
        )
        task_instructions = (
            "Use only non-test tasks from the checklist below. "
            "If a task mixes app+test work, do only the app portion now.\n\n"
        )
    else:
        phase_header = (
            "Phase: test implementation only. "
            "Write/update tests for the already implemented features.\n\n"
        )
        task_instructions = (
            "Use only test-related tasks from the checklist below. "
            "Do not make unrelated feature changes in this phase.\n\n"
        )

    shown_tasks = phase_task if phase_task else full_task

    user_parts: list[str] = [
        "Implement the following in the repository.\n\n",
        phase_header,
        "**Quality gate:** After coding, run `npm install` then `npm run typecheck` via `run_frontend_npm`. "
        "If typecheck fails, fix the errors and re-run `npm run typecheck` until `exit_code` is 0. "
        "Do not stop with only a description of failures — apply code changes until typecheck passes or you document a specific blocker after multiple fix attempts. "
        "Work efficiently: batch file discovery/reads/writes so each iteration accomplishes substantial progress.\n\n",
        task_instructions,
        "Detailed specifications:\n\n",
        detailed_specifications,
        "\n\nRepo context (from exploration):\n\n",
        repo_context or "(none)",
        "\n\nDesign:\n\n",
        design or "(none)",
        "\n\nApproach:\n\n",
        approach or "(none)",
        "\n\nTask checklist for this phase:\n\n",
        _format_task_list(shown_tasks),
    ]
    if feedback_of_code:
        user_parts.append(
            "\n\nPrior code review feedback to address in this pass:\n\n"
            f"{feedback_of_code}"
        )
    if phase == "tests" and feedback_of_test_case:
        user_parts.append(
            "\n\nPrior test-case review feedback to address in this pass:\n\n"
            f"{feedback_of_test_case}"
        )
    if test_output:
        user_parts.append(
            "\n\nLatest test run context from previous iteration:\n\n"
            f"- test_passed: {test_passed}\n"
            f"- test_failure_category: {test_failure_category or 'mixed_or_unclear'}\n\n"
            "Use this to target fixes before re-running checks.\n\n"
            "Raw test output:\n\n"
            f"{test_output}"
        )

    coding = repo_coder.invoke(
        {"messages": [HumanMessage(content="".join(user_parts))]},
        config={"recursion_limit": IMPLEMENT_RECURSION_LIMIT},
    )
    transcript = _format_exploration_transcript(
        coding["messages"],
        tool_body_limit=20000,
    )

    structured_llm = llm.with_structured_output(ImplementationSummaryResponse)
    summary_response = structured_llm.invoke(
        [
            SystemMessage(
                content=(
                    "Summarize the implementation run. From the checklist and transcript, "
                    "describe what was implemented and list relative file paths that were "
                    "created or modified. If paths are unclear, infer them from tool messages; "
                    "use an empty list only if no file changes occurred."
                )
            ),
            HumanMessage(
                content=(
                    "Task checklist:\n\n"
                    f"{_format_task_list(shown_tasks)}\n\n"
                    "---\n\n"
                    "Agent transcript:\n\n"
                    f"{transcript}"
                )
            ),
        ]
    )

    validation_llm = llm.with_structured_output(ImplementationValidationResponse)
    validation_response = validation_llm.invoke(
        [
            SystemMessage(
                content=(
                    "You interpret npm self-check results from an agent transcript. "
                    "Focus on ToolMessage content from `run_frontend_npm`. "
                    "Determine **typecheck_passed_final** from the **last** "
                    "`npm run typecheck` result in the transcript: true only if its "
                    "exit_code is 0 (or output clearly shows success with no TS errors). "
                    "For each of `npm install`, `npm run typecheck` (final state), and "
                    "`npm run dev`, briefly state pass/fail and cite key log lines. "
                    "If the agent described errors but the last typecheck still failed, "
                    "say clearly that the run did **not** finish with a clean typecheck "
                    "and list remaining diagnostics. "
                    "Explain dev `exit_code -1`/timeout notes — expected for Vite. "
                    "If no npm tools appear in the transcript, say so. "
                    "Write a concise summary a human can trust without re-reading raw logs."
                )
            ),
            HumanMessage(content=f"Transcript:\n\n{transcript}"),
        ]
    )

    return {
        "implementation_summary": summary_response.summary,
        "implementation_files": summary_response.files_touched,
        "implementation_validation": validation_response.summary,
        "implementation_typecheck_passed": validation_response.typecheck_passed_final,
    }


def implement_app(state: CodeAgentState):
    return _run_implementation_phase(state, phase="app")


def implement_tests(state: CodeAgentState):
    return _run_implementation_phase(state, phase="tests")

def run_test(state: CodeAgentState):
    report_path = FRONTEND_ROOT / ".tmp" / "vitest.json"
    try:
        if report_path.exists():
            report_path.unlink()
    except Exception:
        # Non-fatal: fallback paths below still handle missing/freshness uncertainty.
        pass

    output = run_frontend_npm.invoke({"command": "npm run test"})
    report_output = read_vitest_report_output()
    compact_output = report_output or output
    if not report_output:
        compact_output += (
            "\n\nnote: vitest JSON report was missing after this run; "
            "used stdout fallback."
        )

    passed = "exit_code: 0" in output or "Success" in output
    if report_output:
        passed = "success: True" in report_output or "failed=0" in report_output
    category = "passed"

    if not passed:
        routing_llm = llm.with_structured_output(TestFailureRoutingResponse)
        routing = routing_llm.invoke(
            [
                SystemMessage(
                    content=(
                        "Classify test failures for routing. "
                        "Return category as one of: passed, test_only, app_logic, mixed_or_unclear.\n\n"
                        "Guidelines:\n"
                        "- test_only: assertion mismatch, test setup/import/wrapper/mocks errors mainly in test files.\n"
                        "- app_logic: runtime or logic errors rooted in app/components/hooks/services code.\n"
                        "- mixed_or_unclear: both appear or unclear.\n"
                        "Prefer test_only when failures are confined to test expectations/selectors/mocks."
                    )
                ),
                HumanMessage(content=f"Test output:\n\n{compact_output}"),
            ]
        )
        category = routing.category

    return {
        "test_output": compact_output,
        "test_passed": passed,
        "test_failure_category": category,
    }

def should_route_after_test(state: CodeAgentState):
    if state.get("test_passed", False):
        return "review_implementation"

    category = state.get("test_failure_category", "mixed_or_unclear")
    if category == "test_only":
        return "implement_tests"

    # app_logic or mixed_or_unclear => safer to fix app first
    return "implement_app"

def review_implementation(state: CodeAgentState):
    detailed_specifications = state.get("detailed_specifications", "")
    design = state.get("design", "")
    approach = state.get("approach", "")
    task = state.get("task") or []
    implementation_summary = state.get("implementation_summary", "")
    implementation_validation = state.get("implementation_validation", "")
    test_output = state.get("test_output", "")
    test_passed = state.get("test_passed", False)
    test_failure_category = state.get("test_failure_category", "mixed_or_unclear")

    review_llm = llm.with_structured_output(ReviewImplementationResponse)
    response = review_llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are reviewing implementation quality after coding + tests. "
                    "Decide whether to finish or route to one next node.\n\n"
                    "Return:\n"
                    "- review_implementation_passed: true only if tasks appear complete, "
                    "test coverage/edge-cases are acceptable for the scope, and latest tests are clean.\n"
                    "- route: one of end, implement_app, implement_tests, run_test.\n"
                    "- feedback_of_code: concrete app-code fixes (empty if none).\n"
                    "- feedback_of_test_case: concrete testing gaps/fixes (empty if none).\n\n"
                    "Routing guidance:\n"
                    "- end: everything looks done and tests pass.\n"
                    "- implement_app: app logic/features missing/incorrect.\n"
                    "- implement_tests: tests/coverage/edge-cases insufficient.\n"
                    "- run_test: implementation is done but tests need a rerun to verify.\n"
                    "Prefer a single most useful next step."
                )
            ),
            HumanMessage(
                content=(
                    "Detailed specifications:\n"
                    f"{detailed_specifications}\n\n"
                    "Design:\n"
                    f"{design}\n\n"
                    "Approach:\n"
                    f"{approach}\n\n"
                    "Task checklist:\n"
                    f"{_format_task_list(task)}\n\n"
                    "Implementation summary:\n"
                    f"{implementation_summary}\n\n"
                    "Implementation validation:\n"
                    f"{implementation_validation}\n\n"
                    f"Latest test_passed: {test_passed}\n"
                    f"Latest test_failure_category: {test_failure_category}\n\n"
                    "Latest test output:\n"
                    f"{test_output}"
                )
            ),
        ]
    )

    route = response.route if response.route in {"end", "implement_app", "implement_tests", "run_test"} else "implement_app"
    return {
        "review_implementation_passed": response.review_implementation_passed,
        "review_implementation_route": route,
        "feedback_of_code": response.feedback_of_code,
        "feedback_of_test_case": response.feedback_of_test_case,
    }

def should_route_after_review_implementation(state: CodeAgentState):
    review_passed = state.get("review_implementation_passed", False)
    route = state.get("review_implementation_route", "implement_app")
    feedback_of_code = (state.get("feedback_of_code") or "").strip()
    feedback_of_test_case = (state.get("feedback_of_test_case") or "").strip()

    # Deterministic guard rails: if review did not pass and feedback exists,
    # force implementation loops instead of re-running tests immediately.
    if not review_passed:
        if feedback_of_test_case:
            return "implement_tests"
        if feedback_of_code:
            return "implement_app"

    if route == "end":
        return END

    if route == "run_test" and not review_passed:
        # Do not allow run_test when reviewer explicitly marked failure.
        return "implement_app"

    if route in {"implement_app", "implement_tests", "run_test"}:
        return route

    return "implement_app"