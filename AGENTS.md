## How to work in this repo
- Strictly make as entry point to invoke all targets, runtime and test.
- Operate only inside this pwd unless explicitly told otherwise (PWD rules apply).
- Do not stage or commit changes. Git commits belong to the operator unless the operator explicitly asks an agent to create one.
- Read the Makefile first before using any tools or adding targets.
- Call `make digest` to understand the codebase; it is the sanctioned way to learn the structure.
- All execution happens via make; add or adjust Make targets rather than invoking tools or scripts directly.
- Keep each utility's implementation and Make targets self-contained under `utils/<utility>/`. Invoke utilities through their own Makefiles with `make -C utils/<utility> <target>`; never add utility help text, aliases, forwarding targets, or includes to the root `Makefile`.
- Do not add role-specific targets to the root `Makefile`. Apply roles assigned to the exact current hostname only through `make setup`, using the host selection in `setup.yml` and `machines.yml`.
- During role development, a generic `make test_role role=xyz` target may be added when an isolated run is needed. It must reuse the same current-host selection as `make setup` and reject a role that is not assigned to that host; do not add a target named for the role or bypass `machines.yml`.
- `pane.sh` is available at the repo root as a tmux pane runner helper.
- `pane.sh` remains non-executable; invoke it with `bash pane.sh` from the Make-owned workflow when needed.
- If a `make` target needs sudo/become, prompts for a password, or writes outside the workspace (for example Ansible temp paths under `~/.ansible`), run that `make` target through `pane.sh` first so the user can type credentials in the pane while the agent reads output.

## Architectural alignment
- Align with the existing architecture. Reuse what is here; do not reframe components.
- Do not add modules (files, packages, services) unless explicitly approved by the operator.
- The stub worker and spawner are the only additions needed for this milestone, routed through the Makefile.

## Principles (Prime directives)
- YAGNI - build only what this stub needs.
- DRY - if something exists, reuse it.
- KISS - keep it straightforward; no optional branches or toggles.
- No fallbacks - they hide failures; let issues surface immediately.
