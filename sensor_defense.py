"""
Spoofed-Sensor Defense Module (Requirement 4).

Defends against sensor spoofing attacks where an adversary or compromised node
injects false normal/low torque readings to conceal real physical degradation
and suppress automated maintenance or safety alarms.

Uses cross-sensor physical coupling (thermodynamic and vibrational energy conservation)
and residual consistency checks to detect forged telemetry.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from config import JOINT_THRESHOLDS, MIN_TORQUE_AT_HIGH_STRESS, JointName


@dataclass
class DefenseResult:
    is_spoofed: bool
    confidence: float
    affected_joints: List[str]
    reasons: List[str]


def detect_sensor_spoofing(sensor_readings: Dict[str, Dict[str, float]]) -> DefenseResult:
    """
    Performs multi-sensor cross-validation to detect forged torque readings.

    Physical Principle:
    In a robotic joint, mechanical friction, vibration, and temperature are coupled:
    P_friction = tau_loss * angular_velocity.
    Elevated temperature (T > warning) and high vibration (RMS > warning) cannot
    physically occur during manipulator operation if the torque is at minimum or idle.
    If vibration and temperature indicate severe mechanical stress while reported torque
    is artificially suppressed/flatlined, a spoofing attack is occurring.
    """
    spoof_detected = False
    affected_joints = []
    reasons = []
    max_confidence = 0.0

    for joint_key, metrics in sensor_readings.items():
        try:
            joint = JointName(joint_key.lower())
        except ValueError:
            continue

        thresholds = JOINT_THRESHOLDS[joint]
        reported_tau = metrics.get("torque", 0.0)
        temp = metrics.get("temp", 0.0)
        vibration = metrics.get("vibration", 0.0)

        # Condition 1: High Stress Cross-Sensor Discrepancy
        # Severe vibration or temperature observed, but torque is falsely reported as low/normal
        temp_elevated = temp >= thresholds.warn_temp
        vib_elevated = vibration >= thresholds.warn_vibration
        min_expected_torque = MIN_TORQUE_AT_HIGH_STRESS.get(joint, 50.0)

        if (temp_elevated and vib_elevated) and (reported_tau < min_expected_torque):
            spoof_detected = True
            affected_joints.append(joint.value)
            conf = min(0.99, 0.70 + 0.15 * ((vibration - thresholds.warn_vibration) / 2.0))
            max_confidence = max(max_confidence, conf)
            reasons.append(
                f"SPOOF ATTACK DETECTED on [{joint.value.upper()}]: "
                f"Reported torque ({reported_tau:.1f} Nm) is artificially low while "
                f"temp ({temp:.1f} °C) and vibration ({vibration:.2f} mm/s) indicate extreme friction. "
                f"Physical coupling violation (expected torque >= {min_expected_torque:.1f} Nm)."
            )

        # Condition 2: Extreme Thermal Runaway with Sub-Nominal Torque
        # Temperature is near shutdown (>72°C), but torque is reported near zero/idle
        elif (temp >= thresholds.warn_temp + 8.0) and (reported_tau < thresholds.nominal_torque_range[0]):
            spoof_detected = True
            affected_joints.append(joint.value)
            max_confidence = max(max_confidence, 0.95)
            reasons.append(
                f"SPOOF ATTACK DETECTED on [{joint.value.upper()}]: "
                f"Critical thermal level ({temp:.1f} °C) with impossible near-zero torque ({reported_tau:.1f} Nm)."
            )

        # Condition 3: Impossible Negative or Zero Torque Under Heavy Dynamic Motion
        # High vibration (> 4.0 mm/s) indicates active movement, yet torque is <= 0.0 Nm
        elif vibration > 4.0 and reported_tau <= 0.5:
            spoof_detected = True
            affected_joints.append(joint.value)
            max_confidence = max(max_confidence, 0.98)
            reasons.append(
                f"SPOOF ATTACK DETECTED on [{joint.value.upper()}]: "
                f"Reported torque ({reported_tau:.1f} Nm) is zero/negative despite active high-vibration motion ({vibration:.2f} mm/s)."
            )

    return DefenseResult(
        is_spoofed=spoof_detected,
        confidence=round(max_confidence, 2) if spoof_detected else 0.0,
        affected_joints=affected_joints,
        reasons=reasons
    )
