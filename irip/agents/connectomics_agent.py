"""
Connectomics Agent
Brain connectivity-based personalization for device placement

Implements NetworkX graph analysis of rs-fMRI connectomes for
optimizing DLPFC targeting in neurostimulation.

References:
- Fox et al. (2012). Efficacy of transcranial magnetic stimulation targets
  for depression is related to intrinsic functional connectivity.
  Biological Psychiatry, 72(7), 595-603. [PMID: 22658708]
- Weigand et al. (2018). Prospective validation that subgenual connectivity
  predicts antidepressant efficacy. Biological Psychiatry, 84(1), 28-37. [PMID: 29274805]
- Cash et al. (2021). Using brain imaging for personalized brain stimulation.
  Biological Psychiatry, 90(10), 689-703. [PMID: 33715824]
"""

import asyncio
import logging
import numpy as np
import networkx as nx
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .base_agent import (
    BaseAgent, AgentMessage, PatientContext, AgentCapability,
    AgentPriority, AgentState
)

logger = logging.getLogger(__name__)


class BrainRegion(Enum):
    """Standard brain regions for stimulation targeting"""
    DLPFC_LEFT = "dlpfc_left"        # Dorsolateral prefrontal cortex
    DLPFC_RIGHT = "dlpfc_right"
    VLPFC_LEFT = "vlpfc_left"        # Ventrolateral prefrontal
    VLPFC_RIGHT = "vlpfc_right"
    SG_ACC = "sg_acc"                # Subgenual anterior cingulate
    DMPFC = "dmpfc"                  # Dorsomedial prefrontal
    OFC = "ofc"                       # Orbitofrontal cortex
    INSULA_LEFT = "insula_left"
    INSULA_RIGHT = "insula_right"
    AMYGDALA_LEFT = "amygdala_left"
    AMYGDALA_RIGHT = "amygdala_right"
    HIPPOCAMPUS_LEFT = "hippocampus_left"
    HIPPOCAMPUS_RIGHT = "hippocampus_right"


class ConnectivityMetric(Enum):
    """Network metrics for target optimization"""
    DEGREE_CENTRALITY = "degree_centrality"
    BETWEENNESS = "betweenness"
    EIGENVECTOR = "eigenvector"
    PAGERANK = "pagerank"
    HUB_SCORE = "hub_score"


@dataclass
class ConnectomeData:
    """Patient brain connectivity data"""
    patient_id: str
    scan_date: datetime
    parcellation: str  # "schaefer_400", "aal116", etc.
    adjacency_matrix: np.ndarray
    region_labels: List[str]
    session_quality: float
    motion_parameters: Optional[Dict[str, float]] = None


@dataclass
class StimulationTarget:
    """Optimized stimulation target"""
    region: BrainRegion
    mni_coordinates: Tuple[float, float, float]  # MNI space (x, y, z)
    target_strength: float  # 0-1
    connectivity_to_sgacc: float  # Key predictor per Fox et al.
    hub_score: float
    confidence: float
    alternative_targets: List[Dict[str, Any]]


@dataclass
class NetworkAnalysis:
    """Brain network analysis results"""
    patient_id: str
    global_efficiency: float
    local_efficiency: float
    modularity: float
    small_worldness: float
    hub_regions: List[str]
    depression_circuit_integrity: float
    recommended_target: StimulationTarget


