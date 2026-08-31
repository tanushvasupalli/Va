import re
import socket
import struct
import subprocess
import threading
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, List
import requests

import config

def _clean_mac(mac: str) -> bytes:
    """Parses MAC address string into 6 bytes."""
    cleaned = re.sub(r"[^0-9a-fA-F]", "", mac)
    if len(cleaned) != 12:
        raise ValueError(f"Invalid MAC address format: {mac}")
    return bytes.fromhex(cleaned)

def wake_pc_via_wol(mac_address: Optional[str] = None) -> str:
    """
    Sends a Wake-on-LAN (WOL) magic packet across the network to power on a sleeping PC.
    
    Args:
        mac_address: Target PC's MAC address (e.g. 'AA:BB:CC:DD:EE:FF').
                     Defaults to config.PC_MAC_ADDRESS.
    """
    target_mac = mac_address or getattr(config, "PC_MAC_ADDRESS", "")
    if not target_mac:
        return "Please provide a MAC address or set PC_MAC_ADDRESS in your .env configuration."

    try:
        mac_bytes = _clean_mac(target_mac)
        # Magic packet = 6 bytes of 0xFF followed by 16 repetitions of target MAC
        magic_packet = b"\xff" * 6 + mac_bytes * 16

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, ("255.255.255.255", 9))
            sock.sendto(magic_packet, ("255.255.255.255", 7))
        return f"Wake-on-LAN magic packet sent to MAC: {target_mac}. Your PC should be waking up now."
    except Exception as e:
        return f"Failed to send Wake-on-LAN packet: {e}"

def ping_network_device(host: str) -> str:
    """
    Pings a network device or IP to check if it is online and responsive.
    """
    if not host or not host.strip():
        return "Please specify a hostname or IP address to ping."
    
    clean_host = host.strip()
    param = "-n" if sys.platform == "win32" else "-c"
    timeout_param = "-w" if sys.platform == "win32" else "-W"
    timeout_val = "1000" if sys.platform == "win32" else "1"

    try:
        proc = subprocess.run(
            ["ping", param, "1", timeout_param, timeout_val, clean_host],
            capture_output=True,
            text=True,
            timeout=5
        )
        if proc.returncode == 0:
            try:
                resolved = socket.gethostbyaddr(clean_host)[0]
                host_tag = f" ({resolved})"
            except Exception:
                host_tag = ""
            return f"Device {clean_host}{host_tag} is ONLINE and responding."
        return f"Device {clean_host} is OFFLINE or not responding to ICMP ping."
    except Exception as e:
        return f"Ping check error for {clean_host}: {e}"

def scan_local_network(subnet: Optional[str] = None) -> str:
    """
    Scans the local area network (LAN) across the entire /24 subnet (1..254) and ARP table.
    Discovers active devices, resolves hostnames, and fingerprints open services (e.g. PC Companion, Router, Home Assistant).
    """
    devices_dict: Dict[str, Dict[str, Any]] = {}
    
    # 1. Determine local subnet prefix
    prefix = "192.168.1"
    if subnet and "/" in subnet:
        prefix = subnet.split("/")[0].rsplit(".", 1)[0]
    elif subnet and len(subnet.split(".")) >= 3:
        prefix = ".".join(subnet.split(".")[:3])
    else:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            prefix = ".".join(local_ip.split(".")[:3])
        except Exception:
            prefix = "192.168.1"

    # Common service ports to probe for instant discovery
    PROBE_PORTS = [80, 8085, 443, 8000, 22, 445, 8123, 8080, 53, 8008, 554, 3389]
    PORT_NAMES = {
        80: "HTTP Web/Router",
        443: "HTTPS Web",
        8085: "Wednesday PC Companion",
        8000: "Wednesday Web UI / FastAPI",
        22: "SSH Server",
        445: "Windows SMB / File Sharing",
        8123: "Home Assistant",
        8080: "HTTP Alt / Web Portal",
        53: "DNS / Router Gateway",
        8008: "Google Cast / Smart TV",
        554: "RTSP IP Camera",
        3389: "Windows Remote Desktop (RDP)"
    }

    def probe_host(host_ip: str):
        active_ports = []
        for port in PROBE_PORTS:
            try:
                s_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s_sock.settimeout(0.12)
                res = s_sock.connect_ex((host_ip, port))
                s_sock.close()
                if res == 0:
                    active_ports.append(port)
            except Exception:
                pass
        if active_ports:
            devices_dict[host_ip] = {"ports": active_ports, "mac": "Unknown", "hostname": ""}

    # 2. Multi-threaded full subnet sweep (1 to 254)
    with ThreadPoolExecutor(max_workers=60) as executor:
        executor.map(probe_host, [f"{prefix}.{i}" for i in range(1, 255)])

    # 3. Read system ARP table to find MAC addresses and any additional IP entries
    try:
        arp_out = ""
        if sys.platform == "win32":
            proc = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=4)
            arp_out = proc.stdout
        else:
            try:
                with open("/proc/net/arp", "r") as f:
                    arp_out = f.read()
            except Exception:
                proc = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=4)
                arp_out = proc.stdout

        lines = arp_out.splitlines()
        for line in lines:
            ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
            mac_match = re.search(r"([0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2})", line)
            if ip_match and mac_match:
                ip = ip_match.group(1)
                mac = mac_match.group(1).upper().replace("-", ":")
                if not ip.startswith("255.") and not ip.startswith("224.") and not ip.endswith(".255") and mac != "00:00:00:00:00:00":
                    if ip in devices_dict:
                        devices_dict[ip]["mac"] = mac
                    elif ip.startswith(prefix):
                        devices_dict[ip] = {"ports": [], "mac": mac, "hostname": ""}
    except Exception:
        pass

    if not devices_dict:
        return f"No active devices found on subnet {prefix}.0/24. Ensure Wi-Fi is connected."

    # 4. Resolve hostnames and format discovered devices
    results = []
    # Sort IPs numerically
    sorted_ips = sorted(devices_dict.keys(), key=lambda ip: [int(p) for p in ip.split(".")])

    for ip in sorted_ips:
        info = devices_dict[ip]
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except Exception:
            hostname = "Network Host"

        services = [PORT_NAMES.get(p, f"Port {p}") for p in info.get("ports", [])]
        services_str = f" | Services: {', '.join(services)}" if services else ""
        mac_str = f" | MAC: {info['mac']}" if info['mac'] != "Unknown" else ""
        
        results.append(f"• `{ip}` - *{hostname}*{mac_str}{services_str}")

    return f"🌐 *Discovered {len(results)} active device(s) on `{prefix}.0/24`:*\n\n" + "\n".join(results)

