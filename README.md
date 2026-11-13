# MacHelper

MacHelper is a lightweight, terminal-first toolkit for macOS. It is designed for older Macs, including OS X Yosemite 10.10, and uses only the Python standard library.

## Version 0.1.0

The first release includes:

- File scanning and rule-based organization previews.
- AI-generated organization plans through an OpenAI-compatible chat endpoint.
- Explicit review before any move or Trash operation.
- A local operation journal and an undo command.
- Read-only inspection of macOS application bundles and crash reports.
- Optional local Ollama runtime controls.
- Connections to local or remote model servers that expose an OpenAI-compatible API.

Scanning, planning, and asking the AI do not change files. Every organization plan must be reviewed and explicitly applied. A Trash action moves a file to macOS Trash; it does not permanently erase it.

## Requirements

- macOS 10.10 or later.
- Python 2.7 or Python 3.6+.
- No pip packages or heavyweight IDE required.

The AI connector uses the standard library and an OpenAI-compatible HTTP endpoint. A model server can run on this Mac or another computer on the network. Remote HTTPS services may require a newer Python/TLS stack than Yosemite includes; for an older Mac, a local HTTP endpoint on a trusted network is often the easiest path.

## Quick start

From the repository directory:

    chmod +x machelper
    ./machelper --help
    ./machelper doctor
    ./machelper files scan ~/Downloads
    ./machelper files plan ~/Downloads
    ./machelper files review PLAN_ID
    ./machelper files apply PLAN_ID

The plan command only creates a preview. The apply command asks for confirmation. For a one-command rule-based workflow:

    ./machelper files organize ~/Downloads

After a successful apply, MacHelper prints an undo journal ID. Restore the original locations with:

    ./machelper files undo JOURNAL_ID

## AI setup

Configure an OpenAI-compatible endpoint:

    ./machelper ai configure --url http://127.0.0.1:11434/v1 --model llama3.2:3b

Or use another computer running a compatible server:

    ./machelper ai configure --url http://192.168.1.50:11434/v1 --model llama3.2:3b

Ask a question:

    ./machelper ai ask "How can I find what is using disk space?"

Ask AI to propose a file organization plan:

    ./machelper ai organize ~/Downloads

AI organization sends filenames, extensions, and file sizes to the configured endpoint. It does not upload file contents. Only point it at folders whose metadata you are comfortable sharing with that endpoint.

For providers that require a bearer token, set MACHELPER_API_KEY in the environment. The key is not written to the MacHelper config file. OPENAI_API_KEY is also recognized.

## Local model runtime

If Ollama is installed and available in PATH on a capable Mac:

    ./machelper ai runtime start
    ./machelper ai runtime status
    ./machelper ai runtime list
    ./machelper ai runtime pull llama3.2:3b
    ./machelper ai runtime run llama3.2:3b

The runtime commands call the installed Ollama CLI; MacHelper does not bundle, install, or silently download a model runtime. Model downloads can be several gigabytes. The Yosemite Mac with 2 GB RAM is better used as a client for a model server running on a more powerful computer.

To connect to a model server on another computer, configure its reachable API URL with ai configure. The server must expose an OpenAI-compatible API.

## Application debugging

Inspect an application bundle without changing it:

    ./machelper debug inspect /Applications/Safari.app

List recent crash reports:

    ./machelper debug crashes
    ./machelper debug crashes --app Safari

Read the start of a crash report:

    ./machelper debug crash ~/Library/Logs/DiagnosticReports/REPORT.crash

The debugger reports bundle metadata and, when available, executable format, linked libraries, code-signing details, and Gatekeeper assessment. Crash-report reading is limited to macOS diagnostic log folders and is read-only.

## Install

The install script defaults to the current user's home directory:

    sh install.sh

It installs the command to ~/.local/bin/machelper and application files to ~/.local/lib/machelper. Add ~/.local/bin to PATH if it is not already there.

For a different prefix:

    PREFIX=/usr/local sh install.sh

## Tests

Run the standard-library test suite from the repository:

    python -m unittest discover -s tests -v

## Safety model

- Scan and plan operations are read-only.
- Every move or Trash operation is displayed for review first.
- Applying a plan requires interactive confirmation, unless --yes is explicitly supplied.
- Organization plans are constrained to the selected folder.
- Existing destination files are never intentionally overwritten.
- Trash means moving to ~/.Trash, not permanent deletion.
- Each apply creates an undo journal. Partial applies are recorded and can be undone.
- Undo refuses to overwrite an existing original file.
- AI output is untrusted and validated before it becomes a plan.

## Project status

MacHelper 0.1.0 is an early functional foundation. The command-line core comes first; a native graphical interface, additional AI providers, more debugging adapters, and richer model-management tools can build on it later without making the core depend on a heavyweight desktop framework.

## License

MIT. See LICENSE.