class ConnectomicsAgent(BaseAgent):
    """
    Connectomics Agent for personalized brain stimulation targeting
    
    Uses resting-state fMRI functional connectivity to optimize
    DLPFC targeting for TMS/tDCS. Key principle from Fox et al. (2012):
    targets with stronger anti-correlation to sgACC show better efficacy.
    
    Implements:
    - Graph theory metrics (degree, betweenness, hub scores)
    - Depression circuit assessment (DLPFC-sgACC connectivity)
    - Personalized MNI coordinate optimization
    - Network integrity scoring
    """
    
    # Standard MNI coordinates for DLPFC targets
    # Based on Beam et al. (2009) meta-analysis
    STANDARD_TARGETS = {
        BrainRegion.DLPFC_LEFT: (-46, 45, 38),
        BrainRegion.DLPFC_RIGHT: (46, 45, 38),
        BrainRegion.DMPFC: (0, 52, 36),
        BrainRegion.VLPFC_LEFT: (-44, 36, 4),
    }
    
    # Region indices in Schaefer 400 parcellation (approximate)
    REGION_INDICES = {
        BrainRegion.DLPFC_LEFT: list(range(0, 30)),
        BrainRegion.DLPFC_RIGHT: list(range(200, 230)),
        BrainRegion.SG_ACC: list(range(90, 100)),
        BrainRegion.INSULA_LEFT: list(range(60, 70)),
        BrainRegion.AMYGDALA_LEFT: list(range(180, 185)),
    }
    
    def __init__(self, agent_id: str = "connectomics_agent"):
        super().__init__(
            agent_id=agent_id,
            capabilities=[
                AgentCapability.DATA_ANALYSIS,
                AgentCapability.TREATMENT_OPTIMIZATION
            ]
        )
    
    async def initialize(self):
        """Initialize agent"""
        await super().initialize()
        logger.info(f"{self.agent_id} initialized with NetworkX graph analysis")
    
    def _build_graph(self, connectome: ConnectomeData) -> nx.Graph:
        """
        Build NetworkX graph from connectivity matrix
        
        Args:
            connectome: ConnectomeData with adjacency matrix
        
        Returns:
            Weighted undirected graph
        """
        n_regions = connectome.adjacency_matrix.shape[0]
        
        # Threshold weak connections (r < 0.1)
        adj = connectome.adjacency_matrix.copy()
        adj[np.abs(adj) < 0.1] = 0
        
        # Build graph
        G = nx.Graph()
        
        # Add nodes with region labels
        for i in range(n_regions):
            label = connectome.region_labels[i] if i < len(connectome.region_labels) else f"region_{i}"
            G.add_node(i, label=label)
        
        # Add edges with weights
        for i in range(n_regions):
            for j in range(i + 1, n_regions):
                if adj[i, j] != 0:
                    G.add_edge(i, j, weight=adj[i, j])
        
        return G
    
    def _calculate_network_metrics(self, G: nx.Graph) -> Dict[str, float]:
        """Calculate global network metrics"""
        metrics = {}
        
        # Global efficiency
        try:
            metrics['global_efficiency'] = nx.global_efficiency(G)
        except:
            metrics['global_efficiency'] = 0.0
        
        # Average clustering (local efficiency proxy)
        try:
            metrics['local_efficiency'] = nx.average_clustering(G, weight='weight')
        except:
            metrics['local_efficiency'] = 0.0
        
        # Modularity (requires community detection)
        try:
            from networkx.algorithms.community import greedy_modularity_communities
            communities = greedy_modularity_communities(G)
            metrics['modularity'] = nx.algorithms.community.quality.modularity(G, communities)
        except:
            metrics['modularity'] = 0.0
        
        # Small-worldness (simplified: clustering/path_length ratio)
        try:
            C = metrics['local_efficiency']
            L = nx.average_shortest_path_length(G) if nx.is_connected(G) else 3.0
            # Compare to random graph
            C_rand = 0.1  # Approximate for random
            L_rand = 2.0
            sigma = (C / C_rand) / (L / L_rand) if C_rand > 0 and L_rand > 0 else 1.0
            metrics['small_worldness'] = sigma
        except:
            metrics['small_worldness'] = 1.0
        
        return metrics
    
    def _find_hub_regions(self, G: nx.Graph, top_n: int = 10) -> List[Tuple[int, float]]:
        """
        Identify hub regions using multiple centrality measures
        
        Combines degree, betweenness, and eigenvector centrality
        """
        # Calculate centralities
        degree = nx.degree_centrality(G)
        betweenness = nx.betweenness_centrality(G, weight='weight')
        
        try:
            eigenvector = nx.eigenvector_centrality(G, max_iter=1000, weight='weight')
        except:
            eigenvector = degree
        
        try:
            pagerank = nx.pagerank(G, weight='weight')
        except:
            pagerank = degree
        
        # Combine scores (weighted average)
        combined = {}
        for node in G.nodes():
            combined[node] = (
                0.3 * degree.get(node, 0) +
                0.3 * betweenness.get(node, 0) +
                0.2 * eigenvector.get(node, 0) +
                0.2 * pagerank.get(node, 0)
            )
        
        # Sort and return top hubs
        hubs = sorted(combined.items(), key=lambda x: -x[1])[:top_n]
        
        return hubs
    
    def _calculate_sgacc_connectivity(self, connectome: ConnectomeData,
                                     target_region: BrainRegion) -> float:
        """
        Calculate connectivity between target and subgenual ACC
        
        Per Fox et al. (2012), anti-correlation with sgACC predicts efficacy
        """
        adj = connectome.adjacency_matrix
        
        # Get region indices
        target_indices = self.REGION_INDICES.get(target_region, [0])
        sgacc_indices = self.REGION_INDICES.get(BrainRegion.SG_ACC, [90])
        
        # Calculate mean connectivity
        connectivities = []
        for t in target_indices:
            for s in sgacc_indices:
                if t < adj.shape[0] and s < adj.shape[1]:
                    connectivities.append(adj[t, s])
        
        if connectivities:
            return float(np.mean(connectivities))
        return 0.0
    
    def personalize_placement(self, connectome: nx.Graph) -> Tuple[float, float, float]:
        """
        Personalize stimulation placement based on connectome
        
        Args:
            connectome: NetworkX graph of brain connectivity
        
        Returns:
            tuple: (x, y, z) MNI coordinates for optimal target
        
        Example:
            >>> G = nx.random_graphs.watts_strogatz_graph(100, 10, 0.3)
            >>> coords = agent.personalize_placement(G)
            >>> print(f"Target: MNI ({coords[0]:.1f}, {coords[1]:.1f}, {coords[2]:.1f})")
        """
        # Find hubs in DLPFC region
        hubs = self._find_hub_regions(connectome, top_n=20)
        
        # Get hub indices in DLPFC range
        dlpfc_hubs = [h for h in hubs if h[0] < 30]  # Left DLPFC nodes
        
        if dlpfc_hubs:
            # Weight coordinates by hub score
            base_coords = self.STANDARD_TARGETS[BrainRegion.DLPFC_LEFT]
            
            # Slight personalization based on hub location
            best_hub, hub_score = dlpfc_hubs[0]
            offset = (best_hub - 15) / 15  # Normalize to -1 to 1
            
            x = base_coords[0] + offset * 5  # ±5mm adjustment
            y = base_coords[1] + offset * 3
            z = base_coords[2]
            
            return (round(x, 1), round(y, 1), round(z, 1))
        
        # Default to standard DLPFC target
        return self.STANDARD_TARGETS[BrainRegion.DLPFC_LEFT]
    
    async def analyze_connectome(self, connectome: ConnectomeData) -> NetworkAnalysis:
        """
        Comprehensive connectome analysis for treatment planning
        
        Args:
            connectome: Patient's fMRI connectivity data
        
        Returns:
            NetworkAnalysis with metrics and target recommendation
        """
        # Build graph
        G = self._build_graph(connectome)
        
        # Calculate network metrics
        metrics = self._calculate_network_metrics(G)
        
        # Find hub regions
        hubs = self._find_hub_regions(G)
        hub_labels = [
            connectome.region_labels[h[0]] if h[0] < len(connectome.region_labels) 
            else f"region_{h[0]}" 
            for h in hubs[:5]
        ]
        
        # Calculate DLPFC-sgACC connectivity (key predictor)
        dlpfc_sgacc = self._calculate_sgacc_connectivity(
            connectome, BrainRegion.DLPFC_LEFT
        )
        
        # Depression circuit integrity
        # Stronger anti-correlation = better prognosis
        circuit_integrity = 0.5 - dlpfc_sgacc  # Negative correlation is good
        circuit_integrity = max(0, min(1, circuit_integrity + 0.5))
        
        # Personalize target
        coords = self.personalize_placement(G)
        
        # Build target recommendation
        target = StimulationTarget(
            region=BrainRegion.DLPFC_LEFT,
            mni_coordinates=coords,
            target_strength=0.8,
            connectivity_to_sgacc=dlpfc_sgacc,
            hub_score=hubs[0][1] if hubs else 0.5,
            confidence=connectome.session_quality,
            alternative_targets=[
                {
                    'region': BrainRegion.DLPFC_RIGHT.value,
                    'coordinates': self.STANDARD_TARGETS[BrainRegion.DLPFC_RIGHT],
                    'rationale': 'Alternative for non-responders'
                },
                {
                    'region': BrainRegion.DMPFC.value,
                    'coordinates': self.STANDARD_TARGETS[BrainRegion.DMPFC],
                    'rationale': 'For bilateral depression circuits'
                }
            ]
        )
        
        return NetworkAnalysis(
            patient_id=connectome.patient_id,
            global_efficiency=round(metrics['global_efficiency'], 3),
            local_efficiency=round(metrics['local_efficiency'], 3),
            modularity=round(metrics['modularity'], 3),
            small_worldness=round(metrics['small_worldness'], 3),
            hub_regions=hub_labels,
            depression_circuit_integrity=round(circuit_integrity, 3),
            recommended_target=target
        )
    
    async def optimize_dlpfc_targeting(self, connectome: ConnectomeData) -> Dict[str, Any]:
        """
        Optimize DLPFC targeting based on individual connectome
        
        Returns JSON-friendly dict with targeting parameters
        """
        analysis = await self.analyze_connectome(connectome)
        target = analysis.recommended_target
        
        return {
            'patient_id': connectome.patient_id,
            'target_region': target.region.value,
            'mni_coordinates': {
                'x': target.mni_coordinates[0],
                'y': target.mni_coordinates[1],
                'z': target.mni_coordinates[2]
            },
            'sgacc_connectivity': target.connectivity_to_sgacc,
            'hub_score': target.hub_score,
            'confidence': target.confidence,
            'network_metrics': {
                'global_efficiency': analysis.global_efficiency,
                'local_efficiency': analysis.local_efficiency,
                'modularity': analysis.modularity,
                'small_worldness': analysis.small_worldness
            },
            'depression_circuit_integrity': analysis.depression_circuit_integrity,
            'alternative_targets': target.alternative_targets
        }
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages"""
        if message.message_type == "optimize_targeting":
            patient_id = message.content['patient_id']
            adj_matrix = np.array(message.content['adjacency_matrix'])
            labels = message.content.get('region_labels', [])
            
            connectome = ConnectomeData(
                patient_id=patient_id,
                scan_date=datetime.now(),
                parcellation="schaefer_400",
                adjacency_matrix=adj_matrix,
                region_labels=labels,
                session_quality=0.9
            )
            
            result = await self.optimize_dlpfc_targeting(connectome)
            
            return AgentMessage(
                message_id=f"msg_{datetime.now().timestamp()}",
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="targeting_result",
                content=result,
                priority=AgentPriority.NORMAL,
                timestamp=datetime.now().timestamp(),
                correlation_id=message.message_id
            )
        
        return None


def generate_synthetic_connectome(patient_id: str, 
                                 n_regions: int = 100,
                                 healthy: bool = True) -> ConnectomeData:
    """
    Generate synthetic connectome for testing
    
    Args:
        patient_id: Patient identifier
        n_regions: Number of brain regions
        healthy: Whether to simulate healthy or disrupted connectivity
    
    Returns:
        Synthetic ConnectomeData
    """
    np.random.seed(hash(patient_id) % 2**32)
    
    # Generate small-world-like connectivity matrix
    # Using simplified model based on Watts-Strogatz
    
    # Start with ring lattice
    adj = np.zeros((n_regions, n_regions))
    k = 10  # Each node connected to k nearest neighbors
    
    for i in range(n_regions):
        for j in range(1, k // 2 + 1):
            adj[i, (i + j) % n_regions] = np.random.uniform(0.3, 0.8)
            adj[i, (i - j) % n_regions] = np.random.uniform(0.3, 0.8)
    
    # Add long-range connections (rewiring)
    rewire_prob = 0.1
    for i in range(n_regions):
        for j in range(i + 1, n_regions):
            if adj[i, j] == 0 and np.random.random() < rewire_prob:
                adj[i, j] = np.random.uniform(0.2, 0.5)
                adj[j, i] = adj[i, j]
    
    # Make symmetric
    adj = (adj + adj.T) / 2
    
    # If not healthy, disrupt some connections
    if not healthy:
        # Reduce DLPFC-sgACC connectivity (depression signature)
        for i in range(0, 30):
            for j in range(90, 100):
                adj[i, j] *= 0.5
                adj[j, i] *= 0.5
    
    # Generate region labels
    labels = [f"region_{i}" for i in range(n_regions)]
    
    return ConnectomeData(
        patient_id=patient_id,
        scan_date=datetime.now(),
        parcellation="schaefer_100",
        adjacency_matrix=adj,
        region_labels=labels,
        session_quality=np.random.uniform(0.85, 0.95)
    )
