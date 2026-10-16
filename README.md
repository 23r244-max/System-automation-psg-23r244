# Robotic Arm Joint Health Monitoring System

An end-to-end industrial health monitoring, predictive maintenance, and sensor spoofing defense system for a fleet of 6-axis robotic arms.

Developed for **23IF02 · System Automation — Bonus Challenge**.

---

## 📁 Repository Structure

```
robotic_arm_health_monitor/
├── config.py                 # Joint specifications, physics limits, and threshold definitions
├── safety_stop.py            # Deterministic immediate safety stop (Requirement 1 - Zero ML)
├── dataset_generator.py      # Synthetic historical dataset generator (Requirement 2 - 150 records)
├── historical_joint_data.csv # Generated historical training dataset (>50 samples)
├── model.py                  # Random Forest predictive wear classifier & feature evaluator (Req 2)
├── wear_model.joblib         # Serialized trained model
├── nlp_log_analyzer.py       # Free-text technician maintenance note NLP scanner (Req 3)
├── maintenance_logs.txt      # Sample maintenance log file (10 entries, mixed relevant & noise)
├── sensor_defense.py         # Cross-sensor physical spoofing defense (Requirement 4)
├── decision_engine.py        # Multi-signal decision fusion engine (Requirement 5)
├── main.py                   # Full end-to-end pipeline runner & fleet demonstration
├── test_pipeline.py          # Automated test suite verifying all requirements & constraints
├── EXPLANATION.md            # Required written explanation (half-page technical justification)
└── README.md                 # Project documentation & instructions
```

---

## 🚀 Quick Start & Execution

### 1. Run the Complete End-to-End Pipeline
Executes the dataset generation, ML training, log parsing, and fleet health assessment across 5 real-world scenarios:
```bash
python main.py
```

### 2. Run Automated Unit & Integration Tests
Verifies immediate safety stops, reachability of all 4 decisions, spoof detection, and NLP parsing:
```bash
python test_pipeline.py
```

### 3. Generate a Fresh Historical Dataset
Generates an updated synthetic historical dataset:
```bash
python dataset_generator.py
```

---

## 🎯 Verification of All 5 Requirements & Constraints

| # | Requirement | Implementation Module | Verification Status |
|---|---|---|---|
| **1** | **Immediate Safety Stop** | `safety_stop.py` | ✅ Instant, deterministic, hard limits. **Zero ML dependency**. |
| **2** | **Predictive Wear Detection** | `model.py`, `dataset_generator.py` | ✅ Trained on 150 historical records; 94.7% test accuracy. |
| **3** | **Maintenance Notes Signal** | `nlp_log_analyzer.py`, `maintenance_logs.txt` | ✅ NLP parser extracts arm, joint, filters noise, scores severity. |
| **4** | **Spoofed-Sensor Defense** | `sensor_defense.py` | ✅ Cross-sensor thermodynamic coupling flags forged torque. |
| **5** | **One Decision Per Arm** | `decision_engine.py` | ✅ All 4 states reachable: `SAFE`, `MONITOR`, `SCHEDULE_MAINTENANCE`, `EMERGENCY_STOP`. |
