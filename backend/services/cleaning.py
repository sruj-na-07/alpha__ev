import re
import html
import unicodedata
import hashlib
from typing import Dict, List, Tuple, Any, Optional, Set
from bs4 import BeautifulSoup

try:
    from langdetect import detect as lang_detect
    from langdetect import DetectorFactory
    DetectorFactory.seed = 0
except ImportError:
    lang_detect = None


# Common English stop words for low-information detection (excluding negations!)
NEGATION_WORDS = {
    "not", "no", "nor", "neither", "never", "none", "nobody", "nowhere",
    "nothing", "hardly", "scarcely", "barely", "cannot", "cant", "can't",
    "dont", "don't", "doesnt", "doesn't", "didnt", "didn't", "isnt", "isn't",
    "arent", "aren't", "wasnt", "wasn't", "werent", "weren't", "wont", "won't",
    "wouldnt", "wouldn't", "shouldnt", "shouldn't", "couldnt", "couldn't"
}

STANDARD_STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "could", "did", "do", "does", "doing", "down",
    "during", "each", "few", "for", "from", "further", "had", "has", "have",
    "having", "he", "her", "here", "hers", "herself", "him", "himself", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me",
    "more", "most", "my", "myself", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "she", "should", "so", "some", "such", "than", "that", "the", "their",
    "theirs", "them", "themselves", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "whom", "why", "with",
    "would", "you", "your", "yours", "yourself", "yourselves"
} - NEGATION_WORDS


# EV-specific protected terms pattern (case-insensitive checks, but preserve exact casings)
EV_TERMS = [
    r"\bCHAdeMO\b", r"\bCCS\b", r"\bCCS1\b", r"\bCCS2\b", r"\bNACS\b",
    r"\bTesla Supercharger\b", r"\bSupercharger\b", r"\bJ1772\b", r"\bType 2\b",
    r"\bGB/T\b", r"\bLevel [123]\b", r"\bL[123]\b", r"\bDC Fast Charger\b",
    r"\bDCFC\b", r"\bkWh\b", r"\bkW\b", r"\bSOC\b", r"\bBMS\b", r"\bOTA\b",
    r"\bRegen\b", r"\bRegenerative Braking\b", r"\bHeat Pump\b", r"\bWLTP\b",
    r"\bEPA\b", r"\bNEDC\b", r"\bEV\b", r"\bBEV\b", r"\bPHEV\b", r"\bFCEV\b",
    r"\bICE\b", r"\bV2L\b", r"\bV2G\b", r"\bV2H\b", r"\bMPGe\b",
    r"\b[A-Z0-9\_]{2,8}\_[a-zA-Z0-9\_]{3,8}\b",
    r"\bP[0-3][0-9A-F]{3}\b",
]

EV_REGEX = re.compile("|".join(EV_TERMS), re.IGNORECASE)


MOJIBAKE_MAP = {
    # Quotes & Apostrophes
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€\x9d": '"',
    "â€\x9c": '"',
    "â€\"": '"',

    # Dashes & Hyphens
    "â€“": "-",
    "â€”": "—",
    "â€•": "―",

    # Ellipsis & Bullet & Symbols
    "â€¦": "...",
    "â€¢": "•",
    "â„¢": "™",
    "â‚¬": "€",

    # Accented Letters
    "Ã©": "é",
    "Ã¨": "è",
    "Ã ": "à",
    "Ã§": "ç",
    "Ã¢": "â",
    "Ã´": "ô",
    "Ã®": "î",
    "Ã»": "û",
    "Ã«": "ë",
    "Ã¯": "ï",
    "Ã¼": "ü",
    "Ã¶": "ö",
    "Ã¤": "ä",
    "Ã±": "ñ",
    "Ã¡": "á",
    "Ã³": "ó",
    "Ãº": "ú",
    "Ã\xad": "í",
    "Ã\x89": "É",
    "Ã€": "À",
    "Ã‡": "Ç",

    # Degrees & Math & Misc
    "Â°": "°",
    "Â±": "±",
    "Â®": "®",
    "Â©": "©",
    "Â": "",
    "\xa0": " ",
    "\u200b": "",
    "\u200c": "",
    "\u200d": "",
    "\ufeff": "",
}


