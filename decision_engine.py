"""
Decision Fusion Engine (Requirement 5).

Combines:
1. Deterministic immediate safety check (Zero-ML hard physical trip)
2. Spoofed-sensor physical defense (Cross-sensor integrity validation)
3. ML predictive wear model (Historical pattern detection)
4. Free-text maintenance log NLP analysis (Technician qualitative observations)

Produces exactly ONE final decision per arm:
- SAFE: All sensors nominal, ML predicts healthy, no maintenance concerns.
- MONITOR: Early/moderate wear detected by ML, sensor in warning band, or technician noted minor concern.
- SCHEDULE_MAINTENANCE: Critical wear predicted, severe defect in logs (shavings/grinding), or spoof attack detected.
- EMERGENCY_STOP: Instant physical safety limit exceeded (deterministic hardware protection).
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from config import ArmDecision, JOINT_THRESHOLDS, JointName
from safety_stop import check_immediate_safety_stop
from sensor_defense import detect_sensor_spoofing, DefenseResult
from model import JointWearPredictor
from nlp_log_analyzer import MaintenanceLogAnalyzer, ParsedLogEntry, NoteSeverity


@dataclass
class ArmEvaluationReport:
    arm_id: str
    decision: ArmDecision
    primary_reason: str
    safety_stop_triggered: bool
    safety_violations: list
    spoof_detected: bool
    spoof_details: list
    ml_prediction: Dict[str, Any]
    nlp_log_signal: Optional[Dict[str, Any]]
    sensor_snapshot: Dict[str, Dict[str, float]]


class ArmHealthDecisionEngine:
    def __init__(self, predictor: Optional[JointWearPredictor] = None,
                 log_analyzer: Optional[MaintenanceLogAnalyzer] = None):
        self.predictor = predictor or JointWearPredictor()
        self.log_analyzer = log_analyzer or MaintenanceLogAnalyzer()

    def evaluate_arm(self,
                     arm_id: str,
                     sensor_readings: Dict[str, Dict[str, float]],
                     maintenance_note: Optional[str] = None) -> ArmEvaluationReport:
        """
        Executes the hierarchical decision pipeline for a robotic arm.
        """
        # STEP 1: Immediate Deterministic Safety Stop (HARD RULE - ZERO ML DEPENDENCE)
        is_emergency, safety_violations = check_immediate_safety_stop(sensor_readings)
        if is_emergency:
            return ArmEvaluationReport(
                arm_id=arm_id,
                decision=ArmDecision.EMERGENCY_STOP,
                primary_reason=f"Immediate safety stop triggered: {'; '.join(safety_violations)}",
                safety_stop_triggered=True,
                safety_violations=safety_violations,
                spoof_detected=False,
                spoof_details=[],
                ml_prediction={"status": "BYPASSED_DUE_TO_EMERGENCY_STOP"},
                nlp_log_signal=None,
                sensor_snapshot=sensor_readings
            )

        # STEP 2: Spoofed-Sensor Cross-Validation Defense
        defense_result: DefenseResult = detect_sensor_spoofing(sensor_readings)

        # STEP 3: Predictive ML Wear Detection
        ml_result = self.predictor.predict_arm(sensor_readings)

        # STEP 4: Technician Maintenance Note NLP Processing
        nlp_entry: Optional[ParsedLogEntry] = None
        if maintenance_note:
            nlp_entry = self.log_analyzer.analyze_entry(maintenance_note)

        # STEP 5: Multi-Signal Decision Fusion
        decision = ArmDecision.SAFE
        reasons = []

        # Priority 1: Security Alert - Spoofed Sensor Attack Detected
        if defense_result.is_spoofed:
            # If other uncompromised sensors are already in near-critical territory, stop immediately
            critical_sensors = any(
                sensor_readings.get(j.value, {}).get("temp", 0) >= JOINT_THRESHOLDS[j].max_safe_temp - 3.0 or
                sensor_readings.get(j.value, {}).get("vibration", 0) >= JOINT_THRESHOLDS[j].max_safe_vibration - 0.5
                for j in [JointName.SHOULDER, JointName.ELBOW, JointName.WRIST]
            )
            if critical_sensors:
                decision = ArmDecision.EMERGENCY_STOP
                reasons.append("Spoofed sensor attack detected under near-critical physical stress")
            else:
                decision = ArmDecision.SCHEDULE_MAINTENANCE
                reasons.append(f"Security Alert: Sensor spoofing detected ({defense_result.reasons[0]})")

        # Priority 2: Critical Wear or Critical Maintenance Log Finding
        elif (ml_result["predicted_class"] == "CRITICAL_WEAR" or
              (nlp_entry and nlp_entry.severity == NoteSeverity.CRITICAL)):
            decision = ArmDecision.SCHEDULE_MAINTENANCE
            if ml_result["predicted_class"] == "CRITICAL_WEAR":
                reasons.append(
                    f"Predictive ML detected CRITICAL_WEAR on {ml_result['top_degrading_joint']} "
                    f"(risk score: {ml_result['wear_risk_score']:.2f})"
                )
            if nlp_entry and nlp_entry.severity == NoteSeverity.CRITICAL:
                reasons.append(
                    f"Technician log noted CRITICAL defects ({', '.join(nlp_entry.matched_keywords)})"
                )

        # Priority 3: Early/Moderate Wear, Maintenance Concern, or Warning Band Sensor
        elif (ml_result["predicted_class"] == "MODERATE_WEAR" or
              (nlp_entry and nlp_entry.severity == NoteSeverity.CONCERN) or
              self._has_sensor_warning(sensor_readings)):
            decision = ArmDecision.MONITOR
            sub_reasons = []
            if ml_result["predicted_class"] == "MODERATE_WEAR":
                sub_reasons.append(f"ML wear prediction: MODERATE_WEAR on {ml_result['top_degrading_joint']}")
            if nlp_entry and nlp_entry.severity == NoteSeverity.CONCERN:
                sub_reasons.append(f"Technician log noted concern ({', '.join(nlp_entry.matched_keywords)})")
            if self._has_sensor_warning(sensor_readings):
                sub_reasons.append("Sensor metrics elevated in advisory warning zone")
            reasons.append(" | ".join(sub_reasons))

        # Priority 4: All Clear
        else:
            decision = ArmDecision.SAFE
            reasons.append("All joint sensors nominal, no spoofing detected, ML indicates healthy baseline, and logs clear.")

        return ArmEvaluationReport(
            arm_id=arm_id,
            decision=decision,
            primary_reason="; ".join(reasons),
            safety_stop_triggered=False,
            safety_violations=[],
            spoof_detected=defense_result.is_spoofed,
            spoof_details=defense_result.reasons,
            ml_prediction=ml_result,
            nlp_log_signal=asdict(nlp_entry) if nlp_entry else None,
            sensor_snapshot=sensor_readings
        )

    def _has_sensor_warning(self, sensor_readings: Dict[str, Dict[str, float]]) -> bool:
        """Checks if any sensor metric is elevated in the advisory warning band."""
        for joint_key, metrics in sensor_readings.items():
            try:
                joint = JointName(joint_key.lower())
            except ValueError:
                continue
            thresh = JOINT_THRESHOLDS[joint]
            if (metrics.get("torque", 0) >= thresh.warn_torque or
                metrics.get("temp", 0) >= thresh.warn_temp or
                metrics.get("vibration", 0) >= thresh.warn_vibration):
                return True
        return False
