"""Pluggable LLM backends. Each returns (text, seconds). Pick with --backend in rag/run_live.py."""
import json, os, re, time, urllib.request

def extract_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m: raise ValueError("no JSON object in model output")
    return json.loads(m.group(0))

class Anthropic:
    """Needs: pip install anthropic ; export ANTHROPIC_API_KEY=... (never commit the key)"""
    def __init__(self, model="claude-sonnet-5-5"):
        import anthropic; self.c = anthropic.Anthropic(); self.model = model; self.name = f"anthropic:{model}"
    def call(self, prompt):
        t = time.perf_counter()
        r = self.c.messages.create(model=self.model, max_tokens=2000, temperature=0, messages=[{"role": "user", "content": prompt}])
        return r.content[0].text, time.perf_counter() - t

class Ollama:
    """Local open model. Needs: ollama serve ; ollama pull llama3.1:8b (or any model)"""
    def __init__(self, model="llama3.1:8b", host="http://localhost:11434"):
        self.model, self.host, self.name = model, host, f"ollama:{model}"
    def call(self, prompt):
        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}}).encode()
        t = time.perf_counter()
        with urllib.request.urlopen(urllib.request.Request(self.host + "/api/generate", body, {"Content-Type": "application/json"}), timeout=600) as r:
            out = json.load(r)["response"]
        return out, time.perf_counter() - t

class Spend:
    """Running cost of this process. Cost = provider-reported usage.cost when present (OpenRouter), else tokens x LLM_PRICE_IN/OUT (USD per 1M tokens; default 3/15 is an ASSUMPTION - set the real price).
    Hard stop: export MAX_USD=5 aborts the run (SystemExit) once the running total passes it. Log: set LLM_USAGE_LOG=path to append one json line per call."""
    usd = 0.0; calls = 0; tin = 0; tout = 0
    @classmethod
    def add(cls, usage, model):
        pi, po = float(os.environ.get("LLM_PRICE_IN", 3)), float(os.environ.get("LLM_PRICE_OUT", 15))
        a, b = int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
        c = usage.get("cost"); c = float(c) if isinstance(c, (int, float)) else (a * pi + b * po) / 1e6
        cls.usd += c; cls.calls += 1; cls.tin += a; cls.tout += b
        if os.environ.get("LLM_USAGE_LOG"):
            with open(os.environ["LLM_USAGE_LOG"], "a") as f: f.write(json.dumps({"model": model, "in": a, "out": b, "usd": round(c, 6), "total_usd": round(cls.usd, 4)}) + "\n")
        cap = os.environ.get("MAX_USD")
        if cap and cls.usd > float(cap): raise SystemExit(f"SPEND CAP: ${cls.usd:.2f} > MAX_USD={cap}. Stopped. Re-run the same command to resume (finished work is kept).")

class OpenAICompat:
    """Any OpenAI-compatible chat API (OpenAI, Together, Groq, OpenRouter, ...). Needs: export LLM_API_KEY=... ; optional LLM_BASE_URL (default https://api.openai.com/v1). Never commit the key.
    Retries 429/5xx/timeouts with exponential backoff (honours Retry-After). Prompts are NOT changed."""
    def __init__(self, model):
        self.model = model; self.base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"); self.key = os.environ["LLM_API_KEY"]; self.name = f"openai-compat:{model}"
    def call(self, prompt, tries=7):
        b = {"model": self.model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}
        if "openrouter" in self.base: b["usage"] = {"include": True}
        body = json.dumps(b).encode(); t = time.perf_counter(); last = None
        for k in range(tries):
            req = urllib.request.Request(self.base + "/chat/completions", body, {"Content-Type": "application/json", "Authorization": "Bearer " + self.key})
            try:
                with urllib.request.urlopen(req, timeout=600) as r: j = json.load(r)
                Spend.add(j.get("usage", {}), self.model); return j["choices"][0]["message"]["content"], time.perf_counter() - t
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (401, 402, 403): raise SystemExit(f"STOPPED: HTTP {e.code} from the API. 401/403 = key rejected, revoked or over its limit; 402 = no credit. Fix the key/credit, then run the same command again (finished work is kept). Nothing was spent on this failed call.")
                if e.code not in (408, 429, 500, 502, 503, 504) or k == tries - 1: raise
                ra = e.headers.get("Retry-After"); time.sleep(min(90, float(ra) if ra and ra.replace(".", "").isdigit() else 3 * 2 ** k))
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last = e
                if k == tries - 1: raise
                time.sleep(min(90, 3 * 2 ** k))
        raise last

def call_json(be, prompt, tries=3):
    """call + parse; re-asks (same prompt) if the output is not valid JSON."""
    last = None
    for _ in range(tries):
        text, sec = be.call(prompt)
        try: return extract_json(text), sec
        except Exception as e: last = e
    raise last

class Mock:
    """For testing the harness only: returns schema-valid JSON quoting the first passage. NOT a result."""
    name = "mock"
    def call(self, prompt):
        time.sleep(0.05); t = time.perf_counter()
        pid = int(re.search(r'<passage id="(\d+)"', prompt).group(1)) if "<passage id" in prompt else 0
        quote = " ".join(re.search(r'<passage id="\d+"[^>]*>\n(.*?)\n</passage>', prompt, re.S).group(1).split()[:8]) if "<passage id" in prompt else ""
        fact = " ".join(re.search(r"<case_facts>\n\[1\] (.*?)\n", prompt, re.S).group(1).split()[:8])
        f = [{"claim": "mock", "passage_id": pid, "quote": quote, "case_fact": fact}]
        if '"decision"' in prompt: out = {"decision": "NOT_COVERED", "reason": "mock", "findings": f, "passage_ids": [pid]}
        else: out = {"verdict": "UNKNOWN", "findings": f}
        return json.dumps(out), time.perf_counter() - t + 0.05

def get(name, model=None):
    return {"anthropic": Anthropic, "ollama": Ollama, "openai": OpenAICompat, "mock": Mock}[name](*([model] if model else []))
