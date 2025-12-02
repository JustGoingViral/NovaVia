"""
Phase 2 Tests: AI Therapy Companion Agent

Tests for CBT/DBT dialogue, crisis detection, and session management.
"""

import pytest
import numpy as np
import asyncio
from datetime import datetime

try:
    from irip.agents.ai_therapy_companion import (
        AITherapyCompanionAgent,
        TherapyModality,
        CrisisLevel,
        ConversationState,
        TherapeuticResponse,
        SessionContext,
        simulate_therapy_session
    )
    THERAPY_AVAILABLE = True
except ImportError:
    THERAPY_AVAILABLE = False


@pytest.mark.skipif(not THERAPY_AVAILABLE, reason="AI Therapy module not available")
class TestAITherapyCompanionAgent:
    """Test suite for AI Therapy Companion Agent"""
    
    @pytest.fixture
    async def agent(self):
        """Create agent instance"""
        agent = AITherapyCompanionAgent()
        await agent.initialize()
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initializes with CBT/DBT frameworks"""
        assert agent.agent_id == "ai_therapy_companion"
        assert len(agent.DBT_SKILLS) > 0
        assert len(agent.CBT_TECHNIQUES) > 0
        assert len(agent.templates) > 0
    
    def test_generate_response_dbt(self, agent):
        """Test DBT response generation"""
        response = agent.generate_response(
            "I'm feeling really anxious about tomorrow",
            modality=TherapyModality.DBT
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
        
        # Should mention anxiety/feeling
        response_lower = response.lower()
        assert 'anxious' in response_lower or 'feeling' in response_lower
    
    def test_generate_response_cbt(self, agent):
        """Test CBT response generation"""
        response = agent.generate_response(
            "I always fail at everything I try",
            modality=TherapyModality.CBT
        )
        
        assert isinstance(response, str)
        
        # CBT response should address cognitive distortion
        # (all-or-nothing thinking with "always")
        response_lower = response.lower()
        # Should have some therapeutic content
        assert len(response) > 50
    
    def test_crisis_detection_high(self, agent):
        """Test high-level crisis detection"""
        crisis_input = "I want to kill myself, I have a plan"
        
        level = agent._detect_crisis(crisis_input)
        
        assert level in [CrisisLevel.HIGH, CrisisLevel.IMMINENT]
    
    def test_crisis_detection_moderate(self, agent):
        """Test moderate crisis detection"""
        distress_input = "I feel like I want to die, everything is hopeless"
        
        level = agent._detect_crisis(distress_input)
        
        assert level in [CrisisLevel.MODERATE, CrisisLevel.HIGH]
    
    def test_crisis_detection_none(self, agent):
        """Test no crisis detection for normal input"""
        normal_input = "I had a stressful day at work"
        
        level = agent._detect_crisis(normal_input)
        
        assert level in [CrisisLevel.NONE, CrisisLevel.LOW]
    
    def test_crisis_response(self, agent):
        """Test that crisis input triggers safety response"""
        response = agent.generate_response(
            "I want to hurt myself",
            modality=TherapyModality.DBT
        )
        
        # Should include crisis resources
        response_lower = response.lower()
        assert '988' in response or 'crisis' in response_lower or 'emergency' in response_lower
    
    def test_emotion_detection_anxious(self, agent):
        """Test anxious emotion detection"""
        emotion = agent._detect_emotion("I'm so worried and nervous about everything")
        assert emotion == 'anxious'
    
    def test_emotion_detection_depressed(self, agent):
        """Test depressed emotion detection"""
        emotion = agent._detect_emotion("I feel so sad and empty inside")
        assert emotion == 'depressed'
    
    def test_emotion_detection_angry(self, agent):
        """Test angry emotion detection"""
        emotion = agent._detect_emotion("I'm so frustrated and angry at everyone")
        assert emotion == 'angry'
    
    def test_emotion_detection_happy(self, agent):
        """Test positive emotion detection"""
        emotion = agent._detect_emotion("I'm feeling much better and hopeful today")
        assert emotion == 'happy'
    
    @pytest.mark.asyncio
    async def test_create_session(self, agent):
        """Test therapy session creation"""
        session = await agent.create_session("patient_001", TherapyModality.DBT)
        
        assert isinstance(session, SessionContext)
        assert session.patient_id == "patient_001"
        assert session.modality == TherapyModality.DBT
        assert session.current_state == ConversationState.GREETING
        assert len(session.messages) == 0
    
    @pytest.mark.asyncio
    async def test_process_user_message(self, agent):
        """Test processing user message in session"""
        session = await agent.create_session("patient_002", TherapyModality.DBT)
        
        response = await agent.process_user_message(
            session.session_id,
            "I've been feeling really overwhelmed lately"
        )
        
        assert isinstance(response, TherapeuticResponse)
        assert len(response.message) > 0
        assert response.modality == TherapyModality.DBT
        assert response.emotion_detected == 'overwhelmed'
        assert len(response.suggested_skills) > 0
    
    @pytest.mark.asyncio
    async def test_session_message_history(self, agent):
        """Test that messages are tracked in session"""
        session = await agent.create_session("patient_003", TherapyModality.DBT)
        
        await agent.process_user_message(session.session_id, "Hello")
        await agent.process_user_message(session.session_id, "I'm anxious")
        
        # Session should have 4 messages (2 user + 2 assistant)
        assert len(agent.active_sessions[session.session_id].messages) == 4
    
    @pytest.mark.asyncio
    async def test_end_session(self, agent):
        """Test session ending and summary"""
        session = await agent.create_session("patient_004", TherapyModality.DBT)
        
        await agent.process_user_message(session.session_id, "I'm feeling better")
        
        summary = await agent.end_session(session.session_id)
        
        assert isinstance(summary, dict)
        assert summary['patient_id'] == "patient_004"
        assert 'duration_minutes' in summary
        assert 'message_count' in summary
        assert 'closing_message' in summary
        
        # Session should be removed
        assert session.session_id not in agent.active_sessions
    
    @pytest.mark.asyncio
    async def test_crisis_escalation(self, agent):
        """Test that crisis triggers escalation flag"""
        session = await agent.create_session("patient_005", TherapyModality.DBT)
        
        response = await agent.process_user_message(
            session.session_id,
            "I want to end my life"
        )
        
        assert response.should_escalate == True
        assert response.crisis_level in [CrisisLevel.HIGH, CrisisLevel.MODERATE]
        
        # Session state should be crisis
        assert agent.active_sessions[session.session_id].current_state == ConversationState.CRISIS
    
    def test_suggest_skills_anxious(self, agent):
        """Test skill suggestions for anxiety"""
        skills = agent._suggest_skills('anxious', TherapyModality.DBT)
        
        assert len(skills) > 0
        
        # Should suggest distress tolerance skills
        skills_lower = ' '.join(skills).lower()
        assert 'tipp' in skills_lower or 'distraction' in skills_lower or 'accepts' in skills_lower
    
    def test_suggest_skills_depressed(self, agent):
        """Test skill suggestions for depression"""
        skills = agent._suggest_skills('depressed', TherapyModality.DBT)
        
        assert len(skills) > 0
        
        # Should suggest emotion regulation
        skills_lower = ' '.join(skills).lower()
        assert 'emotion' in skills_lower or 'opposite' in skills_lower or 'action' in skills_lower or 'fact' in skills_lower


def test_therapy_modality_enum():
    """Test therapy modality enumeration"""
    assert TherapyModality.CBT.value == "cognitive_behavioral_therapy"
    assert TherapyModality.DBT.value == "dialectical_behavior_therapy"


def test_crisis_level_enum():
    """Test crisis level enumeration"""
    assert CrisisLevel.NONE.value == "none"
    assert CrisisLevel.IMMINENT.value == "imminent"


def test_conversation_state_enum():
    """Test conversation state enumeration"""
    assert ConversationState.GREETING.value == "greeting"
    assert ConversationState.CRISIS.value == "crisis"


def test_simulate_therapy_session():
    """Test therapy session simulation"""
    exchanges = simulate_therapy_session(n_exchanges=3)
    
    assert len(exchanges) == 3
    
    for exchange in exchanges:
        assert 'user' in exchange
        assert 'assistant' in exchange
        assert len(exchange['assistant']) > 0


def test_dbt_skills_library():
    """Test DBT skills are defined"""
    from irip.agents.ai_therapy_companion import AITherapyCompanionAgent
    
    agent = AITherapyCompanionAgent()
    
    assert 'distress_tolerance' in agent.DBT_SKILLS
    assert 'emotion_regulation' in agent.DBT_SKILLS
    assert 'interpersonal_effectiveness' in agent.DBT_SKILLS
    assert 'mindfulness' in agent.DBT_SKILLS
    
    # Should have multiple skills per category
    for category, skills in agent.DBT_SKILLS.items():
        assert len(skills) >= 3, f"{category} should have at least 3 skills"


def test_cbt_techniques_library():
    """Test CBT techniques are defined"""
    from irip.agents.ai_therapy_companion import AITherapyCompanionAgent
    
    agent = AITherapyCompanionAgent()
    
    assert 'cognitive_restructuring' in agent.CBT_TECHNIQUES
    assert 'behavioral_activation' in agent.CBT_TECHNIQUES
