from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from my_agent.utils.nodes import (
    implement_app,
    implement_tests,
    plan,
    parse_specifications,
    review_implementation,
    review_plan,
    should_route_after_review_implementation,
    should_continue_to_tests,
    should_finish_implementation,
    should_start_implement, run_test, should_route_after_test,
)
from my_agent.utils.state import CodeAgentState

memory = MemorySaver()

#############################
# subgraph (implementation) #
#############################
implementation_subgraph = StateGraph(CodeAgentState)

# nodes
implementation_subgraph.add_node("implement_app", implement_app)
implementation_subgraph.add_node("implement_tests", implement_tests)
implementation_subgraph.add_node("run_test", run_test)
implementation_subgraph.add_node("review_implementation", review_implementation)


# edges
implementation_subgraph.add_edge(START, "implement_app")
implementation_subgraph.add_conditional_edges(
    "implement_app",
    should_continue_to_tests,
    ["implement_app", "implement_tests"]
)
implementation_subgraph.add_conditional_edges(
    "implement_tests",
    should_finish_implementation,
    ["implement_tests", "run_test"]
)
implementation_subgraph.add_conditional_edges(
    "run_test",should_route_after_test,
    ["review_implementation", "implement_tests", "implement_app"]
)
implementation_subgraph.add_conditional_edges(
    "review_implementation",
    should_route_after_review_implementation,
    ["implement_app", "implement_tests", "run_test", END],
)
compiled_implementation_subgraph = implementation_subgraph.compile()

##############
# main graph #
##############
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
