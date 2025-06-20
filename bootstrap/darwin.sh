/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
if [[ -f "/opt/homebrew/bin/brew" ]]; then
    echo >> /Users/admin/.zprofile
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> /Users/admin/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo >> /Users/admin/.zprofile
    echo 'eval "$(/usr/local/bin/brew shellenv)"' >> /Users/admin/.zprofile
    eval "$(/usr/local/bin/brew shellenv)"
fi
brew install ansible
ansible-galaxy collection install community.general

