#!/usr/bin/env python3
"""
Caption Generator — AI-powered Instagram captions for philosophical content.

Strategy:
  1. PRIMARY: Call Pollinations.ai free text LLM (no API key needed — same
     provider we already use for image generation, so the project stays 100%
     free and runs on GitHub Actions with zero extra setup).
     The LLM produces:
       - 1 scroll-stopping HOOK (first line of the caption — visible before
         "...more" — designed to boost first-3-second retention)
       - 1 short reflection paragraph in the brand voice (1-2 sentences)
       - 1 clear CTA (rotates between Save / Share / Comment / Follow)
       - 18-22 hashtags mixing viral + niche + author + branded
  2. FALLBACK: If the LLM call fails (network down, rate-limited, garbage
     response), use an enhanced local template system that still rotates
     through curated hooks, reflections, CTAs, and a deep hashtag pool.

Engagement rationale
- Hook → IG shows only the first line in the feed; a strong hook boosts
  "tap-to-expand" → boosts dwell time → boosts reach.
- Reflection paragraph → adds unique value (not just the quote) → boosts saves.
- Rotating CTA → drives one specific action per post → boosts that signal
  (saves, shares, comments, follows) which the IG algorithm rewards.
- Hashtag mix → balances reach (viral #fyp #viral) with targeting (niche
  #stoicism #carljung) with brand recall (#innerlogic).
- Variable structure → avoids the "templated content" shadow-ban signal.
"""

import json
import logging
import random
import re
import time
import urllib.parse
import urllib.request

logger = logging.getLogger("innerlogic")


# ─── Brand voice / config ────────────────────────────────────────────────────

BRAND_HANDLE = "@innerlogic.co"

# Hashtag collections by category
CATEGORY_HASHTAGS = {
    "stoicism": [
        "#stoicism", "#stoic", "#marcusaurelius", "#seneca", "#epictetus",
        "#stoicphilosophy", "#dailystoic", "#stoicmindset", "#stoicquotes",
        "#stoicwisdom", "#stoiclife", "#amorfati"
    ],
    "existentialism": [
        "#existentialism", "#nietzsche", "#camus", "#sartre", "#kierkegaard",
        "#existential", "#absurdism", "#meaningoflife", "#philosophy",
        "#deepthoughts", "#nihilism", "#existentialcrisis"
    ],
    "eastern": [
        "#buddhism", "#taoism", "#zen", "#mindfulness", "#meditation",
        "#laotzu", "#buddha", "#easternphilosophy", "#innerpeace",
        "#spiritualawakening", "#tao", "#zenquotes"
    ],
    "psychology": [
        "#psychology", "#carljung", "#mentalhealth", "#selfdiscovery",
        "#shadowwork", "#unconscious", "#psychoanalysis", "#depthpsychology",
        "#personalgrowth", "#selfawareness", "#jungian", "#archetypes"
    ],
    "classical": [
        "#philosophy", "#socrates", "#plato", "#aristotle", "#ancientwisdom",
        "#greekphilosophy", "#classicalphilosophy", "#wisdom", "#thinkers",
        "#philosophical", "#presocratics", "#hellenistic"
    ],
    "mysticism": [
        "#mysticism", "#rumi", "#sufism", "#spirituality", "#divine",
        "#sacred", "#mystical", "#soulsjourney", "#enlightenment",
        "#transcendence", "#sufipoetry", "#rumiquotes"
    ],
    "transcendentalism": [
        "#transcendentalism", "#emerson", "#thoreau", "#nature", "#selfreliance",
        "#individualism", "#spiritual", "#philosophy", "#deepthinking",
        "#wisdomquotes", "#walden", "#emersonquotes"
    ],
    "motivation": [
        "#motivation", "#inspiration", "#mindset", "#growth", "#discipline",
        "#selfimprovement", "#success", "#grind", "#hustle", "#nevergiveup",
        "#mindsetmatters", "#daily motivation".replace(" ", "")
    ],
    "rationalism": [
        "#rationalism", "#descartes", "#reason", "#logic", "#philosophy",
        "#criticalthinking", "#intellect", "#thought", "#mind", "#wisdom",
        "#empiricism", "#spinoza"
    ],
    "courage": [
        "#courage", "#bravery", "#fearless", "#strength", "#resilience",
        "#warriormindset", "#overcome", "#bold", "#fearlessness", "#determination",
        "#faceyourfears", "#brave"
    ],
}

