
#!/bin/bash

# InterroPedago Student App - Update Script for AlmaLinux 9
# Run as root or with sudo

APP_DIR="/opt/interropedago-student"

if [ ! -d "$APP_DIR" ]; then
    echo "Error: App directory $APP_DIR not found. Please install first."
    exit 1
fi

echo "Stopping Service..."
systemctl stop interropedago-student

echo "Updating Files..."
# Copy parent directory contents to target
# Excludes virtual env and config files that shouldn't be overwritten if possible?
# But this is a simple update.
cp -r * $APP_DIR/

# Restore permissions just in case
chown -R interropedago:interropedago $APP_DIR

# Optional: Re-run pip install if requirements changed
if [ -f "requirements.txt" ]; then
    echo "Checking for dependency updates..."
    source $APP_DIR/venv/bin/activate
    pip install -r requirements.txt
    deactivate
fi

echo "Restarting Service..."
systemctl start interropedago-student

echo "Update Complete! Status:"
systemctl status interropedago-student --no-pager
