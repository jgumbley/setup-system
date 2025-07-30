# SSH Public Keys

Place SSH public key files (*.pub) in this directory.

These keys will be automatically added to the authorized_keys file on machines configured with the ssh_host role.

Example files:
- user1.pub
- user2.pub
- admin.pub

Each .pub file should contain a single SSH public key in the standard format:
```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB... user@hostname
```