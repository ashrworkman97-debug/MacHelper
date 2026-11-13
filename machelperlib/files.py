"""Read-only scanning and approval-based file organization."""
from __future__ import print_function
import errno, os, shutil, stat, time, uuid
from machelperlib.common import absolute_path, iso_time, path_is_within, read_json, save_json, state_dir, text_type

CATEGORIES = {
    "Documents": set([".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".pages", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".key"]),
    "Images": set([".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".heic", ".psd", ".svg"]),
    "Audio": set([".mp3", ".m4a", ".aac", ".wav", ".aiff", ".flac", ".ogg"]),
    "Video": set([".mp4", ".mov", ".m4v", ".avi", ".mkv", ".wmv", ".mpg", ".mpeg"]),
    "Archives": set([".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz"]),
    "Installers": set([".dmg", ".pkg", ".mpkg"]),
    "Disk Images": set([".iso", ".img"]),
    "Code": set([".py", ".js", ".html", ".css", ".c", ".h", ".cpp", ".java", ".rb", ".sh", ".pl", ".php", ".json", ".xml", ".yml", ".yaml"])
}

def category_for(filename):
    extension = os.path.splitext(filename)[1].lower()
    for category, extensions in CATEGORIES.items():
        if extension in extensions:
            return category
    return None

def scan_folder(folder):
    root = absolute_path(folder)
    if not os.path.isdir(root):
        raise ValueError("Folder does not exist: %s" % root)
    entries = []
    for name in sorted(os.listdir(root), key=lambda value: value.lower()):
        path = os.path.join(root, name)
        try:
            info = os.lstat(path)
        except OSError:
            continue
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            continue
        entries.append({"name": name, "path": path, "size": info.st_size, "extension": os.path.splitext(name)[1].lower()})
    return {"root": root, "files": entries, "count": len(entries), "total_bytes": sum(item["size"] for item in entries)}

def _plan_id():
    return time.strftime("%Y%m%d-%H%M%S", time.localtime()) + "-" + uuid.uuid4().hex[:6]

def save_plan(root, operations, source):
    plan = {"version": 1, "id": _plan_id(), "created": iso_time(), "root": absolute_path(root),
            "source": source, "status": "pending", "operations": operations}
    save_json(os.path.join(state_dir("plans"), plan["id"] + ".json"), plan)
    return plan

def make_rule_plan(folder):
    scan = scan_folder(folder)
    operations = []
    for item in scan["files"]:
        category = category_for(item["name"])
        if category:
            destination = os.path.join(scan["root"], category, item["name"])
            if os.path.abspath(destination) != os.path.abspath(item["path"]):
                operations.append({"action": "move", "source": item["path"], "destination": destination,
                                   "reason": "File extension matches the %s category." % category})
    return save_plan(scan["root"], operations, "rules")

def validate_ai_operations(root, operations):
    root = absolute_path(root)
    if not isinstance(operations, list) or len(operations) > 200:
        raise ValueError("AI response must contain an operations list of at most 200 items.")
    validated, seen_sources = [], set()
    for item in operations:
        if not isinstance(item, dict):
            raise ValueError("An AI operation was not an object.")
        action = item.get("action")
        source = absolute_path(item.get("source", ""))
        if action not in ("move", "trash"):
            raise ValueError("Unsupported AI action: %s" % action)
        if os.path.dirname(source) != root or not path_is_within(source, root):
            raise ValueError("AI tried to operate outside the selected folder: %s" % source)
        if not os.path.isfile(source) or os.path.islink(source):
            raise ValueError("AI source is not a regular file: %s" % source)
        if source in seen_sources:
            raise ValueError("AI listed the same source more than once: %s" % source)
        seen_sources.add(source)
        operation = {"action": action, "source": source,
                     "reason": text_type(item.get("reason", "Suggested by AI."))[:500]}
        if action == "move":
            destination = absolute_path(item.get("destination", ""))
            parent = os.path.dirname(destination)
            if os.path.dirname(parent) != root or not path_is_within(destination, root):
                raise ValueError("AI destination must be one folder below the selected folder.")
            if os.path.basename(destination) in ("", ".", ".."):
                raise ValueError("AI supplied an invalid destination filename.")
            if os.path.basename(destination) != os.path.basename(source):
                raise ValueError("AI cannot rename files in this version.")
            if os.path.lexists(destination):
                raise ValueError("AI destination already exists: %s" % destination)
            operation["destination"] = destination
        validated.append(operation)
    return validated

def load_plan(plan_id):
    if os.path.sep in plan_id or plan_id in ("", ".", ".."):
        raise ValueError("Use the plan ID shown by MacHelper.")
    path = os.path.join(state_dir("plans"), plan_id + ".json")
    if not os.path.isfile(path):
        raise ValueError("Plan not found: %s" % plan_id)
    return path, read_json(path)

def review_plan(plan_id):
    unused_path, plan = load_plan(plan_id)
    return plan

def _unique_trash_path(name):
    trash = os.path.expanduser("~/.Trash")
    if not os.path.isdir(trash):
        os.makedirs(trash)
    if os.path.islink(trash):
        raise ValueError("The macOS Trash path is a symbolic link; refusing to use it.")
    candidate = os.path.join(trash, name)
    if not os.path.lexists(candidate):
        return candidate
    base, extension = os.path.splitext(name)
    counter = 1
    while True:
        candidate = os.path.join(trash, "%s (MacHelper %d)%s" % (base, counter, extension))
        if not os.path.lexists(candidate):
            return candidate
        counter += 1

def _move_without_overwrite(source, destination):
    if os.path.lexists(destination):
        raise ValueError("Destination already exists; refusing to overwrite: %s" % destination)
    try:
        os.rename(source, destination)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        shutil.move(source, destination)

def apply_plan(plan_id):
    plan_path, plan = load_plan(plan_id)
    if plan.get("status") != "pending":
        raise ValueError("This plan is not pending (status: %s)." % plan.get("status"))
    root = absolute_path(plan["root"])
    if not os.path.isdir(root):
        raise ValueError("The selected folder no longer exists.")
    journal = {"version": 1, "id": time.strftime("%Y%m%d-%H%M%S", time.localtime()) + "-" + uuid.uuid4().hex[:6],
               "created": iso_time(), "plan_id": plan_id, "entries": [], "undone": False}
    journal_path = os.path.join(state_dir("journals"), journal["id"] + ".json")
    try:
        for item in plan.get("operations", []):
            action, source = item.get("action"), absolute_path(item.get("source", ""))
            if os.path.dirname(source) != root or not path_is_within(source, root):
                raise ValueError("Plan source is outside its selected folder: %s" % source)
            if not os.path.isfile(source) or os.path.islink(source):
                raise ValueError("Source is missing or is not a regular file: %s" % source)
            if action == "move":
                destination = absolute_path(item.get("destination", ""))
                parent = os.path.dirname(destination)
                if os.path.dirname(parent) != root or not path_is_within(destination, root):
                    raise ValueError("Move destination must be one folder below the selected folder.")
                if os.path.basename(destination) != os.path.basename(source):
                    raise ValueError("Renaming is not supported by this release.")
                if os.path.lexists(parent) and (os.path.islink(parent) or not os.path.isdir(parent)):
                    raise ValueError("Destination folder is unsafe: %s" % parent)
                if not os.path.isdir(parent):
                    os.mkdir(parent)
            elif action == "trash":
                destination = _unique_trash_path(os.path.basename(source))
            else:
                raise ValueError("Unsupported action in plan: %s" % action)
            _move_without_overwrite(source, destination)
            journal["entries"].append({"action": action, "source": source,
                                       "destination": destination, "restored": False})
            save_json(journal_path, journal)
    except Exception as error:
        if journal["entries"]:
            journal["partial"] = True
            plan["status"], plan["journal_id"] = "partial", journal["id"]
            save_json(journal_path, journal)
            save_json(plan_path, plan)
            raise RuntimeError("Stopped after %d operation(s): %s. Partial work can be undone with: machelper files undo %s" %
                               (len(journal["entries"]), error, journal["id"]))
        raise
    plan["status"], plan["journal_id"] = "applied", journal["id"]
    save_json(plan_path, plan)
    return journal

def undo_journal(journal_id):
    if os.path.sep in journal_id or journal_id in ("", ".", ".."):
        raise ValueError("Use the journal ID shown by MacHelper.")
    path = os.path.join(state_dir("journals"), journal_id + ".json")
    if not os.path.isfile(path):
        raise ValueError("Journal not found: %s" % journal_id)
    journal = read_json(path)
    if journal.get("undone"):
        raise ValueError("This journal has already been undone.")
    restored = 0
    for entry in reversed(journal.get("entries", [])):
        if entry.get("restored"):
            continue
        source, destination = entry["source"], entry["destination"]
        if not os.path.lexists(destination):
            raise ValueError("Cannot restore; moved file is missing: %s" % destination)
        if os.path.lexists(source):
            raise ValueError("Cannot restore without overwriting an existing file: %s" % source)
        if not os.path.isdir(os.path.dirname(source)):
            raise ValueError("Original folder no longer exists: %s" % os.path.dirname(source))
        _move_without_overwrite(destination, source)
        entry["restored"] = True
        save_json(path, journal)
        restored += 1
    journal["undone"], journal["undone_at"] = True, iso_time()
    save_json(path, journal)
    return restored

def operation_summary(plan):
    counts = {"move": 0, "trash": 0}
    for item in plan.get("operations", []):
        counts[item.get("action", "unknown")] = counts.get(item.get("action", "unknown"), 0) + 1
    return counts
