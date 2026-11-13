"""Read-only diagnostics for macOS application bundles and crash reports."""
from __future__ import print_function
import os, subprocess, sys, time
from machelperlib.common import path_is_within

def _capture(arguments):
    try:
        process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = process.communicate()[0]
        if not isinstance(output, str):
            output = output.decode("utf-8", "replace")
        return output.strip() or "(no output)"
    except OSError as error:
        return "Unavailable: %s" % error

def _first_executable(folder):
    if not os.path.isdir(folder):
        return None
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None

def inspect_app(path):
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        raise ValueError("Path does not exist: %s" % path)
    if not path.endswith(".app") or not os.path.isdir(path):
        raise ValueError("Expected a macOS .app bundle directory.")
    contents = os.path.join(path, "Contents")
    info = os.path.join(contents, "Info.plist")
    executable = _first_executable(os.path.join(contents, "MacOS"))
    result = ["APPLICATION: " + path, "", "[Bundle metadata]"]
    if os.path.isfile(info):
        result.append(_capture(["/usr/bin/plutil", "-lint", info]))
        for key in ("CFBundleIdentifier", "CFBundleName", "CFBundleShortVersionString",
                    "CFBundleVersion", "LSMinimumSystemVersion"):
            value = _capture(["/usr/libexec/PlistBuddy", "-c", "Print :" + key, info])
            if value not in ("(no output)", "") and not value.startswith("Unavailable:"):
                result.append("%s: %s" % (key, value.splitlines()[0]))
    else:
        result.append("Info.plist is missing.")
    result.extend(["", "[Main executable]"])
    if executable:
        result.extend([executable, _capture(["/usr/bin/file", executable]), "", "[Linked libraries]",
                       _capture(["/usr/bin/otool", "-L", executable])])
    else:
        result.append("No executable file found in Contents/MacOS.")
    result.extend(["", "[Code signature]", _capture(["/usr/bin/codesign", "-dv", "--verbose=2", path]),
                   "", "[Gatekeeper assessment]", _capture(["/usr/sbin/spctl", "-a", "-vv", path]),
                   "", "MacHelper did not modify the application."])
    return "\n".join(result)

def crash_report_dirs():
    home = os.path.expanduser("~")
    return [os.path.join(home, "Library", "Logs", "DiagnosticReports"),
            os.path.join(home, "Library", "Logs", "CrashReporter"),
            "/Library/Logs/DiagnosticReports"]

def list_crash_reports(app_name=None, limit=10):
    matches = []
    needle = (app_name or "").lower()
    for folder in crash_report_dirs():
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if not name.lower().endswith((".crash", ".ips")):
                continue
            if needle and needle not in name.lower():
                continue
            path = os.path.join(folder, name)
            try:
                info = os.lstat(path)
            except OSError:
                continue
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            matches.append({"path": path, "modified": info.st_mtime, "size": info.st_size})
    matches.sort(key=lambda item: item["modified"], reverse=True)
    return matches[:max(1, min(int(limit), 100))]

def read_crash_report(path, max_lines=200):
    path = os.path.abspath(os.path.expanduser(path))
    allowed = False
    for folder in crash_report_dirs():
        if path_is_within(path, folder):
            allowed = True
            break
    if not allowed or os.path.islink(path) or not os.path.isfile(path):
        raise ValueError("Only regular crash reports in macOS diagnostic log folders can be read.")
    max_lines = max(1, min(int(max_lines), 1000))
    output = []
    handle = open(path, "rb")
    try:
        for unused_index in range(max_lines):
            line = handle.readline()
            if not line:
                break
            try:
                line = line.decode("utf-8", "replace")
            except AttributeError:
                pass
            output.append(line.rstrip("\r\n"))
    finally:
        handle.close()
    if len(output) == max_lines:
        output.append("[Output truncated after %d lines.]" % max_lines)
    if sys.version_info[0] < 3:
        return u"\n".join(output)
    return "\n".join(output)
