# Robotic Arm Joint Health Monitoring System — Architecture & Design Rationale

**Course / Module:** 23IF02 · System Automation — Bonus Challenge  
**Target Platform:** 6-Axis Robotic Arm Assembly Line Fleet  
**Monitored Joints:** Shoulder (J2), Elbow (J3), Wrist (J5)  
**Monitored Modalities:** Joint Torque ($Nm$), Temperature ($^\circ C$), Vibration RMS ($mm/s$), Free-Text Maintenance Logs  

---

## 1. Why Specific Safety Thresholds Were Chosen (Immediate Safety Stop)

The immediate safety stop operates as a deterministic, zero-latency safety interlock with **zero ML dependency**. The thresholds are derived from physical failure modes of industrial 6-axis articulated robots (e.g., harmonic drives, cycloidal reducers, and brushless servomotors):

| Joint | Metric | Threshold | Physical Rationale & Failure Mode |
|---|---|---|---|
| **Shoulder (J2)** | Torque | **180.0 Nm** | High-load vertical lift axis. 180 Nm represents structural yield limits; exceeding this causes catastrophic harmonic drive flexspline tooth shearing or gear teeth fracture. |
| **Elbow (J3)** | Torque | **130.0 Nm** | Mid-arm cantilever joint. Over-torque indicates collision, axis lockup, or bearing seizure. |
| **Wrist (J5)** | Torque | **65.0 Nm** | High-speed orientation axis with delicate micro-cycloidal gearing. 65 Nm is the mechanical shear safety limit. |
| **All Joints** | Temperature | **75.0 – 80.0 °C** | Industrial servomotor Class F/H windings can withstand electrical heat, but harmonic drive synthetic grease (fluorinated/ester based) suffers irreversible thermal oxidation and viscosity breakdown above 80 °C, precipitating rapid boundary friction and galling. |
| **All Joints** | Vibration | **7.5 – 8.5 mm/s** | Derived from **ISO 10816 / ISO 20816 Class D vibration severity criteria** ("Unrestricted damage occurs"). Vibration RMS $>8.5\text{ mm/s}$ signifies severe bearing raceway spalling, ball cage fragmentation, or loose structural casting. |

---

## 2. How the Predictive Model & Maintenance Log Combine into a Final Decision

The system uses a **hierarchical, defense-in-depth decision fusion engine** that combines quantitative high-frequency telemetry with qualitative human domain observations:

```
[ Raw Sensor Telemetry ]  ──────────> [ Immediate Safety Stop Check ] ──(Exceeded)──> EMERGENCY_STOP
           │                                      │ (Pass)
           ├───> [ Spoofed-Sensor Defense ] ──────┴─(Spoof Confirmed)───────────────> SCHEDULE_MAINTENANCE / EMERGENCY_STOP
           │                │ (Pass)
           ├───> [ ML Predictive Wear Model ] ───┐
           │     (Trained on Historical Data)    │
           │                                     ├──> [ Decision Fusion Matrix ] ───> SAFE
[ Technician Text Log ] ──> [ NLP Log Analyzer ] ─┘                                 │ MONITOR
                            (Domain Lexicon)                                        │ SCHEDULE_MAINTENANCE
                                                                                    │ EMERGENCY_STOP
```

### Fusion Priority Rules:
1. **Emergency Safety Override (Priority 1):** If any instantaneous sensor metric violates hard physical safety thresholds, `EMERGENCY_STOP` is triggered immediately. The ML pipeline is completely bypassed to prevent software latency or model hallucinations from delaying physical protection.
2. **Security Integrity Breach (Priority 2):** If the spoofed-sensor defense flags forged torque while other channels indicate severe stress, the arm is flagged as compromised and escalated to `EMERGENCY_STOP` or `SCHEDULE_MAINTENANCE`.
3. **Critical Mechanical Alert (Priority 3):** If the Random Forest model predicts `CRITICAL_WEAR` ($P(\text{Wear}) > 0.70$) **OR** the technician log contains critical indicators (e.g., *"metal shavings"*, *"tactile grinding"*, *"burnt black oil"*, *"severe backlash"*), the decision becomes `SCHEDULE_MAINTENANCE`.
4. **Early Degradation & Advisory (Priority 4):** If the model predicts `MODERATE_WEAR`, **OR** sensors enter the warning band, **OR** technician notes report mild auditory/tactile concerns (e.g., *"faint whining"*, *"warm to touch"*, *"minor play"*), the decision becomes `MONITOR` (triggering increased sensor logging and shift inspection).
5. **Nominal Clearance (Priority 5):** When all sensors are within baseline limits, the ML model confirms healthy state, no spoofing is detected, and logs report clean inspections, the decision is `SAFE`.

---

## 3. Spoofed-Sensor Defense: Mechanics, Capabilities & Limitations

### How It Works:
The defense is grounded in **thermodynamic energy conservation and mechanical friction coupling**:
$$\Delta T \propto P_{\text{friction}} = \mu \cdot \tau_{\text{loss}} \cdot \omega$$
When mechanical joints degrade (micro-pitting, gear tooth wear, lubrication dry-out), the dynamic friction coefficient $\mu$ spikes. The motor MUST supply increased counter-torque to maintain angular speed $\omega$, while lost mechanical power converts into dissipated heat ($\Delta T$) and high-frequency structural vibration ($RMS_{\text{vib}}$).

An attacker attempting to suppress alarms by falsifying torque down to nominal (e.g., reporting $42\text{ Nm}$ on a heavy shoulder joint) while temperature is surging ($73.5^\circ C$) and vibration is excessive ($7.2\text{ mm/s}$) creates a **physically impossible thermodynamic state**. The defense evaluates cross-sensor residuals; when high vibration and thermal escalation occur alongside artificially low or zero torque, a `SPOOF ATTACK DETECTED` security alert is raised.

### What Kind of Attack It WOULD Catch:
- **Single-Channel Torque Forgery:** Attackers or rogue telemetry nodes falsifying joint torque to "normal" values to silence alarms while physical degradation escalates.
- **Uncoupled Low-Torque Injections:** Any spoofed torque reading that violates the minimum torque floor required under high vibrational and thermal stress.
- **Flatline / Zero / Negative Torque Spoofs:** Injecting zero or negative torque during active, vibrating robot motions.

### What Kind of Attack It WOULD NOT Catch:
- **Coordinated Multi-Channel Digital Twin Spoofing:** If an adversary compromises **all three sensor channels** (torque, temperature, AND vibration) simultaneously and feeds synthetic values generated by a high-fidelity physics model of a healthy robot.
- **In-Band Stealth Drift:** Gradual, minute torque bias injections that remain within legitimate multi-variable normal covariance envelopes.
- **Unmonitored Subsystem Failures:** Attacks or physical faults on sensors outside the monitored joint cluster (e.g., end-effector vacuum pressure or pneumatic grip sensors).
