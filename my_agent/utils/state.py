from operator import add

from pydantic import BaseModel, Field
from typing import Annotated
from typing_extensions import NotRequired, TypedDict

class CodeAgentState(TypedDict):
    raw_specifications: str
    detailed_specifications: str
    repo_context: str
    design: str
    approach: str
    task: list[str]
    app_task: NotRequired[list[str]]
    test_task: NotRequired[list[str]]
    plan_approved: bool
    feedback_of_plan: str
    human_feedback_of_plan: str
    feedback_of_code: str
    feedback_of_test_case: str
    human_feedback_of_code: str
    implementation_summary: NotRequired[str]
    implementation_files: NotRequired[Annotated[list[str], add]]
    implementation_validation: NotRequired[str]
    implementation_typecheck_passed: NotRequired[bool]
    test_output: NotRequired[str]
    test_passed: NotRequired[bool]
    test_failure_category: NotRequired[str]
    test_failure_repeat_count: NotRequired[int]
    test_errors_skipped: NotRequired[bool]
    unresolved_test_errors: NotRequired[str]
    review_implementation_passed: NotRequired[bool]
    review_implementation_route: NotRequired[str]


class ImplementationSubgraphState(TypedDict):
    detailed_specifications: str
    repo_context: str
    design: str
    approach: str
    task: list[str]
    app_task: NotRequired[list[str]]
    test_task: NotRequired[list[str]]
    feedback_of_code: NotRequired[str]
    feedback_of_test_case: NotRequired[str]
    implementation_summary: NotRequired[str]
    implementation_files: NotRequired[Annotated[list[str], add]]
    implementation_validation: NotRequired[str]
    implementation_typecheck_passed: NotRequired[bool]
    test_output: NotRequired[str]
    test_passed: NotRequired[bool]
    test_failure_category: NotRequired[str]
    test_failure_repeat_count: NotRequired[int]
    test_errors_skipped: NotRequired[bool]
    unresolved_test_errors: NotRequired[str]
    review_implementation_passed: NotRequired[bool]
    review_implementation_route: NotRequired[str]

class PlannerResponse(BaseModel):
    repo_context: str
    design: str
    approach: str
    task: list[str]


class SplitTaskResponse(BaseModel):
    app_task: list[str] = Field(default_factory=list)
    test_task: list[str] = Field(default_factory=list)

class DetailedSpecifications(BaseModel):
    detailed_specifications: str

class ReviewPlanResponse(BaseModel):
    plan_approved: bool
    feedback_of_plan: str


class ImplementationSummaryResponse(BaseModel):
    summary: str
    files_touched: list[str] = Field(default_factory=list)


class ImplementationValidationResponse(BaseModel):
    """Interpretation of npm self-check output (filled after the coding agent run)."""

    summary: str
    typecheck_passed_final: bool = Field(
        description="True if the last `npm run typecheck` in the transcript exited with code 0."
    )


class ImplementationPostRunResponse(BaseModel):
    """Combined summary + npm validation from a single post-coding analysis call."""

    summary: str
    files_touched: list[str] = Field(default_factory=list)
    validation_summary: str
    typecheck_passed_final: bool = Field(
        description="True if the last `npm run typecheck` in the transcript exited with code 0."
    )

class TestFailureRoutingResponse(BaseModel):
    category: str = Field(
        description="One of: passed, test_only, app_logic, mixed_or_unclear"
    )


class ReviewImplementationResponse(BaseModel):
    review_implementation_passed: bool
    route: str = Field(
        description="One of: end, implement_app, implement_tests, run_test"
    )
    feedback_of_code: str = Field(
        description="Actionable feedback for app implementation fixes. Empty if none."
    )
    feedback_of_test_case: str = Field(
        description="Actionable feedback for test-case improvements. Empty if none."
    )