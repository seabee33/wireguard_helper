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

> ⚠️ Note: This script is intended for use on Debian-based systems. Other distros may require package name adjustments.

## 🚀 Installation & Usage

1. **Download** the script to any directory on your system.

2. **Set the admin password** on **line 13** of the file:
    ```python
    ADMIN_PASSWORD = "your_secure_password_here"
    ```
