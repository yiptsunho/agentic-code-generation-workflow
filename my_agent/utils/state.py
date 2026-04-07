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