# Regex to match genuine HTML tags
HTML_TAG_PATTERN = re.compile(
    r"<!--[\s\S]*?-->|<\/?([a-zA-Z][a-zA-Z0-9]*)\b(?:\s+[^>]*?)?\/?>",
    re.IGNORECASE,
)

# Regex to match script and style blocks including their contents
SCRIPT_STYLE_PATTERN = re.compile(
    r"<(script|style)[^>]*>[\s\S]*?<\/\1>",
    re.IGNORECASE,
)

# Regex for promotional or web URLs
URL_PATTERN = re.compile(
    r"https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
    re.IGNORECASE,
)


def _safe_repair_mojibake_bytes(text: str) -> str:
    """
    Repair misencoded UTF-8 bytes decoded as cp1252 or latin-1 without
    failing when the text also contains emojis or non-Latin-1 characters.
    """
    if not any(c in text for c in ("Ã", "â", "ï", "¿", "½")):
        return text

    def repair_segment(match: re.Match) -> str:
        segment = match.group(0)
        for enc in ("cp1252", "latin-1"):
            try:
                raw = segment.encode(enc)
                decoded = raw.decode("utf-8")
                if decoded and not any(c in decoded for c in ("Ã", "â", "ï", "¿", "½")):
                    return decoded
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
        return segment

    return re.sub(r"[\xc0-\xff][\x80-\xbf]+", repair_segment, text)


def fix_encoding_and_mojibake(text: str) -> Tuple[str, bool]:
    """Fix common encoding artifacts and mojibake sequences while preserving emojis."""
    if not text:
        return "", False

    original = text

    for bad, good in MOJIBAKE_MAP.items():
        if bad in text:
            text = text.replace(bad, good)

    text = _safe_repair_mojibake_bytes(text)

    return text, text != original


def clean_html(text: str) -> Tuple[str, bool]:
    """
    Remove HTML tags while strictly preserving mathematical comparators
    (e.g., '< 20%' or '> 100kW') and unescaping HTML entities.
    """
    if not text:
        return "", False

    original = text

    text = SCRIPT_STYLE_PATTERN.sub(" ", text)

    has_html_tags = bool(HTML_TAG_PATTERN.search(text))
    if has_html_tags:
        text = HTML_TAG_PATTERN.sub(" ", text)

    if "&" in text and ";" in text:
        text = html.unescape(text)

    return text, has_html_tags or (text != original)


def normalize_unicode_and_whitespace(text: str) -> str:
    """Normalize unicode characters, remove zero-width characters, and collapse whitespace."""
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()


def extract_meaningful_tokens(text: str) -> List[str]:
    """
    Extract Unicode-aware tokens while preserving negations,
    contractions, numbers, and meaningful technical terms.
    """
    text = (text or "").lower()
    words = re.findall(
        r"[^\W_]+(?:['’\-][^\W_]+)*",
        text,
        flags=re.UNICODE,
    )

    meaningful = []
    for word in words:
        normalized_word = word.replace("’", "'")
        if normalized_word in NEGATION_WORDS:
            meaningful.append(normalized_word)
        elif normalized_word not in STANDARD_STOP_WORDS and len(normalized_word) > 1:
            meaningful.append(normalized_word)

    return meaningful


# Reviews that contain praise only, with no service-specific information.
GENERIC_PRAISE_WORDS = {
    "good", "great", "excellent", "amazing", "awesome", "superb",
    "fantastic", "wonderful", "nice", "best", "brilliant", "perfect",
    "outstanding", "love", "loved", "lovely", "cool", "wow", "beautiful",
    "app", "application", "experience", "service", "work", "working",
    "very", "really", "too", "so", "just", "simply", "absolutely",
    "extremely", "overall", "the", "is", "it", "its", "it's", "this",
    "that", "a", "an", "and", "my", "i", "we", "you", "your", "for",
    "of", "to", "thank", "thanks", "thankyou", "u", "all", "super",
    "useful", "user", "friendly", "easy", "smooth", "fast", "quick",
    "excellent", "😍", "👍", "❤️", "⭐", "🌟",
}

