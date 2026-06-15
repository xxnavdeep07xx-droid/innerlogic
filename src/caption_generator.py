#!/usr/bin/env python3
"""
Caption Generator — Creates Instagram captions with descriptions and hashtags.
Generates engaging, relevant captions for philosophical/psychological content.
"""

import random


# Hashtag collections by category
CATEGORY_HASHTAGS = {
    "stoicism": [
        "#stoicism", "#stoic", "#marcusaurelius", "#seneca", "#epictetus",
        "#stoicphilosophy", "#dailystoic", "#stoicmindset", "#stoicquotes",
        "#stoicwisdom"
    ],
    "existentialism": [
        "#existentialism", "#nietzsche", "#camus", "#sartre", "#kierkegaard",
        "#existential", "#absurdism", "#meaningoflife", "#philosophy",
        "#deepthoughts"
    ],
    "eastern": [
        "#buddhism", "#taoism", "#zen", "#mindfulness", "#meditation",
        "#laotzu", "#buddha", "#easternphilosophy", "#innerpeace",
        "#spiritualawakening"
    ],
    "psychology": [
        "#psychology", "#carljung", "#mentalhealth", "#selfdiscovery",
        "#shadowwork", "#unconscious", "#psychoanalysis", "#depthpsychology",
        "#personalgrowth", "#selfawareness"
    ],
    "classical": [
        "#philosophy", "#socrates", "#plato", "#aristotle", "#ancientwisdom",
        "#greekphilosophy", "#classicalphilosophy", "#wisdom", "#thinkers",
        "#philosophical"
    ],
    "mysticism": [
        "#mysticism", "#rumi", "#sufism", "#spirituality", "#divine",
        "#sacred", "#mystical", "#soulsjourney", "#enlightenment",
        "#transcendence"
    ],
    "transcendentalism": [
        "#transcendentalism", "#emerson", "#thoreau", "#nature", "#selfreliance",
        "#individualism", "#spiritual", "#philosophy", "#deepthinking",
        "#wisdomquotes"
    ],
    "motivation": [
        "#motivation", "#inspiration", "#mindset", "#growth", "#discipline",
        "#selfimprovement", "#success", "#grind", "#hustle", "#nevergiveup"
    ],
    "rationalism": [
        "#rationalism", "#descartes", "#reason", "#logic", "#philosophy",
        "#criticalthinking", "#intellect", "#thought", "#mind", "#wisdom"
    ],
    "courage": [
        "#courage", "#bravery", "#fearless", "#strength", "#resilience",
        "#warriormindset", "#overcome", "#bold", "#fearlessness", "#determination"
    ],
}

# Universal hashtags (always included)
UNIVERSAL_HASHTAGS = [
    "#innerlogic", "#philosophy", "#deepquotes", "#psychology",
    "#quotestoliveby", "#philosophical", "#mindset", "#wisdom",
    "#deepthoughts", "#thinkaboutit", "#reelquotes", "#instaquotes",
    "#philosophyquotes", "#psychologyfacts", "#darkaesthetic",
    "#cinematic", "#motivationalquotes", "#lifelessons"
]

# Caption templates
CAPTION_TEMPLATES = [
    '📝 "{quote}"\n\n— {author}\n\n\n{hashtags}',
    '"{quote}"\n\n— {author}\n\n💭 What are your thoughts?\n\n{hashtags}',
    '{quote}\n\n— {author}\n\n🔄 Share if this resonates.\n\n{hashtags}',
    '"{quote}"\n\n— {author}\n\n🧠 Food for thought.\n\n{hashtags}',
    '💡 "{quote}"\n\n— {author}\n\n👇 Comment your interpretation.\n\n{hashtags}',
]


def generate_caption(quote_data):
    """
    Generate an Instagram caption with the quote, author, and relevant hashtags.
    
    Args:
        quote_data: Dict with 'text', 'author', 'category' keys
    
    Returns:
        str: Complete Instagram caption
    """
    text = quote_data["text"]
    author = quote_data["author"]
    category = quote_data.get("category", "philosophy")
    
    # Get category-specific hashtags (pick 5-8 random ones)
    category_tags = CATEGORY_HASHTAGS.get(category, CATEGORY_HASHTAGS["classical"])
    num_category_tags = random.randint(5, 8)
    selected_category_tags = random.sample(category_tags, min(num_category_tags, len(category_tags)))
    
    # Get universal hashtags (pick 8-12 random ones)
    num_universal_tags = random.randint(8, 12)
    selected_universal_tags = random.sample(UNIVERSAL_HASHTAGS, min(num_universal_tags, len(UNIVERSAL_HASHTAGS)))
    
    # Combine and shuffle hashtags
    all_hashtags = selected_category_tags + selected_universal_tags
    random.shuffle(all_hashtags)
    hashtag_string = " ".join(all_hashtags)
    
    # Pick a caption template
    template = random.choice(CAPTION_TEMPLATES)
    
    # Format the caption
    caption = template.format(
        quote=text,
        author=author,
        hashtags=hashtag_string
    )
    
    # Instagram caption limit is 2200 characters
    if len(caption) > 2200:
        # Truncate hashtags if needed
        caption = caption[:2197] + "..."
    
    return caption


if __name__ == "__main__":
    # Quick test
    test_quote = {
        "text": "The unexamined life is not worth living.",
        "author": "Socrates",
        "category": "classical"
    }
    caption = generate_caption(test_quote)
    print(caption)
    print(f"\n--- Caption length: {len(caption)} chars ---")
