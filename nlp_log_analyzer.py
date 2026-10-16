"""
Technician Maintenance Notes NLP & Signal Processing Module (Requirement 3).

Incorporate technician maintenance notes as an independent second signal
from free unstructured natural language text. Extracts arm references,
identifies joint associations, filters irrelevant chatter, and scores
mechanical severity.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class NoteSeverity(str, Enum):
    IRRELEVANT = "IRRELEVANT"
    NORMAL = "NORMAL"
    CONCERN = "CONCERN"
    CRITICAL = "CRITICAL"


@dataclass
class ParsedLogEntry:
    raw_text: str
    arm_id: Optional[str]
    joint: Optional[str]
    severity: NoteSeverity
    score: float             # 0.0 to 1.0 risk level
    matched_keywords: List[str]
    is_actionable: bool


# Domain-specific lexicons for industrial robotics maintenance
CRITICAL_KEYWORDS = [
    "metal shavings", "metal flakes", "grinding", "grinding noise",
    "burnt", "black oil", "burnt lubricant", "smoke", "burning odor",
    "severe backlash", "backlash", "jerking", "slipping", "jammed",
    "seized", "teeth sheared", "oil leakage", "catastrophic", "cracked housing"
]

CONCERN_KEYWORDS = [
    "whining", "squeaking", "squeak", "clicking", "clicking noise",
    "warm to touch", "hot to touch", "unusual noise", "abnormal vibration",
    "stiff movement", "sluggish", "minor play", "wobble", "resistance",
    "periodic knock", "chatter", "humming"
]

NORMAL_KEYWORDS = [
    "nominal", "no defects", "all clear", "operating normally",
    "passed inspection", "satisfactory", "routine inspection completed",
    "clean", "zero abnormalities", "good condition"
]

IRRELEVANT_PATTERNS = [
    r"breakroom", r"coffee", r"shift handover", r"lunch", r"network switch",
    r"wi-fi", r"meeting", r"badge access", r"fire drill", r"floor sweeping"
]


class MaintenanceLogAnalyzer:
    def __init__(self, log_file_path: Optional[str] = None):
        self.log_file_path = log_file_path

    def analyze_entry(self, text: str) -> ParsedLogEntry:
        """Parses a single free-text technician log entry."""
        lower_text = text.lower()

        # 1. Check if entirely irrelevant chatter
        for pattern in IRRELEVANT_PATTERNS:
            if re.search(pattern, lower_text):
                return ParsedLogEntry(
                    raw_text=text,
                    arm_id=None,
                    joint=None,
                    severity=NoteSeverity.IRRELEVANT,
                    score=0.0,
                    matched_keywords=[],
                    is_actionable=False
                )

        # 2. Extract Arm ID (e.g., ARM-01, Arm 02, Robot-3)
        arm_match = re.search(r"\b(?:arm|robot)[-\s]?([0-9]+)\b", lower_text)
        arm_id = f"ARM-{int(arm_match.group(1)):02d}" if arm_match else None

        # 3. Extract Joint Reference
        joint = None
        for j in ["shoulder", "elbow", "wrist"]:
            if j in lower_text:
                joint = j
                break

        # 4. Keyword matching & severity scoring
        crit_matches = [kw for kw in CRITICAL_KEYWORDS if kw in lower_text]
        concern_matches = [kw for kw in CONCERN_KEYWORDS if kw in lower_text]
        normal_matches = [kw for kw in NORMAL_KEYWORDS if kw in lower_text]

        if crit_matches:
            severity = NoteSeverity.CRITICAL
            score = 0.95
            matched = crit_matches
            actionable = True
        elif concern_matches:
            severity = NoteSeverity.CONCERN
            score = 0.60
            matched = concern_matches
            actionable = True
        elif normal_matches:
            severity = NoteSeverity.NORMAL
            score = 0.05
            matched = normal_matches
            actionable = False
        else:
            # If an arm is mentioned without standard keywords, evaluate general sentiment
            if arm_id:
                severity = NoteSeverity.NORMAL
                score = 0.10
                matched = ["generic mention"]
                actionable = False
            else:
                severity = NoteSeverity.IRRELEVANT
                score = 0.0
                matched = []
                actionable = False

        return ParsedLogEntry(
            raw_text=text,
            arm_id=arm_id,
            joint=joint,
            severity=severity,
            score=score,
            matched_keywords=matched,
            is_actionable=actionable
        )

    def parse_file(self, file_path: Optional[str] = None) -> Dict[str, ParsedLogEntry]:
        """
        Parses an entire maintenance log file and returns the highest severity entry
        for each referenced arm.
        """
        path = file_path or self.log_file_path
        if not path:
            raise ValueError("No log file path provided.")

        arm_entries: Dict[str, ParsedLogEntry] = {}

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parsed = self.analyze_entry(line)
                if parsed.arm_id:
                    # Keep the entry with highest severity score for that arm
                    if parsed.arm_id not in arm_entries or parsed.score > arm_entries[parsed.arm_id].score:
                        arm_entries[parsed.arm_id] = parsed

        return arm_entries
