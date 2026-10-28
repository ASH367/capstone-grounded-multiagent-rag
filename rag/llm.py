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
    return {"anthropic": Anthropic, "ollama": Ollama, "mock": Mock}[name](*([model] if model else []))
