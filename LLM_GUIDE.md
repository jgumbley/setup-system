# LLM Guide for Configuration Management

This repository contains configuration files and templates for setting up a Linux desktop environment using tools like Sway, Waybar, and Kanshi. The key points to understand are:

1. **Configuration Files**: The templates/ directory contains Jinja2 templates that generate configuration files for various tools. These should be edited rather than directly modifying system files.

2. **Ansible Automation**: The repository uses Ansible to manage the configuration and deployment process. The main playbooks are in the root directory, with tasks and handlers organized in their respective directories.

3. **Key Files**:
   - templates/swayconfig.j2: Template for Sway window manager configuration
   - templates/waybar.j2: Template for Waybar configuration
   - templates/kanshi-config.j2: Template for Kanshi display configuration
   - main.yml: Main Ansible playbook

4. **Best Practices**:
   - Always modify the templates rather than system files directly
   - Test changes by running the Ansible playbook
   - Document any changes in the relevant template files
   - Use the Makefile for common tasks

5. **Important Note**: This repository manages configurations through templates and automation. Do not attempt to directly install packages or modify system settings outside of this framework.