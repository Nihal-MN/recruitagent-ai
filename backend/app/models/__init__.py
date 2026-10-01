"""All models, imported so Alembic and the app see a complete metadata object."""

from app.models.activity import ActivityEvent
from app.models.agent import (
    AgentConversation,
    AgentMessage,
    ApprovalRequest,
    ApprovalStatus,
    ToolExecution,
    ToolExecutionStatus,
)
from app.models.application import ALL_STAGES, OFF_RAMPS, STAGES, Application
from app.models.candidate import Candidate, CandidateExperience, CandidateSkill
from app.models.job import JOB_STATUSES, Job, JobRequirement
from app.models.note import CandidateNote

__all__ = [
    "ActivityEvent",
    "AgentConversation",
    "AgentMessage",
    "ApprovalRequest",
    "ApprovalStatus",
    "Application",
    "Candidate",
    "CandidateExperience",
    "CandidateNote",
    "CandidateSkill",
    "Job",
    "JobRequirement",
    "ToolExecution",
    "ToolExecutionStatus",
    "ALL_STAGES",
    "OFF_RAMPS",
    "STAGES",
    "JOB_STATUSES",
]
