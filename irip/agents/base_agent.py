"""
IRIP Base Agent Framework
Abstract base class for all AI agents in the Integrated Recovery Intelligence Platform
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json


class AgentState(Enum):
    """Agent operational state"""
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class AgentCapability(Enum):
    """Agent capability enumeration"""
    CRISIS_INTERVENTION = "crisis_intervention"
    MEDICATION_MANAGEMENT = "medication_management"
    THERAPY_COORDINATION = "therapy_coordination"
    BIOHACKING_INTEGRATION = "biohacking_integration"
    ANALYTICS_PROCESSING = "analytics_processing"
    REAL_TIME_MONITORING = "real_time_monitoring"
    PATIENT_COMMUNICATION = "patient_communication"
    TREATMENT_OPTIMIZATION = "treatment_optimization"
    EMERGENCY_RESPONSE = "emergency_response"
    DATA_ANALYSIS = "data_analysis"
    # Phase 2 capabilities for orchestration and advanced agents
    TREATMENT_ORCHESTRATION = "treatment_orchestration"
    EMERGENCY_COORDINATION = "emergency_coordination"
    RESOURCE_MANAGEMENT = "resource_management"
    DECISION_OPTIMIZATION = "decision_optimization"
    WORKFLOW_MANAGEMENT = "workflow_management"
    PREDICTIVE_MODELING = "predictive_modeling"
    TREATMENT_COORDINATION = "treatment_coordination"


class AgentPriority(Enum):
    """Agent priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class AgentMessage:
    """Message structure for inter-agent communication"""
    message_id: str
    sender_id: str
    recipient_id: str
    message_type: str
    content: Dict[str, Any]
    priority: AgentPriority
    timestamp: float
    requires_response: bool = False
    correlation_id: Optional[str] = None


@dataclass
class PatientContext:
    """Patient context information for agents"""
    patient_id: str
    addiction_type: str  # opioid, alcohol, stimulant, etc.
    treatment_phase: str  # detox, stabilization, maintenance, recovery
    severity_score: float  # 0.0 to 1.0
    medications: List[Dict[str, Any]]
    biohacking_protocols: List[str]
    crisis_risk_level: str  # low, moderate, high, critical
    support_network: Dict[str, Any]
    treatment_history: List[Dict[str, Any]]
    current_vitals: Optional[Dict[str, Any]] = None


@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    agent_id: str
    timestamp: float
    state: AgentState
    active_tasks: int
    completed_tasks: int
    response_time_ms: float
    success_rate: float
    error_count: int
    uptime_seconds: float


