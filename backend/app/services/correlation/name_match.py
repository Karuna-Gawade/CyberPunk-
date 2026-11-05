"""
In-house Indian entity and name matching engine.
Uses pure Python standard library: custom Jaro-Winkler, Levenshtein, token sorting,
initials expansion, honorific normalization, and transliteration variant tables.
Zero external fuzzy libraries (strictly adheres to Section 3.1).
"""

import re
from typing import List, Set, Tuple

# Common Indian honorifics and titles to strip during normalization
HONORIFICS = {
    "mr", "mrs", "ms", "miss", "shri", "smt", "shrimati", "dr", "prof", "kumar", "kumari"
}

# Transliteration and phonetic substitution clusters
TRANSLITERATION_GROUPS = [
    {"mohammed", "mohammad", "mohamed", "muhammad", "muhammed", "md"},
    {"sai", "saie"},
    {"laxmi", "lakshmi"},
    {"choudhary", "chaudhary", "choudhury", "chowdhury"},
    {"iyer", "aiyer"},
    {"menon", "manon"},
    {"patil", "patel"},
    {"agarwal", "aggarwal", "agrawal"},
    {"prasad", "prasada"},
    {"sharma", "sarma"},
]


def normalize_token(token: str) -> str:
    """Normalizes an individual name token: lowercase, letters only, transliteration lookup."""
    t = re.sub(r"[^a-z]", "", token.lower())
    for group in TRANSLITERATION_GROUPS:
        if t in group:
            # Return canonical representative of the group (sorted first)
            return sorted(list(group))[0]
    return t


def normalize_name(name: str) -> List[str]:
    """
    Cleans punctuation, strips honorifics, normalizes tokens.
    Returns clean list of name tokens.
    """
    if not name:
        return []
    raw_tokens = re.split(r"[\s,.\-_]+", name.strip())
    tokens = []
    for raw in raw_tokens:
        clean = normalize_token(raw)
        if clean and clean not in HONORIFICS:
            tokens.append(clean)
    return tokens


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def jaro_distance(s1: str, s2: str) -> float:
    """Calculates Jaro similarity score (0.0 to 1.0)."""
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    match_distance = max(len1, len2) // 2 - 1
    s1_matches = [False] * len1
    s2_matches = [False] * len2

    matches = 0
    transpositions = 0

    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    return (
        (matches / len1)
        + (matches / len2)
        + ((matches - transpositions / 2) / matches)
    ) / 3.0


def jaro_winkler_similarity(s1: str, s2: str, prefix_weight: float = 0.1) -> float:
    """Calculates Jaro-Winkler similarity (0.0 to 1.0) with common prefix scaling."""
    jaro_sim = jaro_distance(s1, s2)
    if jaro_sim < 0.7:
        return jaro_sim

    # Find common prefix up to 4 characters
    prefix_len = 0
    for i in range(min(len(s1), len(s2), 4)):
        if s1[i] == s2[i]:
            prefix_len += 1
        else:
            break

    return jaro_sim + (prefix_len * prefix_weight * (1.0 - jaro_sim))


def match_initial_to_token(initial: str, token: str) -> bool:
    """Checks if a 1-character initial matches the first letter of a token."""
    return len(initial) == 1 and len(token) > 1 and initial[0] == token[0]


def compare_names(name1: str, name2: str) -> Tuple[float, str, str]:
    """
    Compares two Indian names using token permutation, initials expansion,
    and Jaro-Winkler metric.
    Returns:
      (score: 0-100, band: "match" | "needs_review" | "conflict", detail: str)
    """
    tokens1 = normalize_name(name1)
    tokens2 = normalize_name(name2)

    if not tokens1 or not tokens2:
        return 0.0, "conflict", "One or both names are empty"

    # Exact token match after order sorting (e.g. "Sharma Rahul" == "Rahul Sharma")
    if sorted(tokens1) == sorted(tokens2):
        return 100.0, "match", "Exact token match (including order permutations)"

    # Check for initials match (e.g. "Rahul S. Sharma" vs "Rahul Suresh Sharma")
    len1, len2 = len(tokens1), len(tokens2)
    if len1 == len2:
        initial_match_count = 0
        exact_match_count = 0
        for t1, t2 in zip(sorted(tokens1), sorted(tokens2)):
            if t1 == t2:
                exact_match_count += 1
            elif match_initial_to_token(t1, t2) or match_initial_to_token(t2, t1):
                initial_match_count += 1

        if exact_match_count + initial_match_count == len1:
            score = round(85.0 + (exact_match_count / len1) * 10.0, 1)
            return score, "needs_review", "Initials match across sibling tokens"

    # Full string Jaro-Winkler on sorted tokens
    str1 = " ".join(sorted(tokens1))
    str2 = " ".join(sorted(tokens2))
    jw_score = round(jaro_winkler_similarity(str1, str2) * 100.0, 1)

    # Token overlap ratio
    set1, set2 = set(tokens1), set(tokens2)
    overlap = len(set1.intersection(set2))
    total_unique = len(set1.union(set2))
    jaccard = (overlap / total_unique) if total_unique > 0 else 0.0

    composite_score = round((jw_score * 0.7) + (jaccard * 100.0 * 0.3), 1)

    # Band calibration
    if composite_score >= 88.0:
        band = "match"
        detail = f"High similarity match ({composite_score}%)"
    elif composite_score >= 65.0:
        band = "needs_review"
        detail = f"Minor name variation requires reviewer verification ({composite_score}%)"
    else:
        band = "conflict"
        detail = f"Significant name conflict ({composite_score}%)"

    return composite_score, band, detail
