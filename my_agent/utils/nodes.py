from pathlib import Path
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

from my_agent.utils.state import CodeAgentState, DetailedSpecifications, PlannerResponse, ReviewPlanResponse

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
- design, approach, task: concrete plan for implementing the specifications.
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

def parse_specifications(state: CodeAgentState):

    raw_specifications = state["raw_specifications"]
    structured_llm = llm.with_structured_output(DetailedSpecifications)
    response = structured_llm.invoke([
        SystemMessage(content=convert_detailed_specification_prompt.format(raw_specifications=raw_specifications))
    ])

    return {
        "detailed_specifications": response.detailed_specifications
    }

toolkit = FileManagementToolkit(
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
    tools=toolkit.get_tools(),
    system_prompt=explore_prompt,
    middleware=explorer_middleware,
)


def _format_exploration_transcript(messages: Sequence[BaseMessage]) -> str:
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
            if len(body) > 4000:
                body = body[:4000] + "\n... [truncated]"
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

def implement(state: CodeAgentState):
    return {}