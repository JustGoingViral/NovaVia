"""
EEG Processing Module

Real-time EEG stream processing, pattern analysis, and neuroplasticity prediction.
"""

from anep.eeg_processor.pattern_analyzer import NeuroplasticityPatternAnalyzer
from anep.eeg_processor.neuroplasticity_predictor import NeuroplasticityPredictor
from anep.eeg_processor.stream_processor import EEGStreamProcessor
from anep.eeg_processor.wavi_integration import WAViIntegration

__all__ = [
    "NeuroplasticityPatternAnalyzer",
    "NeuroplasticityPredictor",
    "EEGStreamProcessor",
    "WAViIntegration",
]
