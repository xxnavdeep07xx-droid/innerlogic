#!/usr/bin/env python3
"""
Quote Picker — Selects an unused philosophical quote from the collection.
Tracks used quotes to avoid repetition. Resets when all quotes are used.
"""

import json
import random
import os
from datetime import datetime


def load_quotes(quotes_file):
    """Load the quotes collection from JSON file."""
    with open(quotes_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_used_quotes(used_file):
    """Load the set of already-used quote indices."""
    if not os.path.exists(used_file):
        return {"used_indices": [], "last_reset": None}
    with open(used_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_used_quotes(used_file, data):
    """Save the updated used quotes tracking data."""
    dir_name = os.path.dirname(used_file)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(used_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def pick_quote(quotes_file, used_file):
    """
    Pick a random unused quote from the collection.
    Resets the used list when all quotes have been used.
    
    Returns:
        dict: Quote object with 'text', 'author', and 'category' keys.
    """
    quotes = load_quotes(quotes_file)
    total = len(quotes)
    
    used_data = load_used_quotes(used_file)
    used_indices = set(used_data.get("used_indices", []))
    
    # Find unused indices
    all_indices = set(range(total))
    unused_indices = all_indices - used_indices
    
    # If all quotes used, reset
    if not unused_indices:
        today = datetime.now().strftime("%Y-%m-%d")
        used_data = {"used_indices": [], "last_reset": today}
        save_used_quotes(used_file, used_data)
        unused_indices = all_indices
        print(f"   ♻️  All {total} quotes used — resetting collection!")
    
    # Pick a random unused quote
    chosen_index = random.choice(list(unused_indices))
    quote = quotes[chosen_index]
    
    # Track this quote as used
    used_data["used_indices"].append(chosen_index)
    save_used_quotes(used_file, used_data)
    
    print(f"   📊 Quote {len(used_data['used_indices'])}/{total} used in current cycle")
    
    return quote


if __name__ == "__main__":
    # Quick test
    quote = pick_quote("data/quotes.json", "data/used_quotes.json")
    print(f"\n📝 \"{quote['text']}\"")
    print(f"   — {quote['author']} ({quote['category']})")
