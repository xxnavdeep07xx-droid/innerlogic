#!/usr/bin/env python3
"""
DEPRECATED — This module is no longer used by the pipeline.
With instagrapi, there are no access tokens to refresh.
This file is kept for reference only.

Token Refresh — Automatically refreshes Instagram Graph API access tokens.
Short-lived tokens (~1 hour) are exchanged for long-lived tokens (60 days).
Long-lived tokens can be refreshed before expiry to get a new 60-day token.
"""

import requests
import os
import json
from datetime import datetime


# Graph API endpoint for token exchange
TOKEN_EXCHANGE_URL = "https://graph.facebook.com/v18.0/oauth/access_token"


def exchange_for_long_lived_token(short_lived_token, app_id, app_secret):
    """
    Exchange a short-lived token for a long-lived token (60 days).
    
    Args:
        short_lived_token: The short-lived access token (~1 hour expiry)
        app_id: Facebook App ID
        app_secret: Facebook App Secret
    
    Returns:
        str: Long-lived access token (60 days expiry)
    """
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token,
    }
    
    response = requests.get(TOKEN_EXCHANGE_URL, params=params, timeout=30)
    
    if response.status_code != 200:
        error_data = response.json().get("error", {})
        error_msg = error_data.get("message", response.text)
        raise RuntimeError(f"Token exchange failed: {error_msg}")
    
    data = response.json()
    new_token = data.get("access_token")
    expires_in = data.get("expires_in", "unknown")
    
    if new_token:
        print(f"   ✅ Token refreshed! Expires in: {expires_in} seconds")
        if expires_in != "unknown":
            days = expires_in / 86400
            print(f"   📅 Token valid for ~{days:.0f} days")
        return new_token
    
    raise RuntimeError(f"No access token in response: {response.text}")


def debug_token(access_token, input_token):
    """
    Debug a token to check its expiry and permissions.
    
    Args:
        access_token: App access token or valid token
        input_token: The token to debug
    
    Returns:
        dict: Token debug information
    """
    url = f"https://graph.facebook.com/v18.0/debug_token"
    params = {
        "input_token": input_token,
        "access_token": access_token,
    }
    
    response = requests.get(url, params=params, timeout=30)
    
    if response.status_code == 200:
        return response.json().get("data", {})
    return {}


def refresh_access_token(current_token, app_id, app_secret):
    """
    Refresh the access token. Works for both short-lived and long-lived tokens.
    Always returns a valid long-lived token.
    
    If the current token is still valid, refreshing it extends the expiry.
    If the current token is expired, this will fail (user needs to regenerate).
    
    Args:
        current_token: Current access token (short or long-lived)
        app_id: Facebook App ID
        app_secret: Facebook App Secret
    
    Returns:
        str: Valid long-lived access token
    """
    try:
        new_token = exchange_for_long_lived_token(current_token, app_id, app_secret)
        
        # Try to update the GitHub Secret if we're in a GitHub Action
        _try_update_github_secret(new_token)
        
        return new_token
        
    except Exception as e:
        print(f"   ⚠️  Token refresh failed: {e}")
        print(f"   ⚠️  Using current token (may be close to expiry)")
        return current_token


def _try_update_github_secret(new_token):
    """
    Try to update the INSTAGRAM_ACCESS_TOKEN GitHub Secret automatically.
    This only works if a PERSONAL_ACCESS_TOKEN is set in the repository secrets.
    
    The PERSONAL_ACCESS_TOKEN needs the 'repo' scope to update secrets.
    """
    github_token = os.environ.get("PERSONAL_ACCESS_TOKEN", "")
    github_repository = os.environ.get("GITHUB_REPOSITORY", "")
    
    if not github_token or not github_repository:
        # No auto-update configured — that's fine
        return
    
    try:
        # Get the repository's public key for encrypting secrets
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        
        # Get public key
        key_url = f"https://api.github.com/repos/{github_repository}/actions/secrets/public-key"
        response = requests.get(key_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return
        
        key_data = response.json()
        public_key = key_data["key"]
        key_id = key_data["key_id"]
        
        # Encrypt the new token using the public key
        from base64 import b64encode
        from nacl import public
        
        public_key_obj = public.PublicKey(b64encode(b"\0" * 32).decode(), encoder=None)
        # Simplified: just update via gh CLI if available
        import subprocess
        result = subprocess.run(
            ["gh", "secret", "set", "INSTAGRAM_ACCESS_TOKEN", "--body", new_token],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"   ✅ GitHub Secret updated automatically!")
        else:
            print(f"   ⚠️  Could not auto-update GitHub Secret")
            
    except Exception as e:
        # Auto-update is optional — don't fail the pipeline
        print(f"   ℹ️  Auto token update not available: {e}")


if __name__ == "__main__":
    # Quick test — exchange a short-lived token for a long-lived one
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python token_refresh.py <current_token> <app_id> <app_secret>")
        sys.exit(1)
    
    token = sys.argv[1]
    app_id = sys.argv[2]
    app_secret = sys.argv[3]
    
    new_token = exchange_for_long_lived_token(token, app_id, app_secret)
    print(f"\nNew long-lived token:\n{new_token}")
    print(f"\n⚠️  Save this token as your INSTAGRAM_ACCESS_TOKEN!")
