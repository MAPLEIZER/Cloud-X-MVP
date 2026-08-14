"""Wazuh Syscollector-backed endpoint metric snapshots.

Syscollector exposes real inventory snapshots such as RAM usage and cumulative
interface counters. It does not provide a trustworthy live CPU-utilization or
GPU/VRAM metric, so those values are intentionally reported as unavailable.
"""

from datetime import datetime, timezone

from .wazuh import _affected_items


def _timestamp_ms():
    return datetime.now(timezone.utc).timestamp() * 1000


def _point(value, *, is_spike=False):
    return {
        "value": round(float(value), 3),
        "timestamp": _timestamp_ms(),
        "isSpike": bool(is_spike),
    }


def _scan_time(items):
    times = []
    for item in items:
        scan = item.get("scan") if isinstance(item, dict) else None
        if isinstance(scan, dict) and scan.get("time"):
            times.append(str(scan["time"]))
    return max(times) if times else None


class WazuhSystemMetricsProvider:
    """Resolve Cloud-X monitor targets to Wazuh agents and return snapshots."""

    def __init__(self, security_engine):
        self.security_engine = security_engine

    def _resolve_agent(self, target):
        normalized = target.rstrip(".").lower()
        for agent in self.security_engine.agents(limit=500):
            candidates = {
                str(agent.get("id") or "").lower(),
                str(agent.get("name") or "").rstrip(".").lower(),
                str(agent.get("ip") or "").lower(),
            }
            if normalized in candidates:
                return agent
        return None

    def metrics_for_target(self, target):
        agent = self._resolve_agent(target)
        if agent is None:
            return None

        agent_id = agent["id"]
        hardware_items = _affected_items(
            self.security_engine.server_client.get(
                f"/syscollector/{agent_id}/hardware", query={"limit": 1}
            )
        )
        interface_items = _affected_items(
            self.security_engine.server_client.get(
                f"/syscollector/{agent_id}/netiface", query={"limit": 500}
            )
        )

        hardware = hardware_items[0] if hardware_items else {}
        ram = hardware.get("ram") if isinstance(hardware.get("ram"), dict) else {}
        cpu = hardware.get("cpu") if isinstance(hardware.get("cpu"), dict) else {}

        try:
            memory_percent = float(ram["usage"]) if ram.get("usage") is not None else None
        except (TypeError, ValueError):
            memory_percent = None

        rx_bytes = 0
        tx_bytes = 0
        for interface in interface_items:
            if not isinstance(interface, dict):
                continue
            rx = interface.get("rx") if isinstance(interface.get("rx"), dict) else {}
            tx = interface.get("tx") if isinstance(interface.get("tx"), dict) else {}
            try:
                rx_bytes += int(rx.get("bytes", 0) or 0)
            except (TypeError, ValueError):
                pass
            try:
                tx_bytes += int(tx.get("bytes", 0) or 0)
            except (TypeError, ValueError):
                pass

        collected_at = _scan_time(hardware_items + interface_items)
        return {
            "source": "wazuh_syscollector",
            "mode": "agent",
            "target": target,
            "is_agentless": False,
            "is_agent_based": True,
            "collected_at": collected_at,
            "agent": {
                "id": agent_id,
                "name": agent.get("name"),
                "ip": agent.get("ip"),
                "status": agent.get("status"),
            },
            "cpu": [],
            "memory": (
                [_point(memory_percent, is_spike=memory_percent > 80)]
                if memory_percent is not None
                else []
            ),
            "disk": [],
            "network": [],
            "latency": [],
            "network_rx_mbps": None,
            "network_tx_mbps": None,
            "network_unit": None,
            "network_counters": {
                "rx_bytes": rx_bytes,
                "tx_bytes": tx_bytes,
            },
            "hardware": {
                "cpu_name": cpu.get("name"),
                "cpu_cores": cpu.get("cores"),
                "cpu_mhz": cpu.get("mhz"),
                "ram_total": ram.get("total"),
                "ram_free": ram.get("free"),
            },
            "availability": {
                "cpu": False,
                "memory": memory_percent is not None,
                "disk": False,
                "network_throughput": False,
                "latency": False,
                "gpu": False,
                "vram": False,
            },
            "note": (
                "Wazuh Syscollector snapshot. RAM usage and network byte counters are "
                "collected endpoint data; live CPU/GPU/VRAM and throughput are not "
                "reported because Syscollector does not provide those live values."
            ),
        }
