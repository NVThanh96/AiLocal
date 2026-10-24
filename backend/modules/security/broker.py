import os
import socket
import ipaddress
from pathlib import Path
from urllib.parse import urlparse
from typing import Tuple

class SecurityBroker:
    """
    Execution Broker and Security Sentinel:
    - Enforces strict workspace boundary isolation (prevents path traversal).
    - Enforces SSRF prevention on network fetch.
    """

    @staticmethod
    def validate_workspace_path(target_path: str | Path, workspace_root: str | Path) -> Tuple[bool, Path]:
        """
        Validates that target_path resolves strictly within workspace_root.
        Returns (is_valid, resolved_path).
        """
        try:
            root = Path(workspace_root).resolve()
            if not root.exists() or not root.is_dir():
                return False, Path(target_path)
            
            clean_str = str(target_path).strip()
            target = Path(clean_str)
            if target.is_absolute():
                resolved = target.resolve()
            else:
                clean_rel = clean_str.replace("\\", "/").lstrip("/")
                resolved = (root / clean_rel).resolve()
            
            # Check boundary: must be root or a descendant of root
            is_inside = (resolved == root) or (root in resolved.parents)
            return is_inside, resolved
        except Exception:
            return False, Path(target_path)

    @staticmethod
    def validate_network_url(url: str) -> Tuple[bool, str]:
        """
        Validates that the URL uses HTTP/HTTPS and does NOT target localhost,
        loopback, private subnets, link-local, or cloud metadata endpoints.
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme.lower() not in ("http", "https"):
                return False, f"Unsupported scheme: {parsed.scheme}. Only HTTP/HTTPS permitted."

            hostname = parsed.hostname
            if not hostname:
                return False, "Missing hostname in URL."

            # Block literal localhost / loopback names
            if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
                return False, "Targeting loopback addresses is forbidden (SSRF protection)."

            # Check if hostname is an IP literal
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved:
                    return False, f"Targeting private/reserved IP ({ip}) is blocked."
            except ValueError:
                # Hostname is a domain name. Resolve DNS to verify destination IP.
                try:
                    resolved_ip_str = socket.gethostbyname(hostname)
                    resolved_ip = ipaddress.ip_address(resolved_ip_str)
                    if resolved_ip.is_loopback or resolved_ip.is_private or resolved_ip.is_link_local or resolved_ip.is_reserved:
                        return False, f"Resolved IP ({resolved_ip}) is private/internal."
                except socket.gaierror:
                    # DNS resolution failure, will fail safely at fetch time
                    pass

            return True, "URL is safe for external request."
        except Exception as e:
            return False, str(e)
