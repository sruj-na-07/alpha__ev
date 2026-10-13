import re
import html
import unicodedata
import hashlib
from typing import Dict, List, Tuple, Any, Optional, Set
from bs4 import BeautifulSoup
import chardet

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
    r"\b[A-Z0-9_]{2,8}_[a-zA-Z0-9_]{3,8}\b",  # Error codes like CP_a054, BMS_w123, DI_u014
    r"\bP[0-3][0-9A-F]{3}\b",  # OBD-II EV diagnostic codes like P0A80
]
EV_REGEX = re.compile("|".join(EV_TERMS), re.IGNORECASE)

MOJIBAKE_MAP = {
    "â€™": "'",
    "â€œ": '"',
    "â€\x9d": '"',
    "â€“": "-",
    "â€”": "—",
    "â€¦": "...",
    "Ã©": "é",
    "Ã¨": "è",
    "Ã ": "à",
    "Ã§": "ç",
    "Â": "",
    "\xa0": " ",
}


def fix_encoding_and_mojibake(text: str) -> Tuple[str, bool]:
    """Fix common encoding artifacts and mojibake sequences."""
    modified = False
    original = text

    # Handle mojibake
    for bad, good in MOJIBAKE_MAP.items():
        if bad in text:
            text = text.replace(bad, good)
            modified = True

    # Try raw byte recovery if obvious UTF-8 in Windows-1252 / latin-1
    if any(char in text for char in ("Ã", "â", "ï", "¿", "½")):
        try:
            fixed = text.encode("latin-1").decode("utf-8")
            if len(fixed) > 0:
                text = fixed
                modified = True
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return text, modified or (text != original)


def clean_html(text: str) -> Tuple[str, bool]:
    """Remove HTML tags while preserving text formatting and decoding entities."""
    if not ("<" in text and ">" in text) and not ("&" in text and ";" in text):
        return text, False

    original = text
    try:
        # Check if contains tag
        if re.search(r"<[^>]+>", text):
            soup = BeautifulSoup(text, "html.parser")
            cleaned = soup.get_text(separator=" ")
        else:
            cleaned = text
        cleaned = html.unescape(cleaned)
        return cleaned, cleaned != original
    except Exception:
        # Fallback to regex if BeautifulSoup fails
        cleaned = re.sub(r"<[^>]+>", " ", text)
        cleaned = html.unescape(cleaned)
        return cleaned, cleaned != original


def normalize_unicode_and_whitespace(text: str) -> str:
    """Normalize unicode characters to NFKC and collapse excessive whitespaces."""
    # NFKC normalizes compatibility characters while preserving emojis and letters
    text = unicodedata.normalize("NFKC", text)
    # Remove control characters except standard newlines and tabs
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Normalize excessive blank lines and spaces
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_meaningful_tokens(text: str) -> List[str]:
    """Extract lowercased word tokens excluding standard stop words."""
    # Split on whitespace/punctuation, keeping alphanumeric words and contractions
    words = re.findall(r"\b[a-zA-Z0-9_\'-]+\b", text.lower())
    meaningful = [
        w for w in words
        if w not in STANDARD_STOP_WORDS and len(w) > 1 or w in NEGATION_WORDS
    ]
    return meaningful


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
    """Detect language safely, returning None or language code (e.g., 'en')."""
    if not lang_detect or len(text.strip()) < 8:
        return "en"
    try:
        lang = lang_detect(text)
        return lang
    except Exception:
        return "en"