# Universal hashtags — always included
UNIVERSAL_HASHTAGS = [
    "#innerlogic", "#philosophy", "#deepquotes", "#psychology",
    "#quotestoliveby", "#philosophical", "#mindset", "#wisdom",
    "#deepthoughts", "#thinkaboutit", "#reelquotes", "#instaquotes",
    "#philosophyquotes", "#psychologyfacts", "#darkaesthetic",
    "#cinematic", "#motivationalquotes", "#lifelessons",
    "#quotestagram", "#wordsofwisdom", "#thinkers", "#deep",
    "#meaning", "#truth", "#consciousness", "#awakening"
]

# Viral/reach hashtags — small mix, rotated
VIRAL_HASHTAGS = [
    "#viral", "#reels", "#reelsinstagram", "#explore", "#explorepage",
    "#fyp", "#foryou", "#trending", "#reelitfeelit", "#instareels",
    "#reelsviral", "#trendingreels"
]

# Curated hooks — used by the FALLBACK path. AI generates fresh ones when available.
HOOK_TEMPLATES = [
    "Read this slowly. 📖",
    "Save this for when you need it. 🔖",
    "This stopped me mid-scroll. ⏸️",
    "Don't skip this one. ⚠️",
    "Took me years to understand this. ⏳",
    "Most people will never get this. 🧠",
    "Read it twice. The second time hits different. ♻️",
    "If nobody told you today… 👇",
    "This is your sign. ✨",
    "Whoever needs to hear this, send it to them. 📨",
    "Stop scrolling for 10 seconds. ⏸️",
    "This is the part most people miss. 👀",
    "The truth nobody talks about. 🤫",
    "Pin this. You'll want it later. 📌",
    "Some truths arrive late. This is one. ⏰",
]

# Reflection templates — used by the FALLBACK path.
REFLECTION_TEMPLATES = [
    "We rarely get to choose when the truth arrives — only whether we'll meet it honestly when it does.",
    "The hardest part isn't knowing the truth. It's letting it change the way you've been living.",
    "What we resist understanding doesn't disappear. It just waits, quietly, until we're ready.",
    "Most of us spend years running from a single realization that could free us in an afternoon.",
    "Wisdom isn't information. It's the slow, painful process of becoming someone who can hold it.",
    "Every profound idea sounds obvious once you've lived it. That's how you know it's true.",
    "The mind protects itself with distractions. The soul waits in silence for the moment you stop.",
    "Truth doesn't shout. It whispers. And it's patient enough to wait for you.",
    "What looks like darkness is often just an unfinished thought, asking to be completed.",
    "Freedom begins the moment you stop negotiating with what you already know.",
]

# CTA pool — rotated for engagement signal diversity
CTA_POOL = [
    "🔖 Save this — you'll want to come back to it later.",
    "📨 Send this to someone who needs to hear it today.",
    "💬 What's your take? Drop a comment below.",
    "👉 Follow {brand} for daily philosophical reels.",
    "♻️ Share this if it resonated with you.",
    "📌 Save this and read it again next week.",
    "🧠 Comment '✓' if this changed your perspective.",
    "🔥 Follow {brand} for more reels like this.",
    "✨ Tag a friend who'd appreciate this.",
    "🌿 Follow {brand} — daily wisdom, no fluff.",
]


# ─── AI caption generation (Pollinations.ai free text LLM) ──────────────────

