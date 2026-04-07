from pydantic import BaseModel, Field
from typing_extensions import NotRequired, TypedDict

class CodeAgentState(TypedDict):
    raw_specifications: str
    detailed_specifications: str
    repo_context: str
    design: str
    approach: str
    task: list[str]
    plan_approved: bool
    feedback_of_plan: str
    human_feedback_of_plan: str
    feedback_of_code: str
    feedback_of_test_case: str
    human_feedback_of_code: str
    implementation_summary: NotRequired[str]
    implementation_files: NotRequired[list[str]]
    implementation_validation: NotRequired[str]
    implementation_typecheck_passed: NotRequired[bool]
    test_output: NotRequired[str]
    test_passed: NotRequired[bool]
    test_failure_category: NotRequired[str]

class PlannerResponse(BaseModel):
    repo_context: str
    design: str
    approach: str
    task: list[str]

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

class TestFailureRoutingResponse(BaseModel):
    category: str = Field(
        description="One of: passed, test_only, app_logic, mixed_or_unclear"
    )