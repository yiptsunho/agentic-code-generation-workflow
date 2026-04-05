from dataclasses import dataclass
from typing import Any, Dict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from my_agent.utils.nodes import plan, parse_specifications
from my_agent.utils.state import CodeAgentState

memory = MemorySaver()

graph = StateGraph(CodeAgentState)

# nodes
graph.add_node("parse_specifications", parse_specifications)
graph.add_node("plan", plan)

# edges
graph.add_edge(START, "parse_specifications")
graph.add_edge("parse_specifications", "plan")
graph.add_edge("plan", END)
agent = graph.compile()
