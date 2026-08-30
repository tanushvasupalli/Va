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
    Scans the local area network (LAN) and ARP cache to discover active devices.
    Returns list of discovered IP addresses, MAC addresses, and hostnames.
    """
    devices = []
    
    # 1. Read system ARP table
    try:
        arp_out = ""
        if sys.platform == "win32":
            proc = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
            arp_out = proc.stdout
        else:
            # Linux / Android Termux
            try:
                with open("/proc/net/arp", "r") as f:
                    arp_out = f.read()
            except Exception:
                proc = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
                arp_out = proc.stdout

        # Parse ARP output for IPs and MACs
        lines = arp_out.splitlines()
        for line in lines:
            ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
            mac_match = re.search(r"([0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2})", line)
            if ip_match and mac_match:
                ip = ip_match.group(1)
                mac = mac_match.group(1).upper().replace("-", ":")
                if not ip.startswith("255.") and not ip.startswith("224.") and not ip.endswith(".255"):
                    devices.append({"ip": ip, "mac": mac})
    except Exception:
        pass

    # 2. Multi-threaded quick sweep on common subnet if few devices found
    if len(devices) < 2:
        try:
            # Find local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            prefix = ".".join(local_ip.split(".")[:3])

            def check_ip(i):
                target = f"{prefix}.{i}"
                try:
                    s_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s_sock.settimeout(0.15)
                    # Check common port (80, 443, 8080, 53, 22)
                    res = s_sock.connect_ex((target, 80))
                    s_sock.close()
                    if res == 0:
                        devices.append({"ip": target, "mac": "Unknown"})
                except Exception:
                    pass

            with ThreadPoolExecutor(max_workers=30) as executor:
                executor.map(check_ip, range(1, 40))
        except Exception:
            pass

    if not devices:
        return "No devices discovered on local network cache. Ensure your phone or PC is connected to Wi-Fi."

    # Resolve hostnames for found IPs
    results = []
    seen = set()
    for d in devices:
        ip = d["ip"]
        if ip in seen:
            continue
        seen.add(ip)
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except Exception:
            hostname = "Generic Network Device"
        results.append(f"• {ip} - {hostname} (MAC: {d['mac']})")

    return f"Discovered {len(results)} active device(s) on local network:\n" + "\n".join(results)

def send_network_http_request(url: str, method: str = "GET", json_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Sends an HTTP GET or POST request to a local smart device, router, or IoT endpoint.
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"http://{url}"
    try:
        if method.upper() == "POST":
            res = requests.post(url, json=json_data or {}, timeout=8)
        else:
            res = requests.get(url, params=json_data, timeout=8)
        return f"Response from {url} (HTTP {res.status_code}):\n{res.text[:300]}"
    except Exception as e:
        return f"Failed to send HTTP request to {url}: {e}"
