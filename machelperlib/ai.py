"""OpenAI-compatible AI connector using only the Python standard library."""
from __future__ import print_function
import json, os, sys
from machelperlib.common import load_config, save_json, config_path
from machelperlib.files import scan_folder, validate_ai_operations, save_plan
try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import Request, urlopen, HTTPError, URLError

def configure(url, model):
    url = (url or "").strip().rstrip("/")
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("Provide an API base URL starting with http:// or https://.")
    if not model:
        raise ValueError("Provide a model name.")
    config = load_config()
    config.setdefault("ai", {})
    config["ai"]["base_url"], config["ai"]["model"] = url, model
    save_json(config_path(), config)

def _request(path, method="GET", payload=None):
    config = load_config().get("ai", {})
    base_url = config.get("base_url", "").rstrip("/")
    if not base_url:
        raise ValueError("AI is not configured. Run: machelper ai configure --url URL --model MODEL")
    headers = {"Accept": "application/json", "User-Agent": "MacHelper/0.1.0"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    api_key = os.environ.get("MACHELPER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    request = Request(base_url + path, data=data, headers=headers)
    request.get_method = lambda: method
    try:
        response = urlopen(request, timeout=90)
        try:
            raw = response.read()
        finally:
            response.close()
    except HTTPError as error:
        raise RuntimeError("AI server returned HTTP %s: %s" % (error.code, error.read()[:500]))
    except URLError as error:
        raise RuntimeError("Could not reach AI server: %s" % error)
    try:
        if sys.version_info[0] >= 3:
            raw = raw.decode("utf-8")
        return json.loads(raw)
    except Exception:
        raise RuntimeError("AI server returned invalid JSON.")

def model_list():
    result = _request("/models")
    return result.get("data", result.get("models", []))

def chat(question, system_prompt=None):
    config = load_config().get("ai", {})
    model = config.get("model", "")
    if not model:
        raise ValueError("No model configured. Run: machelper ai configure --url URL --model MODEL")
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": question})
    result = _request("/chat/completions", "POST", {"model": model, "messages": messages, "temperature": 0.2})
    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError("AI server response did not contain any choices.")
    return choices[0].get("message", {}).get("content", "")

def _extract_json(text):
    value = text.strip()
    fence = chr(96) * 3
    if value.startswith(fence):
        lines = value.splitlines()
        if lines and lines[0].startswith(fence):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith(fence):
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    start, end = value.find("{"), value.rfind("}")
    if start < 0 or end < start:
        raise ValueError("AI did not return a JSON object.")
    return json.loads(value[start:end + 1])

def organize(folder):
    scan = scan_folder(folder)
    if len(scan["files"]) > 200:
        raise ValueError("AI organization is limited to 200 top-level files at a time.")
    metadata = [{"name": item["name"], "path": item["path"], "extension": item["extension"],
                 "size_bytes": item["size"]} for item in scan["files"]]
    prompt = (
        "Create a cautious organization plan. Return ONLY a JSON object with an operations array. "
        "Each operation has action, source, destination for move, and reason. Allowed actions: move or trash. "
        "Moves must put the original filename into one descriptive subfolder directly inside the selected root. "
        "Do not rename files. Never suggest Trash unless the filename clearly indicates a temporary or duplicate "
        "file; when uncertain, omit it. Do not invent paths. The user reviews every operation before it is applied. "
        "File contents were NOT provided; use filenames and metadata only. Selected root: " + scan["root"] +
        " Files: " + json.dumps(metadata, ensure_ascii=True))
    answer = chat(prompt, "You are a cautious desktop file organization assistant. Never claim you changed files.")
    data = _extract_json(answer)
    operations = validate_ai_operations(scan["root"], data.get("operations", []))
    return save_plan(scan["root"], operations, "ai")
