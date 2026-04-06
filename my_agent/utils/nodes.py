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

from my_agent.utils.state import CodeAgentState, DetailedSpecifications, PlannerResponse

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

convert_detailed_specification_prompt = """You are an agent responsible for converting product specifications into detailed specifications.
The original specifications may be vague, so your job is to list out every detail of the specifications that developers would the specifications for implementation.

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
Given the detailed specifications and the repository exploration transcript, fill in:
- repo_context: concise notes grounded in what the transcript shows (paths read, patterns, styling).
- design, approach, task: concrete plan for implementing the specifications.
Do not invent file contents or paths that are not supported by the transcript."""


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

def plan(state: CodeAgentState):
    detailed_specifications = state["detailed_specifications"]

    explore = repo_explorer.invoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "Detailed specifications to implement:\n\n"
                        f"{detailed_specifications}"
                    )
                )
            ],
        },
        config={"recursion_limit": EXPLORER_RECURSION_LIMIT},
    )
    transcript = _format_exploration_transcript(explore["messages"])

    structured_llm = llm.with_structured_output(PlannerResponse)
    response = structured_llm.invoke(
        [
            SystemMessage(content=final_plan_prompt),
            HumanMessage(
                content=(
                    "Detailed specifications:\n\n"
                    f"{detailed_specifications}\n\n"
                    "Repository exploration transcript:\n\n"
                    f"{transcript}"
                )
            ),
        ]
    )

    return {
        "repo_context": response.repo_context,
        "design": response.design,
        "approach": response.approach,
        "task": response.task,
    }