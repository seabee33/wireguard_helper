from flask import Flask, request, render_template_string, redirect, url_for, session, Response, abort
import os, subprocess, shutil, sys, json, html, secrets

if os.geteuid() != 0:
    print("This script needs to be run as root or sudo, try 'sudo python3 wg_helper.py'")
    sys.exit(1)


# ===================== #
ADMIN_PASSWORD = "CHANGEME"
# ===================== #


app = Flask(__name__)
app.secret_key = os.urandom(24)
wireguard_dir = "/etc/wireguard"
config_file = "wg_helper.json"
full_config_file_path = os.path.join(wireguard_dir, config_file)
SYSCTL_CONF = "/etc/sysctl.conf"


@app.before_request
def check_auth_and_csrf():
    if request.endpoint in ("login", "static", None):
        return
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if request.method == "POST":
        token = session.get("csrf_token")
        if not token or request.form.get("csrf_token") != token:
            abort(403)


def get_default_interface():
    result = subprocess.run(["ip", "-o", "-4", "route", "show", "to", "default"], capture_output=True, text=True)
    parts = result.stdout.split()
    return parts[4] if len(parts) > 4 else ""


default_config = {
    "server": {
        "server_network_interface": get_default_interface(),
        "Endpoint": "",
        "ListenPort": 51820,
        "PrivateKey": "",
        "PublicKey": ""
    },
    "peers": [
    ]
}

# Common CSS for all pages
CSS = """
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f5f7fa;
    padding: 0;
    margin: 0;
}

.container {
    width: 95%;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.header {
    background-color: #2c3e50;
    color: white;
    padding: 15px 0;
    margin-bottom: 20px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.header h1 {
    margin: 0;
    font-size: 24px;
}

.navbar {
    text-align: right;
}

.navbar a {
    color: white;
    text-decoration: none;
    padding: 8px 12px;
    border-radius: 4px;
    transition: background-color 0.3s;
}

.navbar a:hover {
    background-color: rgba(255,255,255,0.1);
}

.card {
    background-color: white;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.card h2 {
    color: #2c3e50;
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
}

.card strong {
    color: #34495e;
}

.divider {
    height: 1px;
    background-color: #e1e4e8;
    margin: 20px 0;
}

input[type="text"],
input[type="password"] {
    width: 100%;
    padding: 10px;
    margin: 8px 0;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 16px;
}

.btn, input[type="submit"] {
    background-color: #3498db;
    color: white;
    border: none;
    padding: 8px 15px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    margin-right: 5px;
    transition: background-color 0.3s;
}

.btn:hover, input[type="submit"]:hover {
    background-color: #2980b9;
}

.btn-small {
    padding: 5px 10px;
    font-size: 12px;
}

.btn-danger {
    background-color: #e74c3c;
}

.btn-danger:hover {
    background-color: #c0392b;
}

.btn-success {
    background-color: #2ecc71;
}

.btn-success:hover {
    background-color: #27ae60;
}

.status-item {
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
}

.status-item form {
    margin-left: 10px;
}

.login-form {
    max-width: 400px;
    margin: 100px auto;
    background-color: white;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}

.login-form h2 {
    text-align: center;
    margin-bottom: 20px;
    color: #2c3e50;
}

.login-form input[type="submit"] {
    width: 100%;
    padding: 10px;
    margin-top: 15px;
}

.error-message {
    color: #e74c3c;
    margin-top: 10px;
    text-align: center;
}

.peer-item {
    background-color: #f8f9fa;
    border-left: 4px solid #3498db;
    padding: 15px;
    margin-bottom: 15px;
    border-radius: 4px;
}

.peer-item form {
    margin-top: 10px;
}

.peer-actions {
    margin-top: 10px;
    display: flex;
    gap: 5px;
}

.option-row {
    display: flex;
    align-items: center;
    margin-bottom: 15px;
}

.option-row strong {
    min-width: 150px;
}

.option-row form {
    flex-grow: 1;
    display: flex;
    gap: 10px;
}

.option-row input[type="text"] {
    flex-grow: 1;
}

.success {
    color: #2ecc71;
}

.danger {
    color: #e74c3c;
}

.warning {
    color: #f39c12;
}

@media (max-width: 768px) {
    .option-row {
        flex-direction: column;
        align-items: flex-start;
    }
    
    .option-row strong {
        margin-bottom: 5px;
    }
    
    .option-row form {
        width: 100%;
    }
}
"""


