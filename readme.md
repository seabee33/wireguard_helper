# SeaBee's WireGuard Helper Script

This Python script simplifies the installation and management of a WireGuard VPN server, including client configuration.

## 🔧 Features

- Installs WireGuard and required dependencies
- Generates server and peer key pairs
- Edits and manages the WireGuard config file (`wg0.conf`)
- Stores configuration data in a JSON file for easy reuse
- Allows editing the server endpoint
- Starts a temporary web admin panel for WireGuard management
- Automatically opens port `51820` using UFW (if enabled)

## 📦 Requirements

- Python 3
- Flask (`sudo apt install python3-flask` **or** `pip install flask`)
- A Linux-based system
- Internet connection

> ⚠️ Note: This script has been tested on debain and may not work on your machine

## 🚀 Installation & Usage

1. Ensure you have **all** dependencies

```bash
sudo apt install curl python3-flask -y
```

2. Download and run the script
```bash
curl -L -o wg_helper.py https://raw.githubusercontent.com/seabee33/wireguard_helper/main/wg_helper.py
```

3. **Set the admin password** on **line 10** of the file: `ADMIN_PASSWORD = "CHANGEME"`
    
4. **Run the script with sudo or as root** `sudo python3 wg_helper.py`

5. Access the web panel: Open your browser and go to: `http://<SERVER_IP>:5050` and go through the easy setup steps:


## Setup once web panel loaded
1. Install and activate necessary software in **system status** (Install wireguard, autostart wireguard at boot, install iptables, Open Port 51820 *if ufw is installed*)
2. Fill in endpoint in options
3. generate keys
4. Add peers with a unique name
5. download peer config and connect on client device
6. Don't forget to port forward your server on your modem! (port 51820)

Preview:
![image](https://github.com/user-attachments/assets/005ca4e2-0569-4605-acd4-0f0961fc2ba5)
