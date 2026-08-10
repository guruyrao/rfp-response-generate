"""LLM client. LLM chat calls go to a fast cloud API (Groq/DeepSeek) by
default; embeddings stay on local Ollama (cloud providers have no embeddings).

Provider switch:
  LLM_PROVIDER=groq    (default) -> Groq OpenAI-compatible /chat/completions
   LLM_PROVIDER=deepseek           -> DeepSeek OpenAI-compatible /chat/completions
   LLM_PROVIDER=ollama             -> local Ollama /api/chat (no API key / quota)
                                       Set OLLAMA_MODEL (default deepseek-r1:7b)

Env overrides:
  GROQ_API_KEY       (falls back to ~/.local/share/opencode/auth.json groq.key)
  GROQ_BASE_URL      (default https://api.groq.com/openai/v1)
  GROQ_MODEL         (default llama-3.3-70b-versatile)
  DEEPSEEK_API_KEY   (falls back to ~/.local/share/opencode/auth.json deepseek.key)
  DEEPSEEK_BASE_URL  (default https://api.deepseek.com/v1)
  DEEPSEEK_MODEL     (default deepseek-v4-flash)
  OLLAMA_URL         (default http://localhost:11434)
   LLAMA_MODEL        (default llama-3.3-70b-versatile)
   OLLAMA_NUM_CTX     (default 16384; passes num_ctx to Ollama so models like
                       deepseek-r1:7b can use their native large context)
    EMBED_MODEL        (default nomic-embed-text)
   OLLAMA_MODEL        (default deepseek-r1:7b)
"""
import json
import os
import sys
import urllib.request
import urllib.error

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
GROQ_BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1:7b")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq")


class LLMError(Exception):
    pass


def _auth_key(provider):
    key = os.environ.get(f"{provider.upper()}_API_KEY", "").strip()
    if key:
        return key
    auth_path = os.path.join(
        os.environ.get("USERPROFILE", r"C:\Users\guru"),
        ".local", "share", "opencode", "auth.json",
    )
    try:
        with open(auth_path, "r", encoding="utf-8") as f:
            auth = json.load(f)
        return (auth.get(provider) or {}).get("key", "")
    except Exception:
        return ""


def _post(url, payload, headers, timeout=1800):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        raise LLMError(f"HTTP {e.code} from {url}: {body}")
    except Exception as e:
        raise LLMError(f"Request failed: {e}")


def _chat_openai(base_url, key, model, system_prompt, user_prompt, format_json):
    if not key:
        raise LLMError(f"No API key found for {base_url} (set the corresponding env var)")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": "rfp-response-generate/1.0",
    }
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    payload = {"model": model, "messages": messages, "stream": False, "temperature": 0.2}
    if format_json:
        payload["response_format"] = {"type": "json_object"}
    resp = _post(base_url + "/chat/completions", payload, headers)
    try:
        content = resp["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LLMError(f"Unexpected API response: {str(resp)[:400]}")
    return (content or "").strip()


def _chat_deepseek(system_prompt, user_prompt, model, format_json):
    return _chat_openai(
        DEEPSEEK_BASE_URL, _auth_key("deepseek"), model,
        system_prompt, user_prompt, format_json,
    )


def _chat_groq(system_prompt, user_prompt, model, format_json):
    return _chat_openai(
        GROQ_BASE_URL, _auth_key("groq"), model,
        system_prompt, user_prompt, format_json,
    )


def _chat_ollama(system_prompt, user_prompt, model, format_json):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    payload = {"model": model, "messages": messages, "stream": False}
    options = {}
    num_ctx = os.environ.get("OLLAMA_NUM_CTX")
    if num_ctx:
        options["num_ctx"] = int(num_ctx)
    if options:
        payload["options"] = options
    if format_json:
        payload["format"] = "json"
    resp = _post(OLLAMA_URL + "/api/chat", payload, {"Content-Type": "application/json"})
    return resp.get("message", {}).get("content", "").strip()


def chat(system_prompt, user_prompt, model=None, format_json=True):
    """Call the LLM. Returns parsed JSON if format_json, else raw text."""
    if model is None:
        model = {"groq": GROQ_MODEL, "deepseek": DEEPSEEK_MODEL, "ollama": OLLAMA_MODEL}[LLM_PROVIDER]
    if LLM_PROVIDER == "ollama":
        content = _chat_ollama(system_prompt, user_prompt, model, format_json)
    elif LLM_PROVIDER == "deepseek":
        content = _chat_deepseek(system_prompt, user_prompt, model, format_json)
    else:
        content = _chat_groq(system_prompt, user_prompt, model, format_json)

    if format_json:
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        return json.loads(content)
    return content


def chat_retry(system_prompt, user_prompt, model=None, format_json=True, attempts=3):
    """Call the LLM with retry on malformed JSON or transport errors.
    Backs off ~30s on HTTP 429 (rate limit)."""
    import time

    last = None
    for i in range(attempts):
        try:
            return chat(system_prompt, user_prompt, model, format_json)
        except (json.JSONDecodeError, LLMError) as e:
            last = e
            msg = str(e)
            print(f"    [retry {i + 1}/{attempts}] {msg[:200]}", file=sys.stderr)
            if "429" in msg and i < attempts - 1:
                time.sleep(30)
    raise LLMError(f"LLM call failed after {attempts} attempts: {last}")


def embed(text, model=None):
    """Embed a single text via Ollama. NOTE: /api/embed uses the `input` field."""
    model = model or EMBED_MODEL
    resp = _post(OLLAMA_URL + "/api/embed", {"model": model, "input": text},
                 {"Content-Type": "application/json"}, timeout=600)
    embeddings = resp.get("embeddings") or []
    if not embeddings:
        raise LLMError("Embedding response was empty")
    return embeddings[0]


def embed_many(texts, model=None, batch=8):
    """Embed a list of texts in batches via Ollama."""
    model = model or EMBED_MODEL
    out = []
    for i in range(0, len(texts), batch):
        batch_texts = texts[i : i + batch]
        resp = _post(OLLAMA_URL + "/api/embed", {"model": model, "input": batch_texts},
                     {"Content-Type": "application/json"}, timeout=1200)
        embeddings = resp.get("embeddings") or []
        if len(embeddings) != len(batch_texts):
            raise LLMError(f"Embedding count mismatch: got {len(embeddings)} for {len(batch_texts)}")
        out.extend(embeddings)
    return out
