"""
detector.py - Core dark pattern detection logic.
Uses rule-based keyword matching per category.
"""

import re
import requests
from bs4 import BeautifulSoup

# ─── Keyword Rules ──────────────────────────────────────────────────────────

PATTERNS = {
    "urgency": {
        "keywords": [
            "limited time", "act now", "hurry", "expires soon", "don't miss",
            "last chance", "ending soon", "offer ends", "today only", "flash sale",
            "time is running out", "almost gone", "deal expires", "only today",
            "must end", "closing soon", "countdown", "urgent", "immediately",
            "right now", "don't wait", "order now", "buy now", "get it now",
        ],
        "deduction": 10,
        "color": "#ff4444",
        "label": "Fake Urgency",
        "explanation": "This language creates artificial time pressure to rush you into a decision without thinking it through.",
    },
    "scarcity": {
        "keywords": [
            "only \d+ left", "limited stock", "few remaining", "almost sold out",
            "running low", "last one", "out of stock soon", "in high demand",
            "selling fast", "limited availability", "limited quantity", "rare find",
            "only a few", "stock running out", "grab yours", "don't miss out",
            "low inventory", "limited edition", "exclusive offer", "while supplies last",
        ],
        "deduction": 8,
        "color": "#ff8800",
        "label": "Scarcity",
        "explanation": "This language implies products are about to run out to pressure you into buying before you're ready.",
    },
    "social_pressure": {
        "keywords": [
            "people are viewing", "others are looking", "trending", "popular choice",
            "best seller", "most popular", "everyone is buying", "people bought",
            "currently viewing", "in their cart", "in demand", "high demand",
            "recommended by", "customers also bought", "join thousands", "join millions",
            "rated #1", "top rated", "most reviewed", "highly rated",
        ],
        "deduction": 6,
        "color": "#aa44ff",
        "label": "Social Pressure",
        "explanation": "This language uses crowd behavior to pressure you into conforming, rather than making your own decision.",
    },
    "confirmshaming": {
        "keywords": [
            "no thanks", "no, i don't want", "i don't want to save", "i prefer to pay more",
            "no, i'll pass", "i don't need", "no thanks, i hate", "reject",
            "i don't want this deal", "skip the discount", "no thanks, i'm good",
            "no i don't want to", "decline", "i hate savings", "no thank you",
            "i'll stay uninformed", "i don't want to be smart", "keep paying full price",
        ],
        "deduction": 7,
        "color": "#00aaff",
        "label": "Confirmshaming",
        "explanation": "This language guilts or shames you for declining an offer, making rejection feel like a character flaw.",
    },
}

# ─── Text Cleaning ──────────────────────────────────────────────────────────

def clean_text(text):
    """Remove HTML artifacts, extra whitespace, and normalize text."""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def split_sentences(text):
    """Split text into sentences."""
    # Simple sentence splitter
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]


# ─── Scraping ──────────────────────────────────────────────────────────────

def scrape_url(url):
    """Fetch and extract readable text from a URL."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove unwanted tags
        for tag in soup(["script", "style", "noscript", "meta", "link", "header", "footer", "nav"]):
            tag.decompose()

        text = soup.get_text(separator=" ")
        text = clean_text(text)
        return text, None
    except requests.exceptions.ConnectionError:
        return None, "Could not connect to the URL. Please check the address."
    except requests.exceptions.Timeout:
        return None, "The request timed out. The site may be slow or blocking scrapers."
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP error: {e}"
    except Exception as e:
        return None, f"Failed to fetch URL: {str(e)}"


# ─── Detection Engine ──────────────────────────────────────────────────────

def detect_patterns(text):
    """
    Scan text for dark patterns.
    Returns a dict: { category: [list of matched sentences] }
    """
    sentences = split_sentences(text)
    text_lower = text.lower()

    matched = {cat: [] for cat in PATTERNS}
    sentence_annotations = []  # [{sentence, category, label, color, explanation}]

    for sentence in sentences:
        s_lower = sentence.lower()
        sentence_cats = []

        for cat, info in PATTERNS.items():
            for kw in info["keywords"]:
                if re.search(kw, s_lower):
                    if sentence not in matched[cat]:
                        matched[cat].append(sentence)
                    sentence_cats.append(cat)
                    break  # one match per category per sentence

        if sentence_cats:
            # Pick the first matched category for highlighting
            cat = sentence_cats[0]
            sentence_annotations.append({
                "sentence": sentence,
                "category": cat,
                "label": PATTERNS[cat]["label"],
                "color": PATTERNS[cat]["color"],
                "explanation": PATTERNS[cat]["explanation"],
            })
        else:
            sentence_annotations.append({
                "sentence": sentence,
                "category": None,
                "label": None,
                "color": None,
                "explanation": None,
            })

    return matched, sentence_annotations


def compute_score(patterns):
    """Compute honesty score starting from 100, deducting per pattern type."""
    score = 100
    for cat, sentences in patterns.items():
        if sentences:
            deduction = PATTERNS[cat]["deduction"] * len(sentences)
            score -= deduction
    return max(0, score)


def get_risk_level(score):
    if score > 70:
        return "Low", "#22c55e"
    elif score >= 40:
        return "Medium", "#f59e0b"
    else:
        return "High", "#ef4444"


# ─── Main Analyze Functions ─────────────────────────────────────────────────

def analyze_url(url):
    """Full pipeline: scrape → detect → score."""
    text, error = scrape_url(url)
    if error:
        return {"error": error}
    return _build_result(text, url)


def analyze_text(text):
    """Analyze raw text directly."""
    return _build_result(text, url=None)


def _build_result(text, url):
    """Build the full result dict."""
    if not text or len(text) < 20:
        return {"error": "Not enough text content found to analyze."}

    patterns, annotations = detect_patterns(text)
    score = compute_score(patterns)
    risk, risk_color = get_risk_level(score)

    total_flags = sum(len(v) for v in patterns.values())

    return {
        "url": url,
        "score": score,
        "risk": risk,
        "risk_color": risk_color,
        "patterns": patterns,
        "annotations": annotations,
        "total_flags": total_flags,
        "pattern_info": {cat: {
            "label": info["label"],
            "color": info["color"],
            "explanation": info["explanation"],
            "count": len(patterns.get(cat, [])),
        } for cat, info in PATTERNS.items()},
        "text_preview": text[:500],
    }
