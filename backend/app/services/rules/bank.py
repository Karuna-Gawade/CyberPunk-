"""
Pure validation rule for bank account statement running balance ledger continuity.
Audits transaction rows sequentially:
Current Balance = Previous Balance + Credit - Debit
Explicitly flags the FIRST row where the ledger math breaks.
"""

from typing import Any, Dict, List, Optional
from backend.app.models.contracts import (
    EvidenceItem,
    FindingStrength,
    FindingTier,
    RuleResult,
    RuleStatus,
    BBox,
)

LEDGER_TOLERANCE_INR = 1.0


def validate_bank_running_balance(
    transactions: List[Dict[str, Any]],
    opening_balance: Optional[float] = None,
    closing_balance: Optional[float] = None,
    field_id: str = "F-BANK-TX",
    doc_id: str = "DOC-BANK",
    page: int = 1,
    table_bbox: Optional[BBox] = None,
) -> RuleResult:
    """
    Validates row-by-row transaction continuity and overall statement balance.
    Pinpoints the exact first broken row.
    Never throws on missing data.
    """
    table_bbox = table_bbox or [0, 0, 0, 0]

    if not transactions or len(transactions) == 0:
        return RuleResult(
            rule_id="bank_balance_continuity",
            result=RuleStatus.NOT_APPLICABLE,
            field_ids_used=[field_id],
            detail="No transaction rows available for ledger continuity checking.",
        )

    # If opening balance is missing, attempt to seed from row 0
    if opening_balance is None:
        first_tx = transactions[0]
        # Inferred opening = row0 balance - row0 credit + row0 debit
        opening_balance = first_tx.get("balance", 0.0) - first_tx.get("credit", 0.0) + first_tx.get("debit", 0.0)

    running = opening_balance

    for row_idx, tx in enumerate(transactions, start=1):
        debit = float(tx.get("debit") or 0.0)
        credit = float(tx.get("credit") or 0.0)
        reported_bal = float(tx.get("balance") or 0.0)

        expected_bal = running + credit - debit
        diff = abs(expected_bal - reported_bal)

        if diff > LEDGER_TOLERANCE_INR:
            date_str = tx.get("date", "Unknown Date")
            desc = tx.get("description", "Unknown Description")
            return RuleResult(
                rule_id="bank_balance_continuity",
                result=RuleStatus.FAIL,
                field_ids_used=[field_id],
                detail=(
                    f"Bank ledger math break at row {row_idx} ({date_str} - '{desc}'): "
                    f"prior balance was {running:,.2f}, credit of {credit:,.2f}, debit of {debit:,.2f} "
                    f"yields expected balance {expected_bal:,.2f}, but statement reports {reported_bal:,.2f} "
                    f"(discrepancy of {diff:,.2f} INR)."
                ),
                tier=FindingTier.INCONSISTENCY,
                strength=FindingStrength.STRONG,
                title=f"Bank statement running balance continuity break at row {row_idx}",
                evidence=[EvidenceItem(doc_id=doc_id, field_id=field_id, page=page, bbox=table_bbox)],
                signals=["bank_running_balance_break"],
            )

        running = reported_bal

    # Verify overall closing balance if provided
    if closing_balance is not None:
        diff_closing = abs(running - closing_balance)
        if diff_closing > LEDGER_TOLERANCE_INR:
            return RuleResult(
                rule_id="bank_balance_continuity",
                result=RuleStatus.FAIL,
                field_ids_used=[field_id],
                detail=f"Final transaction row balance ({running:,.2f}) does not match statement closing balance header ({closing_balance:,.2f}).",
                tier=FindingTier.INCONSISTENCY,
                strength=FindingStrength.STRONG,
                title="Bank statement closing balance header mismatch",
                evidence=[EvidenceItem(doc_id=doc_id, field_id=field_id, page=page, bbox=table_bbox)],
                signals=["bank_closing_balance_mismatch"],
            )

    return RuleResult(
        rule_id="bank_balance_continuity",
        result=RuleStatus.PASS,
        field_ids_used=[field_id],
        detail=f"All {len(transactions)} transaction rows maintain continuous ledger balance math.",
    )
