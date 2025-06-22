# Setup machine for Jim 
---------------------

Ideally not doing this too often but you never know

## Usage

The setup is organized into cross-platform terminal preferences, dotfiles and basic tools, and linux-specific whole machine setups.

### Cross-platform commands (Mac & Linux)

```bash
make core-tools   # Install basic tools (automatically runs bootstrap if needed)
make term         # Configure dotfiles essentially (fish, tmux, vim, git, kitty)
make nas          # Mount NAS (prompts for password)
```

### Linix specific full machine setups

```bash
make setup # Full Linux setup based on hostname
```

## Linux Machine Archetypes

Linux machines get different configurations based on hostname. 

### Configure machines.yml

```yaml
machine_configs:
  # Laptop/desktop with full GUI
  "jim-laptop":
    - sway           # Window manager + waybar
    - development    # Rust, Node, dev tools
    - applications   # Discord, Steam, Spotify, VS Code
  
  # Minimal Raspberry Pi
  "pi-*":
    - basic-tools    # Just essentials
```

The `make setup` command detects hostname and applies matching configs automatically. Wildcards supported.

