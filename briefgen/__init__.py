"""Competitive-Research Brief Generator — workflow vs agent."""
from .workflow import run_workflow
from .agent import run_agent
from .brief import Brief

__all__ = ["run_workflow", "run_agent", "Brief"]
