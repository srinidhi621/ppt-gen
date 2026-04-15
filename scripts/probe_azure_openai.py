"""Probe Azure OpenAI Responses API credentials and discover capabilities.

Usage:
    python scripts/probe_azure_openai.py

Uses the Responses API exclusively (/openai/responses?api-version=...).
Does NOT use the Chat Completions API. Tests the three approved models:
gpt-5.4, gpt-5.3-codex, gpt-5.2.

Writes AzureOpenAI_Capabilities.md with full findings.
"""

from __future__ import annotations

import base64
import json
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, parse, request

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
OUTPUT_MD = PROJECT_ROOT / "AzureOpenAI_Capabilities.md"

# Approved models (minimum floor: gpt-5.2)
APPROVED_MODELS = ["gpt-5.4", "gpt-5.3-codex", "gpt-5.2"]

# Management API versions for model listing
_MGMT_API_VERSIONS = [
    "2024-10-21",
    "2024-06-01",
    "2024-02-01",
    "2023-12-01-preview",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_env(path: Path) -> dict[str, str]:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def _http_get(url: str, api_key: str, timeout: int = 15) -> dict | None:
    """GET JSON from a URL. Returns parsed body or None on failure."""
    try:
        req = request.Request(
            url,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            method="GET",
        )
        with request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _responses_post(
    base_url: str, api_key: str, api_version: str, payload: dict, timeout: int = 30
) -> tuple[dict, dict]:
    """POST to the Responses API. Returns (body, headers)."""
    url = f"{base_url}/openai/responses?api-version={api_version}"
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        headers = dict(resp.headers)
        return body, headers


def _extract_output_text(body: dict) -> str:
    """Extract text from a Responses API response body."""
    for item in body.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("text"):
                    return c["text"]
    return ""


def _make_test_png(
    width: int = 10, height: int = 10, r: int = 255, g: int = 0, b: int = 0
) -> bytes:
    """Create a minimal valid PNG for vision testing."""
    def chunk(ctype: bytes, data: bytes) -> bytes:
        c = ctype + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    raw = b""
    for _ in range(height):
        raw += b"\x00" + bytes([r, g, b]) * width
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return header + ihdr + idat + iend


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------

def list_models(base_url: str, api_key: str) -> list[dict]:
    """List available models via management API."""
    for ver in _MGMT_API_VERSIONS:
        url = f"{base_url}/openai/models?api-version={ver}"
        body = _http_get(url, api_key)
        if body and "data" in body:
            return body["data"]
    return []


def test_responses_api(
    base_url: str, api_key: str, api_version: str, model: str
) -> dict:
    """Test a model via the Responses API. Returns result dict."""
    result = {
        "model": model,
        "success": False,
        "model_returned": None,
        "response": None,
        "usage": {},
        "rate_limits": {},
        "error": None,
    }
    try:
        payload = {
            "model": model,
            "input": "Reply with exactly: PROBE_OK",
            "max_output_tokens": 20,
        }
        body, headers = _responses_post(base_url, api_key, api_version, payload)
        result["success"] = True
        result["model_returned"] = body.get("model")
        result["response"] = _extract_output_text(body)
        result["usage"] = body.get("usage", {})
        result["rate_limits"] = {
            k: v for k, v in headers.items()
            if "ratelimit" in k.lower() or "remaining" in k.lower()
        }
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        result["error"] = f"HTTP {exc.code}: {detail}"
    except Exception as exc:
        result["error"] = str(exc)
    return result


def test_json_mode(
    base_url: str, api_key: str, api_version: str, model: str
) -> dict:
    """Test JSON mode via the Responses API."""
    try:
        payload = {
            "model": model,
            "input": 'Return valid JSON: {"status": "ok", "count": 42}',
            "max_output_tokens": 50,
            "text": {"format": {"type": "json_object"}},
        }
        body, _ = _responses_post(base_url, api_key, api_version, payload)
        text = _extract_output_text(body)
        return {"supported": True, "response": text, "error": None}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return {"supported": False, "response": None, "error": f"HTTP {exc.code}: {detail}"}
    except Exception as exc:
        return {"supported": False, "response": None, "error": str(exc)}


def test_vision(
    base_url: str, api_key: str, api_version: str, model: str
) -> dict:
    """Test vision (image input) via the Responses API."""
    png_b64 = base64.b64encode(_make_test_png()).decode("ascii")
    try:
        payload = {
            "model": model,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "What color is this image? One word only."},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{png_b64}"},
                    ],
                },
            ],
            "max_output_tokens": 20,
        }
        body, _ = _responses_post(base_url, api_key, api_version, payload)
        text = _extract_output_text(body)
        return {"supported": True, "response": text, "error": None}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return {"supported": False, "response": None, "error": f"HTTP {exc.code}: {detail}"}
    except Exception as exc:
        return {"supported": False, "response": None, "error": str(exc)}