@app.route("/", methods=["GET", "POST"])
def login():
    LOGIN_HTML = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>WireGuard Helper - Login</title>
        <style>
            """ + CSS + """
        </style>
    </head>
    <body>
        <div class="container">
            <div class="login-form">
                <h2>SeaBee's WireGuard Helper</h2>
                <form method="POST">
                    <div>
                        <input type="password" name="password" placeholder="Enter admin password" required autofocus>
                    </div>
                    <div>
                        <input type="submit" value="Login" class="btn">
                    </div>
                    {% if error %}
                    <div class="error-message">{{ error }}</div>
                    {% endif %}
                </form>
            </div>
        </div>
    </body>
    </html>
    """
        
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            session["csrf_token"] = secrets.token_hex(32)
            return redirect(url_for("dashboard"))
        else:
            return render_template_string(LOGIN_HTML, error="Incorrect password, please try again")
    return render_template_string(LOGIN_HTML, error=None)


@app.route("/dashboard")
def dashboard():
    csrf_token = session.get("csrf_token", "")
    config_data = load_config()

    # One liners
    is_wg_installed = shutil.which("wg") is not None
    is_ufw_installed = ufw_get_path()
    is_iptables_installed = iptables_get_path()
    server_network_interface = config_data.get("server", {}).get("server_network_interface", "")

    # Status indicators
    wg_installed_status = "Installed" if is_wg_installed else "Not installed"
    wg_installed_class = "success" if is_wg_installed else "danger"
    
    install_wg_button = ""
    if not is_wg_installed:
        install_wg_button = """
        <form action="/install_wireguard" method="POST" style='display:inline'>
            <input type="submit" value="Install WireGuard" class="btn btn-success">
        </form>
        """

    ufw_allow_port_button = """
    <form action='/ufw_open_port' method='POST' style='display:inline'> 
        <input type='submit' value='Open Port 51820' class="btn btn-success">
    </form>
    """

    ufw_installed_status = "Installed" if is_ufw_installed else "Not installed"
    ufw_installed_class = "success" if is_ufw_installed else "warning"
    
    if is_ufw_installed:
        ufw_path = ufw_get_path()
        ufw_result = subprocess.run([ufw_path, "status"], capture_output=True, text=True)
        ufw_enabled_status = ""
        for line in ufw_result.stdout.splitlines():
            if "Status:" in line:
                ufw_enabled_status = line.split()[-1]
                break
        if ufw_enabled_status == "active":
            ufw_enabled_status = "active"
            ufw_enabled_class = "success"
        else:
            ufw_enabled_status = "disabled"
            ufw_enabled_class = "warning"
    else:
        ufw_enabled_status = ""
        ufw_enabled_class = ""

    iptables_installed_status = "Installed" if is_iptables_installed else "Not installed"
    iptables_installed_class = "success" if is_iptables_installed else "danger"
    
    if not is_iptables_installed:
        iptables_install_button = """
        <form action="/install_iptables" method="POST" style='display:inline'>
            <input type="submit" value="Install iptables" class="btn btn-success">
        </form>
        """
    else:
        iptables_install_button = ""

    wg_running_status = ""
    wg_running_class = ""
    wg_running_button = ""
    
    if is_wg_installed:
        wg_running_check = subprocess.run(["systemctl", "is-active", "wg-quick@wg0"], capture_output=True, text=True).stdout.strip()

        config_data = load_config()
        server_priv_key = config_data.get("server", {}).get("PrivateKey", "")

        if server_priv_key == "":
            wg_running_status = "Server keys need to be generated first"
            wg_running_class = "warning"
        else:
            if wg_running_check == "failed":
                wg_running_status = "Not running"
                wg_running_class = "danger"
                wg_running_button = """
                <form action='/start_wg' method='POST' style='display:inline'> 
                    <input type='submit' value='Start wireguard' class="btn btn-success">
                </form>
                """
            else:
                wg_running_status = "Running"
                wg_running_class = "success"
    else:
        wg_running_status = "Not running, waiting for install"
        wg_running_class = "warning"

    wg_enabled_at_boot_status = ""
    wg_enabled_at_boot_class = ""
    wg_enabled_at_boot_button = ""
    
    wg_enabled_at_boot_check = subprocess.run(["systemctl", "is-enabled", "wg-quick@wg0"], capture_output=True, text=True).stdout.strip()
    if wg_enabled_at_boot_check == "enabled":
        wg_enabled_at_boot_status = "Enabled"
        wg_enabled_at_boot_class = "success"
    else:
        wg_enabled_at_boot_status = "DISABLED"
        wg_enabled_at_boot_class = "danger"
        wg_enabled_at_boot_button = """
        <form action='/autostart_wg_on_boot' method='POST' style='display:inline'> 
            <input type='submit' value='Autostart Wireguard at boot' class="btn btn-success">
        </form>
        """

    ufw_port_status = ""
    ufw_port_class = ""
    
    if is_ufw_installed and ufw_enabled_status == "active":
        ufw_path = ufw_get_path()
        ufw_port_result = subprocess.run([ufw_path, "status"], capture_output=True, text=True)
        ufw_wg_port_check = ""
        for line in ufw_port_result.stdout.splitlines():
            if "51820" in line:
                ufw_wg_port_check = line.split()[1]
                break
        if ufw_wg_port_check == "":
            ufw_port_status = "Not added"
            ufw_port_class = "danger"
            ufw_port_button = ufw_allow_port_button
        else:
            ufw_port_status = "Allowed" if ufw_wg_port_check == "ALLOW" else "Denied"
            ufw_port_class = "success" if ufw_wg_port_check == "ALLOW" else "danger"
            ufw_port_button = "" if ufw_wg_port_check == "ALLOW" else ufw_allow_port_button
    else:
        ufw_port_status = "N/A"
        ufw_port_class = "warning"
        ufw_port_button = ""

    # Endpoint data
    server_endpoint_data = html.escape(config_data.get("server", {}).get("Endpoint", ""))
    if server_endpoint_data == "":
        server_endpoint_form = """
        <form action="/update_server_endpoint" method="POST" class="option-form">
            <input type="text" placeholder="Set server endpoint" name='endpoint' required>
            <input type="submit" value="Set endpoint" class="btn btn-success">
        </form>
        """
    else:
        server_endpoint_form = f"""
        <span>{server_endpoint_data}</span>
        <form action="/update_server_endpoint" method="POST" class="option-form">
            <input type="text" placeholder='Enter new endpoint' name='endpoint' required>
            <input type="submit" value="Update endpoint" class="btn">
        </form>
        """

    # Server public key
    server_public_key = html.escape(config_data.get("server", {}).get("PublicKey", ""))
    if server_public_key == "":

        server_public_key_form = f"""
        <span class="warning">No Keys set</span>
        <form action="/regenerate_server_keys" method="POST" class="option-form">
            <input type="submit" value="Generate server keys" class="btn btn-success">
        </form>
        """
    else:
        server_public_key_form = f"""
        <code class="success">{server_public_key}</code>
        <form action="/regenerate_server_keys" method="POST" class="option-form">
            <input type="submit" value="Regenerate server keys" class="btn">
        </form>
        """

    # Peers list
    peers_list = ""
    peer_config = config_data.get("peers", [])
    for peer in peer_config:
        peer_id = peer["id"]
        peer_name = html.escape(peer["name"])
        peer_public_key = html.escape(peer["PublicKey"])

        peers_list += f"""
        <div class="peer-item">
            <div><strong>ID:</strong> {peer_id}</div>
            <div><strong>Name:</strong> {peer_name}</div>
            <div><strong>Public Key:</strong> <code>{peer_public_key}</code></div>
            <div class="peer-actions">
                <form action='/delete_peer' method='POST'>
                    <input type='hidden' name='peer_id_to_delete' value='{peer_id}'>
                    <input type='submit' value='Delete peer' class="btn btn-danger">
                </form> 
                <form action='/download_peer_config' method='POST'>
                    <input type='hidden' name='peer_id' value='{peer_id}'>
                    <input type='submit' value='Download config file' class="btn">
                </form>
            </div>
        </div>"""

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SeaBee's WG Helper</title>
        <style>
            {CSS}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="container header-content">
                <h1>SeaBee's Wireguard Helper v0.2</h1>
                <div class="navbar">
                    <a href="/logout">Logout</a>
                </div>
            </div>
        </div>
        
        <div class="container">
            <div class="card">
                <h2>System Status</h2>
                
                <div class="status-item">
                    <strong>Wireguard software:</strong>&nbsp;
                    <span class="{wg_installed_class}">{wg_installed_status}</span>
                    {install_wg_button}
                </div>
                
                <div class="status-item">
                    <strong>Wireguard autostart at boot:</strong>&nbsp;
                    <span class="{wg_enabled_at_boot_class}">{wg_enabled_at_boot_status}</span>
                    {wg_enabled_at_boot_button}
                </div>
                
                <div class="status-item">
                    <strong>UFW:</strong>&nbsp;
                    <span class="{ufw_installed_class}">{ufw_installed_status}</span>
                    {' &nbsp;&&nbsp; ' + '<span class="' + ufw_enabled_class + '">' + ufw_enabled_status + '</span>' if ufw_enabled_status else ''}
                </div>
                
                {f'''
                <div class="status-item">
                    <strong>UFW Wireguard Port:</strong>&nbsp;
                    <span class="{ufw_port_class}">{ufw_port_status}</span>
                    {ufw_port_button}
                </div>
                ''' if ufw_port_status else ''}
                
                <div class="status-item">
                    <strong>iptables:</strong>&nbsp;
                    <span class="{iptables_installed_class}">{iptables_installed_status}</span>
                    {iptables_install_button}
                </div>
                
                <div class="status-item">
                    <strong>Server network interface:</strong>&nbsp;
                    <span>{server_network_interface}</span>
                </div>
                
                <div class="status-item">
                    <strong>Wireguard status:</strong>&nbsp;
                    <span class="{wg_running_class}">{wg_running_status}</span>
                    {wg_running_button}
                </div>
            </div>

            <div class="card">
                <h2>Server Configuration</h2>
                
                <div class="option-row">
                    <strong>Server endpoint:</strong>
                    <div>{server_endpoint_form}</div>
                </div>
                
                <div class="option-row">
                    <strong>Server Public key:</strong>
                    <div>{server_public_key_form}</div>
                </div>
            </div>

            <div class="card">
                <h2>Peer Management</h2>
                
                <div class="status-item" style="margin-bottom: 20px;">
                    <strong>Create new peer:</strong>
                    <form action="/create_new_peer" method="POST" style="display:flex; gap:10px; margin-left:10px;">
                        <input type="text" placeholder="Peer name" name="peer_name" required>
                        <input type="submit" value="Create" class="btn btn-success">
                    </form>
                </div>
                
                {peers_list if peers_list else '<p>No peers configured yet. Create your first peer above.</p>'}
            </div>
        </div>
        <script>
        document.querySelectorAll('form').forEach(function(f) {{
            if (f.method === 'post') {{
                var i = document.createElement('input');
                i.type = 'hidden';
                i.name = 'csrf_token';
                i.value = '{csrf_token}';
                f.appendChild(i);
            }}
        }});
        </script>
    </body>
    </html>
    """
    return html


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/install_wireguard", methods=["POST"])
def install_wireguard():


    try:
        subprocess.check_call(["sudo", "apt", "install", "-y", "wireguard"])
        return redirect(url_for("dashboard"))
    except subprocess.CalledProcessError as e:
        error_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Installation Error</title>
            <style>{CSS}</style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h2>Installation Failed</h2>
                    <p class="danger">Error: {e}</p>
                    <a href="/dashboard" class="btn">Back to Dashboard</a>
                </div>
            </div>
        </body>
        </html>
        """
        return error_html


@app.route("/install_iptables", methods=["POST"])
def install_iptables():


    try:
        subprocess.check_call(["sudo", "apt", "install", "-y", "iptables"])
        return redirect(url_for("dashboard"))
    except subprocess.CalledProcessError as e:
        error_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Installation Error</title>
            <style>{CSS}</style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h2>Installation Failed</h2>
                    <p class="danger">Error: {e}</p>
                    <a href="/dashboard" class="btn">Back to Dashboard</a>
                </div>
            </div>
        </body>
        </html>
        """
        return error_html


