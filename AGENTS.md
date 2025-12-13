# Coding Agents Workflow

This repository occasionally uses coding agents (Claude Code, Codex, etc.) to
drive `make` targets that pause for sudo/BECOME prompts. The agents do **not**
receive secrets, so we route those commands through tmux and let a human type
passwords directly inside the pane.

## Quick Start: `make agent-core`

1. Start or attach to a tmux session in this repository.
2. Run `make agent-core`.
3. The target splits a pane **above** the current one and starts `make core`
   there (with a pane title of `agent-core`).
4. Watch the new pane. When Ansible asks for a password, type it right in that
   pane. Echo is disabled so nothing sensitive shows up in the capture buffer.
5. The lower pane (the agent / chat UI) can keep polling the top pane via
   `tmux capture-pane` to read progress or errors without ever seeing the
   password input.
6. After `make core` completes the pane prints its exit status and waits for
   you to hit **Enter** (inside that pane) to rerun the command. Capture
   whatever you need first, then press Enter to run again or kill the pane with
   `Ctrl-b x`.

If you leave the pane open, you can rejoin it later with
`tmux join-pane -sb <pane-id>`. The target prints the pane id after it starts,
so the agent and human can refer to the same identifier.

## Generic agent wrapper

You can wrap any Make target in the same tmux workflow without adding a new
target: run `make agent-<target>`. Examples:

```bash
make agent-setup      # runs `make setup` in the agent pane
make agent-term       # runs `make term` in the agent pane
make agent-inference  # runs `make inference` in the agent pane
```

Under the hood the Make logic handles tmux setup, pane sizing, and reruns, so
no extra wrapper scripts are needed.

## When to use this pattern

The tmux-driven workflow is ideal whenever:

* `make core`, `make caffeinate`, or other targets run `sudo` / `ansible -K`.
* You need to watch long-running output together with the agent.
* You want the agent to recover context by scraping tmux instead of re-running.

The `AGENT_PANE_PERCENT` environment variable (default 45) can be exported
before calling a target to change the height of the spawned pane.

## Guidance for Agent Skills

If you are wiring this repository into an Agent Skill (e.g. the tmux skill from
obra’s `superpowers-lab`), follow these rules:

* Start privileged commands by running `make agent-core` (or another wrapper)
  inside tmux. Never try to run `make core` directly through the chat channel.
* Continue reading the pane output using the tmux skill (`capture-pane`,
  `send-keys`, etc.).
* Whenever the pane shows a password/passphrase prompt, **stop** sending keys
  and instruct the human operator to type the secret locally inside the pane.
  Resume automation only after the human confirms that the prompt cleared.
* Share the pane id (`tmux display-message -p "#{pane_id}"`) whenever you ask
  the human to intervene, so everyone knows which pane to use.
* Wait for the human to confirm they are done inspecting the logs before sending
  the final Enter that closes the pane; otherwise leave it open.

This keeps secrets off the model context while still letting the agent debug
and recover from Ansible failures in the tmux session.
