"""
Unit tests for deterministic explanation templates.
Strictly verifies that ZERO forbidden words exist in any generated explanation.
"""

from backend.app.models.contracts import (
    Finding,
    FindingCategory,
    FindingStatus,
    FindingStrength,
    FindingTier,
    ReviewerAction,
)
from backend.app.services.explanation import (
    COMPILED_FORBIDDEN_REGEX,
    EXPLANATION_TEMPLATES,
    generate_finding_explanation,
)


def test_zero_forbidden_words_in_all_templates():
    forbidden_terms = ["fraud", "forged", "fake", "counterfeit", "confirmed fraud"]

    for rule_id, template in EXPLANATION_TEMPLATES.items():
        finding = Finding(
            finding_id="F-TEST",
            tier=FindingTier.INCONSISTENCY,
            category=FindingCategory.WITHIN_DOCUMENT,
            rule_id=rule_id,
            title=f"Test for {rule_id}",
            evidence=[],
            signals=[rule_id],
            strength=FindingStrength.STRONG,
            confidence=0.9,
            status=FindingStatus.REQUIRES_INVESTIGATION,
            explanation=f"Testing rule {rule_id} values discrepancy.",
            reviewer=ReviewerAction(),
        )
        text = generate_finding_explanation(finding)

        # Assert no forbidden words
        assert not COMPILED_FORBIDDEN_REGEX.search(text)
        for term in forbidden_terms:
            assert term not in text.lower(), f"Forbidden word '{term}' found in rule '{rule_id}' explanation: {text}"

        # Assert contains actionable next steps and why it matters
        assert "Forensic Context:" in text
        assert "Recommended Action:" in text
