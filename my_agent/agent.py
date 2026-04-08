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
from my_agent.utils.state import CodeAgentState, ImplementationSubgraphState

memory = MemorySaver()

#############################
# subgraph (implementation) #
#############################
implementation_subgraph = StateGraph(ImplementationSubgraphState)

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


def run_implementation_subgraph(state: CodeAgentState):
    impl_input: ImplementationSubgraphState = {
        "detailed_specifications": state["detailed_specifications"],
        "repo_context": state.get("repo_context", ""),
        "design": state.get("design", ""),
        "approach": state.get("approach", ""),
        "task": state.get("task", []),
        "feedback_of_code": state.get("feedback_of_code", ""),
        "feedback_of_test_case": state.get("feedback_of_test_case", ""),
        "implementation_summary": state.get("implementation_summary", ""),
        "implementation_files": state.get("implementation_files", []),
        "implementation_validation": state.get("implementation_validation", ""),
        "implementation_typecheck_passed": state.get("implementation_typecheck_passed", False),
        "test_output": state.get("test_output", ""),
        "test_passed": state.get("test_passed", False),
        "test_failure_category": state.get("test_failure_category", ""),
        "test_failure_signature": state.get("test_failure_signature", ""),
        "test_failure_repeat_count": state.get("test_failure_repeat_count", 0),
        "review_implementation_passed": state.get("review_implementation_passed", False),
        "review_implementation_route": state.get("review_implementation_route", ""),
    }
    impl_result = compiled_implementation_subgraph.invoke(impl_input)
    return {
        "feedback_of_code": impl_result.get("feedback_of_code", ""),
        "feedback_of_test_case": impl_result.get("feedback_of_test_case", ""),
        "implementation_summary": impl_result.get("implementation_summary", ""),
        "implementation_files": impl_result.get("implementation_files", []),
        "implementation_validation": impl_result.get("implementation_validation", ""),
        "implementation_typecheck_passed": impl_result.get("implementation_typecheck_passed", False),
        "test_output": impl_result.get("test_output", ""),
        "test_passed": impl_result.get("test_passed", False),
        "test_failure_category": impl_result.get("test_failure_category", ""),
        "test_failure_signature": impl_result.get("test_failure_signature", ""),
        "test_failure_repeat_count": impl_result.get("test_failure_repeat_count", 0),
        "review_implementation_passed": impl_result.get("review_implementation_passed", False),
        "review_implementation_route": impl_result.get("review_implementation_route", ""),
    }

##############
# main graph #
##############
main_graph = StateGraph(CodeAgentState)

# nodes
main_graph.add_node("parse_specifications", parse_specifications)
main_graph.add_node("plan", plan)
main_graph.add_node("review_plan", review_plan)
main_graph.add_node("implement", run_implementation_subgraph)

# edges
main_graph.add_edge(START, "parse_specifications")
main_graph.add_edge("parse_specifications", "plan")
main_graph.add_edge("plan", "review_plan")
main_graph.add_conditional_edges("review_plan", should_start_implement, ["implement", "plan"])
agent = main_graph.compile()
