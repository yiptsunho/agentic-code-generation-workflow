from pydantic import BaseModel
from typing_extensions import TypedDict

class CodeAgentState(TypedDict):
    raw_specifications: str
    detailed_specifications: str
    repo_context: str
    design: str
    approach: str
    task: list[str]
    plan_approved: bool
    feedback_of_plan: str
    human_comment_of_plan: str
    comment_of_code: str
    comment_of_test_case: str
    human_comment_of_code: str

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