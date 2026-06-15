#!/usr/bin/env python3
"""
Reddit Quote Scraper — Fetches unique philosophical/psychological quotes from Reddit.
Uses Reddit's official OAuth2 API for reliable access.
Supports both authenticated (preferred) and unauthenticated access.
Deduplicates against used quotes using MD5 hashing.
"""

import requests
import json
import os
import re
import time
import random
import hashlib
from datetime import datetime


# ─── Subreddits to scrape from ──────────────────────────────────────────────

SUBREDDITS = [
    "Stoicism",
    "philosophy",
    "Existentialism",
    "Jung",
    "Nietzsche",
    "Zen",
    "Buddhism",
    "Quotes",
    "QuotePorn",
    "DeepThoughts",
    "Mindfulness",
    "SelfImprovement",
    "Camus",
    "EasternPhilosophy",
    "Meditation",
    "ShadowWork",
    "Psychoanalysis",
    "Schopenhauer",
    "Heidegger",
    "Sartre",
]

# ─── Quality Filters ────────────────────────────────────────────────────────

MIN_QUOTE_LENGTH = 25      # Minimum characters
MAX_QUOTE_LENGTH = 300     # Maximum characters
MIN_UPVOTES = 10           # Minimum upvotes for a post
MIN_COMMENT_UPVOTES = 5    # Minimum upvotes for a comment

# ─── Used Quotes Tracking ───────────────────────────────────────────────────

USED_QUOTES_HASHES = set()


def _hash_quote(text):
    """Create a hash of normalized quote text for deduplication."""
    normalized = re.sub(r'[^\w\s]', '', text.lower().strip())
    normalized = re.sub(r'\s+', ' ', normalized)
    return hashlib.md5(normalized.encode()).hexdigest()


