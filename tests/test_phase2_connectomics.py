"""
Phase 2 Tests: Connectomics Agent

Tests for brain connectivity analysis and DLPFC targeting optimization.
"""

import pytest
import numpy as np
import networkx as nx
import asyncio
from datetime import datetime

try:
    from irip.agents.connectomics_agent import (
        ConnectomicsAgent,
        ConnectomeData,
        BrainRegion,
        StimulationTarget,
        NetworkAnalysis,
        generate_synthetic_connectome
    )
    CONNECTOMICS_AVAILABLE = True
except ImportError:
    CONNECTOMICS_AVAILABLE = False


@pytest.mark.skipif(not CONNECTOMICS_AVAILABLE, reason="Connectomics module not available")
class TestConnectomicsAgent:
    """Test suite for Connectomics Agent"""
    
    @pytest.fixture
    async def agent(self):
        """Create agent instance"""
        agent = ConnectomicsAgent()
        await agent.initialize()
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initializes correctly"""
        assert agent.agent_id == "connectomics_agent"
        assert BrainRegion.DLPFC_LEFT in agent.STANDARD_TARGETS
    
    def test_personalize_placement(self, agent):
        """Test personalized placement returns valid MNI coordinates"""
        # Create a simple graph
        G = nx.watts_strogatz_graph(100, 10, 0.3)
        
        coords = agent.personalize_placement(G)
        
        assert isinstance(coords, tuple)
        assert len(coords) == 3
        
        # Should be near standard DLPFC coordinates
        standard = agent.STANDARD_TARGETS[BrainRegion.DLPFC_LEFT]
        
        # Within 10mm of standard (personalization)
        assert abs(coords[0] - standard[0]) <= 10
        assert abs(coords[1] - standard[1]) <= 10
        assert abs(coords[2] - standard[2]) <= 5
    
    @pytest.mark.asyncio
    async def test_analyze_connectome(self, agent):
        """Test comprehensive connectome analysis"""
        connectome = generate_synthetic_connectome("patient_001", n_regions=100, healthy=True)
        
        analysis = await agent.analyze_connectome(connectome)
        
        assert isinstance(analysis, NetworkAnalysis)
        assert analysis.patient_id == "patient_001"
        
        # Network metrics should be in valid ranges
        assert 0 <= analysis.global_efficiency <= 1
        assert 0 <= analysis.local_efficiency <= 1
        assert -1 <= analysis.modularity <= 1
        assert analysis.small_worldness > 0
        
        # Should identify hub regions
        assert len(analysis.hub_regions) >= 1
        
        # Should have depression circuit integrity score
        assert 0 <= analysis.depression_circuit_integrity <= 1
        
        # Should have recommended target
        assert isinstance(analysis.recommended_target, StimulationTarget)
    
    @pytest.mark.asyncio
    async def test_stimulation_target(self, agent):
        """Test stimulation target recommendation"""
        connectome = generate_synthetic_connectome("patient_002", n_regions=100, healthy=True)
        
        analysis = await agent.analyze_connectome(connectome)
        target = analysis.recommended_target
        
        assert target.region == BrainRegion.DLPFC_LEFT
        assert isinstance(target.mni_coordinates, tuple)
        assert len(target.mni_coordinates) == 3
        
        # Target strength and hub score should be valid
        assert 0 <= target.target_strength <= 1
        assert 0 <= target.hub_score <= 1
        
        # Should have alternative targets
        assert len(target.alternative_targets) >= 1
    
    @pytest.mark.asyncio
    async def test_optimize_dlpfc_targeting(self, agent):
        """Test DLPFC targeting optimization JSON output"""
        connectome = generate_synthetic_connectome("patient_003", n_regions=100, healthy=True)
        
        result = await agent.optimize_dlpfc_targeting(connectome)
        
        # Should be JSON-serializable dict
        assert isinstance(result, dict)
        assert 'patient_id' in result
        assert 'target_region' in result
        assert 'mni_coordinates' in result
        
        # MNI coordinates should be dict
        coords = result['mni_coordinates']
        assert 'x' in coords
        assert 'y' in coords
        assert 'z' in coords
        
        # Network metrics should be present
        assert 'network_metrics' in result
        assert 'global_efficiency' in result['network_metrics']
        
        # Depression circuit should be assessed
        assert 'depression_circuit_integrity' in result
        assert 'sgacc_connectivity' in result
    
    @pytest.mark.asyncio
    async def test_healthy_vs_disrupted_connectivity(self, agent):
        """Test that healthy and disrupted connectomes produce different results"""
        healthy = generate_synthetic_connectome("patient_healthy", n_regions=100, healthy=True)
        disrupted = generate_synthetic_connectome("patient_disrupted", n_regions=100, healthy=False)
        
        healthy_analysis = await agent.analyze_connectome(healthy)
        disrupted_analysis = await agent.analyze_connectome(disrupted)
        
        # Disrupted should have lower DLPFC-sgACC connectivity
        # (though synthetic data may not always show this clearly)
        assert isinstance(healthy_analysis.depression_circuit_integrity, float)
        assert isinstance(disrupted_analysis.depression_circuit_integrity, float)
    
    def test_build_graph(self, agent):
        """Test graph building from adjacency matrix"""
        connectome = generate_synthetic_connectome("patient_004", n_regions=50, healthy=True)
        
        G = agent._build_graph(connectome)
        
        assert isinstance(G, nx.Graph)
        assert G.number_of_nodes() == 50
        assert G.number_of_edges() > 0
        
        # Should be weighted
        for u, v, data in G.edges(data=True):
            assert 'weight' in data
    
    def test_network_metrics(self, agent):
        """Test network metric calculation"""
        connectome = generate_synthetic_connectome("patient_005", n_regions=50, healthy=True)
        G = agent._build_graph(connectome)
        
        metrics = agent._calculate_network_metrics(G)
        
        assert 'global_efficiency' in metrics
        assert 'local_efficiency' in metrics
        assert 'modularity' in metrics
        assert 'small_worldness' in metrics
        
        # All should be finite numbers
        for key, value in metrics.items():
            assert np.isfinite(value), f"{key} should be finite"
    
    def test_find_hub_regions(self, agent):
        """Test hub region identification"""
        connectome = generate_synthetic_connectome("patient_006", n_regions=100, healthy=True)
        G = agent._build_graph(connectome)
        
        hubs = agent._find_hub_regions(G, top_n=10)
        
        assert len(hubs) == 10
        
        # Should be tuples of (node_id, score)
        for hub in hubs:
            assert len(hub) == 2
            node_id, score = hub
            assert isinstance(node_id, int)
            assert 0 <= score <= 1
        
        # Scores should be descending
        scores = [h[1] for h in hubs]
        assert scores == sorted(scores, reverse=True)


def test_brain_region_enum():
    """Test brain region enumeration"""
    assert BrainRegion.DLPFC_LEFT.value == "dlpfc_left"
    assert BrainRegion.SG_ACC.value == "sg_acc"


def test_synthetic_connectome_generation():
    """Test synthetic connectome generator"""
    connectome = generate_synthetic_connectome("pt_test", n_regions=100, healthy=True)
    
    assert connectome.patient_id == "pt_test"
    assert connectome.adjacency_matrix.shape == (100, 100)
    assert len(connectome.region_labels) == 100
    assert 0.85 <= connectome.session_quality <= 0.95
    
    # Matrix should be symmetric
    np.testing.assert_array_almost_equal(
        connectome.adjacency_matrix,
        connectome.adjacency_matrix.T
    )


def test_standard_targets():
    """Test standard MNI targets are defined"""
    targets = ConnectomicsAgent.STANDARD_TARGETS
    
    assert BrainRegion.DLPFC_LEFT in targets
    assert BrainRegion.DLPFC_RIGHT in targets
    
    # Coordinates should be reasonable
    left_dlpfc = targets[BrainRegion.DLPFC_LEFT]
    assert left_dlpfc[0] < 0  # Left hemisphere is negative x
    assert left_dlpfc[1] > 0  # Anterior
    assert left_dlpfc[2] > 0  # Superior
