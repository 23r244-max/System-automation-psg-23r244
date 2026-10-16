"""
Predictive Joint Wear Detection Model (Requirement 2).

Trains a machine learning model on historical joint failure/wear data
to detect incipient mechanical degradation before it crosses into
immediate safety stop territory.
"""

import os
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib

FEATURE_COLUMNS = [
    "shoulder_torque", "shoulder_temp", "shoulder_vibration",
    "elbow_torque", "elbow_temp", "elbow_vibration",
    "wrist_torque", "wrist_temp", "wrist_vibration",
]

TARGET_COLUMN = "wear_level"  # 0: NORMAL, 1: MODERATE_WEAR, 2: CRITICAL_WEAR
MODEL_FILE = os.path.join(os.path.dirname(__file__), "wear_model.joblib")
DATASET_FILE = os.path.join(os.path.dirname(__file__), "historical_joint_data.csv")


class JointWearPredictor:
    def __init__(self, model_path: str = MODEL_FILE):
        self.model_path = model_path
        self.model = None
        self.class_labels = {0: "NORMAL", 1: "MODERATE_WEAR", 2: "CRITICAL_WEAR"}

    def train(self, data_path: str = DATASET_FILE) -> Dict[str, Any]:
        """Trains the Random Forest wear classifier and saves the artifact."""
        if not os.path.exists(data_path):
            from dataset_generator import generate_synthetic_dataset
            df = generate_synthetic_dataset(150)
            df.to_csv(data_path, index=False)
        else:
            df = pd.read_csv(data_path)

        X = df[FEATURE_COLUMNS]
        y = df[TARGET_COLUMN]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y
        )

        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            min_samples_split=3,
            random_state=42
        )
        clf.fit(X_train, y_train)

        y_pred = clf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, target_names=["NORMAL", "MODERATE_WEAR", "CRITICAL_WEAR"], output_dict=True)

        feature_importances = dict(zip(FEATURE_COLUMNS, clf.feature_importances_))
        # Sort feature importances descending
        feature_importances = dict(sorted(feature_importances.items(), key=lambda item: item[1], reverse=True))

        self.model = clf
        joblib.dump(clf, self.model_path)

        return {
            "accuracy": acc,
            "test_samples": len(y_test),
            "feature_importances": feature_importances,
            "classification_report": report
        }

    def load_or_train(self) -> None:
        """Loads saved model or trains a new one if missing."""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                return
            except Exception:
                pass
        self.train()

    def predict_arm(self, sensor_readings: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """
        Predicts wear level from structured joint sensor readings.

        Parameters:
            sensor_readings: {
                "shoulder": {"torque": ..., "temp": ..., "vibration": ...},
                "elbow":    {"torque": ..., "temp": ..., "vibration": ...},
                "wrist":    {"torque": ..., "temp": ..., "vibration": ...}
            }

        Returns:
            {
                "predicted_class": "NORMAL" | "MODERATE_WEAR" | "CRITICAL_WEAR",
                "wear_level": 0 | 1 | 2,
                "wear_risk_score": float (0.0 to 1.0, probability of wear),
                "class_probabilities": Dict[str, float],
                "top_degrading_joint": str
            }
        """
        if self.model is None:
            self.load_or_train()

        # Format input vector
        feature_vector = [
            sensor_readings.get("shoulder", {}).get("torque", 0.0),
            sensor_readings.get("shoulder", {}).get("temp", 0.0),
            sensor_readings.get("shoulder", {}).get("vibration", 0.0),
            sensor_readings.get("elbow", {}).get("torque", 0.0),
            sensor_readings.get("elbow", {}).get("temp", 0.0),
            sensor_readings.get("elbow", {}).get("vibration", 0.0),
            sensor_readings.get("wrist", {}).get("torque", 0.0),
            sensor_readings.get("wrist", {}).get("temp", 0.0),
            sensor_readings.get("wrist", {}).get("vibration", 0.0),
        ]

        X_input = pd.DataFrame([feature_vector], columns=FEATURE_COLUMNS)
        pred_level = int(self.model.predict(X_input)[0])
        probabilities = self.model.predict_proba(X_input)[0]

        prob_dict = {
            self.class_labels[i]: round(float(prob), 3)
            for i, prob in enumerate(probabilities)
        }

        # Wear risk score is probability of non-normal (moderate + critical)
        wear_risk_score = round(float(1.0 - prob_dict.get("NORMAL", 1.0)), 3)

        # Identify which joint has the largest relative anomaly compared to nominal
        from config import JOINT_THRESHOLDS, JointName
        joint_stresses = {}
        for j_enum in [JointName.SHOULDER, JointName.ELBOW, JointName.WRIST]:
            t = JOINT_THRESHOLDS[j_enum]
            m = sensor_readings.get(j_enum.value, {})
            # Normalized stress score against warning limits
            tau_ratio = m.get("torque", 0.0) / t.warn_torque
            temp_ratio = m.get("temp", 0.0) / t.warn_temp
            vib_ratio = m.get("vibration", 0.0) / t.warn_vibration
            joint_stresses[j_enum.value] = max(tau_ratio, temp_ratio, vib_ratio)

        top_joint = max(joint_stresses.items(), key=lambda x: x[1])[0]

        return {
            "predicted_class": self.class_labels[pred_level],
            "wear_level": pred_level,
            "wear_risk_score": wear_risk_score,
            "class_probabilities": prob_dict,
            "top_degrading_joint": top_joint,
        }


if __name__ == "__main__":
    predictor = JointWearPredictor()
    metrics = predictor.train()
    print(f"Model Training Accuracy: {metrics['accuracy'] * 100:.2f}%")
    print("Top Feature Importances:")
    for feat, imp in list(metrics["feature_importances"].items())[:5]:
        print(f"  - {feat}: {imp:.4f}")
