"""
analyzer.py — Dark Pattern Detection Engine
============================================
Handles:
  - Web scraping (requests + BeautifulSoup)
  - Text cleaning
  - Rule-based dark pattern detection
  - Honesty score calculation
  - Sentence-level highlighting
"""

import re
import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# DARK PATTERN KEYWORD RULES
# ─────────────────────────────────────────────

PATTERNS = {
    "urgency": {
        "keywords": [
            "hurry", "limited time", "act now", "don't miss", "expires soon",
            "ending soon", "last chance", "today only", "offer ends",
            "time is running out", "flash sale", "deal ends", "countdown",
            "midnight", "hours left", "minutes left", "seconds left",
            "now or never", "don't wait", "urgent", "immediately",
            "right now", "this week only", "ends tonight", "grab it now",
        ],
        "deduction": 10,
        "label": "⏰ Fake Urgency",
        "explanation": "This sentence uses time pressure to rush your decision, preventing careful consideration."
    },
    "scarcity": {
        "keywords": [
            "only a few left", "limited stock", "almost gone", "selling fast",
            "low stock", "few remaining", "only left", "limited availability",
            "running out", "nearly sold out", "sold out soon", "last one",
            "limited edition", "exclusive", "rare", "in high demand",
            "almost out of stock", "grab yours", "while supplies last",
            "limited quantity", "only [0-9]+ left",
        ],
        "deduction": 8,
        "label": "📦 Artificial Scarcity",
        "explanation": "This sentence creates false scarcity to pressure you into buying before it's too late."
    },
    "social_pressure": {
        "keywords": [
            "people are viewing", "others are looking", "trending",
            "best seller", "most popular", "everyone is buying",
            "customers love", "highly rated", "top rated",
            "people bought this", "others also bought", "join millions",
            "thousands of customers", "viewers right now", "sold today",
            "people have this in their cart", "watching this",
            "high demand", "flying off shelves", "crowd favorite",
        ],
        "deduction": 6,
        "label": "👥 Social Pressure",
        "explanation": "This sentence uses herd mentality to make you feel you'll miss out if others are doing it."
    },
    "confirmshaming": {
        "keywords": [
            "no thanks", "no, i don't want", "i don't want to save",
            "i prefer to pay more", "no, i hate", "i don't want deals",
            "no thanks, i don't need", "i'll pass", "i don't want to",
            "no thanks i'm fine paying", "skip", "i don't care about",
            "no, i want to miss out", "i don't need savings",
            "not interested in", "i'll stay broke", "no i'm good",
        ],
        "deduction": 7,
        "label": "😔 Confirmshaming",
        "explanation": "This sentence shames or guilts you into accepting an offer by making decline options feel bad."
    },
}

# Common English stopwords to clean text
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "this", "that", "these",
    "those", "it", "its", "they", "them", "their", "we", "our", "you",
    "your", "he", "she", "his", "her", "i", "my", "me", "us", "not",
}


# ─────────────────────────────────────────────
# WEB SCRAPING
# ─────────────────────────────────────────────

