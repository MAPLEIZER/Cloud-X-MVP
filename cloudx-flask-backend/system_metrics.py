"""Real system-monitor metrics with explicit source/provenance metadata.

The legacy monitor UI historically filled missing data with generated values. This
module provides a production view that only returns measured values. Local
metrics come from psutil, a configured provider can return agent snapshots, and
unmanaged remote hosts fall back to clearly-labelled ping latency only.
"""

import logging
import time
from datetime import datetime, timezone

import psutil
from flask import jsonify, request
from ping3 import ping as ping_host

from auth import clerk_authorized
from security_utils import is_valid_host

logger = logging.getLogger(__name__)


def _timestamp_ms():
    return datetime.now(timezone.utc).timestamp() * 1000


def _point(value, *, is_spike=False):
    return {
        "value": round(float(value), 3),
        "timestamp": _timestamp_ms(),
        "isSpike": bool(is_spike),
    }


def _local_network_throughput(sample_seconds=0.2):
    """Measure aggregate host throughput from real counter deltas."""

    before = psutil.net_io_counters()
    started = time.monotonic()
    time.sleep(sample_seconds)
    after = psutil.net_io_counters()
    elapsed = max(time.monotonic() - started, 0.001)

    rx_mbps = max(0, after.bytes_recv - before.bytes_recv) / elapsed / 1024 / 1024
    tx_mbps = max(0, after.bytes_sent - before.bytes_sent) / elapsed / 1024 / 1024
    return rx_mbps, tx_mbps


def _local_metrics(target):
    cpu_percent = psutil.cpu_percent(interval=0.2)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    rx_mbps, tx_mbps = _local_network_throughput()
    total_mbps = rx_mbps + tx_mbps

    return {
        "source": "local_psutil",
        "mode": "local",
        "target": target,
        "is_agentless": False,
        "is_agent_based": False,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "cpu": [_point(cpu_percent, is_spike=cpu_percent > 80)],
        "memory": [_point(memory.percent, is_spike=memory.percent > 80)],
        "disk": [_point(disk.percent, is_spike=disk.percent > 90)],
        "network": [_point(total_mbps)],
        "latency": [],
        "network_rx_mbps": round(rx_mbps, 3),
        "network_tx_mbps": round(tx_mbps, 3),
        "network_unit": "MiB/s",
        "availability": {
            "cpu": True,
            "memory": True,
            "disk": True,
            "network_throughput": True,
            "latency": False,
            "gpu": False,
            "vram": False,
        },
        "note": "Local CPU, memory, disk and network throughput are measured on demand.",
    }


def _agentless_metrics(target):
    try:
        latency = ping_host(target, unit="ms", timeout=2)
    except Exception:
        latency = None

    return {
        "source": "agentless_ping",
        "mode": "agentless",
        "target": target,
        "is_agentless": True,
        "is_agent_based": False,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "cpu": [],
        "memory": [],
        "disk": [],
        "network": [],
        "latency": [_point(latency)] if latency is not None else [],
        "network_rx_mbps": None,
        "network_tx_mbps": None,
        "network_unit": None,
        "availability": {
            "cpu": False,
            "memory": False,
            "disk": False,
            "network_throughput": False,
            "latency": latency is not None,
            "gpu": False,
            "vram": False,
        },
        "note": "No managed endpoint matched this target; only measured ICMP latency is available.",
    }


def create_system_monitor_view(metrics_provider=None):
    """Create the authenticated production system-monitor view.

    ``metrics_provider`` is provider-neutral from this module's perspective. It
    may return a managed endpoint snapshot for a target or ``None`` when the
    target is not managed by that provider.
    """

    @clerk_authorized
    def system_monitor_view():
        target = request.args.get("target", "localhost")
        if not is_valid_host(target):
            return jsonify({"error": "Invalid monitoring target"}), 400

        if target in {"localhost", "127.0.0.1", "::1"}:
            return jsonify(_local_metrics(target))

        if metrics_provider is not None:
            try:
                snapshot = metrics_provider.metrics_for_target(target)
            except Exception:
                logger.exception("Managed endpoint metrics provider failed for %s", target)
                return (
                    jsonify(
                        {
                            "error": "Managed endpoint metrics are temporarily unavailable",
                            "source": "managed_provider_error",
                            "mode": "agent",
                        }
                    ),
                    502,
                )
            if snapshot is not None:
                return jsonify(snapshot)

        return jsonify(_agentless_metrics(target))

    return system_monitor_view
