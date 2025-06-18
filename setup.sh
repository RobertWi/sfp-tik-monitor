#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Make monitor.py executable
chmod +x monitor.py

# Set up systemd user service
mkdir -p ~/.config/systemd/user/
cp mikrotik-monitor.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable mikrotik-monitor
systemctl --user start mikrotik-monitor

echo "Setup complete. Check status with: systemctl --user status mikrotik-monitor" 