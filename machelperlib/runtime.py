"""Optional Ollama runtime controls. No model runtime is bundled or auto-installed."""
from __future__ import print_function
import json, os, subprocess, time

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

def find_ollama():
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(folder, "ollama")
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None

def status():
    try:
        response = urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
        try:
            data = json.loads(response.read())
        finally:
            response.close()
        return True, data.get("models", [])
    except Exception:
        return False, []

def start():
    running, models = status()
    if running:
        return "Ollama is already responding on 127.0.0.1:11434."
    executable = find_ollama()
    if not executable:
        raise RuntimeError("The Ollama command was not found in PATH. Install Ollama on this Mac first.")
    from machelperlib.common import state_dir
    log_path = os.path.join(state_dir("logs"), "ollama.log")
    log_handle = open(log_path, "a")
    null_input = open(os.devnull, "r")
    try:
        process = subprocess.Popen([executable, "serve"], stdin=null_input,
                                   stdout=log_handle, stderr=subprocess.STDOUT,
                                   close_fds=True)
    finally:
        null_input.close()
        log_handle.close()
    time.sleep(0.5)
    if process.poll() is not None:
        raise RuntimeError("Ollama exited during startup. Check " + log_path)
    return "Started Ollama (PID %s). Log: %s" % (process.pid, log_path)

def command(arguments):
    executable = find_ollama()
    if not executable:
        raise RuntimeError("The Ollama command was not found in PATH. Install Ollama first.")
    return subprocess.call([executable] + list(arguments))
