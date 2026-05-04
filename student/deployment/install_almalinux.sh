
#!/bin/bash

# InterroPedago Student App - Setup Script for AlmaLinux 9
# Run as root or with sudo

echo "Installing System Dependencies..."
# AlmaLinux uses dnf. Python 3.9 is available via appstream or standard repos usually.
dnf install -y python3 python3-pip git

echo "Setting up Application Directory..."
APP_DIR="/opt/interropedago-student"
mkdir -p $APP_DIR
# Copy parent directory contents (assuming script is run from inside deployment/ or we copy files manually)
# Better assumption: User unzips the 'student' folder to /opt/interropedago-student or similar.
# Let's assume we are running this script FROM the 'student' folder.
cp -r * $APP_DIR/ || echo "Warning: run this script from the student folder root"

echo "Creating Virtual Environment..."
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate

echo "Installing Python Dependencies..."
pip install -r requirements.txt

echo "Setting Permissions..."
# Create user if not exists (Alma might default to something else, but 'nobody' is usually safe for simple apps, or create dedicated user)
id -u interropedago &>/dev/null || useradd -r -s /bin/false interropedago
chown -R interropedago:interropedago $APP_DIR

echo "Creating Systemd Service..."
cat <<EOF > /etc/systemd/system/interropedago-student.service
[Unit]
Description=InterroPedago Student App
After=network.target

[Service]
User=interropedago
Group=interropedago
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
# TODO: Admin must set the key here
Environment="GEMINI_API_KEY=votre_cle_ici"
ExecStart=$APP_DIR/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8002
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading Daemon..."
systemctl daemon-reload

echo "Setup Complete!"
echo "1. Edit API Key: nano /etc/systemd/system/interropedago-student.service"
echo "2. Start Service: systemctl start interropedago-student"
echo "3. Enable on Boot: systemctl enable interropedago-student"
