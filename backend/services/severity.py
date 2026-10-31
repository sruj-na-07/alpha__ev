"""
AlphaEV Severity-First Critical Issue Prioritization Service.

Provides deterministic, evidence-grounded severity assessment for EV reviews:
1. Evaluates potential harm, physical safety, operational impact, urgency, and confidence.
2. Ensures a single credible report of a severe safety issue outranks high-frequency minor complaints.
3. Preserves scientific uncertainty by tracking verification status (unverified complaint vs confirmed incident).
4. Groups similar problems into actionable clusters while retaining individual review IDs and verbatim evidence quotes.
5. Provides top 2 featured distinct problems for the dashboard plus a full register of all critical flags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Hazard Taxonomy & Severity Classifications
# ---------------------------------------------------------------------------

HAZARD_TAXONOMY: Dict[str, Dict[str, Any]] = {
    # 1. Critical Physical & Electrical Hazards (Base Score: 95 - 100)
    "electrical_thermal_hazard": {
        "severity": "Critical",
        "base_score": 98.0,
        "title": "Electrical Arcing, Sparking & Thermal Overheating",
        "category": "Physical Safety Hazard",
        "potential_harm": (
            "Severe risk of electrical shock, coupler melting, thermal runaway, or facility fire "
            "during high-voltage charging."
        ),
        "urgency": "Urgent Investigation Required",
        "recommended_action": (
            "Immediately disable the affected charging dispenser via central telemetry and dispatch "
            "certified high-voltage field technicians for coupler, contactor, and ground-fault inspection."
        ),
        "patterns": [
            r"\b(spark|sparks|sparking|sparked)\b",
            r"\b(fire|flame|flames|burned|burning smell)\b",
            r"\b(smoke|smoking)\b",
            r"\b(shock|shocks|shocked|electric shock|electrocuted)\b",
            r"\b(melt|melts|melted|melting|melted plastic|melted pin)\b",
            r"\b(explosion|exploded)\b",
            r"\b(exposed wire|exposed cable|bare wire)\b",
            r"\b(insulation fault|ground fault|earth fault)\b",
            r"\b(dangerously hot|overheating|scalding|burning hot)\b",
            r"\b(water in (plug|socket|connector|port))\b",
        ],
    },

    # 2. High Operational & Trapping Hazards (Base Score: 75 - 80)
    "vehicle_trapped_lock_failure": {
        "severity": "High",
        "base_score": 80.0,
        "title": "Connector Lock Failure & Vehicle Immobilization",
        "category": "Operational Entrapment",
        "potential_harm": (
            "Vehicle physically trapped at charging station due to motorized locking pin failure, "
            "causing complete immobilization and potential customer stranding."
        ),
        "urgency": "Urgent Operational Response",
        "recommended_action": (
            "Provide immediate remote unlock command or dispatch emergency technician to execute "
            "manual actuator release; inspect locking solenoid mechanism on dispenser."
        ),
        "patterns": [
            r"\b(stuck in (car|port|vehicle)|connector stuck|gun stuck|plug stuck)\b",
            r"\b(won't release|will not release|refuses? to unlock|locking pin stuck)\b",
            r"\b(unable to unplug|could not unplug|can't unplug|cannot unplug)\b",
            r"\b(trapped my (car|vehicle)|car is trapped|vehicle trapped)\b",
            r"\b(had to call (tow|towing|mechanic|emergency))\b",
        ],
    },

    "remote_stranding_emergency": {
        "severity": "High",
        "base_score": 75.0,
        "title": "Night-time / Remote Roadside Stranding",
        "category": "Passenger Safety & Stranding",
        "potential_harm": (
            "Customer stranded in remote, dark, or unsafe roadside conditions with critically low battery "
            "due to sudden charger shutoff or unannounced station closure."
        ),
        "urgency": "Urgent Operational Response",
        "recommended_action": (
            "Verify real-time operational status, dispatch roadside assistance or mobile charging support, "
            "and update live route-planning telemetry."
        ),
        "patterns": [
            r"\b(stranded (at night|in the dark|with family|with kids|alone|on highway))\b",
            r"\b(completely stranded|left me stranded|stranded at \d+%)\b",
            r"\b(deserted|pitch dark|no lights|unsafe location|unlit)\b",
            r"\b(battery (died|reached 0%|drained completely))\b",
        ],
    },

    # 3. Medium Operational & Financial Disruptions (Base Score: 40 - 45)
    "payment_deduction_no_charge": {
        "severity": "Medium",
        "base_score": 45.0,
        "title": "Payment Deducted with Zero Power Delivery",
        "category": "Financial & Billing Integrity",
        "potential_harm": (
            "Customer financial loss and session failure where funds or pre-authorization holds are captured "
            "without initiating energy transfer."
        ),
        "urgency": "Standard Operational Ticket",
        "recommended_action": (
            "Audit payment gateway webhook timeouts and auto-reverse failed pre-authorization holds "
            "within 15 minutes of non-start."
        ),
        "patterns": [
            r"\b(money deducted|amount deducted|balance deducted|debited)\b.*\b(not starting|didn't charge|zero (kwh|power)|failed)\b",
            r"\b(charged twice|double charge|deducted twice)\b",
            r"\b(no refund|refund not received|waiting for refund)\b",
        ],
    },

    "hardware_station_offline": {
        "severity": "Medium",
        "base_score": 40.0,
        "title": "Hardware Breakdown & Unresponsive Dispenser",
        "category": "Equipment Reliability",
        "potential_harm": (
            "Complete station outage preventing vehicle charging, causing travel delays and customer frustration."
        ),
        "urgency": "Standard Maintenance",
        "recommended_action": (
            "Reboot station controller remotely, test grid power supply, and schedule preventative contactor maintenance."
        ),
        "patterns": [
            r"\b(out of service|not working|broken charger|completely dead|black screen)\b",
            r"\b(screen (blank|frozen|rebooting|dead))\b",
            r"\b(emergency stop (pressed|stuck|activated))\b",
            r"\b(frequent breakdown|constantly broken|never working)\b",
        ],
    },

    "charging_speed_throttled": {
        "severity": "Medium",
        "base_score": 35.0,
        "title": "Severe Charging Rate Throttling",
        "category": "Performance Degradation",
        "potential_harm": (
            "Significantly extended charging times due to power conversion faults or cable cooling throttling."
        ),
        "urgency": "Performance Optimization",
        "recommended_action": (
            "Check liquid cooling levels on high-power cables and inspect dispenser power module allocation."
        ),
        "patterns": [
            r"\b(extremely slow|charging (too|very) slow|speed dropped to \d+kw)\b",
            r"\b(rated for \d+kw but (getting|gave) \d+kw)\b",
            r"\b(throttled|throttling|power drop)\b",
        ],
    },

    "app_connectivity_failure": {
        "severity": "Medium",
        "base_score": 35.0,
        "title": "Mobile App Crash & Connectivity Failure",
        "category": "Digital Experience",
        "potential_harm": (
            "Inability to authenticate or initiate charging sessions via mobile application."
        ),
        "urgency": "Software Release",
        "recommended_action": (
            "Diagnose BLE / OCPP backend socket drops and deploy stability hotfix to mobile app build."
        ),
        "patterns": [
            r"\b(app (keeps crashing|crashed|freezes|failed to open))\b",
            r"\b(bluetooth (won't connect|failure|disconnected))\b",
            r"\b(network error|server error|cannot login|login failed)\b",
        ],
    },

    # 4. Low Convenience & Aesthetic Issues (Base Score: 15 - 20)
    "queue_waiting_time": {
        "severity": "Low",
        "base_score": 20.0,
        "title": "Station Congestion & Queue Delays",
        "category": "Convenience & Capacity",
        "potential_harm": "Customer inconvenience and travel delay from high utilization.",
        "urgency": "Capacity Planning",
        "recommended_action": "Evaluate station utilization data to plan additional dispenser capacity or queue management.",
        "patterns": [
            r"\b(long queue|long wait|waited for \d+ (minutes|hours)|queue)\b",
            r"\b(too few chargers|need more chargers)\b",
        ],
    },

    "amenities_and_location": {
        "severity": "Low",
        "base_score": 15.0,
        "title": "Site Amenities, Shelter & Access Guidance",
        "category": "Site Amenities",
        "potential_harm": "Minor customer discomfort or difficulty locating charging stalls.",
        "urgency": "Quality of Life",
        "recommended_action": "Add weather canopies, lighting, trash receptacles, and improved directional signage.",
        "patterns": [
            r"\b(no (shelter|roof|shade|cover|canopy))\b",
            r"\b(no (seating|chairs|restroom|toilet|dustbin|trash))\b",
            r"\b(difficult to find|poor directions|hard to locate)\b",
            r"\b(dirty|littered|unclean)\b",
        ],
    },

    "pricing_transparency": {
        "severity": "Low",
        "base_score": 15.0,
        "title": "Tariff Perception & Fee Transparency",
        "category": "Commercial & Pricing",
        "potential_harm": "Customer dissatisfaction regarding charging rates or idle fee structures.",
        "urgency": "Commercial Review",
        "recommended_action": "Clearly itemize pricing components and idle fee policies in mobile app prior to plug-in.",
        "patterns": [
            r"\b(expensive|overpriced|high price|hidden fees?|costly)\b",
            r"\b(parking fee|idle fee|expensive rate)\b",
        ],
    },
}


# ---------------------------------------------------------------------------
# Data Models for Severity Assessment
# ---------------------------------------------------------------------------

@dataclass
class ReviewSeverityAssessment:
    review_id: str
    original_text: str
    cleaned_text: str
    rating: Optional[float]
    hazard_key: str
    severity: str  # "Critical", "High", "Medium", "Low"
    base_score: float
    evidence_confidence: float
    priority_score: float
    title: str
    category: str
    potential_harm: str
    urgency: str
    verification_status: str  # "unverified_complaint", "under_investigation", "verified_incident"
    evidence_quote: str
    matched_patterns: List[str] = field(default_factory=list)

    @property
    def status_display(self) -> str:
        mapping = {
            "unverified_complaint": "Unverified Customer Complaint (Pending Technical Inspection)",
            "under_investigation": "Under Engineering Investigation",
            "verified_incident": "Verified Field Incident",
        }
        return mapping.get(self.verification_status, "Unverified Customer Complaint")


@dataclass
class ProblemCluster:
    hazard_key: str
    title: str
    category: str
    severity: str  # "Critical", "High", "Medium", "Low"
    potential_harm: str
    urgency: str
    priority_score: float
    complaint_count: int
    evidence_confidence: float
    verification_status: str
    recommended_action: str
    supporting_review_ids: List[str] = field(default_factory=list)
    supporting_reviews: List[Dict[str, Any]] = field(default_factory=list)
    top_evidence_quote: str = ""

    @property
    def status_display(self) -> str:
        mapping = {
            "unverified_complaint": "Unverified Customer Complaint (Pending Technical Inspection)",
            "under_investigation": "Under Engineering Investigation",
            "verified_incident": "Verified Field Incident",
        }
        return mapping.get(self.verification_status, "Unverified Customer Complaint")


# ---------------------------------------------------------------------------
# Severity Assessment Service
# ---------------------------------------------------------------------------

class SeverityService:
    """
    Evaluates individual reviews for potential hazards, assigns deterministic severity scores,
    and groups findings into ranked problem clusters.
    """

    def __init__(self):
        # Compile all regex patterns for efficient matching
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        for h_key, h_data in HAZARD_TAXONOMY.items():
            self._compiled_patterns[h_key] = [
                re.compile(p, re.IGNORECASE) for p in h_data["patterns"]
            ]

    def calculate_evidence_confidence(
        self,
        text: str,
        rating: Optional[float],
        matched_count: int,
    ) -> float:
        """
        Calculates an evidence credibility score between 0.50 and 1.00 based on
        technical detail density, length, specific symptoms, and star rating alignment.
        """
        confidence = 0.70  # Baseline

        # Detailed reviews provide more credible evidence
        words = text.split()
        if len(words) >= 15:
            confidence += 0.10
        elif len(words) < 6:
            confidence -= 0.15

        # Technical/hardware terminology adds concrete credibility
        technical_terms = [
            "ccs", "ccs2", "type 2", "chademo", "kw", "kwh", "voltage", "pin", "gun",
            "cable", "screen", "contactor", "bms", "fuse", "relay", "breaker",
            "dispenser", "stall", "charger", "app", "rfid", "upi"
        ]
        text_lower = text.lower()
        if any(term in text_lower for term in technical_terms):
            confidence += 0.10

        # Star rating alignment: severe complaints typically correlate with 1 or 2 stars
        if rating is not None:
            if rating <= 2.0:
                confidence += 0.05
            elif rating >= 4.0:
                confidence -= 0.15  # Positive review mentioning hazard term casually

        # Multiple distinct hazard indicator matches reinforce credibility
        if matched_count > 1:
            confidence += 0.05

        return round(max(0.50, min(1.00, confidence)), 2)

    def assess_review(
        self,
        review_id: str,
        text: str,
        rating: Optional[float] = None,
        cleaned_text: Optional[str] = None,
    ) -> Optional[ReviewSeverityAssessment]:
        """
        Analyzes a single review to evaluate if it describes a recognized problem or safety hazard.
        Returns ReviewSeverityAssessment or None if no problem pattern matches.
        """
        content = (cleaned_text or text or "").strip()
        if not content:
            return None

        detected_hazards: List[Tuple[str, float, List[str]]] = []

        # Evaluate against hazard taxonomy in priority order
        for h_key, patterns in self._compiled_patterns.items():
            matches = []
            for pat in patterns:
                found = pat.findall(content)
                if found:
                    matches.extend(found if isinstance(found[0], str) else [m[0] for m in found])

            if matches:
                h_data = HAZARD_TAXONOMY[h_key]
                base_score = float(h_data["base_score"])
                detected_hazards.append((h_key, base_score, matches))

        if not detected_hazards:
            return None

        # Pick highest base severity hazard detected in this review
        detected_hazards.sort(key=lambda x: x[1], reverse=True)
        top_hazard_key, base_score, matched_patterns = detected_hazards[0]
        hazard_data = HAZARD_TAXONOMY[top_hazard_key]

        conf = self.calculate_evidence_confidence(content, rating, len(matched_patterns))

        # Base priority score for an individual review
        # Critical safety issues start with a high base score regardless of frequency
        priority_score = round(base_score * conf, 2)

        # Extract concise quote containing evidence
        quote = content
        if len(quote) > 180:
            quote = quote[:177] + "..."

        return ReviewSeverityAssessment(
            review_id=review_id,
            original_text=text,
            cleaned_text=content,
            rating=rating,
            hazard_key=top_hazard_key,
            severity=hazard_data["severity"],
            base_score=base_score,
            evidence_confidence=conf,
            priority_score=priority_score,
            title=hazard_data["title"],
            category=hazard_data["category"],
            potential_harm=hazard_data["potential_harm"],
            urgency=hazard_data["urgency"],
            verification_status="unverified_complaint",  # Preserves uncertainty
            evidence_quote=quote,
            matched_patterns=matched_patterns,
        )

    def group_and_prioritize_issues(
        self,
        assessments: List[ReviewSeverityAssessment],
    ) -> Tuple[List[ProblemCluster], List[Dict[str, Any]]]:
        """
        Aggregates individual assessments into distinct problem clusters.
        Ranks clusters using the severity-first deterministic formula:
            Score = (Base Severity * Avg Confidence) + min(Count - 1, 5) * 1.0

        Returns:
            (ranked_problem_clusters, all_critical_flags)
        """
        if not assessments:
            return [], []

        # Group by hazard key
        clusters: Dict[str, List[ReviewSeverityAssessment]] = {}
        all_critical_flags: List[Dict[str, Any]] = []

        for ass in assessments:
            clusters.setdefault(ass.hazard_key, []).append(ass)

            if ass.severity == "Critical":
                all_critical_flags.append({
                    "review_id": ass.review_id,
                    "hazard_key": ass.hazard_key,
                    "title": ass.title,
                    "severity": ass.severity,
                    "priority_score": ass.priority_score,
                    "evidence_confidence": ass.evidence_confidence,
                    "verification_status": ass.verification_status,
                    "potential_harm": ass.potential_harm,
                    "urgency": ass.urgency,
                    "evidence_quote": ass.evidence_quote,
                    "rating": ass.rating,
                })

        ranked_clusters: List[ProblemCluster] = []

        for h_key, items in clusters.items():
            h_data = HAZARD_TAXONOMY[h_key]
            complaint_count = len(items)
            avg_conf = sum(i.evidence_confidence for i in items) / complaint_count
            base_score = float(h_data["base_score"])

            # Deterministic Severity-First Scoring:
            # Base severity weighted by confidence + bounded frequency boost (max +5 pts)
            freq_boost = min(complaint_count - 1, 5) * 1.0
            urgency_bonus = 5.0 if h_data["severity"] == "Critical" else 0.0

            final_priority_score = round(
                (base_score * avg_conf) + freq_boost + urgency_bonus,
                2
            )

            # Sort supporting reviews by lowest rating / highest confidence
            sorted_items = sorted(
                items,
                key=lambda x: (x.rating if x.rating is not None else 999, -x.evidence_confidence)
            )

            supporting_ids = [i.review_id for i in sorted_items]
            supporting_reviews = [
                {
                    "review_id": i.review_id,
                    "quote": i.evidence_quote,
                    "rating": i.rating,
                    "confidence": i.evidence_confidence,
                    "status": i.verification_status,
                }
                for i in sorted_items[:5]  # Top 5 representative evidence quotes
            ]

            top_quote = sorted_items[0].evidence_quote if sorted_items else ""

            cluster = ProblemCluster(
                hazard_key=h_key,
                title=h_data["title"],
                category=h_data["category"],
                severity=h_data["severity"],
                potential_harm=h_data["potential_harm"],
                urgency=h_data["urgency"],
                priority_score=final_priority_score,
                complaint_count=complaint_count,
                evidence_confidence=round(avg_conf, 2),
                verification_status="unverified_complaint",
                recommended_action=h_data["recommended_action"],
                supporting_review_ids=supporting_ids,
                supporting_reviews=supporting_reviews,
                top_evidence_quote=top_quote,
            )
            ranked_clusters.append(cluster)

        # Sort clusters: Severity tier first (Critical > High > Medium > Low), then Priority Score
        severity_rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        ranked_clusters.sort(
            key=lambda c: (
                severity_rank.get(c.severity, 0),
                c.priority_score,
            ),
            reverse=True,
        )

        # Sort critical flags by priority score descending
        all_critical_flags.sort(key=lambda x: x["priority_score"], reverse=True)

        return ranked_clusters, all_critical_flags

    def extract_top_featured_problems(
        self,
        ranked_clusters: List[ProblemCluster],
        limit: int = 2,
    ) -> List[ProblemCluster]:
        """
        Returns exactly the top `limit` (default 2) highest-priority distinct problems.
        If fewer than 2 Critical problems exist, displays the highest-priority available
        problems (e.g. High or Medium) without falsely labeling them as Critical.
        """
        return ranked_clusters[:limit]


# Global service singleton
severity_service = SeverityService()


# Convenience module-level aliases
def assess_review_severity(
    review_id: Any,
    text: str,
    rating: Optional[float] = None,
    cleaned_text: Optional[str] = None,
    **kwargs: Any,
) -> Optional[ReviewSeverityAssessment]:
    return severity_service.assess_review(
        review_id=str(review_id),
        text=text,
        rating=rating,
        cleaned_text=cleaned_text,
    )


def calculate_evidence_confidence(
    text: str,
    rating: Optional[float] = None,
    matched_count: int = 1,
) -> float:
    return severity_service.calculate_evidence_confidence(text, rating=rating, matched_count=matched_count)


def group_and_prioritize_issues(
    assessments: List[ReviewSeverityAssessment],
) -> Tuple[List[ProblemCluster], List[Dict[str, Any]]]:
    return severity_service.group_and_prioritize_issues(assessments)


def extract_top_featured_problems(
    ranked_clusters: List[ProblemCluster],
    limit: int = 2,
) -> List[Dict[str, Any]]:
    clusters = severity_service.extract_top_featured_problems(ranked_clusters, limit=limit)
    return [
        {
            "hazard_key": c.hazard_key,
            "title": c.title,
            "category": c.category,
            "severity": c.severity,
            "priority_score": c.priority_score,
            "complaint_count": c.complaint_count,
            "evidence_confidence": c.evidence_confidence,
            "verification_status": c.verification_status,
            "urgency": c.urgency,
            "potential_harm": c.potential_harm,
            "recommended_action": c.recommended_action,
            "supporting_review_ids": c.supporting_review_ids,
            "supporting_reviews": c.supporting_reviews,
            "top_evidence_quote": c.top_evidence_quote,
        }
        for c in clusters
    ]
