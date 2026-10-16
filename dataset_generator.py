"""
Synthetic Historical Dataset Generator for Robotic Arm Joint Wear (Requirement 2).

Generates at least 50 (we generate 150) realistic labeled historical readings
from past robotic arm operational cycles, simulating normal operations,
moderate mechanical wear (friction/lubrication breakdown), and severe wear
leading up to joint failures.
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from config import JOINT_THRESHOLDS, JointName


def generate_synthetic_dataset(n_samples: int = 150, random_seed: int = 42) -> pd.DataFrame:
    """
    Generates a physically realistic labeled historical dataset for arm health monitoring.

    Labels:
    - wear_level: 0 (Normal), 1 (Moderate Wear / Degraded), 2 (Critical Wear / Near Failure)
    - wear_status: String category ('NORMAL', 'MODERATE_WEAR', 'CRITICAL_WEAR')
    - requires_maintenance: Boolean (False for Normal, True for Moderate/Critical)
    """
    np.random.seed(random_seed)
    random.seed(random_seed)

    records = []
    base_time = datetime(2026, 8, 1, 8, 0, 0)

    # Class distribution: ~50% Normal, ~30% Moderate Wear, ~20% Critical Wear
    n_normal = int(n_samples * 0.50)
    n_moderate = int(n_samples * 0.30)
    n_critical = n_samples - n_normal - n_moderate

    categories = (
        [(0, "NORMAL", False)] * n_normal +
        [(1, "MODERATE_WEAR", True)] * n_moderate +
        [(2, "CRITICAL_WEAR", True)] * n_critical
    )
    random.shuffle(categories)

    for i, (wear_code, wear_label, req_maint) in enumerate(categories):
        arm_id = f"ARM-{(i % 12) + 1:02d}"
        sample_time = base_time + timedelta(hours=i * 4 + random.randint(0, 30))

        # Pick a primary degrading joint if worn
        degrading_joint = random.choice([JointName.SHOULDER, JointName.ELBOW, JointName.WRIST]) if wear_code > 0 else None

        row = {
            "sample_id": f"SMP-{i + 1:04d}",
            "arm_id": arm_id,
            "timestamp": sample_time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        for joint in [JointName.SHOULDER, JointName.ELBOW, JointName.WRIST]:
            thresh = JOINT_THRESHOLDS[joint]
            nom_tau_min, nom_tau_max = thresh.nominal_torque_range
            nom_temp_min, nom_temp_max = thresh.nominal_temp_range
            nom_vib_min, nom_vib_max = thresh.nominal_vibration_range

            is_degraded = (joint == degrading_joint) or (wear_code == 2 and random.random() < 0.35)

            if not is_degraded or wear_code == 0:
                # Normal nominal conditions
                torque = np.random.uniform(nom_tau_min, nom_tau_max)
                temp = np.random.uniform(nom_temp_min, nom_temp_max)
                vibration = np.random.uniform(nom_vib_min, nom_vib_max)
            elif wear_code == 1:
                # Moderate wear: Increased friction torque (+20-40%), elevated heat (+8-15°C), increased RMS vibration
                torque = np.random.uniform(nom_tau_max * 1.05, thresh.warn_torque)
                temp = np.random.uniform(nom_temp_max + 4.0, thresh.warn_temp)
                vibration = np.random.uniform(nom_vib_max * 1.2, thresh.warn_vibration)
            else:  # wear_code == 2: Critical wear
                # Severe degradation: High drag torque, near shutdown temperature, severe vibration harmonic peaks
                # Stays just below immediate stop to represent historical pre-failure operational degradation
                torque = np.random.uniform(thresh.warn_torque, thresh.max_safe_torque - 3.0)
                temp = np.random.uniform(thresh.warn_temp, thresh.max_safe_temp - 2.0)
                vibration = np.random.uniform(thresh.warn_vibration, thresh.max_safe_vibration - 0.4)

            # Add natural sensor white noise
            torque += np.random.normal(0, 0.8)
            temp += np.random.normal(0, 0.4)
            vibration += np.random.normal(0, 0.05)

            # Clamp to positive values
            row[f"{joint.value}_torque"] = round(max(0.0, torque), 2)
            row[f"{joint.value}_temp"] = round(max(15.0, temp), 2)
            row[f"{joint.value}_vibration"] = round(max(0.1, vibration), 2)

        row["wear_level"] = wear_code
        row["wear_status"] = wear_label
        row["requires_maintenance"] = int(req_maint)

        records.append(row)

    df = pd.DataFrame(records)
    return df


if __name__ == "__main__":
    output_path = os.path.join(os.path.dirname(__file__), "historical_joint_data.csv")
    df = generate_synthetic_dataset(n_samples=150)
    df.to_csv(output_path, index=False)
    print(f"Successfully generated synthetic dataset with {len(df)} rows.")
    print(f"Saved to: {output_path}")
    print("\nDataset Class Distribution:")
    print(df["wear_status"].value_counts())
    print("\nSample Preview:")
    print(df.head(3))
