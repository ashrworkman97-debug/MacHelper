"""Command-line interface for MacHelper."""
from __future__ import print_function
import os, platform, sys, time
from machelperlib import __version__
from machelperlib.common import out, human_size, load_config
from machelperlib import ai, debug, files, runtime

def _confirm(prompt):
    try:
        answer = raw_input(prompt)
    except NameError:
        answer = input(prompt)
    return answer.strip().lower() in ("y", "yes")

def _show_plan(plan):
    counts = files.operation_summary(plan)
    out("Plan: " + plan["id"])
    out("Folder: " + plan["root"])
    out("Source: " + plan["source"])
    out("Operations: %d move, %d to Trash" % (counts.get("move", 0), counts.get("trash", 0)))
    if not plan.get("operations"):
        out("No changes were proposed.")
        return
    out("")
    for index, item in enumerate(plan["operations"]):
        out("%d. %s" % (index + 1, item["action"].upper()))
        out("   From: %s" % item["source"])
        if item["action"] == "move":
            out("   To:   %s" % item["destination"])
        out("   Why:  %s" % item.get("reason", "No reason supplied"))
    out("")
    out("Nothing has been changed. Review this plan before applying it.")

def _apply_with_prompt(plan, assume_yes=False):
    _show_plan(plan)
    if not plan.get("operations"):
        return
    if not assume_yes:
        out("")
        if not _confirm("Apply these operations? [y/N] "):
            out("Cancelled. No files were changed.")
            return
    journal = files.apply_plan(plan["id"])
    out("Applied. Undo journal: " + journal["id"])
    out("To undo: machelper files undo " + journal["id"])

def command_doctor(args):
    out("MacHelper %s" % __version__)
    out("System: %s %s" % (platform.system(), platform.mac_ver()[0] or platform.release()))
    out("Python: %s" % sys.version.split()[0])
    out("Executable: %s" % sys.executable)
    for program in ("/usr/bin/file", "/usr/bin/otool", "/usr/bin/plutil",
                    "/usr/bin/codesign", "/usr/sbin/spctl"):
        out("%s: %s" % (program, "available" if os.path.exists(program) else "not found"))
    try:
        stats = os.statvfs(os.path.expanduser("~"))
        out("Free space on home volume: %s" % human_size(stats.f_bavail * stats.f_frsize))
    except Exception:
        out("Free space: unavailable")
    cfg = load_config().get("ai", {})
    out("AI endpoint: %s" % (cfg.get("base_url") or "not configured"))
    out("AI model: %s" % (cfg.get("model") or "not configured"))

def command_scan(args):
    result = files.scan_folder(args.folder)
    out("Folder: %s" % result["root"])
    out("Files: %d" % result["count"])
    out("Total size: %s" % human_size(result["total_bytes"]))
    out("")
    for item in result["files"]:
        out("%8s  %s" % (human_size(item["size"]), item["name"]))

def command_plan(args):
    plan = files.make_rule_plan(args.folder)
    _show_plan(plan)
    out("Review with: machelper files review " + plan["id"])

def command_review(args):
    _show_plan(files.review_plan(args.plan_id))

def command_apply(args):
    _apply_with_prompt(files.review_plan(args.plan_id), args.yes)

def command_organize(args):
    _apply_with_prompt(files.make_rule_plan(args.folder), args.yes)

def command_undo(args):
    out("Restored %d file(s)." % files.undo_journal(args.journal_id))

def command_ai_configure(args):
    ai.configure(args.url, args.model)
    out("Saved AI endpoint and model. API keys are read from MACHELPER_API_KEY or OPENAI_API_KEY and are never saved here.")

def command_ai_ask(args):
    out(ai.chat(args.question))

def command_ai_models(args):
    models = ai.model_list()
    if not models:
        out("The configured server did not report any models.")
        return
    for model in models:
        if isinstance(model, dict):
            out(model.get("id") or model.get("name") or str(model))
        else:
            out(str(model))

def command_ai_organize(args):
    _apply_with_prompt(ai.organize(args.folder), args.yes)

def command_runtime_status(args):
    running, models = runtime.status()
    if not running:
        out("No Ollama server is responding at http://127.0.0.1:11434.")
        return
    out("Ollama is running on this Mac.")
    if models:
        out("Installed models:")
        for model in models:
            out("  " + (model.get("name") or model.get("model") or str(model)))
    else:
        out("No models are installed yet.")

def command_runtime_start(args):
    out(runtime.start())

def command_runtime_list(args):
    code = runtime.command(["list"])
    if code:
        raise RuntimeError("ollama list exited with status %s." % code)

def command_runtime_pull(args):
    code = runtime.command(["pull", args.model])
    if code:
        raise RuntimeError("ollama pull exited with status %s." % code)

def command_runtime_run(args):
    code = runtime.command(["run", args.model])
    if code:
        raise RuntimeError("ollama run exited with status %s." % code)

def command_debug_inspect(args):
    out(debug.inspect_app(args.application))

