"""
Intelligent Cross-Document Relationship Discovery Service for PS-2.
Constructs an Entity-Document Knowledge Graph discovering:
1. Canonical entity nodes (Persons, PAN, Aadhaar, Bank Accounts, Employers, Amounts, Dates)
2. Document provenance and ownership linkages (OWNS, ISSUED_BY, EMPLOYS, DEPOSITED_TO)
3. Relational cross-validation vs. contradictory evidence edges (CROSS_VALIDATES vs CONTRADICTS)
4. Overall bundle consistency score
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from backend.app.models.contracts import (
    CrossDocRelationshipGraph,
    DocumentRecord,
    Finding,
    FindingTier,
    RelationshipEdge,
    RelationshipNode,
)
from backend.app.services.correlation.name_match import compare_names


def _clean_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def build_cross_document_relationship_graph(
    documents: List[DocumentRecord],
    findings: Optional[List[Finding]] = None,
) -> CrossDocRelationshipGraph:
    """
    Analyzes all documents and extracted fields in an investigation to construct
    an interactive cross-document relationship network.
    """
    nodes: List[RelationshipNode] = []
    edges: List[RelationshipEdge] = []
    node_ids: Set[str] = set()

    def add_node(node: RelationshipNode):
        if node.id not in node_ids:
            nodes.append(node)
            node_ids.add(node.id)

    # 1. Add document nodes
    for doc in documents:
        add_node(
            RelationshipNode(
                id=f"doc_{doc.doc_id}",
                label=f"{doc.type.value.upper()}: {doc.filename}",
                type="document",
                doc_id=doc.doc_id,
                properties={
                    "doc_id": doc.doc_id,
                    "filename": doc.filename,
                    "type": doc.type.value,
                    "status": doc.status.value,
                    "confidence": doc.type_confidence,
                    "languages": doc.detected_languages,
                    "has_handwriting": doc.has_handwriting,
                },
            )
        )

    # 2. Extract entities per document
    doc_persons: Dict[str, List[str]] = {}
    doc_pans: Dict[str, List[str]] = {}
    doc_aadhaars: Dict[str, List[str]] = {}
    doc_accounts: Dict[str, List[str]] = {}
    doc_employers: Dict[str, List[str]] = {}
    doc_amounts: Dict[str, List[float]] = {}

    for doc in documents:
        d_id = doc.doc_id
        doc_persons[d_id] = []
        doc_pans[d_id] = []
        doc_aadhaars[d_id] = []
        doc_accounts[d_id] = []
        doc_employers[d_id] = []
        doc_amounts[d_id] = []

        for f in doc.fields:
            fname = f.name.lower()
            val = _clean_str(f.value)
            if not val or f.unable_to_assess:
                continue

            # Person Names
            if any(k in fname for k in ("name", "applicant", "beneficiary", "cardholder", "employee")):
                if len(val) >= 3 and not re.search(r"^\d+$", val):
                    doc_persons[d_id].append(val)
                    p_id = f"person_{re.sub(r'[^a-zA-Z0-9]', '_', val.lower())}"
                    add_node(
                        RelationshipNode(
                            id=p_id,
                            label=val,
                            type="person",
                            doc_id=d_id,
                            properties={"name": val, "source_doc": doc.filename},
                        )
                    )
                    edges.append(
                        RelationshipEdge(
                            id=f"edge_{d_id}_{p_id}",
                            source=f"doc_{d_id}",
                            target=p_id,
                            relation="DECLARES_IDENTITY",
                            confidence=f.confidence,
                            status="consistent",
                        )
                    )

            # PAN Identifiers
            pan_match = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", val.upper())
            if pan_match or "pan" in fname:
                pan_num = pan_match.group(0) if pan_match else val.upper()
                if len(pan_num) == 10:
                    doc_pans[d_id].append(pan_num)
                    pan_node_id = f"id_pan_{pan_num}"
                    add_node(
                        RelationshipNode(
                            id=pan_node_id,
                            label=f"PAN: {pan_num}",
                            type="identifier",
                            doc_id=d_id,
                            properties={"identifier_type": "PAN", "value": pan_num},
                        )
                    )
                    edges.append(
                        RelationshipEdge(
                            id=f"edge_{d_id}_{pan_node_id}",
                            source=f"doc_{d_id}",
                            target=pan_node_id,
                            relation="RECORDS_PAN",
                            confidence=f.confidence,
                            status="consistent",
                        )
                    )

            # Aadhaar Identifiers
            aadhaar_match = re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", val) or re.search(r"\b\d{12}\b", val)
            if aadhaar_match or "aadhaar" in fname:
                a_num = aadhaar_match.group(0) if aadhaar_match else val
                doc_aadhaars[d_id].append(a_num)
                a_node_id = f"id_aadhaar_{re.sub(r'[^0-9]', '', a_num)}"
                add_node(
                    RelationshipNode(
                        id=a_node_id,
                        label=f"Aadhaar: {a_num}",
                        type="identifier",
                        doc_id=d_id,
                        properties={"identifier_type": "Aadhaar", "value": a_num},
                    )
                )
                edges.append(
                    RelationshipEdge(
                        id=f"edge_{d_id}_{a_node_id}",
                        source=f"doc_{d_id}",
                        target=a_node_id,
                        relation="RECORDS_AADHAAR",
                        confidence=f.confidence,
                        status="consistent",
                    )
                )

            # Bank Accounts
            if "account" in fname or "from_account" in fname or "to_account" in fname:
                acc_clean = re.sub(r"[^a-zA-Z0-9]", "", val)
                if len(acc_clean) >= 6:
                    doc_accounts[d_id].append(val)
                    acc_node_id = f"acc_{acc_clean}"
                    add_node(
                        RelationshipNode(
                            id=acc_node_id,
                            label=f"Account: {val}",
                            type="bank_account",
                            doc_id=d_id,
                            properties={"account_number": val},
                        )
                    )
                    edges.append(
                        RelationshipEdge(
                            id=f"edge_{d_id}_{acc_node_id}",
                            source=f"doc_{d_id}",
                            target=acc_node_id,
                            relation="REFERENCES_ACCOUNT",
                            confidence=f.confidence,
                            status="consistent",
                        )
                    )

            # Employer / Organization
            if "employer" in fname or "company" in fname or "organization" in fname:
                if len(val) >= 3:
                    doc_employers[d_id].append(val)
                    emp_node_id = f"org_{re.sub(r'[^a-zA-Z0-9]', '_', val.lower())}"
                    add_node(
                        RelationshipNode(
                            id=emp_node_id,
                            label=f"Org: {val}",
                            type="employer",
                            doc_id=d_id,
                            properties={"organization": val},
                        )
                    )
                    edges.append(
                        RelationshipEdge(
                            id=f"edge_{d_id}_{emp_node_id}",
                            source=f"doc_{d_id}",
                            target=emp_node_id,
                            relation="EMPLOYS_OR_ISSUED_BY",
                            confidence=f.confidence,
                            status="consistent",
                        )
                    )

    # 3. Cross-Document Relational Discovery & Consistency Check
    contradictions_count = 0
    doc_ids = [d.doc_id for d in documents]

    for i in range(len(doc_ids)):
        for j in range(i + 1, len(doc_ids)):
            d1_id = doc_ids[i]
            d2_id = doc_ids[j]

            # Cross-check Persons across d1 and d2
            p1_list = doc_persons.get(d1_id, [])
            p2_list = doc_persons.get(d2_id, [])

            for p1 in p1_list:
                for p2 in p2_list:
                    sim, _, _ = compare_names(p1, p2)
                    p1_node_id = f"person_{re.sub(r'[^a-zA-Z0-9]', '_', p1.lower())}"
                    p2_node_id = f"person_{re.sub(r'[^a-zA-Z0-9]', '_', p2.lower())}"

                    if sim >= 0.85:
                        edges.append(
                            RelationshipEdge(
                                id=f"rel_{d1_id}_{d2_id}_{len(edges)}",
                                source=p1_node_id,
                                target=p2_node_id,
                                relation="CROSS_VALIDATES",
                                confidence=round(sim, 2),
                                status="consistent",
                                details=f"Identity cross-validated across documents ({sim * 100:.1f}% matching confidence).",
                            )
                        )
                    elif 0.30 <= sim < 0.70:
                        contradictions_count += 1
                        edges.append(
                            RelationshipEdge(
                                id=f"rel_{d1_id}_{d2_id}_{len(edges)}",
                                source=p1_node_id,
                                target=p2_node_id,
                                relation="CONTRADICTS",
                                confidence=round(1.0 - sim, 2),
                                status="contradiction",
                                details=f"Identity discrepancy: '{p1}' vs '{p2}' (low match confidence: {sim * 100:.1f}%).",
                            )
                        )

            # Cross-check PAN numbers across d1 and d2
            pans1 = doc_pans.get(d1_id, [])
            pans2 = doc_pans.get(d2_id, [])
            for pan1 in pans1:
                for pan2 in pans2:
                    node1 = f"id_pan_{pan1}"
                    node2 = f"id_pan_{pan2}"
                    if pan1 == pan2:
                        edges.append(
                            RelationshipEdge(
                                id=f"pan_match_{len(edges)}",
                                source=node1,
                                target=node2,
                                relation="CROSS_VALIDATES",
                                confidence=1.0,
                                status="consistent",
                                details=f"Identical Permanent Account Number ({pan1}) verified across documents.",
                            )
                        )
                    else:
                        contradictions_count += 1
                        edges.append(
                            RelationshipEdge(
                                id=f"pan_mismatch_{len(edges)}",
                                source=node1,
                                target=node2,
                                relation="CONTRADICTS",
                                confidence=0.95,
                                status="contradiction",
                                details=f"Conflicting PAN identifiers declared across bundle: {pan1} vs {pan2}.",
                            )
                        )

    # 4. Integrate Findings as Contradiction / Anomaly Edges
    if findings:
        for f in findings:
            if f.tier in (FindingTier.INCONSISTENCY, FindingTier.POTENTIAL_MANIPULATION):
                ev = f.evidence
                if len(ev) >= 2 and ev[0].doc_id != ev[1].doc_id:
                    contradictions_count += 1
                    edges.append(
                        RelationshipEdge(
                            id=f"finding_edge_{f.finding_id}",
                            source=f"doc_{ev[0].doc_id}",
                            target=f"doc_{ev[1].doc_id}",
                            relation="CONTRADICTS",
                            confidence=f.confidence,
                            status="contradiction",
                            details=f"{f.title}: {f.explanation[:120]}...",
                        )
                    )

    # Calculate overall bundle consistency score (0.0 to 1.0)
    total_edges = max(1, len(edges))
    consistency = max(0.10, min(1.0, round(1.0 - (contradictions_count * 0.25) / total_edges, 2)))

    return CrossDocRelationshipGraph(
        nodes=nodes,
        edges=edges,
        consistency_score=consistency,
        total_entities=len(nodes) - len(documents),
        contradictions_count=contradictions_count,
    )