def test_code_gen(
    base_url: str, api_key: str, api_version: str, model: str
) -> dict:
    """Test code generation via the Responses API."""
    try:
        payload = {
            "model": model,
            "instructions": "You are a Python code generator. Output only valid Python code, no markdown fences.",
            "input": "Write a function fibonacci(n) that returns the first n Fibonacci numbers as a list.",
            "max_output_tokens": 200,
        }
        body, _ = _responses_post(base_url, api_key, api_version, payload)
        text = _extract_output_text(body)
        usage = body.get("usage", {})
        return {
            "supported": True,
            "response_preview": text[:150],
            "usage": usage,
            "error": None,
        }
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return {"supported": False, "response_preview": None, "usage": {}, "error": f"HTTP {exc.code}: {detail}"}
    except Exception as exc:
        return {"supported": False, "response_preview": None, "usage": {}, "error": str(exc)}


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def write_report(
    output_path: Path,
    base_url: str,
    api_version: str,
    reachable: bool,
    models: list[dict],
    probe_results: list[dict],
    json_results: dict[str, dict],
    vision_results: dict[str, dict],
    code_results: dict[str, dict],
):
    lines = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append("# Azure OpenAI Capabilities Report")
    lines.append("")
    lines.append(f"**Generated**: {now}")
    lines.append(f"**Endpoint**: `{base_url}`")
    lines.append(f"**API**: Responses API only (`/openai/responses?api-version={api_version}`)")
    lines.append(f"**Approved models**: {', '.join(f'`{m}`' for m in APPROVED_MODELS)}")
    lines.append("")

    # Connectivity
    lines.append("## Connectivity")
    lines.append("")
    lines.append(f"- Endpoint reachable: {'Yes' if reachable else 'No'}")
    lines.append("")

    # Model probe results
    lines.append("## Model Probe Results")
    lines.append("")

    working = [r for r in probe_results if r["success"]]
    failed = [r for r in probe_results if not r["success"]]

    if working:
        lines.append("| Model | Status | JSON Mode | Vision | Code Gen | Requests/min | Tokens/min |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in probe_results:
            model = r["model"]
            if r["success"]:
                jm = json_results.get(model, {})
                vis = vision_results.get(model, {})
                cg = code_results.get(model, {})
                rl = r.get("rate_limits", {})
                req_lim = rl.get("x-ratelimit-limit-requests", "?")
                tok_lim = rl.get("x-ratelimit-limit-tokens", "?")
                lines.append(
                    f"| `{model}` | Working | "
                    f"{'Yes' if jm.get('supported') else 'No'} | "
                    f"{'Yes' if vis.get('supported') else 'No'} | "
                    f"{'Yes' if cg.get('supported') else 'No'} | "
                    f"{req_lim} | {tok_lim} |"
                )
            else:
                lines.append(f"| `{model}` | Failed | - | - | - | - | - |")
        lines.append("")
    else:
        lines.append("No models responded successfully.")
        lines.append("")

    # Detailed results per model
    for r in probe_results:
        model = r["model"]
        if r["success"]:
            lines.append(f"### `{model}`")
            lines.append("")
            lines.append(f"- **Model returned**: `{r['model_returned']}`")
            lines.append(f"- **Test response**: `{r['response']}`")
            u = r["usage"]
            lines.append(f"- **Usage**: {u.get('input_tokens', '?')} input, {u.get('output_tokens', '?')} output, {u.get('total_tokens', '?')} total")

            # Rate limits
            rl = r.get("rate_limits", {})
            if rl:
                lines.append("- **Rate limits**:")
                for k, v in sorted(rl.items()):
                    lines.append(f"  - `{k}`: {v}")

            # JSON mode
            jm = json_results.get(model, {})
            lines.append(f"- **JSON mode**: {'Supported' if jm.get('supported') else 'Not supported'}")
            if jm.get("response"):
                lines.append(f"  - Response: `{jm['response'][:80]}`")

            # Vision
            vis = vision_results.get(model, {})
            lines.append(f"- **Vision**: {'Supported' if vis.get('supported') else 'Not supported'}")
            if vis.get("response"):
                lines.append(f"  - Response: `{vis['response']}`")

            # Code generation
            cg = code_results.get(model, {})
            lines.append(f"- **Code generation**: {'Supported' if cg.get('supported') else 'Not supported'}")
            if cg.get("usage"):
                cu = cg["usage"]
                lines.append(f"  - Tokens: {cu.get('input_tokens', '?')} in, {cu.get('output_tokens', '?')} out")
            lines.append("")
        else:
            lines.append(f"### `{model}` — Failed")
            lines.append("")
            lines.append(f"- **Error**: {r['error']}")
            lines.append("")

    # V3 pipeline mapping
    lines.append("## V3 Pipeline Configuration")
    lines.append("")
    if working:
        working_names = {r["model"] for r in working}
        json_ok = {m for m, r in json_results.items() if r.get("supported")}
        vision_ok = {m for m, r in vision_results.items() if r.get("supported")}
        code_ok = {m for m, r in code_results.items() if r.get("supported")}

        planner_model = "gpt-5.4" if "gpt-5.4" in json_ok else next(iter(json_ok), "?")
        builder_model = "gpt-5.3-codex" if "gpt-5.3-codex" in code_ok else next(iter(code_ok), "?")
        reviewer_model = "gpt-5.4" if "gpt-5.4" in (json_ok & vision_ok) else next(iter(json_ok & vision_ok), "?")

        lines.append("| Role | Requirements | Model | Status |")
        lines.append("|---|---|---|---|")
        lines.append(f"| **Planner** | JSON mode | `{planner_model}` | {'Ready' if planner_model in json_ok else 'Needs JSON mode'} |")
        lines.append(f"| **Builder** | Code generation | `{builder_model}` | {'Ready' if builder_model in code_ok else 'Needs code gen'} |")
        lines.append(f"| **Reviewer** | Vision + JSON mode | `{reviewer_model}` | {'Ready' if reviewer_model in (json_ok & vision_ok) else 'Incomplete'} |")
        lines.append("")

        lines.append("### Recommended .env")
        lines.append("")
        lines.append("```")
        lines.append(f"AZURE_OPENAI_ENDPOINT={base_url}")
        lines.append(f"AZURE_OPENAI_API_VERSION={api_version}")
        lines.append(f"V3_PLANNER_MODEL={planner_model}")
        lines.append(f"V3_BUILDER_MODEL={builder_model}")
        lines.append(f"V3_REVIEWER_MODEL={reviewer_model}")
        lines.append("```")
        lines.append("")

        # Rate limits
        lines.append("### Rate Limits")
        lines.append("")
        lines.append("| Model | Requests/min | Tokens/min |")
        lines.append("|---|---|---|")
        for r in working:
            rl = r.get("rate_limits", {})
            req_lim = rl.get("x-ratelimit-limit-requests", "?")
            tok_lim = rl.get("x-ratelimit-limit-tokens", "?")
            renewal = rl.get("x-ratelimit-renewalperiod-requests", "60")
            lines.append(f"| `{r['model']}` | {req_lim} / {renewal}s | {tok_lim} / {renewal}s |")
        lines.append("")
    else:
        lines.append("No working models found. Check API key and endpoint configuration.")
        lines.append("")

    # API constraint note
    lines.append("## API Constraints")
    lines.append("")
    lines.append("- **Responses API only**. Chat Completions API is not used. (See AGENTS.md Rule 9.)")
    lines.append("- **Minimum model floor**: gpt-5.2. No older models permitted in V3 code.")
    lines.append(f"- **API endpoint**: `POST {base_url}/openai/responses?api-version={api_version}`")
    lines.append("- **Model selection**: via `model` field in request body (not URL path)")
    lines.append("")

    # Available models (filtered to gpt-5.x)
    gpt5_models = [m for m in models if m.get("id", "").startswith("gpt-5")]
    if gpt5_models:
        lines.append("## Available GPT-5.x Models on This Endpoint")
        lines.append("")
        lines.append("| Model ID |")
        lines.append("|---|")
        for m in gpt5_models:
            lines.append(f"| `{m['id']}` |")
        lines.append("")

    output_path.write_text("\n".join(lines))
    return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("--- Azure OpenAI Responses API Probe ---\n")

    # Step 1: Load .env
    if not ENV_PATH.exists():
        print(f"FAIL: .env not found at {ENV_PATH}")
        sys.exit(1)

    env = load_env(ENV_PATH)
    print("[1/5] .env loaded")

    raw_endpoint = env.get("AZURE_OPENAI_ENDPOINT", "")
    api_key = env.get("AZURE_OPENAI_API_KEY", "")
    api_version = env.get("AZURE_OPENAI_API_VERSION", "") or "2025-04-01-preview"

    # Strip any path suffix from endpoint
    parsed = parse.urlparse(raw_endpoint)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"      Endpoint:    {base_url}")
    print(f"      API version: {api_version}")
    print(f"      API key:     {'***' + api_key[-6:] if len(api_key) > 6 else '(not set)'}")
    print(f"      Models:      {', '.join(APPROVED_MODELS)}")
    print()

    if not raw_endpoint or not api_key:
        print("FAIL: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are required.")
        sys.exit(1)

    # Step 2: Reachability
    print("[2/5] Checking reachability...")
    reachable = False
    try:
        req = request.Request(base_url, headers={"api-key": api_key}, method="GET")
        with request.urlopen(req, timeout=10) as resp:
            reachable = resp.status > 0
            print(f"      HTTP {resp.status} (reachable)")
    except error.HTTPError as exc:
        reachable = exc.code > 0
        print(f"      HTTP {exc.code} (reachable)")
    except Exception as exc:
        print(f"      FAIL: {exc}")
        sys.exit(1)
    print()

    # Step 3: List models (for reference)
    print("[3/5] Listing available models...")
    models = list_models(base_url, api_key)
    gpt5_models = [m for m in models if m.get("id", "").startswith("gpt-5")]
    if gpt5_models:
        for m in gpt5_models:
            print(f"      - {m['id']}")
    else:
        print("      No gpt-5.x models found in model listing")
    if models:
        print(f"      ({len(models)} total models available)")
    print()

    # Step 4: Test approved models via Responses API
    print(f"[4/5] Testing {len(APPROVED_MODELS)} approved models via Responses API...")
    probe_results = []
    for model in APPROVED_MODELS:
        print(f"      {model}...", end=" ", flush=True)
        r = test_responses_api(base_url, api_key, api_version, model)
        probe_results.append(r)
        if r["success"]:
            print(f"OK (reply: {r['response'][:30]})")
        else:
            print("FAILED")
    print()

    # Step 5: Test capabilities on working models
    print("[5/5] Testing capabilities (JSON mode, vision, code gen)...")
    json_results = {}
    vision_results = {}
    code_results = {}
    for r in probe_results:
        if not r["success"]:
            continue
        model = r["model"]
        print(f"      {model}:", end="", flush=True)

        print(" JSON...", end="", flush=True)
        jm = test_json_mode(base_url, api_key, api_version, model)
        json_results[model] = jm
        print("Yes" if jm["supported"] else "No", end="", flush=True)

        print("  Vision...", end="", flush=True)
        vis = test_vision(base_url, api_key, api_version, model)
        vision_results[model] = vis
        print("Yes" if vis["supported"] else "No", end="", flush=True)

        print("  Code...", end="", flush=True)
        cg = test_code_gen(base_url, api_key, api_version, model)
        code_results[model] = cg
        print("Yes" if cg["supported"] else "No")
    print()

    # Write report
    report_path = write_report(
        OUTPUT_MD, base_url, api_version,
        reachable, models, probe_results,
        json_results, vision_results, code_results,
    )

    # Summary
    working = [r for r in probe_results if r["success"]]
    failed = [r for r in probe_results if not r["success"]]
    print("--- Summary ---")
    print(f"  Models tested: {len(probe_results)}")
    print(f"  Working:       {len(working)}")
    print(f"  Failed:        {len(failed)}")
    if working:
        for r in working:
            model = r["model"]
            caps = []
            if json_results.get(model, {}).get("supported"):
                caps.append("JSON")
            if vision_results.get(model, {}).get("supported"):
                caps.append("Vision")
            if code_results.get(model, {}).get("supported"):
                caps.append("Code")
            caps_str = ", ".join(caps) if caps else "text only"
            print(f"    {model}: [{caps_str}]")
    if failed:
        for r in failed:
            print(f"    {r['model']}: {r['error'][:80]}")
    print(f"\nReport written to {report_path}")

    if not working:
        sys.exit(1)


if __name__ == "__main__":
    main()
