"""
Deterministic Immediate Safety Stop Module (Requirement 1).

Constraint:
The immediate safety-stop check must NEVER depend on the ML model.
It must execute instantaneously and deterministically, functioning even if
the ML model is completely wrong, missing, or throws an unhandled exception.
"""

from typing import Dict, List, Tuple
from config import JOINT_THRESHOLDS, JointName


def check_immediate_safety_stop(sensor_readings: Dict[str, Dict[str, float]]) -> Tuple[bool, List[str]]:
    """
    Evaluates instantaneous raw sensor readings against hard physical safety thresholds.

    Parameters:
        sensor_readings: Mapping of joint name to dict of readings:
                         {
                             "shoulder": {"torque": 110.5, "temp": 48.2, "vibration": 1.8},
                             "elbow":    {"torque": 65.0,  "temp": 45.0, "vibration": 1.2},
                             "wrist":    {"torque": 22.0,  "temp": 39.5, "vibration": 0.9}
                         }

    Returns:
        Tuple of (is_emergency_stop: bool, violation_reasons: List[str])
    """
    violations: List[str] = []

    for joint_key, metrics in sensor_readings.items():
        try:
            joint = JointName(joint_key.lower())
        except ValueError:
            # Fallback for unrecognized joint keys
            continue

        thresholds = JOINT_THRESHOLDS[joint]
        torque = metrics.get("torque", 0.0)
        temp = metrics.get("temp", 0.0)
        vibration = metrics.get("vibration", 0.0)

        # 1. Torque check (Instant mechanical overload / collision / gearbox jam)
        if torque >= thresholds.max_safe_torque:
            violations.append(
                f"CRITICAL SAFETY STOP: [{joint.value.upper()}] Torque {torque:.1f} Nm exceeds "
                f"immediate danger threshold of {thresholds.max_safe_torque:.1f} Nm."
            )

        # 2. Temperature check (Winding burnout / lubricant boiling / thermal destruction)
        if temp >= thresholds.max_safe_temp:
            violations.append(
                f"CRITICAL SAFETY STOP: [{joint.value.upper()}] Temperature {temp:.1f} °C exceeds "
                f"immediate danger threshold of {thresholds.max_safe_temp:.1f} °C."
            )

        # 3. Vibration check (ISO 10816 Class D - Catastrophic bearing flaking / cage breakage)
        if vibration >= thresholds.max_safe_vibration:
            violations.append(
                f"CRITICAL SAFETY STOP: [{joint.value.upper()}] Vibration {vibration:.2f} mm/s exceeds "
                f"immediate danger threshold of {thresholds.max_safe_vibration:.2f} mm/s."
            )

    is_emergency_stop = len(violations) > 0
    return is_emergency_stop, violations
