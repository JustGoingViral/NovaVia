"""
IRIP - Integrated Recovery Intelligence Platform
Multi-agent AI system for comprehensive addiction recovery management
"""

from .agents.orchestrator import OrchestratorAgent as IRIPOrchestrator
from .agents.base_agent import BaseAgent, AgentCapability, AgentState, AgentPriority
from .agents.medication_agent import MedicationAgent
from .agents.therapy_coordinator_agent import TherapyCoordinatorAgent
from .agents.biohacking_agent import BiohackingAgent
from .agents.crisis_intervention_agent import CrisisInterventionAgent
from .agents.analytics_agent import AnalyticsAgent
# Phase 2 agents
from .agents.connectomics_agent import ConnectomicsAgent
from .agents.epigenetics_agent import EpigeneticsAgent
from .agents.psychedelic_modeling_agent import PsychedelicModelingAgent
from .agents.ai_therapy_companion import AITherapyCompanionAgent

__all__ = [
    "IRIPOrchestrator",
    "BaseAgent",
    "AgentCapability", 
    "AgentState",
    "AgentPriority",
    "MedicationAgent",
    "TherapyCoordinatorAgent",
    "BiohackingAgent", 
    "CrisisInterventionAgent",
    "AnalyticsAgent",
    # Phase 2 agents
    "ConnectomicsAgent",
    "EpigeneticsAgent",
    "PsychedelicModelingAgent",
    "AITherapyCompanionAgent",
]
