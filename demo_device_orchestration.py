"""
NOVA ViA Device Orchestration Demo
Demonstrates synchronized multi-modal stimulation with millisecond precision timing
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any

# Import the orchestration system
from anep.device_orchestrator.device_manager import (
    DeviceOrchestrator, TreatmentProtocol, NeuroplasticityWindow, TreatmentPhase
)


# Configure logging for demo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def create_demo_neuroplasticity_window() -> NeuroplasticityWindow:
    """Create a demo neuroplasticity window prediction"""
    # Predict window starting in 30 seconds
    predicted_start = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    predicted_start = predicted_start.replace(second=predicted_start.second + 30)
    
    predicted_end = predicted_start.replace(second=predicted_start.second + 300)  # 5 minute window
    
    return NeuroplasticityWindow(
        window_id="demo_window_001",
        patient_id="patient_demo_001",
        predicted_start=predicted_start,
        predicted_end=predicted_end,
        confidence_score=0.87,
        window_type="alpha_enhancement",
        optimal_stimulation_params={
            "pressure_ata": 1.3,
            "light_wavelength_nm": 660,
            "pemf_frequency_hz": 10.0,
            "binaural_beat_hz": 10.0
        },
        eeg_features={
            "alpha_power": 0.75,
            "theta_power": 0.45,
            "gamma_power": 0.32,
            "coherence": 0.68,
            "complexity": 0.82
        }
    )


def create_demo_protocol() -> TreatmentProtocol:
    """Create a demo treatment protocol for synchronized stimulation"""
    return TreatmentProtocol(
        protocol_id="demo_sync_protocol_001",
        name="Synchronized Neuroplasticity Enhancement",
        description="Demo protocol showing coordinated multi-modal stimulation",
        phases={
            TreatmentPhase.PREPARATION: {
                "duration_seconds": 30,
                "description": "System preparation and device calibration"
            },
            TreatmentPhase.RAMP_UP: {
                "duration_seconds": 60,
                "description": "Gradual increase to treatment parameters"
            },
            TreatmentPhase.NEUROPLASTICITY_WINDOW: {
                "duration_seconds": 300,  # 5 minutes
                "description": "Synchronized stimulation during optimal window"
            },
            TreatmentPhase.RAMP_DOWN: {
                "duration_seconds": 60,
                "description": "Gradual return to baseline"
            },
            TreatmentPhase.RECOVERY: {
                "duration_seconds": 30,
                "description": "Recovery and system reset"
            }
        },
        device_configurations={
            "hyperbaric_01": {
                "preparation": {
                    "command": "start_treatment",
                    "parameters": {
                        "protocol_name": "neuroplasticity_enhancement",
                        "target_pressure_ata": 1.0,
                        "oxygen_percentage": 21.0,
                        "eeg_feedback_enabled": True
                    },
                    "delay_ms": 0,
                    "priority": 1
                },
                "ramp_up": {
                    "command": "set_pressure",
                    "parameters": {"pressure_ata": 1.3},
                    "delay_ms": 100,
                    "priority": 1
                },
                "neuroplasticity_window": {
                    "command": "set_oxygen",
                    "parameters": {"oxygen_percentage": 100.0},
                    "delay_ms": 0,
                    "priority": 1
                },
                "ramp_down": {
                    "command": "set_pressure", 
                    "parameters": {"pressure_ata": 1.0},
                    "delay_ms": 200,
                    "priority": 1
                }
            },
            "redlight_01": {
                "ramp_up": {
                    "command": "start_treatment",
                    "parameters": {
                        "wavelength_nm": 660,
                        "intensity_percent": 30,
                        "pulse_frequency_hz": 10
                    },
                    "delay_ms": 50,
                    "priority": 2
                },
                "neuroplasticity_window": {
                    "command": "set_intensity",
                    "parameters": {"intensity_percent": 70},
                    "delay_ms": 5,
                    "priority": 2
                },
                "ramp_down": {
                    "command": "stop_treatment",
                    "parameters": {},
                    "delay_ms": 100,
                    "priority": 2
                }
            },
            "pemf_01": {
                "ramp_up": {
                    "command": "start_treatment",
                    "parameters": {
                        "frequency_hz": 10.0,
                        "intensity_percent": 25,
                        "waveform_type": "sine"
                    },
                    "delay_ms": 25,
                    "priority": 3
                },
                "neuroplasticity_window": {
                    "command": "start_treatment",
                    "parameters": {
                        "frequency_hz": 10.0,
                        "intensity_percent": 50
                    },
                    "delay_ms": 10,
                    "priority": 3
                },
                "ramp_down": {
                    "command": "stop_treatment",
                    "parameters": {},
                    "delay_ms": 150,
                    "priority": 3
                }
            },
            "frequency_01": {
                "preparation": {
                    "command": "start_treatment", 
                    "parameters": {
                        "base_frequency_hz": 440,
                        "binaural_beat_hz": 10.0,
                        "volume_percent": 15,
                        "therapy_type": "binaural"
                    },
                    "delay_ms": 75,
                    "priority": 4
                },
                "neuroplasticity_window": {
                    "command": "start_treatment",
                    "parameters": {
                        "binaural_beat_hz": 10.0,
                        "volume_percent": 25
                    },
                    "delay_ms": 15,
                    "priority": 4
                },
                "recovery": {
                    "command": "stop_treatment",
                    "parameters": {},
                    "delay_ms": 0,
                    "priority": 4
                }
            }
        },
        synchronization_points=[
            {
                "name": "neuroplasticity_window_start",
                "description": "All devices begin enhanced stimulation simultaneously",
                "tolerance_ms": 1.0
            }
        ],
        safety_parameters={
            "max_pressure_ata": 1.5,
            "max_light_intensity": 80,
            "max_pemf_intensity": 60,
            "max_audio_volume": 30,
            "emergency_stop_on_eeg_anomaly": True
        },
        expected_duration_minutes=8
    )


async def demonstrate_device_synchronization():
    """Demonstrate the synchronized device orchestration"""
    logger.info("🚀 Starting NOVA ViA Device Orchestration Demo")
    logger.info("=" * 60)
    
    # Initialize orchestrator
    orchestrator = DeviceOrchestrator()
    await orchestrator.initialize()
    
    logger.info("✅ Device Orchestrator initialized")
    logger.info(f"📊 Devices registered: {len(orchestrator.devices)}")
    
    # Show initial system status
    system_status = await orchestrator.get_system_status()
    logger.info("📈 Initial System Status:")
    logger.info(f"   State: {system_status['orchestrator_state']}")
    logger.info(f"   Devices: {system_status['devices']}")
    
    # Add event listeners for demo
    async def on_session_started(data):
        logger.info("🎬 SESSION STARTED")
        logger.info(f"   Patient: {data['patient_id']}")
        logger.info(f"   Protocol: {data['protocol'].name}")
        logger.info(f"   Devices: {', '.join(data['devices'])}")
    
    async def on_phase_changed(data):
        phase = data['phase']
        logger.info(f"⚡ PHASE CHANGE: {phase.value}")
        logger.info(f"   Elapsed: {(time.time() - data['session']['start_time'])/60:.1f} minutes")
    
    async def on_device_synchronized(data):
        commands = data['commands']
        accuracy = data['timing_accuracy']
        logger.info(f"🎯 DEVICE SYNCHRONIZATION")
        logger.info(f"   Commands executed: {len(commands)}")
        logger.info(f"   Timing accuracy: {accuracy:.3f}ms")
        logger.info(f"   Target time: {data['target_time']:.6f}")
        logger.info(f"   Actual time: {data['execution_time']:.6f}")
    
    async def on_neuroplasticity_window_detected(data):
        window = data['window']
        logger.info("🧠 NEUROPLASTICITY WINDOW DETECTED")
        logger.info(f"   Window ID: {window.window_id}")
        logger.info(f"   Confidence: {window.confidence_score:.2%}")
        logger.info(f"   Type: {window.window_type}")
        logger.info("   🎯 INITIATING SYNCHRONIZED STIMULATION")
    
    async def on_session_completed(data):
        metrics = data['metrics']
        logger.info("✅ SESSION COMPLETED")
        logger.info(f"   Duration: {metrics['total_duration']/60:.1f} minutes")
        logger.info(f"   Phases: {metrics['phases_completed']}")
        logger.info(f"   Sync accuracy: {metrics['synchronization_accuracy']:.1f}%")
        logger.info(f"   Status: {metrics['completion_status']}")
    
    # Register event listeners
    orchestrator.add_event_listener('session_started', on_session_started)
    orchestrator.add_event_listener('phase_changed', on_phase_changed)
    orchestrator.add_event_listener('device_synchronized', on_device_synchronized)
    orchestrator.add_event_listener('neuroplasticity_window_detected', on_neuroplasticity_window_detected)
    orchestrator.add_event_listener('session_completed', on_session_completed)
    
    # Create demo scenario
    neuroplasticity_window = await create_demo_neuroplasticity_window()
    treatment_protocol = create_demo_protocol()
    
    logger.info("🔬 Demo Scenario Created:")
    logger.info(f"   Neuroplasticity Window: {neuroplasticity_window.predicted_start}")
    logger.info(f"   Confidence: {neuroplasticity_window.confidence_score:.2%}")
    logger.info(f"   Protocol: {treatment_protocol.name}")
    logger.info(f"   Expected Duration: {treatment_protocol.expected_duration_minutes} minutes")
    
    # Simulate some EEG feedback during demo
    async def simulate_eeg_feedback():
        await asyncio.sleep(2)  # Wait for session to start
        
        # Send simulated EEG data to hyperbaric chamber
        hyperbaric_device = orchestrator.devices.get("hyperbaric_01")
        if hyperbaric_device:
            eeg_data = {
                "alpha_power": 0.75,
                "coherence": 0.68,
                "theta_power": 0.45,
                "gamma_power": 0.32
            }
            await hyperbaric_device.execute_command("update_eeg_feedback", eeg_data)
            logger.info("📡 EEG feedback sent to hyperbaric chamber")
    
    # Start EEG simulation
    asyncio.create_task(simulate_eeg_feedback())
    
    try:
        # Execute the coordinated treatment session
        logger.info("🎬 STARTING COORDINATED TREATMENT SESSION")
        logger.info("=" * 60)
        
        session_id = await orchestrator.coordinate_treatment_session(
            patient_id="demo_patient_001",
            protocol=treatment_protocol,
            neuroplasticity_window=neuroplasticity_window,
            devices=["hyperbaric_01", "redlight_01", "pemf_01", "frequency_01"]
        )
        
        logger.info(f"📋 Session ID: {session_id}")
        
        # Monitor session progress
        while orchestrator.current_session:
            await asyncio.sleep(5)
            
            # Show real-time status
            status = await orchestrator.get_system_status()
            if status['current_session']:
                current_phase = status['current_session']['current_phase']
                elapsed = (time.time() - status['current_session']['start_time']) / 60
                logger.info(f"⏱️  Status Update - Phase: {current_phase.value} | Elapsed: {elapsed:.1f}min")
        
        logger.info("🎉 DEMONSTRATION COMPLETED SUCCESSFULLY")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        await orchestrator.emergency_stop("Demo failure")
    
    finally:
        # Show final system metrics
        logger.info("=" * 60)
        logger.info("📊 FINAL SYSTEM METRICS")
        
        system_metrics = await orchestrator.get_system_status()
        timing_metrics = await orchestrator.timing_coordinator.get_accuracy_metrics()
        
        logger.info(f"⚡ Timing Performance:")
        logger.info(f"   Events executed: {timing_metrics['total_events']}")
        logger.info(f"   Average accuracy: {timing_metrics['average_accuracy_ms']:.3f}ms")
        logger.info(f"   Best case: {timing_metrics['best_case_ms']:.3f}ms")
        logger.info(f"   Sub-millisecond: {timing_metrics['sub_millisecond_percentage']:.1f}%")
        
        logger.info(f"🏥 Device Status:")
        for device_id, device_info in system_metrics['devices'].items():
            logger.info(f"   {device_id}: {device_info['status']} ({device_info['device_type']})")
        
        logger.info("=" * 60)
        logger.info("✨ NOVA ViA Device Orchestration Demo Complete")


async def run_quick_demo():
    """Run a quick demo showing just the key capabilities"""
    logger.info("🚀 NOVA ViA Quick Demo - Synchronized Multi-Modal Stimulation")
    
    orchestrator = DeviceOrchestrator()
    await orchestrator.initialize()
    
    # Show available devices
    logger.info("📱 Available Devices:")
    for device_id, device in orchestrator.devices.items():
        capabilities = device.get_capabilities()
        logger.info(f"   • {device.manufacturer} {device.model} ({device_id})")
        logger.info(f"     Capabilities: {', '.join(capabilities)}")
    
    # Test timing precision
    logger.info("\n⏱️  Testing Timing Precision...")
    validation = await orchestrator.timing_coordinator.validate_timing_precision()
    logger.info(f"   Precision Grade: {validation['precision_grade']}")
    logger.info(f"   Average Accuracy: {validation['average_accuracy_ms']:.3f}ms")
    logger.info(f"   Max Error: {validation['max_error_ms']:.3f}ms")
    
    # Test device coordination
    logger.info("\n🎯 Testing Device Coordination...")
    
    # Create a simple protocol for demo
    simple_protocol = TreatmentProtocol(
        protocol_id="quick_demo",
        name="Quick Demo Protocol",
        description="Quick demonstration of device coordination",
        phases={
            TreatmentPhase.PREPARATION: {"duration_seconds": 5},
            TreatmentPhase.NEUROPLASTICITY_WINDOW: {"duration_seconds": 10},
            TreatmentPhase.RECOVERY: {"duration_seconds": 5}
        },
        device_configurations={
            "hyperbaric_01": {
                "preparation": {
                    "command": "start_treatment",
                    "parameters": {"protocol_name": "maintenance_therapy"},
                    "delay_ms": 0,
                    "priority": 1
                }
            },
            "redlight_01": {
                "neuroplasticity_window": {
                    "command": "start_treatment", 
                    "parameters": {"intensity_percent": 50},
                    "delay_ms": 10,
                    "priority": 2
                }
            }
        },
        synchronization_points=[],
        safety_parameters={},
        expected_duration_minutes=1
    )
    
    # Create immediate neuroplasticity window
    window = NeuroplasticityWindow(
        window_id="quick_demo",
        patient_id="demo_patient",
        predicted_start=datetime.now(timezone.utc),
        predicted_end=datetime.now(timezone.utc).replace(second=datetime.now().second + 20),
        confidence_score=0.95,
        window_type="demo",
        optimal_stimulation_params={},
        eeg_features={}
    )
    
    # Run quick session
    session_id = await orchestrator.coordinate_treatment_session(
        patient_id="demo_patient",
        protocol=simple_protocol,
        neuroplasticity_window=window
    )
    
    logger.info(f"   Session started: {session_id}")
    
    # Wait for completion
    await asyncio.sleep(25)
    
    # Show results
    final_status = await orchestrator.get_system_status()
    logger.info(f"   Session completed: {final_status['orchestrator_state']}")
    
    logger.info("\n✅ Quick Demo Complete - All systems operational!")


if __name__ == "__main__":
    print("NOVA ViA Device Orchestration Demo")
    print("==================================")
    print("1. Full Demo (8+ minutes)")
    print("2. Quick Demo (30 seconds)")
    
    choice = input("Select demo (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(demonstrate_device_synchronization())
    else:
        asyncio.run(run_quick_demo())
