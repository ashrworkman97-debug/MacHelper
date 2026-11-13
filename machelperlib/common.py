"""Shared helpers. Compatible with the Python shipped by OS X Yosemite."""
from __future__ import print_function
import json, os, tempfile, time

try:
    text_type = unicode
except NameError:
    text_type = str

def out(value=""):
    value = text_type(value)
    try:
        import sys
        if sys.version_info[0] < 3:
            sys.stdout.write(value.encode(getattr(sys.stdout, "encoding", None) or "utf-8", "replace") + "\n")
        else:
            sys.stdout.write(value + "\n")
    except Exception:
        print(value)

def state_dir(*parts):
    path = os.path.expanduser("~/.machelper")
    for part in parts:
        path = os.path.join(path, part)
    if not os.path.isdir(path):
        os.makedirs(path)
    return path

def config_path():
    return os.path.join(state_dir(), "config.json")

def load_config():
    defaults = {"ai": {"base_url": "", "model": ""}}
    path = config_path()
    if not os.path.isfile(path):
        return defaults
    try:
        handle = open(path, "r")
        try:
            data = json.load(handle)
        finally:
            handle.close()
        if not isinstance(data, dict):
            return defaults
        if not isinstance(data.get("ai"), dict):
            data["ai"] = defaults["ai"]
        for key, value in defaults["ai"].items():
            data["ai"].setdefault(key, value)
        return data
    except Exception:
        return defaults

def save_json(path, data):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    fd, temporary = tempfile.mkstemp(prefix=".machelper-", dir=parent or None)
    try:
        handle = os.fdopen(fd, "w")
        try:
            handle.write(json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
            handle.flush()
        finally:
            handle.close()
        if os.path.exists(path):
            os.unlink(path)
        os.rename(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except Exception:
            pass
        raise

def read_json(path):
    handle = open(path, "r")
    try:
        return json.load(handle)
    finally:
        handle.close()

def iso_time():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def human_size(number):
    value = float(number)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            return "%d %s" % (int(value), unit) if unit == "B" else "%.1f %s" % (value, unit)
        value /= 1024.0
    return str(number)

def absolute_path(value):
    return os.path.abspath(os.path.expanduser(os.path.expandvars(value)))

def path_is_within(path, root):
    path = os.path.realpath(path)
    root = os.path.realpath(root)
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)