GENERIC_PRAISE_PHRASES = {
    "good", "very good", "really good", "too good", "great", "very great",
    "excellent", "amazing", "awesome", "superb", "fantastic", "wonderful",
    "nice", "very nice", "best", "brilliant", "perfect", "outstanding",
    "good app", "great app", "nice app", "excellent app", "amazing app",
    "awesome app", "superb app", "best app", "very good app",
    "good application", "great application", "nice application",
    "excellent application", "amazing application",
    "good experience", "great experience", "nice experience",
    "excellent experience", "amazing experience", "awesome experience",
    "love it", "loved it", "i love it", "i loved it",
    "thank you", "thanks", "thank u", "👍", "❤️", "😍",
}


def is_generic_praise_only(text: str) -> bool:
    """
    Exclude praise-only/reaction-only reviews, including sentence forms such
    as 'it's amazing', 'its good', 'this is a great app'. A review is kept
    as soon as it contains a concrete issue, feature, location, payment,
    charging, speed, availability, or other substantive detail.
    """
    value = unicodedata.normalize("NFKC", text or "").lower().strip()
    value = re.sub(r"https?://\S+|www\.\S+", " ", value)
    value = re.sub(r"[^\w\s'’]+", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()

    if not value:
        return False

    words = re.findall(r"[^\W_]+(?:['’][^\W_]+)*", value, flags=re.UNICODE)
    words = [w.replace("’", "'") for w in words]

    return bool(words) and len(words) <= 12 and all(
        word in GENERIC_PRAISE_WORDS for word in words
    )


def calculate_jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Calculate Jaccard similarity between two token sets."""
    if not set_a and not set_b:
        return 1.0

    if not set_a or not set_b:
        return 0.0

    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))

    return intersection / union if union > 0 else 0.0


def detect_language_safe(text: str) -> Optional[str]:
    """
    Detect language conservatively.
    Returns None when the text is too short or detection fails.
    """
    text = (text or "").strip()
    if not lang_detect or len(text) < 20:
        return None

    try:
        return lang_detect(text)
    except Exception:
        return None


class DataCleaningService:
    """
    Complete data cleaning pipeline for AlphaEV reviews:

    - Encoding repair & Mojibake correction
    - HTML entity & tag stripping
    - NFKC unicode normalization
    - Negation, EV technical terms, error codes and emoji preservation
    - Exact duplicate detection (SHA-256)
    - Near duplicate detection (flagged for review; not automatically excluded)
    - Language identification
    - Generic-only praise/reaction exclusion (no minimum word-count cutoff)
    """

    def __init__(self, near_duplicate_threshold: float = 0.85):
        self.near_duplicate_threshold = near_duplicate_threshold

    def clean_single_text(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """Cleans a single review text and records transformations."""
        if not text:
            return "", {
                "html_removed": False,
                "encoding_fixed": False,
                "url_removed": False,
            }

        text_fixed, encoding_fixed = fix_encoding_and_mojibake(text)
        text_no_html, html_removed = clean_html(text_fixed)

        url_removed = bool(URL_PATTERN.search(text_no_html))
        text_no_urls = URL_PATTERN.sub(" ", text_no_html) if url_removed else text_no_html

        cleaned = normalize_unicode_and_whitespace(text_no_urls)

        return cleaned, {
            "html_removed": html_removed,
            "encoding_fixed": encoding_fixed,
            "url_removed": url_removed,
        }

    def process_reviews(
        self,
        reviews_data: List[Dict[str, Any]],
        existing_hashes: Optional[Dict[str, str]] = None,
        existing_word_sets: Optional[List[Tuple[str, Set[str]]]] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Process a list of raw review dictionaries.

        Expected dict format:
        {
            "id": str,
            "original_text": str,
            "rating": Optional[float],
            "row_index": int,
            ...
        }

        Returns:
            (processed_reviews, summary_stats)
        """
        processed: List[Dict[str, Any]] = []
        seen_hashes: Dict[str, str] = existing_hashes.copy() if existing_hashes else {}
        seen_token_sets: List[Tuple[str, Set[str]]] = (
            existing_word_sets.copy() if existing_word_sets else []
        )

        # Index previously accepted reviews by token for faster candidate retrieval.
        token_index: Dict[str, Dict[str, Set[str]]] = {}
        seen_order: Dict[str, int] = {}

        for position, (previous_id, previous_tokens) in enumerate(seen_token_sets):
            seen_order[previous_id] = position
            for token in previous_tokens:
                token_index.setdefault(token, {})[previous_id] = previous_tokens

        stats = {
            "total_reviews": len(reviews_data),
            "cleaned_count": 0,
            "exact_duplicates": 0,
            "near_duplicates": 0,
            "low_info_count": 0,
            "generic_reactions": 0,
            "non_english_count": 0,
            "html_removed_count": 0,
            "encoding_fixed_count": 0,
            "url_removed_count": 0,
            "flags_breakdown": {
                "exact_duplicate": 0,
                "near_duplicate": 0,
                "low_info": 0,
                "generic_reaction": 0,
                "empty_text": 0,
                "non_english": 0,
                "html_tags_removed": 0,
                "encoding_fixed": 0,
                "url_removed": 0,
            },
        }

        for item in reviews_data:
            review_id = str(item.get("id"))
            original = str(item.get("original_text") or "")
            flags: List[Dict[str, Any]] = []
            is_dup = False
            dup_of: Optional[str] = None
            is_low_info = False
            lang: Optional[str] = None

            if not original.strip():
                cleaned = ""
                is_low_info = True
                stats["low_info_count"] += 1
                stats["flags_breakdown"]["low_info"] += 1
                stats["flags_breakdown"]["empty_text"] += 1
                flags.append({
                    "type": "empty_text",
                    "message": "Review text is empty or blank",
                    "action": "excluded",
                    "reason": "No readable review content in source",
                })
            else:
                cleaned, flags_info = self.clean_single_text(original)

                if flags_info["html_removed"]:
                    stats["html_removed_count"] += 1
                    stats["flags_breakdown"]["html_tags_removed"] += 1
                    flags.append({
                        "type": "html_cleaned",
                        "message": "HTML tags and entities removed",
                        "action": "flagged",
                        "reason": "Markup removed while preserving text and mathematical comparators",
                    })

                if flags_info["encoding_fixed"]:
                    stats["encoding_fixed_count"] += 1
                    stats["flags_breakdown"]["encoding_fixed"] += 1
                    flags.append({
                        "type": "encoding_fixed",
                        "message": "Character encoding / mojibake normalized",
                        "action": "flagged",
                        "reason": "Repaired misencoded characters",
                    })

                if flags_info.get("url_removed"):
                    stats["url_removed_count"] += 1
                    stats["flags_breakdown"]["url_removed"] += 1
                    flags.append({
                        "type": "url_removed",
                        "message": "Promotional or web URL removed",
                        "action": "flagged",
                        "reason": "Stripped external web address",
                    })

                if not cleaned.strip():
                    is_low_info = True
                    stats["low_info_count"] += 1
                    stats["flags_breakdown"]["low_info"] += 1
                    stats["flags_breakdown"]["empty_text"] += 1
                    flags.append({
                        "type": "empty_text",
                        "message": "Review text became empty after stripping markup",
                        "action": "excluded",
                        "reason": "No semantic content remaining after cleaning",
                    })
                else:
                    tokens = extract_meaningful_tokens(cleaned)
                    token_set = set(tokens)

                    # Exclude only generic praise/reactions. Do NOT use a
                    # minimum word-count rule: short specific feedback and all
                    # meaningful long reviews must be retained.
                    if is_generic_praise_only(cleaned):
                        is_low_info = True
                        stats["low_info_count"] += 1
                        stats["generic_reactions"] += 1
                        stats["flags_breakdown"]["low_info"] += 1
                        stats["flags_breakdown"]["generic_reaction"] += 1
                        flags.append({
                            "type": "generic_reaction",
                            "message": "Generic praise/reaction without specific feedback",
                            "action": "excluded",
                            "reason": "Review contains only generic praise or a reaction",
                        })

                    # Language Detection
                    lang = detect_language_safe(cleaned)
                    if lang and lang != "en":
                        stats["non_english_count"] += 1
                        stats["flags_breakdown"]["non_english"] += 1
                        flags.append({
                            "type": "non_english",
                            "message": f"Review detected in foreign language: {lang}",
                            "action": "flagged",
                            "reason": f"Language detected as {lang}",
                        })

                    # Exact Duplicate Check (Hash of normalized text)
                    normalized_for_hash = re.sub(
                        r"\s+",
                        " ",
                        cleaned.lower().strip(),
                    )
                    text_hash = hashlib.sha256(
                        normalized_for_hash.encode("utf-8")
                    ).hexdigest()

                    if text_hash in seen_hashes and len(cleaned.strip()) > 5:
                        is_dup = True
                        dup_of = seen_hashes[text_hash]
                        stats["exact_duplicates"] += 1
                        stats["flags_breakdown"]["exact_duplicate"] += 1
                        flags.append({
                            "type": "exact_duplicate",
                            "message": f"Exact duplicate of review ID {dup_of}",
                            "action": "excluded",
                            "reason": f"Identical normalized content to review {dup_of}",
                        })
                    else:
                        if len(cleaned.strip()) > 5:
                            seen_hashes[text_hash] = review_id

                        # Compare only reviews sharing at least one token.
                        if not is_dup and len(token_set) >= 4:
                            candidates: Dict[str, Set[str]] = {}
                            for token in token_set:
                                candidates.update(token_index.get(token, {}))

                            ordered_candidates = sorted(
                                candidates.items(),
                                key=lambda pair: seen_order.get(pair[0], -1),
                            )

                            for previous_id, previous_tokens in ordered_candidates:
                                similarity = calculate_jaccard_similarity(
                                    token_set,
                                    previous_tokens,
                                )
                                if similarity >= self.near_duplicate_threshold:
                                    # Similar wording is not proof of duplication.
                                    # Preserve the review and flag it for audit.
                                    dup_of = previous_id
                                    stats["near_duplicates"] += 1
                                    stats["flags_breakdown"]["near_duplicate"] += 1
                                    flags.append({
                                        "type": "near_duplicate",
                                        "message": (
                                            f"Similar to review {dup_of} "
                                            f"(similarity: {similarity:.0%}); retained"
                                        ),
                                        "action": "flagged",
                                        "reason": (
                                            f"Jaccard word similarity >= {self.near_duplicate_threshold:.0%}; "
                                            "review retained because it may contain distinct feedback"
                                        ),
                                    })
                                    break

                        # Index only non-duplicate reviews, matching prior behavior.
                        if len(token_set) >= 4 and not is_dup:
                            seen_order[review_id] = len(seen_order)
                            seen_token_sets.append((review_id, token_set))
                            for token in token_set:
                                token_index.setdefault(token, {})[review_id] = token_set

            stats["cleaned_count"] += 1

            processed.append({
                "id": review_id,
                "dataset_id": item.get("dataset_id"),
                "row_index": item.get("row_index", 0),
                "original_text": original,
                "cleaned_text": cleaned,
                "rating": item.get("rating"),
                "review_date": item.get("review_date"),
                "source": item.get("source"),
                "reviewer": item.get("reviewer"),
                "flags": flags,
                "is_duplicate": is_dup,
                "duplicate_of": dup_of,
                "language": lang,
                "is_low_info": is_low_info,
            })

        # Enforce the requested maximum for this dataset upload. If more than
        # 811 reviews survive generic/duplicate filtering, retain the 811
        # longest substantive reviews and send the overflow to the removed
        # set via an explicit exclusion flag/reason.
        eligible = [
            row for row in processed
            if not any(flag.get("action") == "excluded" for flag in row["flags"])
        ]

        if len(eligible) > 811:
            eligible_sorted = sorted(
                eligible,
                key=lambda row: (
                    len((row.get("cleaned_text") or "").strip()),
                    len(extract_meaningful_tokens(row.get("cleaned_text") or "")),
                ),
                reverse=True,
            )
            keep_ids = {id(row) for row in eligible_sorted[:811]}
            overflow = [row for row in eligible if id(row) not in keep_ids]

            for row in overflow:
                row["flags"].append({
                    "type": "retention_limit",
                    "message": "Excluded because the cleaned dataset limit is 811 reviews",
                    "action": "excluded",
                    "reason": "Dataset retention cap: kept the 811 most information-rich reviews",
                })
                row["is_low_info"] = True

            stats["retention_limit_excluded"] = len(overflow)
        else:
            stats["retention_limit_excluded"] = 0

        stats["retained_count"] = sum(
            1 for row in processed
            if not any(flag.get("action") == "excluded" for flag in row["flags"])
        )

        return processed, stats


cleaning_service = DataCleaningService()
cleaning_pipeline = cleaning_service