"""
Unit tests for three-tier classification escalation and review priority scoring.
"""

from backend.app.models.contracts import (
    EvidenceItem,
    Finding,
    FindingCategory,
    FindingStatus,
    FindingStrength,
    FindingTier,
    ReviewPriority,
    ReviewerAction,
)
from backend.app.services.escalation import EscalationEngine


def test_single_signal_never_exceeds_inconsistency():
    engine = EscalationEngine()
    f = Finding(
        finding_id="F1",
        tier=FindingTier.INCONSISTENCY,
        category=FindingCategory.WITHIN_DOCUMENT,
        rule_id="salary_net_pay_calc",
        title="Salary net pay mismatch",
        evidence=[EvidenceItem(doc_id="DOC1", page=1, bbox=[100, 200, 200, 250])],
        signals=["salary_math_break"],
        strength=FindingStrength.STRONG,
        confidence=0.9,
        status=FindingStatus.REQUIRES_INVESTIGATION,
        explanation="",
        reviewer=ReviewerAction(),
    )
    escalated = engine.escalate_findings([f])
    assert len(escalated) == 1
    assert escalated[0].tier == FindingTier.INCONSISTENCY


def test_two_signals_on_same_region_escalate_to_potential_manipulation():
    engine = EscalationEngine()
    # Signal 1: Math break in Net Pay box
    f1 = Finding(
        finding_id="F1",
        tier=FindingTier.INCONSISTENCY,
        category=FindingCategory.WITHIN_DOCUMENT,
        rule_id="salary_net_pay_calc",
        title="Salary net pay mismatch",
        evidence=[EvidenceItem(doc_id="DOC1", page=1, bbox=[100, 200, 200, 250])],
        signals=["salary_math_break"],
        strength=FindingStrength.STRONG,
        confidence=0.9,
        status=FindingStatus.REQUIRES_INVESTIGATION,
        explanation="",
        reviewer=ReviewerAction(),
    )
    # Signal 2: Font anomaly on the exact same box
    f2 = Finding(
        finding_id="F2",
        tier=FindingTier.OBSERVATION,
        category=FindingCategory.FORENSIC,
        rule_id="font_anomaly",
        title="Font anomaly on Net Pay",
        evidence=[EvidenceItem(doc_id="DOC1", page=1, bbox=[100, 200, 200, 250])],
        signals=["font_deviant_courier"],
        strength=FindingStrength.MODERATE,
        confidence=0.9,
        status=FindingStatus.REQUIRES_INVESTIGATION,
        explanation="",
        reviewer=ReviewerAction(),
    )
    escalated = engine.escalate_findings([f1, f2])
    # Both converge on the same region: must escalate to POTENTIAL_MANIPULATION
    assert escalated[0].tier == FindingTier.POTENTIAL_MANIPULATION


def test_review_priority_scoring_bands():
    engine = EscalationEngine()
    # High priority finding (bank balance continuity = 30 + salary mismatch = 25 -> 55 >= 45)
    f_high1 = Finding(
        finding_id="F1",
        tier=FindingTier.INCONSISTENCY,
        category=FindingCategory.WITHIN_DOCUMENT,
        rule_id="bank_balance_continuity",
        title="Bank break",
        evidence=[],
        signals=[],
        strength=FindingStrength.STRONG,
        confidence=0.9,
        status=FindingStatus.REQUIRES_INVESTIGATION,
        explanation="",
        reviewer=ReviewerAction(),
    )
    f_high2 = Finding(
        finding_id="F2",
        tier=FindingTier.INCONSISTENCY,
        category=FindingCategory.WITHIN_DOCUMENT,
        rule_id="salary_net_pay_calc",
        title="Salary math",
        evidence=[],
        signals=[],
        strength=FindingStrength.STRONG,
        confidence=0.9,
        status=FindingStatus.REQUIRES_INVESTIGATION,
        explanation="",
        reviewer=ReviewerAction(),
    )
    p, score, breakdown = engine.calculate_review_priority([f_high1, f_high2])
    assert p == ReviewPriority.HIGH
    assert score == 55
    assert len(breakdown) == 2