@app.route("/update_server_endpoint", methods=["POST"])
def update_server_endpoint():

    
    new_endpoint = request.form.get("endpoint", "").strip()

    config_data = load_config()
    config_data.setdefault("server", {})["Endpoint"] = new_endpoint

    update_config(config_data)

    return redirect(url_for("dashboard"))


@app.route("/ufw_open_port", methods=["POST"])
def ufw_open_port():


    ufw_path = ufw_get_path()

    try:
        subprocess.check_call([ufw_path, "allow", "51820", "comment", '"Wireguard"'])
    except subprocess.CalledProcessError as e:
        error_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>UFW Error</title>
            <style>{CSS}</style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h2>UFW Configuration Failed</h2>
                    <p class="danger">Error: {e}</p>
                    <a href="/dashboard" class="btn">Back to Dashboard</a>
                </div>
            </div>
        </body>
        </html>
        """
        return error_html

    return redirect(url_for("dashboard"))

@app.route("/regenerate_server_keys", methods=["POST"])
def regenerate_server_keys():

    private_key = subprocess.check_output(["wg", "genkey"], text=True).strip()
    public_key = subprocess.check_output(["wg", "pubkey"], input=private_key, text=True).strip()

    config_data = load_config()

    config_data.setdefault("server", {})["PrivateKey"] = private_key
    config_data.setdefault("server", {})["PublicKey"] = public_key

    update_config(config_data)

    return redirect(url_for("dashboard"))


@app.route("/create_new_peer", methods=["POST"])
def create_new_peer():
    new_peer_name = request.form.get("peer_name", "").strip()

    config_data = load_config()

    peers = config_data.get("peers", [])

    existing_ids = sorted(peer["id"] for peer in peers)

    # Find available ID by checking gaps
    existing_ids = sorted(peer["id"] for peer in peers)  # Get all assigned IDs, sorted

    # Start from 2, find the first missing number
    new_id = 2
    for id in existing_ids:
        if id == new_id:
            new_id += 1
        else:
            break  # Found a gap, use it

    # Generate new keys
    private_key = subprocess.check_output(["wg", "genkey"], text=True).strip()
    public_key = subprocess.check_output(["wg", "pubkey"], input=private_key, text=True).strip()

    # Create new peer info
    new_peer = {
        "id": new_id,
        "name": new_peer_name,
        "PrivateKey": private_key,
        "PublicKey": public_key
    }

    peers.append(new_peer)
    peers = sorted(peers, key=lambda peer: peer.get("id", 0))

    config_data["peers"] = peers

    update_config(config_data)

    return redirect(url_for("dashboard"))


@app.route("/delete_peer", methods=["POST"])
def delete_peer():
    try:
        peer_id_to_delete = int(request.form.get("peer_id_to_delete", "").strip())
    except (ValueError, TypeError):
        return "Invalid peer ID", 400
    config_data = load_config()
    peer_config = config_data.get("peers", [])

    # Literally just set the peers to itself minus the peer ID requested
    new_peer_config = [peer for peer in peer_config if peer["id"] != peer_id_to_delete]
    new_peer_config = sorted(new_peer_config, key=lambda peer: peer.get("id", 0))

    config_data["peers"] = new_peer_config

    update_config(config_data)

    return redirect(url_for("dashboard"))


@app.route("/download_peer_config", methods=["POST"])
def download_peer_config():
    try:
        peer_id_to_download = int(request.form.get("peer_id", "").strip())
    except (ValueError, TypeError):
        return "Invalid peer ID", 400

    config_data = load_config()
    peer_config = config_data.get("peers", [])

    selected_peer = None
    for peer in peer_config:
        if peer.get("id") == peer_id_to_download:
            selected_peer = peer
            break

    if not selected_peer:
        return "Peer not found", 404

    peer_name = selected_peer["name"]
    peer_pub_key = selected_peer["PublicKey"]
    peer_priv_key = selected_peer["PrivateKey"]

    server_pub_key = config_data["server"]["PublicKey"]
    endpoint = config_data["server"]["Endpoint"]
    listen_port = config_data["server"]["ListenPort"]
    interface = config_data["server"]["server_network_interface"]

    # Compose the WireGuard peer config
    config_text = (
        f"[Interface]\n"
        f"PrivateKey = {peer_priv_key}\n"
        f"Address = 10.11.0.{peer_id_to_download}/32\n"
        f"DNS = 1.1.1.1\n"
        f"\n"
        f"[Peer]\n"
        f"PublicKey = {server_pub_key}\n"
        f"Endpoint = {endpoint}:{listen_port}\n"
        f"AllowedIPs = 0.0.0.0/0\n"
        f"PersistentKeepalive = 25\n"
    )

    # Create response with downloadable config file
    filename = f"peer_{peer_name}.conf"
    return Response(
        config_text,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/start_wg", methods=["POST"])
def start_wg():
    subprocess.run(["wg-quick", "up", "wg0"], text=True)

    return redirect(url_for("dashboard"))


@app.route("/autostart_wg_on_boot", methods=["POST"])
def enable_wg_at_boot():
    subprocess.run(["systemctl", "enable", "wg-quick@wg0"], text=True)

    return redirect(url_for("dashboard"))




def ufw_get_path():
    ufw_dirs = ["/bin", "/sbin", "/usr/bin", "/usr/sbin", "/usr/local/bin", "/usr/local/sbin"]

    for dir in ufw_dirs:
        path = os.path.join(dir, "ufw")
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    
    return None


def iptables_get_path():
    iptables_dirs = ["/sbin", "/usr/sbin", "/bin", "/usr/bin", "/usr/local/sbin", "/usr/local/bin"]

    for dir in iptables_dirs:
        path = os.path.join(dir, "iptables")
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    
    return None



def run_first_install_setup():
    # Create /etc/wireguard folder
    if not os.path.exists(wireguard_dir):
        os.mkdir(wireguard_dir)
    
    # Create config json
    if not os.path.isfile(full_config_file_path):
        with open(full_config_file_path, "w") as f:
            json.dump(default_config, f, indent=4)

    # Create wg0.conf
    if not os.path.isfile("/etc/wireguard/wg0.conf"):
        update_config(load_config())

    # Port forward
    update_sysctl()


def update_sysctl():
    try:
        with open(SYSCTL_CONF, "r") as file:
            lines = file.readlines()

        modified = False
        found = False

        for i in range(len(lines)):
            if "net.ipv4.ip_forward=" in lines[i]:  
                found = True
                if lines[i].strip().startswith("#"):  # If commented, uncomment
                    lines[i] = lines[i].lstrip("#")  # Remove leading #
                    modified = True
                if lines[i].strip() != "net.ipv4.ip_forward=1":  # Ensure it's set to 1
                    lines[i] = "net.ipv4.ip_forward=1\n"
                    modified = True

        if not found:  # If not found, append it
            lines.append("\nnet.ipv4.ip_forward=1\n")
            modified = True

        if modified:
            with open(SYSCTL_CONF, "w") as file:
                file.writelines(lines)
            os.system("sudo sysctl -p")  # Apply changes
            print("Updated sysctl.conf and applied changes.")
        else:
            print("No changes needed.")

    except Exception as e:
        print(f"Error: {e}")


def load_config():
    try:
        with open(full_config_file_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_config.copy()


def update_config(config_data):
    with open(full_config_file_path, "w") as f:
        json.dump(config_data, f, indent=4)

    peers = config_data.get("peers", [])
    server_priv_key = config_data.get("server", {}).get("PrivateKey", "")
    server_pub_key = config_data.get("server", {}).get("PublicKey", "")
    server_endpoint = config_data.get("server", {}).get("Endpoint", "")
    server_network_interface = config_data.get("server", {}).get("server_network_interface", "")


    iptables_path = iptables_get_path()
    wg_config_content = (
        f"[Interface]\n"
        f"Address = 10.11.0.1/24\n"
        f"SaveConfig = true\n"
        f"PostUp = {iptables_path} -A FORWARD -i %i -j ACCEPT; {iptables_path} -t nat -A POSTROUTING -o {server_network_interface} -j MASQUERADE\n"
        f"PostDown = {iptables_path} -D FORWARD -i %i -j ACCEPT; {iptables_path} -t nat -D POSTROUTING -o {server_network_interface} -j MASQUERADE\n"
        f"ListenPort = 51820\n"
        f"PrivateKey = {server_priv_key}\n"
    )

    for peer in peers:
        peer_id = peer["id"]
        peer_name = peer["name"]
        peer_pub_key = peer["PublicKey"]

        wg_config_content += (
            f"\n# {peer_name}\n"
            f"[Peer]\n"
            f"PublicKey = {peer_pub_key}\n"
            f"AllowedIPs = 10.11.0.{peer_id}/32\n"
        )

    subprocess.run(["systemctl", "stop", "wg-quick@wg0"], text=True)
    with open("/etc/wireguard/wg0.conf", "w") as f:
        f.write(wg_config_content)

    print("Server config updated")
    print("restarting wireguard service")
    subprocess.run(["systemctl", "start", "wg-quick@wg0"], text=True)



if __name__ == "__main__":
    run_first_install_setup()
    app.run(host="0.0.0.0", port=5050)