AI_SYSTEM_PROMPT = """You write Instagram captions for @innerlogic.co — a philosophical Reels account with a dark, cinematic aesthetic. The audience is 18-35, thoughtful, introspective, tired of motivational fluff.

Your job: given a quote, write ONE complete Instagram caption that maximizes engagement (saves, shares, comments, follows) WITHOUT sounding salesy, gimmicky, or AI-generated.

Output STRICTLY as JSON with these exact keys:
{
  "hook": "One short, scroll-stopping first line. No emojis here unless powerful. 4-10 words. Make the reader NEED to expand the caption.",
  "reflection": "1-2 sentence original reflection in the brand voice — quiet, sharp, slightly melancholic. Do NOT restate the quote. Add a new angle. Max 240 chars.",
  "cta": "One single clear call-to-action with ONE emoji. Rotate between: save, share, comment, follow @innerlogic.co, tag a friend. 8-20 words.",
  "hashtags": "18-22 hashtags as a single space-separated string. Mix: 3-5 viral (#reels #viral #explore), 6-8 niche (based on quote theme), 2-3 author-specific, 3-4 branded (#innerlogic #philosophy #deepquotes). Lowercase, no spaces inside tags."
}

Rules:
- No quote marks around the hook.
- No "Caption:" or "Hook:" labels — just the values.
- The reflection must NOT start with "This quote" or "The author".
- Hashtags must each start with # and have NO spaces.
- Pure JSON only, no markdown fences, no commentary."""


