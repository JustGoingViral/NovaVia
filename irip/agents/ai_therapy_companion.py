"""
AI Therapy Companion Agent
LLM-based therapeutic dialogue with validated CBT/DBT frameworks

Implements evidence-based conversational therapy with proper therapeutic
boundaries and crisis detection.

References:
- Fitzpatrick et al. (2017). Delivering Cognitive Behavior Therapy to Young 
  Adults With Symptoms of Depression and Anxiety Using a Fully Automated 
  Conversational Agent (Woebot). JMIR Mental Health, 4(2), e19. [PMID: 28588005]
- Inkster et al. (2018). An Empathy-Driven, Conversational Artificial Intelligence 
  Agent (Wysa) for Digital Mental Well-Being. JMIR mHealth uHealth, 6(11), e12106. [PMID: 30470676]
- Abd-Alrazaq et al. (2020). Effectiveness and Safety of Using Chatbots to 
  Improve Mental Health: Systematic Review and Meta-Analysis. 
  Journal of Medical Internet Research, 22(7), e16021. [PMID: 32673216]
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re

from .base_agent import (
    BaseAgent, AgentMessage, PatientContext, AgentCapability,
    AgentPriority, AgentState
)

logger = logging.getLogger(__name__)


class TherapyModality(Enum):
    """Evidence-based therapy modalities"""
    CBT = "cognitive_behavioral_therapy"
    DBT = "dialectical_behavior_therapy"
    ACT = "acceptance_commitment_therapy"
    MI = "motivational_interviewing"
    BA = "behavioral_activation"
    MBCT = "mindfulness_based_cognitive_therapy"


class CrisisLevel(Enum):
    """Crisis severity levels"""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    IMMINENT = "imminent"


class ConversationState(Enum):
    """Dialogue state machine states"""
    GREETING = "greeting"
    ASSESSMENT = "assessment"
    PSYCHOEDUCATION = "psychoeducation"
    SKILL_TEACHING = "skill_teaching"
    PRACTICE = "practice"
    REFLECTION = "reflection"
    CLOSING = "closing"
    CRISIS = "crisis"


@dataclass
class TherapeuticResponse:
    """AI companion response"""
    message: str
    modality: TherapyModality
    state: ConversationState
    emotion_detected: Optional[str]
    crisis_level: CrisisLevel
    suggested_skills: List[str]
    follow_up_prompts: List[str]
    should_escalate: bool


@dataclass
class SessionContext:
    """Ongoing session context"""
    session_id: str
    patient_id: str
    start_time: datetime
    current_state: ConversationState
    modality: TherapyModality
    messages: List[Dict[str, str]]
    skills_practiced: List[str]
    mood_trajectory: List[int]  # 1-10 scale over session
    crisis_flags: List[str]


class AITherapyCompanionAgent(BaseAgent):
    """
    AI Therapy Companion for CBT/DBT dialogue
    
    Provides evidence-based conversational support with:
    - CBT cognitive restructuring techniques
    - DBT distress tolerance skills (TIPP, ACCEPTS)
    - Mindfulness exercises
    - Behavioral activation suggestions
    - Crisis detection and escalation
    
    Based on validated chatbot research (Fitzpatrick et al., 2017)
    showing non-inferiority to waitlist controls for mild-moderate symptoms.
    
    IMPORTANT: Not a replacement for professional care. Designed for
    adjunct support between therapy sessions.
    """
    
    # Crisis keywords for detection
    CRISIS_KEYWORDS = [
        'suicide', 'kill myself', 'end my life', 'want to die',
        'hurt myself', 'self-harm', 'cutting', 'overdose',
        'no reason to live', 'better off dead', 'no hope'
    ]
    
    # DBT skills library
    DBT_SKILLS = {
        'distress_tolerance': [
            'TIPP (Temperature, Intense exercise, Paced breathing, Progressive relaxation)',
            'ACCEPTS (Activities, Contributing, Comparisons, Emotions, Push away, Thoughts, Sensations)',
            'IMPROVE (Imagery, Meaning, Prayer, Relaxation, One thing, Vacation, Encouragement)',
            'Radical Acceptance',
            'Distraction with ACCEPTS'
        ],
        'emotion_regulation': [
            'Check the Facts',
            'Opposite Action',
            'PLEASE skills (treat PhysicaL illness, Eat balanced, Avoid drugs, Sleep well, Exercise)',
            'Build Mastery',
            'Accumulate Positive Experiences'
        ],
        'interpersonal_effectiveness': [
            'DEAR MAN (Describe, Express, Assert, Reinforce, Mindful, Appear confident, Negotiate)',
            'GIVE (Gentle, Interested, Validate, Easy manner)',
            'FAST (Fair, no Apologies, Stick to values, Truthful)'
        ],
        'mindfulness': [
            'Observe without judgment',
            'Describe with words',
            'Participate fully',
            'One-mindfully',
            'Non-judgmentally',
            'Effectively'
        ]
    }
    
    # CBT techniques
    CBT_TECHNIQUES = {
        'cognitive_restructuring': [
            'Identify automatic thoughts',
            'Examine evidence for/against',
            'Identify cognitive distortions',
            'Generate alternative thoughts',
            'Behavioral experiments'
        ],
        'behavioral_activation': [
            'Activity scheduling',
            'Pleasure-mastery activities',
            'Graded task assignment',
            'Problem-solving',
            'Values clarification'
        ]
    }
    
    def __init__(self, agent_id: str = "ai_therapy_companion"):
        super().__init__(
            agent_id=agent_id,
            capabilities=[
                AgentCapability.PATIENT_COMMUNICATION,
                AgentCapability.THERAPY_COORDINATION,
                AgentCapability.CRISIS_INTERVENTION
            ]
        )
        
        self.active_sessions: Dict[str, SessionContext] = {}
        
        # Response templates (in production, would use fine-tuned LLM)
        self._init_response_templates()
    
    def _init_response_templates(self):
        """Initialize therapeutic response templates"""
        self.templates = {
            'greeting': [
                "Hello! I'm here to support you between therapy sessions. How are you feeling today?",
                "Welcome back. It's good to see you. What's on your mind?",
                "Hi there. I'm glad you reached out. How can I support you right now?"
            ],
            'validation': [
                "It sounds like you're going through a really difficult time. That makes sense given what you've shared.",
                "Your feelings are valid. Many people would feel the same way in your situation.",
                "Thank you for sharing that with me. I can hear how hard this has been for you."
            ],
            'dbt_tipp': [
                "When emotions feel overwhelming, try the TIPP skill: Temperature (hold ice or splash cold water), "
                "Intense exercise for a few minutes, Paced breathing (slow exhale), or Progressive muscle relaxation.",
                "One thing that can help in intense moments is the Temperature skill - holding an ice cube or "
                "splashing cold water on your face activates the dive reflex and can calm your nervous system quickly."
            ],
            'cbt_thoughts': [
                "Let's examine that thought together. What evidence do you have that supports this thought? "
                "What evidence might go against it?",
                "I noticed you said '{}'. That sounds like it might be an all-or-nothing thought. "
                "Are there any shades of gray we might be missing?"
            ],
            'crisis_response': [
                "I'm concerned about what you've shared. Your safety is the priority right now. "
                "Please contact your therapist, call 988 (Suicide & Crisis Lifeline), "
                "or go to your nearest emergency room.",
                "What you're describing sounds serious, and I want to make sure you get the right support. "
                "Is there someone you can call right now? Your therapist, a crisis line (988), or a trusted person?"
            ],
            'closing': [
                "Great work today practicing these skills. Remember, you can use them anytime. "
                "What's one thing you'll try before our next check-in?",
                "Thank you for spending this time with me. You're building important skills. "
                "Take good care of yourself, and I'm here whenever you need support."
            ]
        }
    
    async def initialize(self):
        """Initialize agent"""
        await super().initialize()
        logger.info(f"{self.agent_id} initialized with CBT/DBT frameworks")
    
    def _detect_crisis(self, user_input: str) -> CrisisLevel:
        """
        Detect crisis indicators in user input
        
        Uses keyword matching and pattern analysis
        """
        input_lower = user_input.lower()
        
        # Check for crisis keywords
        for keyword in self.CRISIS_KEYWORDS:
            if keyword in input_lower:
                # Check for active suicidal ideation
                if any(active in input_lower for active in ['want to', 'going to', 'plan to', 'will']):
                    return CrisisLevel.HIGH
                return CrisisLevel.MODERATE
        
        # Check for distress indicators
        distress_words = ['hopeless', 'worthless', 'can\'t go on', 'giving up', 'alone']
        distress_count = sum(1 for word in distress_words if word in input_lower)
        
        if distress_count >= 3:
            return CrisisLevel.MODERATE
        elif distress_count >= 1:
            return CrisisLevel.LOW
        
        return CrisisLevel.NONE
    
    def _detect_emotion(self, user_input: str) -> Optional[str]:
        """Simple emotion detection from text"""
        input_lower = user_input.lower()
        
        emotion_keywords = {
            'anxious': ['anxious', 'worried', 'nervous', 'scared', 'afraid', 'panic'],
            'depressed': ['depressed', 'sad', 'down', 'empty', 'numb', 'hopeless'],
            'angry': ['angry', 'frustrated', 'irritated', 'mad', 'furious'],
            'overwhelmed': ['overwhelmed', 'stressed', 'too much', 'can\'t cope'],
            'lonely': ['lonely', 'isolated', 'alone', 'disconnected'],
            'happy': ['happy', 'good', 'great', 'better', 'hopeful', 'positive']
        }
        
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                return emotion
        
        return None
    
    def generate_response(self, user_input: str, 
                         modality: TherapyModality = TherapyModality.DBT,
                         session_context: Optional[SessionContext] = None) -> str:
        """
        Generate therapeutic response to user input
        
        Args:
            user_input: User's message
            modality: Therapy modality (CBT, DBT, etc.)
            session_context: Ongoing session context
        
        Returns:
            str: Therapeutic response
        
        Example:
            >>> response = agent.generate_response(
            ...     "I'm feeling really anxious about tomorrow",
            ...     modality=TherapyModality.DBT
            ... )
            >>> print(response)
            "I hear that you're feeling anxious about tomorrow..."
        """
        # Check for crisis first
        crisis_level = self._detect_crisis(user_input)
        
        if crisis_level in [CrisisLevel.HIGH, CrisisLevel.IMMINENT]:
            return np.random.choice(self.templates['crisis_response'])
        
        # Detect emotion
        emotion = self._detect_emotion(user_input)
        
        # Build response based on modality and context
        response_parts = []
        
        # Validation first (per DBT principles)
        if emotion:
            response_parts.append(f"I hear that you're feeling {emotion}.")
        
        response_parts.append(np.random.choice(self.templates['validation']))
        
        # Add modality-specific intervention
        if modality == TherapyModality.DBT:
            if emotion in ['anxious', 'overwhelmed', 'angry']:
                # Suggest distress tolerance
                response_parts.append(np.random.choice(self.templates['dbt_tipp']))
            elif emotion == 'depressed':
                # Suggest opposite action or behavioral activation
                response_parts.append(
                    "One DBT skill that might help is Opposite Action - when you feel like withdrawing, "
                    "doing the opposite (like texting a friend or going for a walk) can shift your mood."
                )
        
        elif modality == TherapyModality.CBT:
            # Cognitive restructuring
            if 'always' in user_input.lower() or 'never' in user_input.lower():
                response_parts.append(self.templates['cbt_thoughts'][1].format(
                    self._extract_thought(user_input)
                ))
            else:
                response_parts.append(self.templates['cbt_thoughts'][0])
        
        # Add a follow-up question
        response_parts.append("What do you think might help you feel a bit better right now?")
        
        return " ".join(response_parts)
    
    def _extract_thought(self, text: str) -> str:
        """Extract the key automatic thought from user input"""
        # Simple extraction - take first sentence or phrase
        sentences = text.split('.')
        if sentences:
            return sentences[0][:50] + "..." if len(sentences[0]) > 50 else sentences[0]
        return text[:50]
    
    async def create_session(self, patient_id: str,
                            modality: TherapyModality = TherapyModality.DBT) -> SessionContext:
        """Create a new therapy session"""
        session_id = f"therapy_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = SessionContext(
            session_id=session_id,
            patient_id=patient_id,
            start_time=datetime.now(),
            current_state=ConversationState.GREETING,
            modality=modality,
            messages=[],
            skills_practiced=[],
            mood_trajectory=[],
            crisis_flags=[]
        )
        
        self.active_sessions[session_id] = session
        
        return session
    
    async def process_user_message(self, session_id: str,
                                  user_input: str) -> TherapeuticResponse:
        """
        Process a user message in an active session
        
        Args:
            session_id: Active session ID
            user_input: User's message
        
        Returns:
            TherapeuticResponse with message and metadata
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        
        # Add user message to history
        session.messages.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat()
        })
        
        # Detect crisis level
        crisis_level = self._detect_crisis(user_input)
        
        if crisis_level in [CrisisLevel.HIGH, CrisisLevel.IMMINENT]:
            session.current_state = ConversationState.CRISIS
            session.crisis_flags.append(user_input[:50])
        
        # Detect emotion
        emotion = self._detect_emotion(user_input)
        
        # Generate response
        response_text = self.generate_response(
            user_input, 
            session.modality,
            session
        )
        
        # Add response to history
        session.messages.append({
            'role': 'assistant',
            'content': response_text,
            'timestamp': datetime.now().isoformat()
        })
        
        # Suggest relevant skills
        suggested_skills = self._suggest_skills(emotion, session.modality)
        
        # Follow-up prompts
        follow_ups = [
            "Would you like to practice a skill together?",
            "Tell me more about what's happening for you.",
            "What has helped you cope with similar feelings before?"
        ]
        
        return TherapeuticResponse(
            message=response_text,
            modality=session.modality,
            state=session.current_state,
            emotion_detected=emotion,
            crisis_level=crisis_level,
            suggested_skills=suggested_skills,
            follow_up_prompts=follow_ups,
            should_escalate=crisis_level in [CrisisLevel.HIGH, CrisisLevel.IMMINENT]
        )
    
    def _suggest_skills(self, emotion: Optional[str],
                       modality: TherapyModality) -> List[str]:
        """Suggest relevant skills based on emotion and modality"""
        skills = []
        
        if modality == TherapyModality.DBT:
            if emotion in ['anxious', 'overwhelmed', 'angry']:
                skills.extend(self.DBT_SKILLS['distress_tolerance'][:2])
            elif emotion == 'depressed':
                skills.extend(self.DBT_SKILLS['emotion_regulation'][:2])
            elif emotion == 'lonely':
                skills.extend(self.DBT_SKILLS['interpersonal_effectiveness'][:2])
            else:
                skills.extend(self.DBT_SKILLS['mindfulness'][:2])
        
        elif modality == TherapyModality.CBT:
            skills.extend(self.CBT_TECHNIQUES['cognitive_restructuring'][:2])
            if emotion in ['depressed', 'empty']:
                skills.extend(self.CBT_TECHNIQUES['behavioral_activation'][:2])
        
        return skills
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a therapy session and return summary"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions.pop(session_id)
        
        duration_minutes = (datetime.now() - session.start_time).total_seconds() / 60
        
        summary = {
            'session_id': session_id,
            'patient_id': session.patient_id,
            'duration_minutes': round(duration_minutes, 1),
            'modality': session.modality.value,
            'message_count': len(session.messages),
            'skills_practiced': session.skills_practiced,
            'crisis_flags': session.crisis_flags,
            'had_crisis': len(session.crisis_flags) > 0,
            'closing_message': np.random.choice(self.templates['closing'])
        }
        
        return summary
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages from other agents"""
        if message.message_type == "therapy_request":
            patient_id = message.content['patient_id']
            user_input = message.content['message']
            modality = TherapyModality(message.content.get('modality', 'dbt'))
            
            # Create or get session
            session_id = message.content.get('session_id')
            
            if not session_id or session_id not in self.active_sessions:
                session = await self.create_session(patient_id, modality)
                session_id = session.session_id
            
            # Process message
            response = await self.process_user_message(session_id, user_input)
            
            return AgentMessage(
                message_id=f"msg_{datetime.now().timestamp()}",
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="therapy_response",
                content={
                    'session_id': session_id,
                    'response': response.message,
                    'emotion': response.emotion_detected,
                    'crisis_level': response.crisis_level.value,
                    'should_escalate': response.should_escalate,
                    'suggested_skills': response.suggested_skills
                },
                priority=AgentPriority.HIGH if response.should_escalate else AgentPriority.NORMAL,
                timestamp=datetime.now().timestamp(),
                correlation_id=message.message_id
            )
        
        return None


def simulate_therapy_session(n_exchanges: int = 5) -> List[Dict[str, str]]:
    """
    Simulate a therapy session for testing
    
    Returns list of user/assistant message pairs
    """
    user_messages = [
        "I've been feeling really anxious about work lately.",
        "Yeah, I keep thinking I'm going to fail at everything.",
        "It's like nothing I do is ever good enough.",
        "I guess I do have some good days too.",
        "That's helpful. I'll try the TIPP skill next time."
    ]
    
    agent = AITherapyCompanionAgent()
    agent._init_response_templates()
    
    exchanges = []
    for i, user_msg in enumerate(user_messages[:n_exchanges]):
        response = agent.generate_response(user_msg, TherapyModality.DBT)
        exchanges.append({
            'user': user_msg,
            'assistant': response
        })
    
    return exchanges