class DataCleaningService:
    """
    Complete data cleaning pipeline for AlphaEV reviews:
    - Encoding repair & Mojibake correction
    - HTML entity & tag stripping
    - NFKC unicode normalization
    - Negation, EV technical terms, error codes and emoji preservation
    - Exact duplicate detection (SHA-256)
    - Near duplicate detection (Jaccard word similarity >= 0.85)
    - Language identification
    - Low-information detection (< 3 meaningful words)
    """

    def __init__(self, near_duplicate_threshold: float = 0.85):
        self.near_duplicate_threshold = near_duplicate_threshold

    def clean_single_text(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """Cleans a single review text and records transformations."""
        if not text:
            return "", {"html_removed": False, "encoding_fixed": False}

        # 1. Encoding fix
        text_fixed, encoding_fixed = fix_encoding_and_mojibake(text)

        # 2. HTML stripping
        text_no_html, html_removed = clean_html(text_fixed)

        # 3. Unicode & whitespace normalization
        cleaned = normalize_unicode_and_whitespace(text_no_html)

        return cleaned, {
            "html_removed": html_removed,
            "encoding_fixed": encoding_fixed,
        }

    def process_reviews(
        self,
        reviews_data: List[Dict[str, Any]],
        existing_hashes: Optional[Dict[str, str]] = None,
        existing_word_sets: Optional[List[Tuple[str, Set[str]]]] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Process a list of raw review dictionaries:
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
        seen_token_sets: List[Tuple[str, Set[str]]] = existing_word_sets.copy() if existing_word_sets else []

        stats = {
            "total_reviews": len(reviews_data),
            "cleaned_count": 0,
            "exact_duplicates": 0,
            "near_duplicates": 0,
            "low_info_count": 0,
            "non_english_count": 0,
            "html_removed_count": 0,
            "encoding_fixed_count": 0,
            "flags_breakdown": {
                "exact_duplicate": 0,
                "near_duplicate": 0,
                "low_info": 0,
                "non_english": 0,
                "html_tags_removed": 0,
                "encoding_fixed": 0,
            },
        }

        for item in reviews_data:
            review_id = str(item.get("id"))
            original = str(item.get("original_text") or "")
            cleaned, flags_info = self.clean_single_text(original)

            flags: List[Dict[str, str]] = []
            is_dup = False
            dup_of: Optional[str] = None
            is_low_info = False

            if flags_info["html_removed"]:
                stats["html_removed_count"] += 1
                stats["flags_breakdown"]["html_tags_removed"] += 1
                flags.append({"type": "html_cleaned", "message": "HTML tags and entities removed"})

            if flags_info["encoding_fixed"]:
                stats["encoding_fixed_count"] += 1
                stats["flags_breakdown"]["encoding_fixed"] += 1
                flags.append({"type": "encoding_fixed", "message": "Character encoding / mojibake normalized"})

            # Tokens & Low Information check
            tokens = extract_meaningful_tokens(cleaned)
            token_set = set(tokens)

            if len(tokens) < 3:
                is_low_info = True
                stats["low_info_count"] += 1
                stats["flags_breakdown"]["low_info"] += 1
                flags.append({
                    "type": "low_info",
                    "message": f"Low information review: contains only {len(tokens)} meaningful words"
                })

            # Language Detection
            lang = detect_language_safe(cleaned)
            if lang and lang != "en":
                stats["non_english_count"] += 1
                stats["flags_breakdown"]["non_english"] += 1
                flags.append({
                    "type": "non_english",
                    "message": f"Review detected in foreign language: {lang}"
                })

            # Exact Duplicate Check (Hash of normalized text)
            normalized_for_hash = re.sub(r"\s+", " ", cleaned.lower().strip())
            text_hash = hashlib.sha256(normalized_for_hash.encode("utf-8")).hexdigest()

            if text_hash in seen_hashes and len(cleaned.strip()) > 5:
                is_dup = True
                dup_of = seen_hashes[text_hash]
                stats["exact_duplicates"] += 1
                stats["flags_breakdown"]["exact_duplicate"] += 1
                flags.append({
                    "type": "exact_duplicate",
                    "message": f"Exact duplicate of review ID {dup_of}"
                })
            else:
                if len(cleaned.strip()) > 5:
                    seen_hashes[text_hash] = review_id

                # Near Duplicate Check (Jaccard similarity on tokens)
                if not is_dup and len(token_set) >= 4:
                    for prev_id, prev_set in seen_token_sets:
                        sim = calculate_jaccard_similarity(token_set, prev_set)
                        if sim >= self.near_duplicate_threshold:
                            is_dup = True
                            dup_of = prev_id
                            stats["near_duplicates"] += 1
                            stats["flags_breakdown"]["near_duplicate"] += 1
                            flags.append({
                                "type": "near_duplicate",
                                "message": f"Near duplicate of review {dup_of} (similarity: {sim:.0%})"
                            })
                            break

                if len(token_set) >= 4 and not is_dup:
                    seen_token_sets.append((review_id, token_set))

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
                "language": lang or "en",
                "is_low_info": is_low_info,
            })

        return processed, stats


cleaning_service = DataCleaningService()
