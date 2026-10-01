"""RecruitAgent AI — a human-in-the-loop recruiting operations agent.

Package layout:

- ``app.agent``      — orchestrator loop, policy, providers (mock / OpenAI)
- ``app.tools``      — the controlled tool registry the agent can call
- ``app.services``   — domain logic (candidates, jobs, matching, approvals…)
- ``app.api``        — FastAPI routes
- ``app.models``     — SQLAlchemy models
- ``app.seed``       — standalone synthetic demo dataset
"""

__version__ = "0.1.0"
