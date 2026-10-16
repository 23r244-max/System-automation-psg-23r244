"""
Configuration and Physical Limits for 6-Axis Robotic Arm Monitoring System.

Monitored Joints:
- Shoulder: Joint 2 (primary payload & vertical lift load)
- Elbow: Joint 3 (flexion/extension, intermediate torque load)
- Wrist: Joint 5 (high velocity, orientation, precision load)

All physical units:
- Torque: Newton-meters (Nm)
- Temperature: Degrees Celsius (°C)
- Vibration: Root Mean Square velocity (mm/s) according to ISO 10816/20816
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict


class ArmDecision(str, Enum):
    SAFE = "SAFE"
    MONITOR = "MONITOR"
    SCHEDULE_MAINTENANCE = "SCHEDULE_MAINTENANCE"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class JointName(str, Enum):
    SHOULDER = "shoulder"
    ELBOW = "elbow"
    WRIST = "wrist"


@dataclass(frozen=True)
class SensorThresholds:
    # Immediate emergency safety stop limits (Hard physical thresholds)
    max_safe_torque: float       # Nm: exceeding causes instant motor/gearbox mechanical shear risk
    max_safe_temp: float         # °C: exceeding causes stator winding & lubricant thermal breakdown
    max_safe_vibration: float    # mm/s: exceeding causes catastrophic bearing failure (ISO Class D)

    # Early warning thresholds (Used for wear detection & monitor state)
    warn_torque: float
    warn_temp: float
    warn_vibration: float

    # Nominal expected baseline operating range
    nominal_torque_range: tuple  # (min, max)
    nominal_temp_range: tuple
    nominal_vibration_range: tuple


# Physical limits based on industrial 6-axis manipulator specifications
# (e.g., KUKA KR / FANUC / Universal Robots industrial arm classes)
JOINT_THRESHOLDS: Dict[JointName, SensorThresholds] = {
    JointName.SHOULDER: SensorThresholds(
        max_safe_torque=180.0,       # Max instantaneous safe torque
        max_safe_temp=80.0,          # Thermal shutdown limit
        max_safe_vibration=8.5,      # ISO 10816 Class D critical vibration limit
        warn_torque=140.0,
        warn_temp=65.0,
        warn_vibration=5.0,
        nominal_torque_range=(40.0, 110.0),
        nominal_temp_range=(35.0, 55.0),
        nominal_vibration_range=(0.8, 2.5),
    ),
    JointName.ELBOW: SensorThresholds(
        max_safe_torque=130.0,
        max_safe_temp=78.0,
        max_safe_vibration=8.0,
        warn_torque=100.0,
        warn_temp=62.0,
        warn_vibration=4.5,
        nominal_torque_range=(25.0, 75.0),
        nominal_temp_range=(32.0, 52.0),
        nominal_vibration_range=(0.7, 2.2),
    ),
    JointName.WRIST: SensorThresholds(
        max_safe_torque=65.0,
        max_safe_temp=75.0,
        max_safe_vibration=7.5,
        warn_torque=45.0,
        warn_temp=60.0,
        warn_vibration=4.0,
        nominal_torque_range=(8.0, 30.0),
        nominal_temp_range=(30.0, 48.0),
        nominal_vibration_range=(0.5, 1.8),
    ),
}

# Cross-sensor coupling expectations for spoofed-sensor defense
# If vibration or temperature is very high, torque cannot be physically near idle/minimum.
MIN_TORQUE_AT_HIGH_STRESS = {
    JointName.SHOULDER: 85.0,   # If temp > 65°C or vib > 5.0 mm/s, torque below this is physically implausible
    JointName.ELBOW: 60.0,
    JointName.WRIST: 22.0,
}