def _call_pollinations_llm(quote_data, timeout=60):
    """
    Call Pollinations.ai's free OpenAI-compatible text endpoint.
    Returns parsed dict on success, None on any failure.
    No API key required.
    """
    quote_text = quote_data["text"]
    author = quote_data.get("author", "Unknown")
    category = quote_data.get("category", "philosophy")

    user_prompt = (
        f"Quote: \"{quote_text}\"\n"
        f"Author: {author}\n"
        f"Category: {category}\n\n"
        f"Write the caption JSON now."
    )

    payload = {
        "model": "openai",
        "messages": [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.85,
        "max_tokens": 700,
    }

    url = "https://text.pollinations.ai/openai"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                # Pollinations requires a Referer header for the free tier.
                # Use the project's domain — no API key needed.
                "Referer": "https://innerlogic.co",
                "User-Agent": "InnerLogic/1.0 (Instagram Reels automation)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        content = data["choices"][0]["message"]["content"].strip()
        return _parse_ai_caption_json(content)
    except Exception as e:
        logger.warning(f"   ⚠️ AI caption API failed: {str(e)[:120]}")
        return None


def _parse_ai_caption_json(content):
    """Robustly extract the JSON object from the LLM response."""
    # Strip markdown code fences if present
    content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
    content = re.sub(r"\s*```$", "", content, flags=re.IGNORECASE).strip()

    # Try direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Fallback: extract the first {...} block
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _validate_ai_caption(caption_dict):
    """Validate the AI caption has all required keys with reasonable content."""
    if not isinstance(caption_dict, dict):
        return False
    required = ["hook", "reflection", "cta", "hashtags"]
    for k in required:
        v = caption_dict.get(k)
        if not isinstance(v, str) or len(v.strip()) < 3:
            return False
    # Hashtags must contain at least 8 # tags
    if caption_dict["hashtags"].count("#") < 8:
        return False
    return True


# ─── Local fallback caption builder ──────────────────────────────────────────

def _build_local_caption(quote_data):
    """Build a caption locally when the AI call fails."""
    text = quote_data["text"]
    author = quote_data.get("author", "Unknown")
    category = quote_data.get("category", "philosophy")

    hook = random.choice(HOOK_TEMPLATES)
    reflection = random.choice(REFLECTION_TEMPLATES)
    cta = random.choice(CTA_POOL).format(brand=BRAND_HANDLE)

    # Hashtags: niche (5-8) + universal (10-12) + viral (3-5)
    niche_pool = CATEGORY_HASHTAGS.get(category, CATEGORY_HASHTAGS["classical"])
    niche_tags = random.sample(niche_pool, min(random.randint(5, 8), len(niche_pool)))
    universal_tags = random.sample(UNIVERSAL_HASHTAGS,
                                   min(random.randint(10, 12), len(UNIVERSAL_HASHTAGS)))
    viral_tags = random.sample(VIRAL_HASHTAGS, min(random.randint(3, 5), len(VIRAL_HASHTAGS)))

    all_tags = niche_tags + universal_tags + viral_tags
    random.shuffle(all_tags)
    hashtag_string = " ".join(all_tags)

    caption = (
        f"{hook}\n\n"
        f"\"{text}\"\n"
        f"— {author}\n\n"
        f"{reflection}\n\n"
        f"{cta}\n\n"
        f"{hashtag_string}"
    )
    return caption


def _build_caption_from_ai(ai_dict, quote_data):
    """Assemble the final caption string from the AI-returned components."""
    text = quote_data["text"]
    author = quote_data.get("author", "Unknown")

    hook = ai_dict.get("hook", "").strip()
    reflection = ai_dict.get("reflection", "").strip()
    cta = ai_dict.get("cta", "").strip().format(brand=BRAND_HANDLE)
    hashtags = ai_dict.get("hashtags", "").strip()

    # Safety: if hashtags don't all start with #, fix the obvious cases
    tags_fixed = []
    for tag in hashtags.split():
        if not tag.startswith("#"):
            tag = "#" + tag
        # Remove internal spaces
        tag = "#" + tag.lstrip("#").replace(" ", "")
        tags_fixed.append(tag)
    hashtags = " ".join(tags_fixed)

    # Always ensure the branded tag is present
    if "#innerlogic" not in hashtags.lower():
        hashtags = "#innerlogic " + hashtags

    caption = (
        f"{hook}\n\n"
        f"\"{text}\"\n"
        f"— {author}\n\n"
        f"{reflection}\n\n"
        f"{cta}\n\n"
        f"{hashtags}"
    )
    return caption


# ─── Public entry point ──────────────────────────────────────────────────────

def generate_caption(quote_data, use_ai=True):
    """
    Generate an Instagram caption.

    Args:
        quote_data: Dict with 'text', 'author', 'category' keys.
        use_ai: If True (default), try the free LLM first. Falls back to
                local templates on any failure.

    Returns:
        str: Complete Instagram caption (≤2200 chars).
    """
    caption = None
    ai_used = False

    if use_ai:
        try:
            t0 = time.time()
            ai_dict = _call_pollinations_llm(quote_data)
            if ai_dict and _validate_ai_caption(ai_dict):
                caption = _build_caption_from_ai(ai_dict, quote_data)
                ai_used = True
                logger.info(f"   ✨ AI caption generated in {time.time()-t0:.1f}s")
            elif ai_dict:
                logger.warning("   ⚠️ AI caption failed validation — using local fallback")
        except Exception as e:
            logger.warning(f"   ⚠️ AI caption error: {str(e)[:120]}")

    if caption is None:
        caption = _build_local_caption(quote_data)
        logger.info("   📝 Caption built from local templates")

    # Instagram caption limit
    if len(caption) > 2200:
        caption = caption[:2197] + "..."

    return caption


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    test_quotes = [
        {"text": "Hell is Truth Seen Too Late", "author": "Thomas Hardy", "category": "classical"},
        {"text": "The unexamined life is not worth living.", "author": "Socrates", "category": "classical"},
        {"text": "He who has a why to live can bear almost any how.", "author": "Friedrich Nietzsche", "category": "existentialism"},
    ]

    use_ai = "--no-ai" not in sys.argv
    for q in test_quotes:
        print(f"\n{'='*70}")
        print(f"QUOTE: {q['text']} — {q['author']} ({q['category']})")
        print('='*70)
        cap = generate_caption(q, use_ai=use_ai)
        print(cap)
        print(f"\n--- {len(cap)} chars ---")