class BaseAgent(ABC):
    """
    Abstract base class for all IRIP AI agents
    
    Provides common functionality for:
    - Inter-agent communication
    - Patient context management
    - Task prioritization
    - Performance monitoring
    - Emergency protocols
    """
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None, 
                 capabilities: Optional[List[AgentCapability]] = None):
        self.agent_id = agent_id
        self.config = config if config is not None else {}
        self.logger = logging.getLogger(f"{__name__}.{agent_id}")
        
        # Agent properties
        self.agent_type: str = "base_agent"
        self.version: str = "1.0.0"
        self.description: str = "Base IRIP AI Agent"
        
        # State management
        self.state = AgentState.INITIALIZING
        self.start_time = time.time()
        self.last_heartbeat = 0.0
        
        # Capabilities and priorities - support both constructor styles
        self.capabilities: List[AgentCapability] = capabilities if capabilities is not None else []
        self.priority_level = AgentPriority.NORMAL
        
        # Communication
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.response_handlers: Dict[str, Callable] = {}
        self.event_listeners: Dict[str, List[Callable]] = {}
        
        # Task management
        self.active_tasks: List[str] = []
        self.task_history: List[Dict[str, Any]] = []
        self.max_concurrent_tasks = self.config.get("max_concurrent_tasks", 5)
        
        # Patient context
        self.current_patients: Dict[str, PatientContext] = {}
        
        # Performance tracking
        self.metrics_history: List[AgentMetrics] = []
        self.max_metrics_history = 1000
        self.total_tasks_completed = 0
        self.total_errors = 0
        
        # Background tasks
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.message_processor_task: Optional[asyncio.Task] = None
        self.monitoring_task: Optional[asyncio.Task] = None
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the agent and its capabilities"""
        pass
    
    @abstractmethod
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming message and optionally return response"""
        pass
    
    async def handle_patient_update(self, patient_context: PatientContext):
        """Handle updates to patient context - default implementation"""
        self.current_patients[patient_context.patient_id] = patient_context
        self.logger.debug(f"Updated context for patient {patient_context.patient_id}")
    
    async def handle_emergency(self, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency situations - default implementation"""
        self.logger.warning(f"Emergency received but not handled by {self.agent_id}: {emergency_data}")
        return {"handled": False, "agent_id": self.agent_id}
    
    async def start(self) -> bool:
        """Start the agent and its background tasks"""
        try:
            self.logger.info(f"Starting agent {self.agent_id}...")
            
            # Initialize agent
            if not await self.initialize():
                self.logger.error("Agent initialization failed")
                self.state = AgentState.ERROR
                return False
            
            # Start background tasks
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.message_processor_task = asyncio.create_task(self._message_processor_loop())
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            self.state = AgentState.READY
            self.logger.info(f"Agent {self.agent_id} started successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Agent start failed: {e}")
            self.state = AgentState.ERROR
            return False
    
    async def stop(self):
        """Stop the agent and cleanup resources"""
        try:
            self.logger.info(f"Stopping agent {self.agent_id}...")
            
            # Cancel background tasks
            for task in [self.heartbeat_task, self.message_processor_task, self.monitoring_task]:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self.state = AgentState.OFFLINE
            self.logger.info(f"Agent {self.agent_id} stopped")
            
        except Exception as e:
            self.logger.error(f"Agent stop error: {e}")
    
    async def send_message(self, recipient_id: str, message_type: str, content: Dict[str, Any], 
                          priority: AgentPriority = AgentPriority.NORMAL, 
                          requires_response: bool = False) -> str:
        """Send message to another agent"""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            priority=priority,
            timestamp=time.time(),
            requires_response=requires_response
        )
        
        # In a real implementation, this would go through the message broker
        # For now, we'll just log it
        self.logger.info(f"Sending message {message_type} to {recipient_id}")
        
        return message.message_id
    
    async def receive_message(self, message: AgentMessage):
        """Receive message from another agent"""
        await self.message_queue.put(message)
    
    async def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast event to registered listeners"""
        listeners = self.event_listeners.get(event_type, [])
        for listener in listeners:
            try:
                await listener(data)
            except Exception as e:
                self.logger.error(f"Event listener error: {e}")
    
    def add_event_listener(self, event_type: str, callback: Callable):
        """Add event listener"""
        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        self.event_listeners[event_type].append(callback)
    
    def remove_event_listener(self, event_type: str, callback: Callable):
        """Remove event listener"""
        if event_type in self.event_listeners:
            try:
                self.event_listeners[event_type].remove(callback)
            except ValueError:
                pass
    
    async def add_patient_context(self, patient_context: PatientContext):
        """Add or update patient context"""
        self.current_patients[patient_context.patient_id] = patient_context
        await self.handle_patient_update(patient_context)
        
        self.logger.info(f"Updated context for patient {patient_context.patient_id}")
    
    def get_patient_context(self, patient_id: str) -> Optional[PatientContext]:
        """Get patient context"""
        return self.current_patients.get(patient_id)
    
    async def start_task(self, task_id: str, task_data: Dict[str, Any]) -> bool:
        """Start a new task"""
        if len(self.active_tasks) >= self.max_concurrent_tasks:
            self.logger.warning(f"Task queue full, rejecting task {task_id}")
            return False
        
        self.active_tasks.append(task_id)
        self.state = AgentState.ACTIVE
        
        # Record task start
        task_record = {
            "task_id": task_id,
            "start_time": time.time(),
            "task_data": task_data,
            "status": "active"
        }
        self.task_history.append(task_record)
        
        self.logger.info(f"Started task {task_id}")
        return True
    
    async def complete_task(self, task_id: str, result: Dict[str, Any]):
        """Complete a task"""
        if task_id in self.active_tasks:
            self.active_tasks.remove(task_id)
            self.total_tasks_completed += 1
            
            # Update task record
            for task_record in self.task_history:
                if task_record["task_id"] == task_id:
                    task_record["end_time"] = time.time()
                    task_record["duration"] = task_record["end_time"] - task_record["start_time"]
                    task_record["status"] = "completed"
                    task_record["result"] = result
                    break
            
            # Update state
            if not self.active_tasks:
                self.state = AgentState.READY
            
            self.logger.info(f"Completed task {task_id}")
    
    async def fail_task(self, task_id: str, error: str):
        """Mark task as failed"""
        if task_id in self.active_tasks:
            self.active_tasks.remove(task_id)
            self.total_errors += 1
            
            # Update task record
            for task_record in self.task_history:
                if task_record["task_id"] == task_id:
                    task_record["end_time"] = time.time()
                    task_record["duration"] = task_record["end_time"] - task_record["start_time"]
                    task_record["status"] = "failed"
                    task_record["error"] = error
                    break
            
            # Update state
            if not self.active_tasks:
                self.state = AgentState.READY
            
            self.logger.error(f"Failed task {task_id}: {error}")
    
    async def get_metrics(self) -> AgentMetrics:
        """Get current agent metrics"""
        response_times = [
            task["duration"] * 1000 for task in self.task_history 
            if task.get("status") == "completed" and "duration" in task
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        success_rate = 0.0
        if self.total_tasks_completed + self.total_errors > 0:
            success_rate = self.total_tasks_completed / (self.total_tasks_completed + self.total_errors)
        
        return AgentMetrics(
            agent_id=self.agent_id,
            timestamp=time.time(),
            state=self.state,
            active_tasks=len(self.active_tasks),
            completed_tasks=self.total_tasks_completed,
            response_time_ms=avg_response_time,
            success_rate=success_rate,
            error_count=self.total_errors,
            uptime_seconds=time.time() - self.start_time
        )
    
    async def _heartbeat_loop(self):
        """Background heartbeat loop"""
        while True:
            try:
                self.last_heartbeat = time.time()
                
                # Collect and store metrics
                metrics = await self.get_metrics()
                self.metrics_history.append(metrics)
                
                # Trim metrics history
                if len(self.metrics_history) > self.max_metrics_history:
                    self.metrics_history = self.metrics_history[-self.max_metrics_history//2:]
                
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(60)
    
    async def _message_processor_loop(self):
        """Background message processing loop"""
        while True:
            try:
                # Get message from queue (with timeout to avoid blocking)
                try:
                    message = await asyncio.wait_for(self.message_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                
                # Process message
                start_time = time.time()
                response = await self.process_message(message)
                processing_time = time.time() - start_time
                
                self.logger.debug(f"Processed message {message.message_type} in {processing_time:.3f}s")
                
                # Send response if required
                if response and message.requires_response:
                    await self.send_message(
                        recipient_id=message.sender_id,
                        message_type=f"{message.message_type}_response",
                        content=response.content,
                        priority=message.priority
                    )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Message processing error: {e}")
                await asyncio.sleep(1)
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                # Check for stuck tasks
                current_time = time.time()
                stuck_tasks = []
                
                for task_record in self.task_history:
                    if (task_record.get("status") == "active" and 
                        current_time - task_record["start_time"] > 300):  # 5 minutes
                        stuck_tasks.append(task_record["task_id"])
                
                for task_id in stuck_tasks:
                    self.logger.warning(f"Task {task_id} appears stuck, marking as failed")
                    await self.fail_task(task_id, "Task timeout")
                
                # Check agent health
                if self.state == AgentState.ERROR:
                    self.logger.warning("Agent in error state, attempting recovery")
                    # Could implement recovery logic here
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(120)
    
    def get_capabilities(self) -> List[str]:
        """Get list of agent capabilities"""
        return [cap.value for cap in self.capabilities]
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status summary"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "state": self.state.value,
            "capabilities": self.get_capabilities(),
            "active_tasks": len(self.active_tasks),
            "total_completed": self.total_tasks_completed,
            "total_errors": self.total_errors,
            "uptime": time.time() - self.start_time,
            "current_patients": len(self.current_patients),
            "last_heartbeat": self.last_heartbeat
        }
    
    def __str__(self) -> str:
        return f"{self.agent_type}[{self.agent_id}]({self.state.value})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.agent_id} {self.state.value}>"