def scrape_url(url: str) -> dict:
    """
    Fetch and parse webpage text from a URL.
    Returns: { "text": "...", "title": "...", "error": None }
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        return {"error": f"Cannot connect to {url}. Check the URL and your internet."}
    except requests.exceptions.Timeout:
        return {"error": f"Request timed out for {url}. Site may be slow."}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP Error {e.response.status_code} for {url}"}
    except Exception as e:
        return {"error": f"Scraping failed: {str(e)}"}

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script and style tags (we don't want JS/CSS text)
    for tag in soup(["script", "style", "noscript", "meta", "head"]):
        tag.decompose()

    # Get page title
    title = soup.title.string.strip() if soup.title else url

    # Extract visible text
    raw_text = soup.get_text(separator=" ", strip=True)

    return {"text": raw_text, "title": title, "error": None}


# ─────────────────────────────────────────────
# TEXT CLEANING
# ─────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Clean raw scraped text:
    - Remove extra whitespace
    - Remove special characters (keep punctuation for sentence splitting)
    - Normalize spaces
    """
    # Remove URLs
    text = re.sub(r"https?://\S+", " ", text)
    # Remove email addresses
    text = re.sub(r"\S+@\S+", " ", text)
    # Remove multiple whitespace/newlines
    text = re.sub(r"\s+", " ", text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def split_into_sentences(text: str) -> list:
    """
    Split text into individual sentences.
    Uses simple punctuation-based splitting.
    """
    # Split on . ! ? followed by space and capital letter (or end of string)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)

    # Also split on newlines that look like separate items
    result = []
    for s in sentences:
        parts = s.split("\n")
        for p in parts:
            p = p.strip()
            if len(p) > 10:  # Skip very short fragments
                result.append(p)

    return result


# ─────────────────────────────────────────────
# DARK PATTERN DETECTION
# ─────────────────────────────────────────────

def detect_patterns_in_sentence(sentence: str) -> list:
    """
    Check a single sentence for all dark patterns.
    Returns a list of matched pattern types.
    """
    sentence_lower = sentence.lower()
    matches = []

    for pattern_type, config in PATTERNS.items():
        for keyword in config["keywords"]:
            # Handle regex patterns (like "only [0-9]+ left")
            if re.search(r"[\[\]\\]", keyword):
                if re.search(keyword, sentence_lower):
                    matches.append(pattern_type)
                    break
            else:
                if keyword in sentence_lower:
                    matches.append(pattern_type)
                    break

    return matches


def analyze_sentences(sentences: list) -> list:
    """
    Analyze each sentence for dark patterns.
    Returns a list of sentence result dicts.
    """
    results = []
    for sentence in sentences:
        matched = detect_patterns_in_sentence(sentence)
        results.append({
            "text": sentence,
            "patterns": matched,
            "flagged": len(matched) > 0
        })
    return results


# ─────────────────────────────────────────────
# HONESTY SCORE
# ─────────────────────────────────────────────

def calculate_score(sentence_results: list) -> dict:
    """
    Calculate honesty score starting from 100.
    Deduct points for each detected dark pattern sentence.
    Returns score, risk level, and pattern counts.
    """
    score = 100
    pattern_counts = {k: 0 for k in PATTERNS}

    for result in sentence_results:
        for pattern_type in result["patterns"]:
            deduction = PATTERNS[pattern_type]["deduction"]
            score -= deduction
            pattern_counts[pattern_type] += 1

    # Clamp score to 0–100
    score = max(0, min(100, score))

    # Determine risk level
    if score > 70:
        risk = "Low"
        risk_color = "green"
    elif score >= 40:
        risk = "Medium"
        risk_color = "orange"
    else:
        risk = "High"
        risk_color = "red"

    return {
        "score": round(score),
        "risk": risk,
        "risk_color": risk_color,
        "pattern_counts": pattern_counts
    }


# ─────────────────────────────────────────────
# BUILD HIGHLIGHTED SENTENCES OUTPUT
# ─────────────────────────────────────────────

def build_highlighted_output(sentence_results: list) -> list:
    """
    Build output suitable for frontend rendering.
    Each item has text, flagged status, and explanations.
    """
    output = []
    for result in sentence_results:
        item = {
            "text": result["text"],
            "flagged": result["flagged"],
            "patterns": []
        }
        for pt in result["patterns"]:
            config = PATTERNS[pt]
            item["patterns"].append({
                "type": pt,
                "label": config["label"],
                "explanation": config["explanation"]
            })
        output.append(item)
    return output


# ─────────────────────────────────────────────
# MAIN ANALYSIS FUNCTIONS
# ─────────────────────────────────────────────

def analyze_text(text: str, source_url: str = "Direct Input") -> dict:
    """
    Analyze a block of raw text for dark patterns.
    This is the core analysis function used by both
    URL analysis and screenshot OCR.
    """
    # Clean and split
    cleaned = clean_text(text)
    sentences = split_into_sentences(cleaned)

    # Limit to 200 sentences for performance
    sentences = sentences[:200]

    # Detect patterns
    sentence_results = analyze_sentences(sentences)

    # Calculate score
    score_info = calculate_score(sentence_results)

    # Build output
    highlighted = build_highlighted_output(sentence_results)

    # Count total flagged sentences
    flagged_count = sum(1 for r in sentence_results if r["flagged"])
    total_sentences = len(sentences)

    return {
        "url": source_url,
        "score": score_info["score"],
        "risk": score_info["risk"],
        "risk_color": score_info["risk_color"],
        "pattern_counts": score_info["pattern_counts"],
        "total_sentences": total_sentences,
        "flagged_sentences": flagged_count,
        "sentences": highlighted,
        "error": None
    }


def analyze_url(url: str) -> dict:
    """
    Full pipeline: scrape URL → clean → analyze → return results.
    """
    # Step 1: Scrape
    scraped = scrape_url(url)
    if scraped.get("error"):
        return {"error": scraped["error"], "url": url}

    # Step 2: Analyze text
    result = analyze_text(scraped["text"], source_url=url)
    result["page_title"] = scraped.get("title", url)

    return result
