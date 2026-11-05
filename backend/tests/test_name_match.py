"""
Unit tests for in-house Indian entity and name matching algorithms.
"""

from backend.app.services.correlation.name_match import (
    compare_names,
    jaro_winkler_similarity,
    levenshtein_distance,
)


def test_levenshtein_and_jaro_winkler_distance():
    assert levenshtein_distance("SHARMA", "SHARMA") == 0
    assert levenshtein_distance("SHARMA", "SARMA") == 1
    assert jaro_winkler_similarity("SHARMA", "SHARMA") == 1.0
    assert jaro_winkler_similarity("RAHUL", "ROHUL") > 0.80


def test_token_order_permutation_exact_match():
    # "Sharma Rahul" vs "Rahul Sharma" must produce 100% Match
    score, band, detail = compare_names("Sharma Rahul", "Rahul Sharma")
    assert score == 100.0
    assert band == "match"


def test_honorific_stripping():
    # "Mr. Rajesh Sharma" vs "Rajesh Sharma"
    score, band, _ = compare_names("Mr. Rajesh Sharma", "Rajesh Sharma")
    assert score == 100.0
    assert band == "match"


def test_transliteration_variants():
    # "Mohammed Farooq" vs "Muhammad Farooq"
    score, band, _ = compare_names("Mohammed Farooq", "Muhammad Farooq")
    assert score >= 90.0
    assert band == "match"


def test_initials_expansion_needs_review():
    # "Rahul S. Sharma" vs "Rahul Suresh Sharma" -> Needs Review observation
    score, band, detail = compare_names("Rahul S. Sharma", "Rahul Suresh Sharma")
    assert band == "needs_review"
    assert score >= 75.0


def test_distinct_names_conflict():
    # "Rahul Sharma" vs "Vikram Malhotra" -> Conflict
    score, band, detail = compare_names("Rahul Sharma", "Vikram Malhotra")
    assert band == "conflict"
    assert score < 50.0