def port_scan_device(host: str, ports: Optional[str] = None) -> str:
    """
    Scans a specific device on the network for open ports and services.
    
    Args:
        host: Target IP address or hostname.
        ports: Optional comma-separated list of ports (e.g. '80,443,8085,8000,22,3389').
               Defaults to standard common service ports.
    """
    if not host or not host.strip():
        return "Please specify a target IP address or hostname to scan."
    
    clean_host = host.strip()
    if ports:
        try:
            port_list = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
        except Exception:
            port_list = [21, 22, 23, 53, 80, 443, 445, 554, 1883, 3389, 5000, 8000, 8008, 8080, 8085, 8123, 9000]
    else:
        port_list = [21, 22, 23, 53, 80, 443, 445, 554, 1883, 3389, 5000, 8000, 8008, 8080, 8085, 8123, 9000]

    open_ports = []
    def check_single_port(port: int):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.25)
            res = s.connect_ex((clean_host, port))
            s.close()
            if res == 0:
                open_ports.append(port)
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=30) as executor:
        executor.map(check_single_port, port_list)

    if not open_ports:
        return f"No common open ports detected on device `{clean_host}`."

    open_ports.sort()
    port_descriptions = {
        21: "FTP",
        22: "SSH",
        23: "Telnet",
        53: "DNS",
        80: "HTTP Web",
        443: "HTTPS",
        445: "SMB / Windows File Sharing",
        554: "RTSP Camera Video Stream",
        1883: "MQTT Smart Home Broker",
        3389: "RDP Remote Desktop",
        5000: "UPnP / Synology / Flask",
        8000: "Wednesday Web UI / FastAPI",
        8008: "Google Cast / TV",
        8080: "HTTP Alternate Web",
        8085: "Wednesday PC Companion Agent",
        8123: "Home Assistant",
        9000: "Portainer / Media Server"
    }
    
    lines = [f"🔍 *Open Ports on `{clean_host}`:*"]
    for p in open_ports:
        desc = port_descriptions.get(p, "Custom Service")
        lines.append(f"• Port `{p}`: {desc}")
    return "\n".join(lines)

def send_network_http_request(
    url: str,
    method: str = "GET",
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 8
) -> str:
    """
    Sends an HTTP request (GET, POST, PUT, DELETE) to a local smart device, router, or IoT endpoint.
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"http://{url}"
    try:
        m = method.upper().strip()
        hdrs = headers or {}
        if m == "POST":
            res = requests.post(url, json=json_data or {}, headers=hdrs, timeout=timeout)
        elif m == "PUT":
            res = requests.put(url, json=json_data or {}, headers=hdrs, timeout=timeout)
        elif m == "DELETE":
            res = requests.delete(url, json=json_data or {}, headers=hdrs, timeout=timeout)
        else:
            res = requests.get(url, params=json_data, headers=hdrs, timeout=timeout)
        return f"Response from {url} (HTTP {res.status_code}):\n{res.text[:400]}"
    except Exception as e:
        return f"Failed to send HTTP {method} to {url}: {e}"
