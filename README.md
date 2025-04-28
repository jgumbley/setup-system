Setup machine for Jim 
---------------------

Ideally not doing this too often but you never know

Classic problem is bootstrap. Imagine we can curl bootstrap and run from there

You'll need to manually install 1password and login to Github, create keys and upload them

## Usage

The setup is now organized into three playbooks:

1. `cross-platform.yml` - Sets up configuration for tools used on both Mac and Linux (no sudo required)
   - Git, Fish, Kitty, Tmux, Vim configs

2. `linux.yml` - Linux-specific setup (requires sudo)
   - Applications, development tools, window managers, NAS mounting

3. `mac.yml` - Mac-specific setup (requires sudo)
   - Mac-specific configurations, NAS mounting

### Make targets

- `make cross-platform` - Run only the cross-platform setup
- `make linux` - Run Linux setup (includes cross-platform setup)
- `make mac` - Run Mac setup (includes cross-platform setup)
- `make config` - Run minimal configuration setup and reload Sway