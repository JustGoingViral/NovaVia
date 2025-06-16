"""
IRIP Master Orchestrator Agent
Central coordination hub for all specialized AI agents in the NOVA ViA addiction recovery system
"""

import asyncio
import time
import logging
import json
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import defaultdict, deque
import heapq

from .base_agent import (
    BaseAgent, AgentMessage, PatientContext, AgentCapability,
    AgentPriority, AgentState
)


class OrchestrationType(Enum):
    """Types of orchestration strategies"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONSENSUS = "consensus"
    HIERARCHICAL = "hierarchical"
    EMERGENCY = "emergency"
    ADAPTIVE = "adaptive"


class DecisionType(Enum):
    """Types of orchestration decisions"""
    TREATMENT_PLAN = "treatment_plan"
    EMERGENCY_RESPONSE = "emergency_response"
    PROTOCOL_ADJUSTMENT = "protocol_adjustment"
    RESOURCE_ALLOCATION = "resource_allocation"
    PATIENT_ASSESSMENT = "patient_assessment"
    OUTCOME_OPTIMIZATION = "outcome_optimization"


class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    PRIORITY_BASED = "priority_based"
    VOTING = "voting"
    EXPERTISE_WEIGHTED = "expertise_weighted"
    CONSENSUS_REQUIRED = "consensus_required"
    OVERRIDE_AUTHORITY = "override_authority"


@dataclass
class AgentRegistration:
    """Registration information for specialized agents"""
    agent_id: str
    agent_type: str
    capabilities: List[AgentCapability]
    priority_level: AgentPriority
    specializations: List[str]
    availability: bool
    load_factor: float
    performance_metrics: Dict[str, float]
    last_heartbeat: float


@dataclass
class OrchestratedDecision:
    """Multi-agent orchestrated decision"""
    decision_id: str
    decision_type: DecisionType
    patient_id: str
    participating_agents: List[str]
    agent_recommendations: Dict[str, Dict[str, Any]]
    conflict_resolution_used: Optional[ConflictResolution]
    final_decision: Dict[str, Any]
    confidence_score: float
    execution_plan: List[Dict[str, Any]]
    timestamp: float
    success: bool


@dataclass
class WorkflowStep:
    """Individual step in orchestrated workflow"""
    step_id: str
    agent_id: str
    action: str
    parameters: Dict[str, Any]
    dependencies: List[str]
    priority: int
    estimated_duration: float
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None


@dataclass
class PatientOrchestrationState:
    """Current orchestration state for a patient"""
    patient_id: str
    active_workflows: Dict[str, List[WorkflowStep]]
    agent_assignments: Dict[str, str]  # agent_id -> current_task
    priority_queue: List[Tuple[int, Dict[str, Any]]]  # priority, task
    last_update: float
    emergency_status: bool = False
    coordination_context: Dict[str, Any] = field(default_factory=dict)


class OrchestratorAgent(BaseAgent):
    """
    Master Orchestrator Agent for NOVA ViA IRIP System
    
    Capabilities:
    - Multi-agent coordination and consensus building
    - Intelligent workflow orchestration
    - Real-time decision optimization
    - Emergency response coordination
    - Resource allocation and load balancing
    - Conflict resolution between agents
    - Treatment pathway optimization
    - Continuous learning and adaptation
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, config)
        
        # Orchestrator identification
        self.agent_type = "orchestrator_agent"
        self.version = "1.0.0"
        self.description = "Master AI Orchestration and Coordination Hub"
        
        # Master orchestrator capabilities
        self.capabilities = [
            AgentCapability.TREATMENT_ORCHESTRATION,
            AgentCapability.EMERGENCY_COORDINATION,
            AgentCapability.RESOURCE_MANAGEMENT,
            AgentCapability.DECISION_OPTIMIZATION,
            AgentCapability.WORKFLOW_MANAGEMENT
        ]
        
        self.priority_level = AgentPriority.CRITICAL
        
        # Agent registry and management
        self.registered_agents: Dict[str, AgentRegistration] = {}
        self.agent_capabilities_map: Dict[AgentCapability, List[str]] = defaultdict(list)
        self.agent_communication_channels: Dict[str, asyncio.Queue] = {}
        
        # Patient orchestration states
        self.patient_states: Dict[str, PatientOrchestrationState] = {}
        self.active_decisions: Dict[str, OrchestratedDecision] = {}
        self.decision_history: List[OrchestratedDecision] = []
        
        # Workflow management
        self.workflow_templates: Dict[str, List[WorkflowStep]] = {}
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # Orchestration strategies
        self.orchestration_strategies = {
            DecisionType.EMERGENCY_RESPONSE: OrchestrationType.EMERGENCY,
            DecisionType.TREATMENT_PLAN: OrchestrationType.CONSENSUS,
            DecisionType.PROTOCOL_ADJUSTMENT: OrchestrationType.ADAPTIVE,
            DecisionType.RESOURCE_ALLOCATION: OrchestrationType.HIERARCHICAL,
            DecisionType.PATIENT_ASSESSMENT: OrchestrationType.PARALLEL,
            DecisionType.OUTCOME_OPTIMIZATION: OrchestrationType.SEQUENTIAL
        }
        
        # Conflict resolution configuration
        self.conflict_resolution_strategies = {
            "high_priority_emergency": ConflictResolution.OVERRIDE_AUTHORITY,
            "treatment_planning": ConflictResolution.EXPERTISE_WEIGHTED,
            "routine_optimization": ConflictResolution.VOTING,
            "protocol_changes": ConflictResolution.CONSENSUS_REQUIRED
        }
        
        # Performance tracking
        self.orchestration_metrics = {
            "decisions_orchestrated": 0,
            "conflicts_resolved": 0,
            "workflows_completed": 0,
            "emergency_responses": 0,
            "average_decision_time": 0.0,
            "success_rate": 0.0
        }
        
        # Learning and adaptation
        self.decision_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.agent_performance_history: Dict[str, List[float]] = defaultdict(list)
        self.optimization_insights: List[Dict[str, Any]] = []
        
        # Communication protocols
        self.message_routing_table: Dict[str, List[str]] = {}
        self.broadcast_channels: Dict[str, Set[str]] = {
            "emergency": set(),
            "treatment_updates": set(),
            "system_alerts": set()
        }
        
        # Emergency response configuration
        self.emergency_escalation_levels = {
            1: ["crisis_intervention_agent"],
            2: ["crisis_intervention_agent", "medication_agent"],
            3: ["crisis_intervention_agent", "medication_agent", "biohacking_agent"],
            4: ["all_agents"]  # Full system response
        }
        
        # Consensus thresholds
        self.consensus_thresholds = {
            "simple_majority": 0.51,
            "strong_majority": 0.67,
            "consensus": 0.85,
            "unanimous": 1.0
        }
    
    async def initialize(self) -> bool:
        """Initialize the master orchestrator"""
        try:
            self.logger.info("Initializing Master Orchestrator Agent...")
            
            # Initialize communication infrastructure
            await self._setup_communication_infrastructure()
            
            # Load workflow templates
            await self._load_workflow_templates()
            
            # Setup agent discovery and registration
            await self._setup_agent_discovery()
            
            # Initialize decision-making algorithms
            await self._initialize_decision_algorithms()
            
            # Start orchestration services
            await self._start_orchestration_services()
            
            self.logger.info("Master Orchestrator Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Master Orchestrator initialization failed: {e}")
            return False
    
    async def register_agent(self, agent_info: Dict[str, Any]) -> bool:
        """Register a specialized agent with the orchestrator"""
        try:
            agent_id = agent_info["agent_id"]
            
            registration = AgentRegistration(
                agent_id=agent_id,
                agent_type=agent_info["agent_type"],
                capabilities=[AgentCapability(cap) for cap in agent_info.get("capabilities", [])],
                priority_level=AgentPriority(agent_info.get("priority_level", "normal")),
                specializations=agent_info.get("specializations", []),
                availability=True,
                load_factor=0.0,
                performance_metrics=agent_info.get("performance_metrics", {}),
                last_heartbeat=time.time()
            )
            
            self.registered_agents[agent_id] = registration
            
            # Update capability mapping
            for capability in registration.capabilities:
                self.agent_capabilities_map[capability].append(agent_id)
            
            # Setup communication channel
            self.agent_communication_channels[agent_id] = asyncio.Queue()
            
            # Add to appropriate broadcast channels
            if AgentCapability.EMERGENCY_RESPONSE in registration.capabilities:
                self.broadcast_channels["emergency"].add(agent_id)
            if AgentCapability.TREATMENT_COORDINATION in registration.capabilities:
                self.broadcast_channels["treatment_updates"].add(agent_id)
            
            self.logger.info(f"Agent {agent_id} registered successfully with capabilities: {registration.capabilities}")
            return True
            
        except Exception as e:
            self.logger.error(f"Agent registration failed: {e}")
            return False
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages for orchestration"""
        try:
            message_type = message.message_type
            
            if message_type == "decision_request":
                return await self._handle_decision_request(message)
            elif message_type == "agent_recommendation":
                return await self._handle_agent_recommendation(message)
            elif message_type == "workflow_request":
                return await self._handle_workflow_request(message)
            elif message_type == "emergency_alert":
                return await self._handle_emergency_orchestration(message)
            elif message_type == "resource_request":
                return await self._handle_resource_allocation(message)
            elif message_type == "agent_heartbeat":
                return await self._handle_agent_heartbeat(message)
            elif message_type == "optimization_request":
                return await self._handle_optimization_orchestration(message)
            else:
                self.logger.warning(f"Unknown orchestration message type: {message_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Orchestration message processing error: {e}")
            return None
    
    async def handle_patient_update(self, patient_context: PatientContext):
        """Handle patient context updates for orchestration"""
        patient_id = patient_context.patient_id
        
        # Update patient orchestration state
        if patient_id not in self.patient_states:
            self.patient_states[patient_id] = PatientOrchestrationState(
                patient_id=patient_id,
                active_workflows={},
                agent_assignments={},
                priority_queue=[],
                last_update=time.time()
            )
        
        # Assess orchestration needs
        orchestration_needs = await self._assess_orchestration_needs(patient_context)
        
        if orchestration_needs["required"]:
            await self._initiate_patient_orchestration(patient_id, orchestration_needs)
    
    async def handle_emergency(self, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system-wide emergency orchestration"""
        try:
            emergency_type = emergency_data.get("type")
            patient_id = emergency_data.get("patient_id")
            severity = emergency_data.get("severity", "moderate")
            
            self.logger.critical(f"ORCHESTRATING EMERGENCY RESPONSE: {emergency_type} (severity: {severity})")
            
            # Determine escalation level
            escalation_level = self._determine_escalation_level(emergency_type, severity)
            
            # Orchestrate emergency response
            response_result = await self._orchestrate_emergency_response(
                emergency_data, escalation_level
            )
            
            self.orchestration_metrics["emergency_responses"] += 1
            
            return response_result
            
        except Exception as e:
            self.logger.error(f"Emergency orchestration failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_decision_request(self, message: AgentMessage) -> AgentMessage:
        """Handle multi-agent decision requests"""
        content = message.content
        decision_type = DecisionType(content.get("decision_type"))
        patient_id = content.get("patient_id")
        decision_context = content.get("context", {})
        
        # Initiate orchestrated decision-making
        decision_result = await self._orchestrate_decision(
            decision_type, patient_id, decision_context
        )
        
        self.orchestration_metrics["decisions_orchestrated"] += 1
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="orchestrated_decision",
            content=decision_result,
            priority=AgentPriority.HIGH,
            timestamp=time.time()
        )
    
    async def _orchestrate_decision(self, decision_type: DecisionType, 
                                  patient_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate multi-agent decision-making process"""
        
        decision_id = f"decision_{int(time.time())}_{patient_id}"
        
        # Determine orchestration strategy
        strategy = self.orchestration_strategies.get(decision_type, OrchestrationType.CONSENSUS)
        
        # Select participating agents
        participating_agents = await self._select_agents_for_decision(decision_type, context)
        
        # Gather recommendations from agents
        recommendations = await self._gather_agent_recommendations(
            participating_agents, decision_type, patient_id, context
        )
        
        # Resolve conflicts if any
        conflict_resolution = None
        if self._has_conflicting_recommendations(recommendations):
            conflict_resolution = await self._resolve_recommendation_conflicts(
                recommendations, decision_type, context
            )
            self.orchestration_metrics["conflicts_resolved"] += 1
        
        # Make final orchestrated decision
        final_decision = await self._make_final_decision(
            recommendations, strategy, conflict_resolution
        )
        
        # Create execution plan
        execution_plan = await self._create_execution_plan(final_decision, participating_agents)
        
        # Store decision
        orchestrated_decision = OrchestratedDecision(
            decision_id=decision_id,
            decision_type=decision_type,
            patient_id=patient_id,
            participating_agents=participating_agents,
            agent_recommendations=recommendations,
            conflict_resolution_used=conflict_resolution,
            final_decision=final_decision,
            confidence_score=self._calculate_decision_confidence(recommendations),
            execution_plan=execution_plan,
            timestamp=time.time(),
            success=True
        )
        
        self.active_decisions[decision_id] = orchestrated_decision
        
        # Learn from decision patterns
        await self._learn_from_decision(orchestrated_decision)
        
        return {
            "decision_id": decision_id,
            "final_decision": final_decision,
            "confidence_score": orchestrated_decision.confidence_score,
            "execution_plan": execution_plan,
            "participating_agents": participating_agents
        }
    
    async def _select_agents_for_decision(self, decision_type: DecisionType, 
                                        context: Dict[str, Any]) -> List[str]:
        """Select appropriate agents for decision-making"""
        
        # Map decision types to required capabilities
        capability_requirements = {
            DecisionType.TREATMENT_PLAN: [
                AgentCapability.TREATMENT_COORDINATION,
                AgentCapability.MEDICATION_MANAGEMENT,
                AgentCapability.THERAPY_COORDINATION
            ],
            DecisionType.EMERGENCY_RESPONSE: [
                AgentCapability.EMERGENCY_RESPONSE,
                AgentCapability.CRISIS_INTERVENTION
            ],
            DecisionType.PROTOCOL_ADJUSTMENT: [
                AgentCapability.TREATMENT_OPTIMIZATION,
                AgentCapability.DATA_ANALYSIS
            ],
            DecisionType.OUTCOME_OPTIMIZATION: [
                AgentCapability.DATA_ANALYSIS,
                AgentCapability.PREDICTIVE_MODELING,
                AgentCapability.TREATMENT_OPTIMIZATION
            ]
        }
        
        required_capabilities = capability_requirements.get(decision_type, [])
        selected_agents = []
        
        # Select agents based on capabilities, availability, and performance
        for capability in required_capabilities:
            available_agents = [
                agent_id for agent_id in self.agent_capabilities_map.get(capability, [])
                if self.registered_agents[agent_id].availability
            ]
            
            if available_agents:
                # Select best performing available agent for this capability
                best_agent = max(available_agents, 
                               key=lambda aid: self.registered_agents[aid].performance_metrics.get("success_rate", 0.5))
                if best_agent not in selected_agents:
                    selected_agents.append(best_agent)
        
        return selected_agents
    
    async def _gather_agent_recommendations(self, agents: List[str], decision_type: DecisionType,
                                          patient_id: str, context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Gather recommendations from participating agents"""
        recommendations = {}
        
        # Create recommendation request
        request_message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            recipient_id="",  # Will be set per agent
            message_type="recommendation_request",
            content={
                "decision_type": decision_type.value,
                "patient_id": patient_id,
                "context": context,
                "timeout": 30.0  # 30 second timeout
            },
            priority=AgentPriority.HIGH,
            timestamp=time.time()
        )
        
        # Send requests to all participating agents
        recommendation_tasks = []
        for agent_id in agents:
            task = asyncio.create_task(
                self._request_agent_recommendation(agent_id, request_message)
            )
            recommendation_tasks.append((agent_id, task))
        
        # Gather recommendations with timeout
        for agent_id, task in recommendation_tasks:
            try:
                recommendation = await asyncio.wait_for(task, timeout=30.0)
                recommendations[agent_id] = recommendation
            except asyncio.TimeoutError:
                self.logger.warning(f"Recommendation timeout for agent {agent_id}")
                recommendations[agent_id] = {"error": "timeout", "confidence": 0.0}
            except Exception as e:
                self.logger.error(f"Error getting recommendation from {agent_id}: {e}")
                recommendations[agent_id] = {"error": str(e), "confidence": 0.0}
        
        return recommendations
    
    async def _request_agent_recommendation(self, agent_id: str, 
                                          request: AgentMessage) -> Dict[str, Any]:
        """Request recommendation from specific agent"""
        # This would send the request to the agent and wait for response
        # For now, simulate agent recommendations
        
        agent_reg = self.registered_agents.get(agent_id)
        if not agent_reg:
            return {"error": "agent_not_found", "confidence": 0.0}
        
        # Simulate different agent responses based on their type
        if "crisis" in agent_reg.agent_type:
            return {
                "recommendation": "immediate_intervention",
                "confidence": 0.9,
                "rationale": "High risk indicators detected",
                "actions": ["activate_crisis_protocol", "notify_emergency_contacts"]
            }
        elif "medication" in agent_reg.agent_type:
            return {
                "recommendation": "adjust_dosage",
                "confidence": 0.8,
                "rationale": "Optimization based on current markers",
                "actions": ["increase_buprenorphine_10mg", "monitor_response"]
            }
        elif "analytics" in agent_reg.agent_type:
            return {
                "recommendation": "continue_current_protocol",
                "confidence": 0.75,
                "rationale": "Positive trend indicators",
                "actions": ["maintain_current_treatment", "schedule_assessment"]
            }
        else:
            return {
                "recommendation": "maintain_status_quo",
                "confidence": 0.6,
                "rationale": "Insufficient data for change",
                "actions": ["continue_monitoring"]
            }
    
    def _has_conflicting_recommendations(self, recommendations: Dict[str, Dict[str, Any]]) -> bool:
        """Check if agent recommendations conflict"""
        recommendation_actions = []
        
        for agent_id, rec in recommendations.items():
            if "recommendation" in rec:
                recommendation_actions.append(rec["recommendation"])
        
        # Simple conflict detection - check for opposing recommendations
        if "immediate_intervention" in recommendation_actions and "maintain_status_quo" in recommendation_actions:
            return True
        if "increase" in str(recommendation_actions) and "decrease" in str(recommendation_actions):
            return True
        
        return False
    
    async def _resolve_recommendation_conflicts(self, recommendations: Dict[str, Dict[str, Any]],
                                             decision_type: DecisionType, 
                                             context: Dict[str, Any]) -> ConflictResolution:
        """Resolve conflicts between agent recommendations"""
        
        # Determine appropriate conflict resolution strategy
        if decision_type == DecisionType.EMERGENCY_RESPONSE:
            resolution_strategy = ConflictResolution.OVERRIDE_AUTHORITY
            # In emergencies, crisis intervention agent has override authority
            for agent_id, rec in recommendations.items():
                if "crisis" in self.registered_agents[agent_id].agent_type:
                    return resolution_strategy
        
        elif decision_type == DecisionType.TREATMENT_PLAN:
            resolution_strategy = ConflictResolution.EXPERTISE_WEIGHTED
            # Weight recommendations by agent expertise and confidence
            
        else:
            resolution_strategy = ConflictResolution.VOTING
        
        return resolution_strategy
    
    async def _make_final_decision(self, recommendations: Dict[str, Dict[str, Any]],
                                 strategy: OrchestrationType, 
                                 conflict_resolution: Optional[ConflictResolution]) -> Dict[str, Any]:
        """Make final orchestrated decision"""
        
        if strategy == OrchestrationType.EMERGENCY:
            # In emergency, take the most urgent action
            urgent_recs = [rec for rec in recommendations.values() 
                          if rec.get("recommendation") == "immediate_intervention"]
            if urgent_recs:
                return urgent_recs[0]
        
        elif strategy == OrchestrationType.CONSENSUS:
            # Find consensus among recommendations
            return self._find_consensus_decision(recommendations)
        
        elif strategy == OrchestrationType.PARALLEL:
            # Combine compatible recommendations
            return self._combine_parallel_recommendations(recommendations)
        
        else:  # Default to highest confidence recommendation
            best_rec = max(recommendations.values(), 
                          key=lambda r: r.get("confidence", 0.0))
            return best_rec
    
    def _find_consensus_decision(self, recommendations: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Find consensus among agent recommendations"""
        # Group similar recommendations
        recommendation_groups = defaultdict(list)
        
        for agent_id, rec in recommendations.items():
            rec_type = rec.get("recommendation", "unknown")
            recommendation_groups[rec_type].append((agent_id, rec))
        
        # Find majority recommendation
        if recommendation_groups:
            majority_group = max(recommendation_groups.items(), key=lambda x: len(x[1]))
            
            # Calculate consensus confidence
            group_confidences = [rec["confidence"] for _, rec in majority_group[1] if "confidence" in rec]
            consensus_confidence = sum(group_confidences) / len(group_confidences) if group_confidences else 0.5
            
            # Combine actions from consensus group
            all_actions = []
            for _, rec in majority_group[1]:
                all_actions.extend(rec.get("actions", []))
            
            return {
                "recommendation": majority_group[0],
                "confidence": consensus_confidence,
                "rationale": f"Consensus among {len(majority_group[1])} agents",
                "actions": list(set(all_actions)),  # Remove duplicates
                "consensus_level": len(majority_group[1]) / len(recommendations)
            }
        
        return {"recommendation": "maintain_status_quo", "confidence": 0.5}
    
    def _combine_parallel_recommendations(self, recommendations: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Combine compatible parallel recommendations"""
        combined_actions = []
        combined_confidence = 0.0
        valid_recs = 0
        
        for agent_id, rec in recommendations.items():
            if "actions" in rec:
                combined_actions.extend(rec["actions"])
            if "confidence" in rec:
                combined_confidence += rec["confidence"]
                valid_recs += 1
        
        avg_confidence = combined_confidence / valid_recs if valid_recs > 0 else 0.5
        
        return {
            "recommendation": "combined_parallel_actions",
            "confidence": avg_confidence,
            "rationale": "Combination of compatible parallel recommendations",
            "actions": list(set(combined_actions))
        }
    
    def _calculate_decision_confidence(self, recommendations: Dict[str, Dict[str, Any]]) -> float:
        """Calculate overall confidence in orchestrated decision"""
        confidences = [rec.get("confidence", 0.5) for rec in recommendations.values()]
        
        if not confidences:
            return 0.5
        
        # Calculate weighted average confidence
        avg_confidence = sum(confidences) / len(confidences)
        
        # Adjust for consensus level
        consensus_bonus = 0.1 if len(set(rec.get("recommendation", "") for rec in recommendations.values())) == 1 else 0.0
        
        return min(1.0, avg_confidence + consensus_bonus)
    
    async def _create_execution_plan(self, decision: Dict[str, Any], 
                                   agents: List[str]) -> List[Dict[str, Any]]:
        """Create execution plan for orchestrated decision"""
        execution_steps = []
        
        actions = decision.get("actions", [])
        
        for i, action in enumerate(actions):
            # Assign action to appropriate agent
            assigned_agent = self._assign_action_to_agent(action, agents)
            
            step = {
                "step_id": f"step_{i+1}",
                "action": action,
                "assigned_agent": assigned_agent,
                "priority": len(actions) - i,  # Higher priority for earlier actions
                "estimated_duration": 300,  # 5 minutes default
                "dependencies": [f"step_{i}"] if i > 0 else []
            }
            execution_steps.append(step)
        
        return execution_steps
    
    def _assign_action_to_agent(self, action: str, available_agents: List[str]) -> str:
        """Assign specific action to most appropriate agent"""
        # Simple action-to-agent mapping based on action keywords
        action_mappings = {
            "crisis": "crisis_intervention_agent",
            "medication": "medication_agent",
            "therapy": "therapy_coordinator_agent",
            "biohacking": "biohacking_agent",
            "analytics": "analytics_agent"
        }
        
        for keyword, agent_type in action_mappings.items():
            if keyword in action.lower():
                # Find agent of this type
                for agent_id in available_agents:
                    if agent_type in self.registered_agents[agent_id].agent_type:
                        return agent_id
        
        # Default to first available agent
        return available_agents[0] if available_agents else "unknown_agent"
    
    async def _learn_from_decision(self, decision: OrchestratedDecision):
        """Learn from orchestrated decision outcomes"""
        pattern_key = f"{decision.decision_type.value}_{decision.patient_id}"
        
        decision_pattern = {
            "decision_type": decision.decision_type.value,
            "participating_agents": decision.participating_agents,
            "confidence": decision.confidence_score,
            "timestamp": decision.timestamp,
            "success": decision.success
        }
        
        self.decision_patterns[pattern_key].append(decision_pattern)
        
        # Update agent performance metrics
        for agent_id in decision.participating_agents:
            if agent_id in self.agent_performance_history:
                self.agent_performance_history[agent_id].append(
                    1.0 if decision.success else 0.0
                )
    
    # Additional orchestration methods
    async def _handle_emergency_orchestration(self, message: AgentMessage) -> AgentMessage:
        """Handle emergency orchestration requests"""
        emergency_data = message.content
        
        # Orchestrate emergency response
        response_result = await self.handle_emergency(emergency_data)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="emergency_orchestration_complete",
            content=response_result,
            priority=AgentPriority.CRITICAL,
            timestamp=time.time()
        )
    
    async def _orchestrate_emergency_response(self, emergency_data: Dict[str, Any], 
                                            escalation_level: int) -> Dict[str, Any]:
        """Orchestrate system-wide emergency response"""
        
        # Determine responding agents based on escalation level
        responding_agents = self._get_emergency_response_agents(escalation_level)
        
        # Create emergency response workflow
        emergency_workflow = await self._create_emergency_workflow(emergency_data, responding_agents)
        
        # Execute emergency response in parallel
        response_results = await self._execute_emergency_workflow(emergency_workflow)
        
        return {
            "success": True,
            "emergency_type": emergency_data.get("type"),
            "escalation_level": escalation_level,
            "responding_agents": responding_agents,
            "response_results": response_results,
            "response_time": time.time() - emergency_data.get("timestamp", time.time())
        }
    
    def _determine_escalation_level(self, emergency_type: str, severity: str) -> int:
        """Determine appropriate escalation level for emergency"""
        # Emergency escalation matrix
        escalation_matrix = {
            ("overdose", "critical"): 4,
            ("overdose", "severe"): 3,
            ("suicide_risk", "critical"): 4,
            ("suicide_risk", "severe"): 3,
            ("medical_emergency", "critical"): 4,
            ("withdrawal_complications", "severe"): 3,
            ("psychological_crisis", "moderate"): 2,
            ("treatment_resistance", "moderate"): 1
        }
        
        return escalation_matrix.get((emergency_type, severity), 2)  # Default to level 2
    
    def _get_emergency_response_agents(self, escalation_level: int) -> List[str]:
        """Get appropriate agents for emergency response"""
        if escalation_level in self.emergency_escalation_levels:
            required_agents = self.emergency_escalation_levels[escalation_level]
            
            if "all_agents" in required_agents:
                return list(self.registered_agents.keys())
            else:
                responding_agents = []
                for agent_type in required_agents:
                    # Find agents of this type
                    for agent_id, reg in self.registered_agents.items():
                        if agent_type in reg.agent_type and reg.availability:
                            responding_agents.append(agent_id)
                return responding_agents
        
        return []
    
    async def _create_emergency_workflow(self, emergency_data: Dict[str, Any], 
                                       agents: List[str]) -> List[WorkflowStep]:
        """Create emergency response workflow"""
        workflow_steps = []
        
        # Step 1: Immediate assessment
        workflow_steps.append(WorkflowStep(
            step_id="emergency_assessment",
            agent_id=self._find_agent_by_capability(agents, AgentCapability.CRISIS_INTERVENTION),
            action="emergency_assessment",
            parameters=emergency_data,
            dependencies=[],
            priority=10,
            estimated_duration=60  # 1 minute
        ))
        
        # Step 2: Stabilization actions
        workflow_steps.append(WorkflowStep(
            step_id="immediate_stabilization",
            agent_id=self._find_agent_by_capability(agents, AgentCapability.EMERGENCY_RESPONSE),
            action="stabilization_protocol",
            parameters=emergency_data,
            dependencies=["emergency_assessment"],
            priority=9,
            estimated_duration=300  # 5 minutes
        ))
        
        # Step 3: Medical intervention if needed
        if emergency_data.get("type") in ["overdose", "medical_emergency"]:
            workflow_steps.append(WorkflowStep(
                step_id="medical_intervention",
                agent_id=self._find_agent_by_capability(agents, AgentCapability.MEDICATION_MANAGEMENT),
                action="emergency_medication_protocol",
                parameters=emergency_data,
                dependencies=["immediate_stabilization"],
                priority=8,
                estimated_duration=180  # 3 minutes
            ))
        
        return workflow_steps
    
    def _find_agent_by_capability(self, agent_ids: List[str], capability: AgentCapability) -> str:
        """Find agent with specific capability from list"""
        for agent_id in agent_ids:
            if agent_id in self.registered_agents:
                if capability in self.registered_agents[agent_id].capabilities:
                    return agent_id
        
        # Return first agent as fallback
        return agent_ids[0] if agent_ids else "unknown_agent"
    
    async def _execute_emergency_workflow(self, workflow: List[WorkflowStep]) -> Dict[str, Any]:
        """Execute emergency workflow with parallel processing where possible"""
        results = {}
        completed_steps = set()
        
        # Execute workflow steps respecting dependencies
        while len(completed_steps) < len(workflow):
            # Find steps ready for execution
            ready_steps = [
                step for step in workflow 
                if step.step_id not in completed_steps and 
                all(dep in completed_steps for dep in step.dependencies)
            ]
            
            if not ready_steps:
                break  # No more steps can be executed
            
            # Execute ready steps in parallel
            step_tasks = []
            for step in ready_steps:
                task = asyncio.create_task(self._execute_workflow_step(step))
                step_tasks.append((step.step_id, task))
            
            # Wait for completion
            for step_id, task in step_tasks:
                try:
                    result = await asyncio.wait_for(task, timeout=step.estimated_duration + 60)
                    results[step_id] = result
                    completed_steps.add(step_id)
                except asyncio.TimeoutError:
                    results[step_id] = {"error": "timeout", "success": False}
                    completed_steps.add(step_id)  # Mark as completed to continue workflow
                except Exception as e:
                    results[step_id] = {"error": str(e), "success": False}
                    completed_steps.add(step_id)
        
        return results
    
    async def _execute_workflow_step(self, step: WorkflowStep) -> Dict[str, Any]:
        """Execute individual workflow step"""
        # Simulate step execution - in real implementation would call agent
        await asyncio.sleep(0.1)  # Simulate processing time
        
        return {
            "success": True,
            "step_id": step.step_id,
            "agent_id": step.agent_id,
            "action": step.action,
            "execution_time": time.time()
        }
    
    # Additional handler methods
    async def _handle_agent_recommendation(self, message: AgentMessage) -> AgentMessage:
        """Handle agent recommendation submissions"""
        content = message.content
        decision_id = content.get("decision_id")
        recommendation = content.get("recommendation")
        
        # Store recommendation for decision
        if decision_id in self.active_decisions:
            decision = self.active_decisions[decision_id]
            decision.agent_recommendations[message.sender_id] = recommendation
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="recommendation_acknowledged",
            content={"decision_id": decision_id, "acknowledged": True},
            priority=AgentPriority.NORMAL,
            timestamp=time.time()
        )
    
    async def _handle_workflow_request(self, message: AgentMessage) -> AgentMessage:
        """Handle workflow orchestration requests"""
        content = message.content
        workflow_type = content.get("workflow_type")
        patient_id = content.get("patient_id")
        
        # Create and execute workflow
        workflow_result = await self._orchestrate_workflow(workflow_type, patient_id, content)
        
        self.orchestration_metrics["workflows_completed"] += 1
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="workflow_orchestrated",
            content=workflow_result,
            priority=AgentPriority.NORMAL,
            timestamp=time.time()
        )
    
    async def _orchestrate_workflow(self, workflow_type: str, patient_id: str, 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate specific workflow type"""
        workflow_id = f"workflow_{int(time.time())}_{patient_id}"
        
        # Get workflow template
        workflow_template = self.workflow_templates.get(workflow_type, [])
        
        # Customize workflow for patient
        customized_workflow = await self._customize_workflow(workflow_template, patient_id, context)
        
        # Execute workflow
        execution_result = await self._execute_workflow(customized_workflow)
        
        return {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "patient_id": patient_id,
            "execution_result": execution_result,
            "success": execution_result.get("success", False)
        }
    
    async def _customize_workflow(self, template: List[WorkflowStep], patient_id: str, 
                                context: Dict[str, Any]) -> List[WorkflowStep]:
        """Customize workflow template for specific patient"""
        customized_steps = []
        
        for step in template:
            # Clone step and customize parameters
            customized_step = WorkflowStep(
                step_id=f"{step.step_id}_{patient_id}",
                agent_id=step.agent_id,
                action=step.action,
                parameters={**step.parameters, "patient_id": patient_id, **context},
                dependencies=step.dependencies,
                priority=step.priority,
                estimated_duration=step.estimated_duration
            )
            customized_steps.append(customized_step)
        
        return customized_steps
    
    async def _execute_workflow(self, workflow: List[WorkflowStep]) -> Dict[str, Any]:
        """Execute general workflow"""
        start_time = time.time()
        results = {}
        
        try:
            # Execute workflow similar to emergency workflow
            results = await self._execute_emergency_workflow(workflow)
            
            success_count = sum(1 for r in results.values() if r.get("success", False))
            
            return {
                "success": success_count > len(workflow) * 0.8,  # 80% success threshold
                "results": results,
                "execution_time": time.time() - start_time,
                "steps_completed": len(results),
                "success_rate": success_count / len(workflow) if workflow else 0.0
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def _handle_resource_allocation(self, message: AgentMessage) -> AgentMessage:
        """Handle resource allocation requests"""
        content = message.content
        resource_type = content.get("resource_type")
        requirements = content.get("requirements", {})
        
        # Allocate resources based on availability and priority
        allocation_result = await self._allocate_resources(resource_type, requirements)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="resource_allocation_complete",
            content=allocation_result,
            priority=AgentPriority.NORMAL,
            timestamp=time.time()
        )
    
    async def _allocate_resources(self, resource_type: str, 
                                requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate system resources based on requirements"""
        # Resource allocation logic
        if resource_type == "agent_capacity":
            return await self._allocate_agent_capacity(requirements)
        elif resource_type == "computation":
            return await self._allocate_computational_resources(requirements)
        elif resource_type == "device_access":
            return await self._allocate_device_resources(requirements)
        else:
            return {"success": False, "error": "Unknown resource type"}
    
    async def _allocate_agent_capacity(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate agent capacity based on requirements"""
        required_capability = requirements.get("capability")
        priority = requirements.get("priority", "normal")
        
        # Find available agents with required capability
        available_agents = []
        if required_capability:
            capability_enum = AgentCapability(required_capability)
            candidate_agents = self.agent_capabilities_map.get(capability_enum, [])
            
            for agent_id in candidate_agents:
                agent_reg = self.registered_agents.get(agent_id)
                if agent_reg and agent_reg.availability and agent_reg.load_factor < 0.8:
                    available_agents.append((agent_id, agent_reg.load_factor))
        
        if available_agents:
            # Select agent with lowest load factor
            selected_agent = min(available_agents, key=lambda x: x[1])
            
            # Update load factor
            self.registered_agents[selected_agent[0]].load_factor += 0.2
            
            return {
                "success": True,
                "allocated_agent": selected_agent[0],
                "load_factor": selected_agent[1]
            }
        else:
            return {
                "success": False,
                "error": "No available agents with required capability"
            }
    
    async def _allocate_computational_resources(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate computational resources"""
        # Simplified computational resource allocation
        return {
            "success": True,
            "allocated_resources": {
                "cpu_cores": requirements.get("cpu_cores", 2),
                "memory_gb": requirements.get("memory_gb", 4),
                "gpu_allocation": requirements.get("gpu_required", False)
            }
        }
    
    async def _allocate_device_resources(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate device access resources"""
        device_type = requirements.get("device_type")
        duration = requirements.get("duration", 1800)  # 30 minutes default
        
        # Simplified device allocation
        return {
            "success": True,
            "allocated_device": f"{device_type}_001",
            "allocation_duration": duration,
            "start_time": time.time()
        }
    
    async def _handle_agent_heartbeat(self, message: AgentMessage) -> AgentMessage:
        """Handle agent heartbeat messages"""
        agent_id = message.sender_id
        content = message.content
        
        # Update agent registration with heartbeat info
        if agent_id in self.registered_agents:
            registration = self.registered_agents[agent_id]
            registration.last_heartbeat = time.time()
            registration.availability = content.get("available", True)
            registration.load_factor = content.get("load_factor", 0.0)
            
            # Update performance metrics if provided
            if "performance_metrics" in content:
                registration.performance_metrics.update(content["performance_metrics"])
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="heartbeat_acknowledged",
            content={"acknowledged": True, "timestamp": time.time()},
            priority=AgentPriority.LOW,
            timestamp=time.time()
        )
    
    async def _handle_optimization_orchestration(self, message: AgentMessage) -> AgentMessage:
        """Handle optimization orchestration requests"""
        content = message.content
        optimization_type = content.get("optimization_type")
        target_metrics = content.get("target_metrics", [])
        
        # Orchestrate system optimization
        optimization_result = await self._orchestrate_optimization(optimization_type, target_metrics, content)
        
        return AgentMessage(
            message_id="",
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="optimization_orchestrated",
            content=optimization_result,
            priority=AgentPriority.NORMAL,
            timestamp=time.time()
        )
    
    async def _orchestrate_optimization(self, optimization_type: str, target_metrics: List[str], 
                                      context: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate system-wide optimization"""
        optimization_id = f"optimization_{int(time.time())}"
        
        # Select agents for optimization
        optimization_agents = await self._select_optimization_agents(optimization_type, target_metrics)
        
        # Create optimization workflow
        optimization_workflow = await self._create_optimization_workflow(
            optimization_type, target_metrics, optimization_agents, context
        )
        
        # Execute optimization
        execution_result = await self._execute_workflow(optimization_workflow)
        
        return {
            "optimization_id": optimization_id,
            "optimization_type": optimization_type,
            "participating_agents": optimization_agents,
            "execution_result": execution_result,
            "target_metrics": target_metrics
        }
    
    async def _select_optimization_agents(self, optimization_type: str, 
                                        target_metrics: List[str]) -> List[str]:
        """Select agents for optimization based on type and metrics"""
        if optimization_type == "treatment_outcomes":
            return [aid for aid in self.registered_agents.keys() 
                   if any(cap in self.registered_agents[aid].capabilities 
                         for cap in [AgentCapability.TREATMENT_OPTIMIZATION, 
                                   AgentCapability.DATA_ANALYSIS])]
        elif optimization_type == "resource_utilization":
            return [aid for aid in self.registered_agents.keys() 
                   if AgentCapability.RESOURCE_MANAGEMENT in self.registered_agents[aid].capabilities]
        else:
            # Default to all available agents
            return [aid for aid in self.registered_agents.keys() 
                   if self.registered_agents[aid].availability]
    
    async def _create_optimization_workflow(self, optimization_type: str, target_metrics: List[str],
                                          agents: List[str], context: Dict[str, Any]) -> List[WorkflowStep]:
        """Create optimization workflow"""
        workflow_steps = []
        
        # Step 1: Gather current performance data
        workflow_steps.append(WorkflowStep(
            step_id="performance_analysis",
            agent_id=self._find_agent_by_capability(agents, AgentCapability.DATA_ANALYSIS),
            action="analyze_current_performance",
            parameters={"metrics": target_metrics, **context},
            dependencies=[],
            priority=5,
            estimated_duration=300
        ))
        
        # Step 2: Generate optimization recommendations
        workflow_steps.append(WorkflowStep(
            step_id="optimization_recommendations",
            agent_id=self._find_agent_by_capability(agents, AgentCapability.TREATMENT_OPTIMIZATION),
            action="generate_optimization_plan",
            parameters={"optimization_type": optimization_type, **context},
            dependencies=["performance_analysis"],
            priority=4,
            estimated_duration=600
        ))
        
        # Step 3: Implement optimizations
        workflow_steps.append(WorkflowStep(
            step_id="implement_optimizations",
            agent_id=agents[0] if agents else "orchestrator",
            action="implement_optimization_plan",
            parameters=context,
            dependencies=["optimization_recommendations"],
            priority=3,
            estimated_duration=900
        ))
        
        return workflow_steps
    
    # Initialization helper methods
    async def _setup_communication_infrastructure(self):
        """Setup communication infrastructure for agent coordination"""
        self.logger.info("Communication infrastructure established")
    
    async def _load_workflow_templates(self):
        """Load predefined workflow templates"""
        # Emergency response workflow
        self.workflow_templates["emergency_response"] = [
            WorkflowStep("assess", "crisis_agent", "emergency_assessment", {}, [], 10, 60),
            WorkflowStep("stabilize", "crisis_agent", "stabilization", {}, ["assess"], 9, 300),
            WorkflowStep("notify", "system", "notification", {}, ["assess"], 8, 30)
        ]
        
        # Treatment planning workflow
        self.workflow_templates["treatment_planning"] = [
            WorkflowStep("analyze", "analytics_agent", "patient_analysis", {}, [], 5, 600),
            WorkflowStep("recommend", "therapy_agent", "treatment_recommendation", {}, ["analyze"], 4, 900),
            WorkflowStep("optimize", "medication_agent", "medication_optimization", {}, ["analyze"], 4, 600),
            WorkflowStep("coordinate", "orchestrator", "plan_coordination", {}, ["recommend", "optimize"], 3, 300)
        ]
        
        self.logger.info("Workflow templates loaded")
    
    async def _setup_agent_discovery(self):
        """Setup agent discovery and registration mechanisms"""
        self.logger.info("Agent discovery mechanisms established")
    
    async def _initialize_decision_algorithms(self):
        """Initialize decision-making algorithms"""
        self.logger.info("Decision algorithms initialized")
    
    async def _start_orchestration_services(self):
        """Start background orchestration services"""
        # Start monitoring tasks
        asyncio.create_task(self._monitor_agent_health())
        asyncio.create_task(self._process_workflow_queue())
        
        self.logger.info("Orchestration services started")
    
    async def _monitor_agent_health(self):
        """Monitor health of registered agents"""
        while True:
            try:
                current_time = time.time()
                
                # Check for stale agents (no heartbeat in 5 minutes)
                for agent_id, registration in self.registered_agents.items():
                    if current_time - registration.last_heartbeat > 300:  # 5 minutes
                        registration.availability = False
                        self.logger.warning(f"Agent {agent_id} marked as unavailable (stale heartbeat)")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Agent health monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _process_workflow_queue(self):
        """Process workflow queue continuously"""
        while True:
            try:
                # Get workflow from queue (would use asyncio.PriorityQueue in practice)
                await asyncio.sleep(1)  # Simplified processing
                
            except Exception as e:
                self.logger.error(f"Workflow queue processing error: {e}")
                await asyncio.sleep(1)
    
    # Orchestration needs assessment
    async def _assess_orchestration_needs(self, patient_context: PatientContext) -> Dict[str, Any]:
        """Assess if patient requires orchestration"""
        # Simplified orchestration needs assessment
        return {
            "required": True,  # Always require orchestration for demo
            "priority": "normal",
            "coordination_type": "treatment_optimization"
        }
    
    async def _initiate_patient_orchestration(self, patient_id: str, needs: Dict[str, Any]):
        """Initiate orchestration for specific patient"""
        coordination_type = needs.get("coordination_type", "general")
        
        # Create orchestration workflow for patient
        patient_workflow = await self._create_patient_orchestration_workflow(patient_id, coordination_type)
        
        # Execute workflow
        await self._execute_workflow(patient_workflow)
    
    async def _create_patient_orchestration_workflow(self, patient_id: str, 
                                                   coordination_type: str) -> List[WorkflowStep]:
        """Create patient-specific orchestration workflow"""
        workflow_steps = []
        
        if coordination_type == "treatment_optimization":
            workflow_steps = [
                WorkflowStep(f"assess_{patient_id}", "analytics_agent", "patient_assessment", 
                           {"patient_id": patient_id}, [], 5, 300),
                WorkflowStep(f"optimize_{patient_id}", "therapy_agent", "treatment_optimization", 
                           {"patient_id": patient_id}, [f"assess_{patient_id}"], 4, 600)
            ]
        
        return workflow_steps