def command_debug_crashes(args):
    reports = debug.list_crash_reports(args.app, args.limit)
    if not reports:
        out("No matching crash reports were found.")
        return
    for report in reports:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(report["modified"]))
        out("%s  %8s  %s" % (stamp, human_size(report["size"]), report["path"]))

def command_debug_crash(args):
    out(debug.read_crash_report(args.report, args.lines))

def build_parser():
    parser = argparse.ArgumentParser(prog="machelper",
        description="A lightweight, terminal-first toolkit for macOS.")
    parser.add_argument("--version", action="version", version="MacHelper " + __version__)
    commands = parser.add_subparsers(dest="command")
    doctor = commands.add_parser("doctor", help="Check the MacHelper runtime and system tools.")
    doctor.set_defaults(function=command_doctor)

    file_parser = commands.add_parser("files", help="Scan, organize, and restore files.")
    file_commands = file_parser.add_subparsers(dest="files_command")
    scan = file_commands.add_parser("scan", help="List regular files in a folder (read-only).")
    scan.add_argument("folder")
    scan.set_defaults(function=command_scan)
    plan = file_commands.add_parser("plan", help="Create a rule-based organization preview.")
    plan.add_argument("folder")
    plan.set_defaults(function=command_plan)
    review = file_commands.add_parser("review", help="Display a saved plan.")
    review.add_argument("plan_id")
    review.set_defaults(function=command_review)
    apply = file_commands.add_parser("apply", help="Apply a reviewed plan after confirmation.")
    apply.add_argument("plan_id")
    apply.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")
    apply.set_defaults(function=command_apply)
    organize = file_commands.add_parser("organize", help="Preview and interactively apply a rule-based plan.")
    organize.add_argument("folder")
    organize.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")
    organize.set_defaults(function=command_organize)
    undo = file_commands.add_parser("undo", help="Restore files from an operation journal.")
    undo.add_argument("journal_id")
    undo.set_defaults(function=command_undo)

    ai_parser = commands.add_parser("ai", help="Connect to local or remote AI providers.")
    ai_commands = ai_parser.add_subparsers(dest="ai_command")
    configure = ai_commands.add_parser("configure", help="Set an OpenAI-compatible API endpoint.")
    configure.add_argument("--url", required=True, help="API base URL, e.g. http://127.0.0.1:11434/v1")
    configure.add_argument("--model", required=True)
    configure.set_defaults(function=command_ai_configure)
    ask = ai_commands.add_parser("ask", help="Ask the configured AI a question.")
    ask.add_argument("question")
    ask.set_defaults(function=command_ai_ask)
    models = ai_commands.add_parser("models", help="List models on the configured API endpoint.")
    models.set_defaults(function=command_ai_models)
    ai_organize = ai_commands.add_parser("organize", help="Ask AI for a file plan, then review it.")
    ai_organize.add_argument("folder")
    ai_organize.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")
    ai_organize.set_defaults(function=command_ai_organize)

    runtime_parser = ai_commands.add_parser("runtime", help="Manage a local Ollama runtime.")
    runtime_commands = runtime_parser.add_subparsers(dest="runtime_command")
    status = runtime_commands.add_parser("status", help="Check the local Ollama server.")
    status.set_defaults(function=command_runtime_status)
    start = runtime_commands.add_parser("start", help="Start ollama serve in the background.")
    start.set_defaults(function=command_runtime_start)
    list_models = runtime_commands.add_parser("list", help="List models installed in local Ollama.")
    list_models.set_defaults(function=command_runtime_list)
    pull = runtime_commands.add_parser("pull", help="Download a model into local Ollama.")
    pull.add_argument("model")
    pull.set_defaults(function=command_runtime_pull)
    run = runtime_commands.add_parser("run", help="Run a model interactively with Ollama.")
    run.add_argument("model")
    run.set_defaults(function=command_runtime_run)

    debug_parser = commands.add_parser("debug", help="Inspect macOS apps and crash reports.")
    debug_commands = debug_parser.add_subparsers(dest="debug_command")
    inspect = debug_commands.add_parser("inspect", help="Read bundle metadata and diagnostics.")
    inspect.add_argument("application")
    inspect.set_defaults(function=command_debug_inspect)
    crashes = debug_commands.add_parser("crashes", help="List recent macOS crash reports.")
    crashes.add_argument("--app", help="Filter report filenames by application name.")
    crashes.add_argument("--limit", type=int, default=10)
    crashes.set_defaults(function=command_debug_crashes)
    crash = debug_commands.add_parser("crash", help="Read the start of one crash report.")
    crash.add_argument("report")
    crash.add_argument("--lines", type=int, default=200)
    crash.set_defaults(function=command_debug_crash)
    return parser

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "function"):
        parser.print_help()
        return 0
    try:
        args.function(args)
        return 0
    except (ValueError, RuntimeError, IOError, OSError) as error:
        out("Error: %s" % error)
        return 2

if __name__ == "__main__":
    sys.exit(main())