def load_used_hashes(used_file):
    """Load previously used quote hashes."""
    global USED_QUOTES_HASHES
    
    if not os.path.exists(used_file):
        USED_QUOTES_HASHES = set()
        return
    
    try:
        with open(used_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            USED_QUOTES_HASHES = set(data.get("hashes", []))
        print(f"   📋 Loaded {len(USED_QUOTES_HASHES)} previously used quotes")
    except (json.JSONDecodeError, KeyError):
        USED_QUOTES_HASHES = set()


def save_used_hash(used_file, quote_hash, quote_text, author, source):
    """Save a new used quote hash."""
    if not os.path.exists(used_file):
        data = {"hashes": [], "quotes": []}
    else:
        try:
            with open(used_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {"hashes": [], "quotes": []}
    
    data["hashes"].append(quote_hash)
    data["quotes"].append({
        "hash": quote_hash,
        "text": quote_text[:100],
        "author": author,
        "source": source,
        "used_at": datetime.now().isoformat()
    })
    
    # Keep the file from growing too large (keep last 500 entries)
    if len(data["hashes"]) > 500:
        data["hashes"] = data["hashes"][-500:]
        data["quotes"] = data["quotes"][-500:]
    
    dir_name = os.path.dirname(used_file)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    
    with open(used_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _is_duplicate(text):
    """Check if a quote has already been used."""
    return _hash_quote(text) in USED_QUOTES_HASHES


def _clean_text(text):
    """Clean and normalize text from Reddit."""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


def _extract_quote_from_title(title, subreddit):
    """Extract a quote from a Reddit post title."""
    patterns = [
        r'["\u201c\u201d](.+?)["\u201c\u201d]\s*[—\-–]\s*(.+?)(?:\s*$|\s*[|\[])',
        r'["\u201c\u201d](.+?)["\u201c\u201d]\s*$',
        r'^(.+?)\s*[—\-–]\s*(.+?)(?:\s*$|\s*[|\[])',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                return {"text": groups[0].strip(), "author": groups[1].strip()}
            elif len(groups) == 1:
                return {"text": groups[0].strip(), "author": f"r/{subreddit}"}
    
    if len(title) >= MIN_QUOTE_LENGTH:
        return {"text": title, "author": f"r/{subreddit}"}
    
    return None


def _is_valid_quote(quote_text):
    """Check if a quote meets quality criteria."""
    if len(quote_text) < MIN_QUOTE_LENGTH or len(quote_text) > MAX_QUOTE_LENGTH:
        return False
    
    word_count = len(quote_text.split())
    if word_count < 5:
        return False
    
    question_starters = [
        "how do", "what do", "why do", "can someone", "help me",
        "does anyone", "what is the", "how can i", "i need",
        "looking for", "recommend me", "where can", "what are your",
        "who else", "is it normal", "am i the only",
    ]
    if any(quote_text.lower().startswith(q) for q in question_starters):
        return False
    
    if "http://" in quote_text or "https://" in quote_text:
        return False
    
    # Skip if too many special characters
    special_count = sum(1 for c in quote_text if not c.isalnum() and c not in ' .,;:!?\'"-—')
    if special_count > len(quote_text) * 0.15:
        return False
    
    return True


def _categorize_quote(text, subreddit):
    """Assign a category based on content and subreddit."""
    subreddit_map = {
        "stoicism": "stoicism", "philosophy": "philosophy",
        "existentialism": "existentialism", "psychology": "psychology",
        "jung": "psychology", "nietzsche": "existentialism",
        "zen": "eastern", "buddhism": "eastern",
        "quotes": "wisdom", "quoteporn": "wisdom",
        "deepthoughts": "philosophy", "mindfulness": "eastern",
        "selfimprovement": "motivation", "camus": "existentialism",
        "easternphilosophy": "eastern", "meditation": "eastern",
        "shadowwork": "psychology", "psychoanalysis": "psychology",
        "schopenhauer": "existentialism", "heidegger": "existentialism",
        "sartre": "existentialism",
    }
    
    category = subreddit_map.get(subreddit.lower(), "philosophy")
    
    text_lower = text.lower()
    if any(w in text_lower for w in ["stoic", "marcus", "seneca", "epictetus"]):
        category = "stoicism"
    elif any(w in text_lower for w in ["nietzsche", "camus", "sartre", "kierkegaard", "absurd", "existential"]):
        category = "existentialism"
    elif any(w in text_lower for w in ["buddha", "zen", "tao", "mindful", "meditat"]):
        category = "eastern"
    elif any(w in text_lower for w in ["jung", "unconscious", "shadow", "psyche", "freud"]):
        category = "psychology"
    
    return category


# ─── Reddit API Authentication ──────────────────────────────────────────────

_reddit_token = None
_reddit_token_expiry = 0


def get_reddit_token():
    """
    Get an OAuth2 access token from Reddit.
    Uses the "Application Only" flow (client_credentials grant).
    Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_ID_SECRET env vars.
    
    If credentials aren't set, returns None (will use old.reddit.com fallback).
    """
    global _reddit_token, _reddit_token_expiry
    
    client_id = os.environ.get("REDDIT_CLIENT_ID", "")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")
    
    if not client_id or not client_secret:
        return None
    
    # Check if we have a valid cached token
    if _reddit_token and time.time() < _reddit_token_expiry:
        return _reddit_token
    
    try:
        auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
        data = {
            "grant_type": "client_credentials",
        }
        headers = {"User-Agent": "InnerLogic/1.0 (by /u/innerlogic_bot)"}
        
        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=auth,
            data=data,
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            token_data = response.json()
            _reddit_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            _reddit_token_expiry = time.time() + expires_in - 60  # 60s buffer
            print(f"   ✅ Reddit API authenticated")
            return _reddit_token
        else:
            print(f"   ⚠️  Reddit auth failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ⚠️  Reddit auth error: {e}")
        return None


def fetch_reddit_posts(subreddit, sort="top", time_filter="week", limit=25):
    """
    Fetch posts from a subreddit.
    Uses OAuth2 API if credentials are available, otherwise falls back to
    old.reddit.com HTML scraping.
    """
    token = get_reddit_token()
    
    if token:
        return _fetch_via_oauth(token, subreddit, sort, time_filter, limit)
    else:
        return _fetch_via_old_reddit(subreddit, sort, time_filter, limit)


def _fetch_via_oauth(token, subreddit, sort, time_filter, limit):
    """Fetch posts using Reddit's OAuth2 API."""
    url = f"https://oauth.reddit.com/r/{subreddit}/{sort}"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "InnerLogic/1.0 (by /u/innerlogic_bot)",
    }
    params = {"t": time_filter, "limit": min(limit, 100)}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 429:
            print(f"   ⚠️  Rate limited by Reddit — waiting...")
            time.sleep(30)
            return []
        
        if response.status_code != 200:
            print(f"   ⚠️  r/{subreddit} returned {response.status_code}")
            return []
        
        data = response.json()
        posts = data.get("data", {}).get("children", [])
        
        result = []
        for post in posts:
            post_data = post.get("data", {})
            result.append({
                "title": post_data.get("title", ""),
                "selftext": post_data.get("selftext", ""),
                "author": post_data.get("author", ""),
                "score": post_data.get("score", 0),
                "subreddit": subreddit,
                "num_comments": post_data.get("num_comments", 0),
                "name": post_data.get("name", ""),
            })
        
        return result
        
    except Exception as e:
        print(f"   ⚠️  Error fetching r/{subreddit}: {e}")
        return []


def _fetch_via_old_reddit(subreddit, sort, time_filter, limit):
    """
    Fetch posts via old.reddit.com as a fallback.
    Parses the HTML to extract post titles and scores.
    """
    url = f"https://old.reddit.com/r/{subreddit}/{sort}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html",
    }
    params = {"t": time_filter, "limit": limit}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code != 200:
            print(f"   ⚠️  r/{subreddit} returned {response.status_code}")
            return []
        
        html = response.text
        result = []
        
        # Parse posts from HTML
        # Pattern: find all post entries
        # <div class="thing ..."> with data-fullname, title in <a class="title">
        # Score in <div class="score unvoted">
        
        thing_pattern = re.finditer(
            r'<div[^>]*class="thing id-t3_\w+"[^>]*>'
            r'.*?'
            r'<a[^>]*class="title may-blank[^"]*"[^>]*>(.*?)</a>'
            r'.*?'
            r'<div[^>]*class="score unvoted"[^>]*>(.*?)</div>',
            html, re.DOTALL
        )
        
        for match in thing_pattern:
            title = re.sub(r'<[^>]+>', '', match.group(1)).strip()
            score_text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            
            # Parse score
            try:
                score = int(score_text) if score_text not in ['•', ''] else 0
            except ValueError:
                score = 0
            
            if score >= MIN_UPVOTES and title:
                result.append({
                    "title": title,
                    "selftext": "",
                    "author": "",
                    "score": score,
                    "subreddit": subreddit,
                    "num_comments": 0,
                    "name": "",
                })
        
        print(f"   📰 Found {len(result)} posts from r/{subreddit} (old.reddit)")
        return result
        
    except Exception as e:
        print(f"   ⚠️  Error fetching r/{subreddit} via old.reddit: {e}")
        return []


def pick_quote_from_reddit(used_file):
    """
    Main function: Scrape Reddit for a unique philosophical quote.
    
    Strategy:
    1. Pick random subreddits
    2. Fetch top posts from the past week
    3. Extract quotes from post titles and content
    4. Filter for quality and deduplicate against used quotes
    5. Return the best unique quote found
    6. Fall back to built-in collection if Reddit fails
    
    Args:
        used_file: Path to the used quotes tracking file
    
    Returns:
        dict: Quote object with 'text', 'author', 'category', 'source' keys
    """
    load_used_hashes(used_file)
    
    shuffled_subreddits = random.sample(SUBREDDITS, len(SUBREDDITS))
    
    candidates = []
    subreddits_tried = 0
    max_subreddits = 6
    
    for subreddit in shuffled_subreddits:
        if subreddits_tried >= max_subreddits:
            break
        
        print(f"   🔍 Scanning r/{subreddit}...")
        posts = fetch_reddit_posts(subreddit, sort="top", time_filter="week", limit=25)
        subreddits_tried += 1
        
        for post in posts:
            if post["score"] < MIN_UPVOTES:
                continue
            
            # Try to extract a quote from the title
            quote_data = _extract_quote_from_title(post["title"], subreddit)
            if quote_data and _is_valid_quote(quote_data["text"]) and not _is_duplicate(quote_data["text"]):
                quote_data["category"] = _categorize_quote(quote_data["text"], subreddit)
                quote_data["source"] = f"r/{subreddit} (post, {post['score']} upvotes)"
                quote_data["score"] = post["score"]
                candidates.append(quote_data)
            
            # Also check selftext for quotes
            if post["selftext"]:
                first_para = post["selftext"].split("\n")[0].strip()
                first_para = _clean_text(first_para)
                if _is_valid_quote(first_para) and not _is_duplicate(first_para):
                    author = post.get("author", "Unknown")
                    if author in ["[deleted]", "AutoModerator"]:
                        continue
                    candidates.append({
                        "text": first_para,
                        "author": author,
                        "category": _categorize_quote(first_para, subreddit),
                        "source": f"r/{subreddit} (selftext, {post['score']} upvotes)",
                        "score": post["score"],
                    })
        
        time.sleep(2)  # Rate limit
    
    # If no candidates found, fall back to built-in collection
    if not candidates:
        print("   ⚠️  No unique quotes found on Reddit — using built-in collection")
        return _fallback_builtin_quote(used_file)
    
    # Sort by score and pick from top candidates
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    top_candidates = candidates[:5]
    chosen = random.choice(top_candidates)
    
    chosen["text"] = _clean_text(chosen["text"])
    
    final_quote = {
        "text": chosen["text"],
        "author": chosen["author"],
        "category": chosen["category"],
        "source": chosen.get("source", "Reddit"),
    }
    
    quote_hash = _hash_quote(chosen["text"])
    USED_QUOTES_HASHES.add(quote_hash)
    save_used_hash(used_file, quote_hash, chosen["text"], chosen["author"], chosen.get("source", ""))
    
    print(f"   📊 Found {len(candidates)} candidates, picked best one")
    print(f"   🔗 Source: {chosen.get('source', 'Reddit')}")
    
    return final_quote


def _fallback_builtin_quote(used_file):
    """Fall back to the built-in quotes collection if Reddit scraping fails."""
    from quote_picker import pick_quote
    
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "quotes.json"),
        "data/quotes.json",
    ]
    
    quotes_file = None
    for path in possible_paths:
        if os.path.exists(path):
            quotes_file = path
            break
    
    if not quotes_file:
        return {
            "text": "The only true wisdom is in knowing you know nothing.",
            "author": "Socrates",
            "category": "classical",
            "source": "built-in fallback",
        }
    
    quote = pick_quote(quotes_file, used_file)
    quote["source"] = "built-in collection"
    return quote


if __name__ == "__main__":
    quote = pick_quote_from_reddit("temp/used_reddit.json")
    print(f"\n📝 \"{quote['text'][:80]}...\"")
    print(f"   — {quote['author']} ({quote['category']})")
    print(f"   Source: {quote.get('source', 'unknown')}")
