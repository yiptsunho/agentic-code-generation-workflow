from dataclasses import dataclass
from typing import Any, Dict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from my_agent.utils.nodes import plan, parse_specifications, review_plan, should_start_implement, implement
from my_agent.utils.state import CodeAgentState

memory = MemorySaver()

implementation_subgraph = StateGraph(CodeAgentState)
implementation_subgraph.add_node("implement", implement)
implementation_subgraph.add_edge(START, "implement")
implementation_subgraph.add_edge("implement", END)
compiled_implementation_subgraph = implementation_subgraph.compile()

main_graph = StateGraph(CodeAgentState)

# nodes
main_graph.add_node("parse_specifications", parse_specifications)
main_graph.add_node("plan", plan)
main_graph.add_node("review_plan", review_plan)
main_graph.add_node("implement", compiled_implementation_subgraph)

# edges
main_graph.add_edge(START, "parse_specifications")
main_graph.add_edge("parse_specifications", "plan")
main_graph.add_edge("plan", "review_plan")
main_graph.add_conditional_edges("review_plan", should_start_implement, ["implement", "plan"])
agent = main_graph.compile()
