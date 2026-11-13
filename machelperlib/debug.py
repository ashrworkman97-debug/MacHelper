"""Read-only diagnostics for macOS application bundles."""
from __future__ import print_function
import os, subprocess

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
