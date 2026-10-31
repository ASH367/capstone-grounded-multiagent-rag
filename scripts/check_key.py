#!/usr/bin/env python3
"""Pre-flight: is the OpenRouter key accepted, and how much credit/limit is left?  Never prints the key.   (reads LLM_API_KEY, LLM_BASE_URL)"""
import json, os, sys, urllib.request, urllib.error
base = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"); key = os.environ.get("LLM_API_KEY", "")
if not key: sys.exit("NO KEY: LLM_API_KEY is empty.")
try:
    with urllib.request.urlopen(urllib.request.Request(base + "/auth/key", headers={"Authorization": "Bearer " + key}), timeout=30) as r: d = json.load(r).get("data", {})
    print(f"key OK | used ${d.get('usage', 0):.2f} | limit {d.get('limit')} | remaining {d.get('limit_remaining')} | free tier: {d.get('is_free_tier')}")
except urllib.error.HTTPError as e:
    sys.exit(f"KEY REJECTED: HTTP {e.code}. Create a new key in OpenRouter (Keys page), check it has credit and no tiny limit, and run again.")
