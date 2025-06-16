"""
NOVA ViA Timing Coordinator
Microsecond precision timing coordination system for synchronized device control
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import statistics
import threading


@dataclass
class TimingEvent:
    """Represents a precisely timed event"""
    event_id: str
    target_time: float
    callback: callable
    priority: int = 0
    tolerance_ms: float = 1.0
    executed: bool = False
    actual_execution_time: Optional[float] = None


class HighPrecisionTimer:
    """High precision timer using system performance counter"""
    
    def __init__(self):
        self.base_time = time.perf_counter()
        self.calibration_offset = 0.0
        self._calibrate()
    
    def _calibrate(self):
        """Calibrate timer for maximum precision"""
        # Measure timer overhead and adjust
        measurements = []
        for _ in range(100):
            start = time.perf_counter()
            end = time.perf_counter()
            measurements.append(end - start)
        
        self.calibration_offset = statistics.mean(measurements)
        logging.info(f"Timer calibrated with {self.calibration_offset*1000000:.2f}μs overhead")
    
    def get_time(self) -> float:
        """Get high precision time"""
        return time.perf_counter() - self.calibration_offset
    
    def sleep_until(self, target_time: float):
        """Sleep until target time with high precision"""
        current_time = self.get_time()
        sleep_duration = target_time - current_time
        
        if sleep_duration <= 0:
            return
        
        # Use a combination of sleep and busy wait for precision
        if sleep_duration > 0.001:  # If more than 1ms, use regular sleep
            time.sleep(sleep_duration - 0.001)
        
        # Busy wait for final precision
        while self.get_time() < target_time:
            pass


class TimingCoordinator:
    """
    Coordinates device timing with microsecond precision for synchronized stimulation
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # High precision timer
        self.timer = HighPrecisionTimer()
        
        # Event scheduling
        self.scheduled_events: List[TimingEvent] = []
        self.event_lock = threading.Lock()
        
        # Timing metrics
        self.execution_metrics: List[Dict[str, float]] = []
        self.synchronization_accuracy: List[float] = []
        
        # Coordination state
        self.is_running = False
        self.coordination_thread: Optional[threading.Thread] = None
        
        # Performance tracking
        self.total_events_executed = 0
        self.average_accuracy_ms = 0.0
        self.worst_case_latency_ms = 0.0
        self.best_case_latency_ms = float('inf')
    
    async def initialize(self):
        """Initialize the timing coordination system"""
        self.logger.info("Initializing High-Precision Timing Coordinator...")
        
        # Start coordination thread
        self.is_running = True
        self.coordination_thread = threading.Thread(target=self._coordination_loop, daemon=True)
        self.coordination_thread.start()
        
        # Calibrate system timing
        await self._calibrate_system_timing()
        
        self.logger.info("Timing Coordinator initialized with microsecond precision")
    
    async def _calibrate_system_timing(self):
        """Calibrate system timing for maximum accuracy"""
        self.logger.info("Calibrating system timing...")
        
        # Test scheduling accuracy
        test_results = []
        for i in range(10):
            target_time = self.timer.get_time() + 0.01  # 10ms in future
            
            start_schedule = self.timer.get_time()
            await self._precise_wait_until(target_time)
            actual_time = self.timer.get_time()
            
            accuracy = abs(actual_time - target_time) * 1000  # Convert to ms
            test_results.append(accuracy)
        
        avg_accuracy = statistics.mean(test_results)
        self.logger.info(f"Timing calibration complete - Average accuracy: {avg_accuracy:.3f}ms")
    
    async def schedule_synchronized_execution(
        self,
        events: List[Dict[str, Any]],
        base_time: Optional[float] = None
    ) -> str:
        """
        Schedule multiple events for synchronized execution
        
        Args:
            events: List of events with timing and callback information
            base_time: Base time for synchronization (defaults to current time + 100ms)
            
        Returns:
            coordination_id: Unique identifier for this coordination session
        """
        coordination_id = f"sync_{int(time.time() * 1000)}"
        
        if base_time is None:
            base_time = self.timer.get_time() + 0.1  # 100ms buffer
        
        scheduled_events = []
        
        for i, event_data in enumerate(events):
            timing_event = TimingEvent(
                event_id=f"{coordination_id}_{i}",
                target_time=base_time + event_data.get('delay_ms', 0) / 1000.0,
                callback=event_data['callback'],
                priority=event_data.get('priority', 0),
                tolerance_ms=event_data.get('tolerance_ms', 1.0)
            )
            scheduled_events.append(timing_event)
        
        # Add events to scheduler
        with self.event_lock:
            self.scheduled_events.extend(scheduled_events)
            # Sort by target time and priority
            self.scheduled_events.sort(key=lambda e: (e.target_time, -e.priority))
        
        self.logger.info(f"Scheduled {len(events)} synchronized events (ID: {coordination_id})")
        
        return coordination_id
    
    async def wait_until(self, target_time: float):
        """Wait until specified time with high precision"""
        await self._precise_wait_until(target_time)
    
    async def _precise_wait_until(self, target_time: float):
        """High precision wait implementation"""
        current_time = self.timer.get_time()
        wait_duration = target_time - current_time
        
        if wait_duration <= 0:
            return
        
        # For longer waits, use asyncio.sleep to avoid blocking
        if wait_duration > 0.01:  # 10ms threshold
            await asyncio.sleep(wait_duration - 0.01)
        
        # Final precision wait using busy loop
        while self.timer.get_time() < target_time:
            await asyncio.sleep(0)  # Yield control briefly
    
    def _coordination_loop(self):
        """Main coordination loop running in separate thread for maximum precision"""
        while self.is_running:
            try:
                current_time = self.timer.get_time()
                
                # Check for events ready to execute
                with self.event_lock:
                    ready_events = [
                        event for event in self.scheduled_events
                        if not event.executed and event.target_time <= current_time + 0.001  # 1ms lookahead
                    ]
                
                # Execute ready events
                for event in ready_events:
                    self._execute_timing_event(event)
                
                # Remove executed events
                with self.event_lock:
                    self.scheduled_events = [
                        event for event in self.scheduled_events if not event.executed
                    ]
                
                # Short sleep to prevent excessive CPU usage
                time.sleep(0.0001)  # 0.1ms sleep
                
            except Exception as e:
                self.logger.error(f"Coordination loop error: {e}")
                time.sleep(0.001)
    
    def _execute_timing_event(self, event: TimingEvent):
        """Execute a timing event with precision measurement"""
        # Wait until exact target time
        self.timer.sleep_until(event.target_time)
        
        # Record actual execution time
        execution_start = self.timer.get_time()
        
        try:
            # Execute callback
            if asyncio.iscoroutinefunction(event.callback):
                # For async callbacks, schedule in event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(event.callback())
                loop.close()
            else:
                event.callback()
            
            execution_end = self.timer.get_time()
            
            # Record timing metrics
            timing_accuracy = abs(execution_start - event.target_time) * 1000  # ms
            execution_duration = (execution_end - execution_start) * 1000  # ms
            
            self._record_timing_metrics(event, timing_accuracy, execution_duration)
            
            event.executed = True
            event.actual_execution_time = execution_start
            
            self.logger.debug(
                f"Event {event.event_id} executed - "
                f"Accuracy: {timing_accuracy:.3f}ms, "
                f"Duration: {execution_duration:.3f}ms"
            )
            
        except Exception as e:
            self.logger.error(f"Event execution failed: {event.event_id} - {e}")
            event.executed = True  # Mark as executed to avoid retry
    
    def _record_timing_metrics(self, event: TimingEvent, accuracy_ms: float, duration_ms: float):
        """Record timing metrics for performance analysis"""
        metrics = {
            'event_id': event.event_id,
            'target_time': event.target_time,
            'actual_time': event.actual_execution_time,
            'accuracy_ms': accuracy_ms,
            'duration_ms': duration_ms,
            'timestamp': time.time()
        }
        
        self.execution_metrics.append(metrics)
        self.synchronization_accuracy.append(accuracy_ms)
        
        # Update performance statistics
        self.total_events_executed += 1
        
        if accuracy_ms < self.best_case_latency_ms:
            self.best_case_latency_ms = accuracy_ms
        
        if accuracy_ms > self.worst_case_latency_ms:
            self.worst_case_latency_ms = accuracy_ms
        
        if len(self.synchronization_accuracy) > 0:
            self.average_accuracy_ms = statistics.mean(self.synchronization_accuracy[-100:])  # Last 100 events
        
        # Keep metrics list manageable
        if len(self.execution_metrics) > 1000:
            self.execution_metrics = self.execution_metrics[-500:]
        
        if len(self.synchronization_accuracy) > 1000:
            self.synchronization_accuracy = self.synchronization_accuracy[-500:]
    
    async def get_accuracy_metrics(self) -> Dict[str, Any]:
        """Get timing accuracy metrics"""
        if not self.synchronization_accuracy:
            return {
                "total_events": 0,
                "average_accuracy_ms": 0.0,
                "best_case_ms": 0.0,
                "worst_case_ms": 0.0,
                "std_deviation_ms": 0.0,
                "sub_millisecond_percentage": 0.0
            }
        
        recent_accuracy = self.synchronization_accuracy[-100:] if len(self.synchronization_accuracy) > 100 else self.synchronization_accuracy
        
        sub_ms_count = sum(1 for acc in recent_accuracy if acc < 1.0)
        sub_ms_percentage = (sub_ms_count / len(recent_accuracy)) * 100
        
        return {
            "total_events": self.total_events_executed,
            "average_accuracy_ms": self.average_accuracy_ms,
            "best_case_ms": self.best_case_latency_ms,
            "worst_case_ms": self.worst_case_latency_ms,
            "std_deviation_ms": statistics.stdev(recent_accuracy) if len(recent_accuracy) > 1 else 0.0,
            "sub_millisecond_percentage": sub_ms_percentage,
            "recent_accuracy_samples": len(recent_accuracy)
        }
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time timing metrics for monitoring"""
        recent_metrics = self.execution_metrics[-10:] if len(self.execution_metrics) >= 10 else self.execution_metrics
        
        if not recent_metrics:
            return {"status": "no_data"}
        
        return {
            "current_accuracy_ms": recent_metrics[-1]['accuracy_ms'] if recent_metrics else 0.0,
            "recent_average_ms": statistics.mean([m['accuracy_ms'] for m in recent_metrics]),
            "recent_best_ms": min([m['accuracy_ms'] for m in recent_metrics]),
            "recent_worst_ms": max([m['accuracy_ms'] for m in recent_metrics]),
            "events_in_queue": len([e for e in self.scheduled_events if not e.executed]),
            "system_time": self.timer.get_time(),
            "timestamp": time.time()
        }
    
    async def create_synchronization_barrier(self, device_count: int, timeout_ms: float = 5000) -> Dict[str, Any]:
        """
        Create a synchronization barrier for multiple devices
        
        Args:
            device_count: Number of devices to synchronize
            timeout_ms: Maximum wait time for synchronization
            
        Returns:
            Barrier information including sync time and coordination ID
        """
        barrier_id = f"barrier_{int(time.time() * 1000)}"
        sync_time = self.timer.get_time() + (timeout_ms / 1000.0)
        
        barrier_info = {
            "barrier_id": barrier_id,
            "sync_time": sync_time,
            "device_count": device_count,
            "timeout_ms": timeout_ms,
            "created_at": time.time()
        }
        
        self.logger.info(f"Synchronization barrier created: {barrier_id} for {device_count} devices")
        
        return barrier_info
    
    async def validate_timing_precision(self) -> Dict[str, Any]:
        """Validate system timing precision"""
        self.logger.info("Validating timing precision...")
        
        # Test with multiple rapid events
        test_events = []
        base_time = self.timer.get_time() + 0.1
        
        # Create test callbacks that record their execution time
        execution_times = []
        
        def create_test_callback(expected_time):
            def callback():
                execution_times.append((expected_time, self.timer.get_time()))
            return callback
        
        # Schedule 10 events with 1ms intervals
        for i in range(10):
            target_time = base_time + (i * 0.001)  # 1ms intervals
            test_events.append({
                'callback': create_test_callback(target_time),
                'delay_ms': i,
                'tolerance_ms': 0.5
            })
        
        # Execute test
        coordination_id = await self.schedule_synchronized_execution(test_events, base_time)
        
        # Wait for completion
        await asyncio.sleep(0.2)
        
        # Analyze results
        accuracies = []
        for expected, actual in execution_times:
            accuracy = abs(actual - expected) * 1000  # ms
            accuracies.append(accuracy)
        
        if accuracies:
            validation_result = {
                "test_passed": max(accuracies) < 2.0,  # All events within 2ms
                "average_accuracy_ms": statistics.mean(accuracies),
                "max_error_ms": max(accuracies),
                "min_error_ms": min(accuracies),
                "events_tested": len(accuracies),
                "sub_millisecond_count": sum(1 for acc in accuracies if acc < 1.0),
                "precision_grade": self._calculate_precision_grade(accuracies)
            }
        else:
            validation_result = {
                "test_passed": False,
                "error": "No test events executed"
            }
        
        self.logger.info(f"Timing validation complete: {validation_result}")
        return validation_result
    
    def _calculate_precision_grade(self, accuracies: List[float]) -> str:
        """Calculate precision grade based on accuracy measurements"""
        avg_accuracy = statistics.mean(accuracies)
        max_accuracy = max(accuracies)
        
        if avg_accuracy < 0.1 and max_accuracy < 0.5:
            return "EXCELLENT"  # Sub-100μs average, max 500μs
        elif avg_accuracy < 0.5 and max_accuracy < 1.0:
            return "VERY_GOOD"  # Sub-500μs average, max 1ms
        elif avg_accuracy < 1.0 and max_accuracy < 2.0:
            return "GOOD"  # Sub-1ms average, max 2ms
        elif avg_accuracy < 2.0 and max_accuracy < 5.0:
            return "ACCEPTABLE"  # Sub-2ms average, max 5ms
        else:
            return "POOR"  # Above 2ms average
    
    async def shutdown(self):
        """Shutdown the timing coordinator"""
        self.logger.info("Shutting down Timing Coordinator...")
        
        self.is_running = False
        
        if self.coordination_thread and self.coordination_thread.is_alive():
            self.coordination_thread.join(timeout=1.0)
        
        self.logger.info("Timing Coordinator shutdown complete")
