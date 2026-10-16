"""
Automated Test Suite for Robotic Arm Health Monitoring System.

Verifies:
1. Immediate safety stop triggers deterministically without ML model.
2. All 4 final decisions (SAFE, MONITOR, SCHEDULE_MAINTENANCE, EMERGENCY_STOP) are reachable.
3. Spoofed sensor defense catches fake low torque during high-stress conditions.
4. Maintenance notes NLP extracts arm IDs, filters irrelevant text, and identifies severity.
"""

import unittest
from config import ArmDecision, JOINT_THRESHOLDS, JointName
from safety_stop import check_immediate_safety_stop
from sensor_defense import detect_sensor_spoofing
from nlp_log_analyzer import MaintenanceLogAnalyzer, NoteSeverity
from decision_engine import ArmHealthDecisionEngine
from model import JointWearPredictor


class TestRoboticArmHealthMonitor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.predictor = JointWearPredictor()
        cls.predictor.load_or_train()
        cls.engine = ArmHealthDecisionEngine(predictor=cls.predictor)
        cls.log_analyzer = MaintenanceLogAnalyzer()

    def test_01_immediate_safety_stop_deterministic_zero_ml(self):
        """Constraint 1: Immediate safety stop must trigger on physical limits with zero ML."""
        # Over-torque on shoulder (> 180 Nm)
        dangerous_readings = {
            "shoulder": {"torque": 192.5, "temp": 45.0, "vibration": 1.2},
            "elbow":    {"torque": 50.0, "temp": 40.0, "vibration": 1.0},
            "wrist":    {"torque": 20.0, "temp": 35.0, "vibration": 0.8},
        }
        is_emergency, reasons = check_immediate_safety_stop(dangerous_readings)
        self.assertTrue(is_emergency)
        self.assertTrue(any("Torque" in r for r in reasons))

        # Over-temperature on elbow (> 78 °C)
        overtemp_readings = {
            "shoulder": {"torque": 80.0, "temp": 50.0, "vibration": 1.5},
            "elbow":    {"torque": 60.0, "temp": 82.0, "vibration": 1.8},
            "wrist":    {"torque": 20.0, "temp": 35.0, "vibration": 0.8},
        }
        is_emergency, reasons = check_immediate_safety_stop(overtemp_readings)
        self.assertTrue(is_emergency)
        self.assertTrue(any("Temperature" in r for r in reasons))

        # Over-vibration on wrist (> 7.5 mm/s)
        overvib_readings = {
            "shoulder": {"torque": 80.0, "temp": 50.0, "vibration": 1.5},
            "elbow":    {"torque": 60.0, "temp": 45.0, "vibration": 1.8},
            "wrist":    {"torque": 20.0, "temp": 35.0, "vibration": 8.1},
        }
        is_emergency, reasons = check_immediate_safety_stop(overvib_readings)
        self.assertTrue(is_emergency)
        self.assertTrue(any("Vibration" in r for r in reasons))

    def test_02_all_four_decisions_reachable(self):
        """Constraint 2: All 4 possible final decisions must each be reachable."""
        # 1. Reach SAFE
        safe_readings = {
            "shoulder": {"torque": 60.0, "temp": 40.0, "vibration": 1.2},
            "elbow":    {"torque": 40.0, "temp": 36.0, "vibration": 1.0},
            "wrist":    {"torque": 15.0, "temp": 32.0, "vibration": 0.7},
        }
        res_safe = self.engine.evaluate_arm("ARM-01", safe_readings, "Clean inspection, operating normally.")
        self.assertEqual(res_safe.decision, ArmDecision.SAFE)

        # 2. Reach MONITOR
        monitor_readings = {
            "shoulder": {"torque": 75.0, "temp": 45.0, "vibration": 1.5},
            "elbow":    {"torque": 105.0, "temp": 64.0, "vibration": 4.6},  # Warning band
            "wrist":    {"torque": 18.0, "temp": 35.0, "vibration": 0.9},
        }
        res_monitor = self.engine.evaluate_arm("ARM-02", monitor_readings, "Operator reported faint whining noise from Arm-02 elbow.")
        self.assertEqual(res_monitor.decision, ArmDecision.MONITOR)

        # 3. Reach SCHEDULE_MAINTENANCE
        maint_readings = {
            "shoulder": {"torque": 160.0, "temp": 72.0, "vibration": 7.0},
            "elbow":    {"torque": 65.0, "temp": 48.0, "vibration": 2.0},
            "wrist":    {"torque": 22.0, "temp": 38.0, "vibration": 1.2},
        }
        res_maint = self.engine.evaluate_arm("ARM-04", maint_readings, "Found fine metal shavings below shoulder gear casing.")
        self.assertEqual(res_maint.decision, ArmDecision.SCHEDULE_MAINTENANCE)

        # 4. Reach EMERGENCY_STOP
        estop_readings = {
            "shoulder": {"torque": 195.0, "temp": 50.0, "vibration": 1.5},  # Hard stop limit exceeded
            "elbow":    {"torque": 45.0, "temp": 38.0, "vibration": 1.0},
            "wrist":    {"torque": 15.0, "temp": 32.0, "vibration": 0.7},
        }
        res_estop = self.engine.evaluate_arm("ARM-06", estop_readings, None)
        self.assertEqual(res_estop.decision, ArmDecision.EMERGENCY_STOP)

    def test_03_spoofed_sensor_defense(self):
        """Requirement 4: Detect spoofed torque masking physical degradation."""
        # Shoulder has high temp and high vibration, but attacker faked torque to 35 Nm (safe)
        spoofed_readings = {
            "shoulder": {"torque": 35.0, "temp": 72.0, "vibration": 6.8},
            "elbow":    {"torque": 40.0, "temp": 38.0, "vibration": 1.0},
            "wrist":    {"torque": 15.0, "temp": 32.0, "vibration": 0.8},
        }
        defense = detect_sensor_spoofing(spoofed_readings)
        self.assertTrue(defense.is_spoofed)
        self.assertIn("shoulder", defense.affected_joints)

        # Legitimate healthy arm should NOT flag spoofing
        legit_readings = {
            "shoulder": {"torque": 70.0, "temp": 42.0, "vibration": 1.5},
            "elbow":    {"torque": 45.0, "temp": 38.0, "vibration": 1.1},
            "wrist":    {"torque": 16.0, "temp": 34.0, "vibration": 0.8},
        }
        defense_legit = detect_sensor_spoofing(legit_readings)
        self.assertFalse(defense_legit.is_spoofed)

    def test_04_maintenance_notes_nlp_parsing(self):
        """Requirement 3: Free text parsing, joint extraction, noise filtering."""
        # Irrelevant note
        res_noise = self.log_analyzer.analyze_entry("Shift handover meeting complete. Coffee machine refilled.")
        self.assertEqual(res_noise.severity, NoteSeverity.IRRELEVANT)
        self.assertFalse(res_noise.is_actionable)

        # Concern note
        res_concern = self.log_analyzer.analyze_entry("Arm-02 elbow making faint clicking and whining noises during motion.")
        self.assertEqual(res_concern.arm_id, "ARM-02")
        self.assertEqual(res_concern.joint, "elbow")
        self.assertEqual(res_concern.severity, NoteSeverity.CONCERN)
        self.assertTrue(res_concern.is_actionable)

        # Critical note
        res_crit = self.log_analyzer.analyze_entry("Discovered metal shavings under Arm-04 shoulder, grinding tactile feel!")
        self.assertEqual(res_crit.arm_id, "ARM-04")
        self.assertEqual(res_crit.joint, "shoulder")
        self.assertEqual(res_crit.severity, NoteSeverity.CRITICAL)
        self.assertTrue(res_crit.is_actionable)


if __name__ == "__main__":
    unittest.main()
