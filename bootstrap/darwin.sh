/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
if [[ -f "/opt/homebrew/bin/brew" ]]; then
    if ! grep -q "/opt/homebrew/bin/brew shellenv" /Users/admin/.zprofile 2>/dev/null; then
        echo >> /Users/admin/.zprofile
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> /Users/admin/.zprofile
    fi
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    if ! grep -q "/usr/local/bin/brew shellenv" /Users/admin/.zprofile 2>/dev/null; then
        echo >> /Users/admin/.zprofile
        echo 'eval "$(/usr/local/bin/brew shellenv)"' >> /Users/admin/.zprofile
    fi
    eval "$(/usr/local/bin/brew shellenv)"
fi
brew install ansible
ansible-galaxy collection install community.general

