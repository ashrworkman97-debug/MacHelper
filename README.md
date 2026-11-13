# MacHelper

MacHelper is a lightweight, terminal-first toolkit for macOS. It is designed to be useful on older Macs, including OS X Yosemite 10.10, without third-party Python packages.

## Current version: 0.1.0

The first release includes:

- File scanning and a rule-based organization preview.
- AI-generated organization plans through an OpenAI-compatible chat endpoint.
- Explicit review before any move or Trash operation.
- A local operation journal and an undo command.
- Read-only inspection tools for macOS application bundles.
- Optional connections to local or remote model servers that expose an OpenAI-compatible API.

Nothing is moved or trashed just by scanning, planning, or asking the AI. Review a saved plan and explicitly apply it before files are changed. Trash operations move files to the macOS Trash; they do not permanently erase them.

## Requirements

- macOS 10.10 or later.
- Python 2.7 or Python 3.6+.
- Standard-library-only core; no pip packages are required.

The AI connector uses the Python standard library and an OpenAI-compatible HTTP endpoint. For a local model, run a compatible model server on this Mac or another computer on your network. A remote HTTPS provider may require a newer Python/TLS stack than the one included with Yosemite; a local HTTP endpoint on a trusted network is often the easiest option for an older Mac.

## Quick start

From the repository directory:

    chmod +x maclab
    ./maclab --help
    ./maclab doctor
    ./maclab files scan ~/Downloads
    ./maclab files plan ~/Downloads
    ./maclab files review PLAN_ID
    ./maclab files apply PLAN_ID

The plan command only creates a preview. The apply command asks for confirmation. You can also use the one-command flow:

    ./maclab files organize ~/Downloads

## AI setup

Configure an OpenAI-compatible endpoint:

    ./maclab ai configure --url http://127.0.0.1:11434/v1 --model llama3.2:3b

Or point it at another computer running a compatible server:

    ./maclab ai configure --url http://192.168.1.50:11434/v1 --model llama3.2:3b

Ask a question:

    ./maclab ai ask "How can I find what is using disk space?"

Ask AI to propose an organization plan:

    ./maclab ai organize ~/Downloads

AI organization sends filenames, file sizes, and extensions to the configured model endpoint. It does not upload file contents. Treat the endpoint as a service you trust, and do not point it at private folders unless you understand what metadata will be sent.

Set MACLAB_API_KEY in the environment for providers that require a bearer token. The key is not written to the MacHelper config file.

## Application debugging

Inspect a macOS application bundle without changing it:

    ./maclab debug inspect /Applications/Safari.app

The debugger reports bundle metadata and, when available, executable format, linked libraries, code-signing details, and Gatekeeper assessment.

## Install

The install script defaults to the current user's home directory:

    sh install.sh

It installs the command to ~/.local/bin/maclab and the application files to ~/.local/lib/maclab. Add ~/.local/bin to PATH if it is not already there.

To install somewhere else:

    PREFIX=/usr/local sh install.sh

## Safety model

- Scan and plan operations are read-only.
- Every move or Trash operation is displayed for review first.
- Applying a plan requires an interactive confirmation, unless --yes is explicitly supplied.
- Paths are constrained to the selected folder for organization plans.
- Existing destination files are never overwritten.
- Trash means moving to ~/.Trash, not permanent deletion.
- Each successful apply creates a journal. The undo command attempts to restore files and refuses to overwrite an existing source.
- AI output is treated as untrusted input and validated before it becomes a plan.

## Project status

MacHelper 0.1.0 is an early functional foundation. The command-line core is the priority; a native graphical interface, additional debug adapters, more AI providers, and richer model management can be added without making the core depend on a heavyweight desktop framework.

## License

MIT. See LICENSE.
