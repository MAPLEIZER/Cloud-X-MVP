from flask import Flask, request, jsonify, g
import logging
import uuid
import threading
import json
import os
from datetime import datetime, timezone

from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import psutil
from ping3 import ping as ping_host
from auth import clerk_authorized
from deployer import AgentDeployer
from scanners import network_scanners as scanners
from security_utils import (
    is_valid_host,
    is_valid_identifier,
    is_valid_known_hosts_line,
    is_valid_scan_target,
    parse_csv,
    parse_origin_csv,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _positive_int_env(name, default):
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < 1:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_JWT_KEY = os.getenv("CLERK_JWT_KEY")
CLERK_AUTHORIZED_PARTIES = parse_origin_csv(os.getenv("CLERK_AUTHORIZED_PARTIES"))
CLERK_ALLOWED_USER_IDS = frozenset(parse_csv(os.getenv("CLERK_ALLOWED_USER_IDS")))

if not (CLERK_SECRET_KEY or CLERK_JWT_KEY):
    raise RuntimeError(
        "Cloud-X backend authentication is not configured. Set CLERK_SECRET_KEY "
        "or CLERK_JWT_KEY."
    )
if not CLERK_AUTHORIZED_PARTIES:
    raise RuntimeError(
        "CLERK_AUTHORIZED_PARTIES must contain at least one trusted frontend origin."
    )
if not CLERK_ALLOWED_USER_IDS:
    raise RuntimeError(
        "CLERK_ALLOWED_USER_IDS must contain at least one authorized Clerk user ID."
    )

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
deployer = AgentDeployer(SCRIPTS_DIR)

app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL must be configured with a PostgreSQL connection URL."
    )
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
app.config["CLERK_SECRET_KEY"] = CLERK_SECRET_KEY
app.config["CLERK_JWT_KEY"] = CLERK_JWT_KEY
app.config["CLERK_AUTHORIZED_PARTIES"] = CLERK_AUTHORIZED_PARTIES
app.config["CLERK_ALLOWED_USER_IDS"] = CLERK_ALLOWED_USER_IDS
app.config["MAX_CONCURRENT_SCANS"] = _positive_int_env("MAX_CONCURRENT_SCANS", 4)

db = SQLAlchemy(app)

CORS(
    app,
    resources={r"/api/*": {"origins": CLERK_AUTHORIZED_PARTIES}},
    allow_headers=["Authorization", "Content-Type"],
    methods=["GET", "POST", "DELETE", "OPTIONS"],
    supports_credentials=False,
    max_age=600,
)

active_scans = {}
scan_state_lock = threading.Lock()


class Scan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    tool = db.Column(db.String(50), nullable=False, default="nmap")
    target = db.Column(db.String(255), nullable=False)
    scan_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="submitted")
    progress = db.Column(db.Integer, default=0)
    results = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Scan {self.job_id}>"


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "DENY")
    return response


def _json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data


def _set_active_process(job_id, process):
    with scan_state_lock:
        active_scans[job_id] = process


def _remove_active_process(job_id):
    with scan_state_lock:
        active_scans.pop(job_id, None)


def _terminate_scan_process(job_id):
    with scan_state_lock:
        proc = active_scans.get(job_id)

    if proc is None:
        return False

    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        logger.exception("Failed to terminate scan process %s", job_id)
        try:
            proc.kill()
        except Exception:
            logger.exception("Failed to kill scan process %s", job_id)
        raise
    finally:
        _remove_active_process(job_id)

    return True


def run_scan_in_background(app_instance, job_id, tool, target, scan_type, port=None):
    with app_instance.app_context():
        try:
            scan_generator = scanners.run_scan(tool, target, scan_type, port=port)

            process_update = next(scan_generator)
            if process_update["type"] == "process":
                _set_active_process(job_id, process_update["value"])
            else:
                raise RuntimeError("Scanner did not yield process object first")

            scan = Scan.query.filter_by(job_id=job_id).first()
            if scan:
                scan.status = "running"
                db.session.commit()

            for update in scan_generator:
                scan = Scan.query.filter_by(job_id=job_id).first()
                if not scan:
                    logger.warning("Scan %s was deleted while running", job_id)
                    return

                if update["type"] == "progress":
                    scan.progress = update["value"]
                    db.session.commit()
                elif update["type"] == "result":
                    scan.results = json.dumps(update["value"])
                    scan.status = "completed"
                    scan.progress = 100
                    db.session.commit()
                    break
                elif update["type"] == "error":
                    scan.status = "failed"
                    scan.results = json.dumps({"error": update["value"]})
                    db.session.commit()
                    break

        except StopIteration:
            logger.exception("Scanner terminated before yielding a process for %s", job_id)
            scan = Scan.query.filter_by(job_id=job_id).first()
            if scan:
                scan.status = "failed"
                scan.results = json.dumps({"error": "Scanner failed to start."})
                db.session.commit()
        except Exception:
            logger.exception("Error in background scan %s", job_id)
            scan = Scan.query.filter_by(job_id=job_id).first()
            if scan:
                scan.status = "failed"
                scan.progress = 0
                scan.results = json.dumps({"error": "The scan failed internally."})
                db.session.commit()
        finally:
            _remove_active_process(job_id)


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify({"status": "pong"}), 200


@app.route("/api/sync-status", methods=["GET"])
@clerk_authorized
def sync_status():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    heartbeat_file_path = os.path.join(base_dir, "sync_heartbeat.json")
    sync_active_threshold_seconds = 30

    if not os.path.exists(heartbeat_file_path):
        return (
            jsonify({"status": "inactive", "reason": "Heartbeat file not found."}),
            200,
        )

    try:
        with open(heartbeat_file_path, "r", encoding="utf-8") as heartbeat_file:
            data = json.load(heartbeat_file)

        last_heartbeat_str = data.get("timestamp")
        if not last_heartbeat_str:
            return (
                jsonify({"status": "inactive", "reason": "Invalid heartbeat format."}),
                200,
            )

        last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
        now = datetime.now(timezone.utc)

        if last_heartbeat.tzinfo is None:
            last_heartbeat = last_heartbeat.replace(tzinfo=timezone.utc)

        time_difference = (now - last_heartbeat).total_seconds()

        if time_difference <= sync_active_threshold_seconds:
            return jsonify({"status": "active"}), 200

        return (
            jsonify(
                {
                    "status": "inactive",
                    "reason": f"Heartbeat is stale. Last seen {time_difference:.0f} seconds ago.",
                }
            ),
            200,
        )

    except (json.JSONDecodeError, OSError):
        logger.exception("Error reading sync heartbeat file")
        return jsonify({"status": "error", "reason": "Unable to read heartbeat."}), 500


@app.route("/api/scans", methods=["POST"])
@clerk_authorized
def start_scan():
    data = _json_body()
    if data is None:
        return jsonify({"error": "A JSON object is required"}), 400

    target = data.get("target")
    tool = data.get("tool", "nmap")
    scan_type = data.get("scan_type", "default")
    port = data.get("port")

    if not is_valid_scan_target(target):
        return (
            jsonify(
                {
                    "error": "Target must be a valid hostname, IP address, or IP network."
                }
            ),
            400,
        )

    allowed_scan_types = {
        "nmap": {"default", "quick", "intense", "tcp", "udp"},
        "zmap": {"tcp_syn", "icmp_echo"},
        "masscan": {"tcp_scan", "udp_scan", "ping_scan"},
    }
    if tool not in allowed_scan_types:
        return jsonify({"error": "Unsupported scanning tool"}), 400
    if scan_type not in allowed_scan_types[tool]:
        return jsonify({"error": "Unsupported scan type for selected tool"}), 400

    if port is not None:
        try:
            port = int(port)
            if port < 1 or port > 65535:
                raise ValueError
        except (TypeError, ValueError):
            return (
                jsonify(
                    {
                        "error": "Port must be an integer between 1 and 65535 when provided."
                    }
                ),
                400,
            )

    if tool in {"zmap", "masscan"} and scan_type not in {"icmp_echo", "ping_scan"}:
        if port is None:
            return jsonify({"error": "A port is required for this scan type"}), 400

    with scan_state_lock:
        active_count = Scan.query.filter(
            Scan.status.in_(["submitted", "running"])
        ).count()
        if active_count >= app.config["MAX_CONCURRENT_SCANS"]:
            return jsonify({"error": "Maximum concurrent scans reached"}), 429

        new_scan = Scan(
            tool=tool,
            target=target,
            scan_type=scan_type,
            status="submitted",
        )
        db.session.add(new_scan)
        db.session.commit()

        thread = threading.Thread(
            target=run_scan_in_background,
            args=(app, new_scan.job_id, tool, target, scan_type, port),
            daemon=True,
        )
        thread.start()

    logger.info("User %s started scan %s", g.user_id, new_scan.job_id)
    return jsonify({"job_id": new_scan.job_id, "status": "submitted"}), 202


@app.route("/api/scans", methods=["GET"])
@clerk_authorized
def get_scans():
    scans = Scan.query.order_by(Scan.created_at.desc()).limit(500).all()
    return jsonify(
        [
            {
                "job_id": scan.job_id,
                "tool": scan.tool,
                "target": scan.target,
                "scan_type": scan.scan_type,
                "status": scan.status,
                "progress": scan.progress,
                "results": json.loads(scan.results) if scan.results else None,
                "created_at": scan.created_at.isoformat(),
            }
            for scan in scans
        ]
    )


@app.route("/api/scans/<job_id>/stop", methods=["POST"])
@clerk_authorized
def stop_scan(job_id):
    if not _terminate_scan_process(job_id):
        return jsonify({"error": "Scan not found or already completed"}), 404

    scan = Scan.query.filter_by(job_id=job_id).first()
    if scan:
        scan.status = "stopped"
        db.session.commit()

    logger.info("User %s stopped scan %s", g.user_id, job_id)
    return jsonify({"message": "Scan stopped successfully"}), 200


@app.route("/api/scans/<job_id>", methods=["GET"])
@clerk_authorized
def get_scan_status(job_id):
    scan = Scan.query.filter_by(job_id=job_id).first_or_404()

    response = {
        "job_id": scan.job_id,
        "tool": scan.tool,
        "target": scan.target,
        "scan_type": scan.scan_type,
        "status": scan.status,
        "progress": scan.progress,
        "created_at": scan.created_at.isoformat(),
        "results": json.loads(scan.results) if scan.results else None,
    }
    return jsonify(response)


@app.route("/api/scans/<job_id>", methods=["DELETE"])
@clerk_authorized
def delete_scan(job_id):
    scan = Scan.query.filter_by(job_id=job_id).first()
    if not scan:
        return jsonify({"error": "Scan not found"}), 404

    try:
        with scan_state_lock:
            proc = active_scans.get(job_id)
        if proc is not None:
            _terminate_scan_process(job_id)

        db.session.delete(scan)
        db.session.commit()
        logger.info("User %s deleted scan %s", g.user_id, job_id)
        return jsonify({"message": "Scan deleted successfully"}), 200
    except Exception:
        db.session.rollback()
        logger.exception("Failed to delete scan %s", job_id)
        return jsonify({"error": "Failed to delete scan"}), 500


@app.route("/api/system-monitor", methods=["GET"])
@clerk_authorized
def system_monitor():
    target = request.args.get("target", "localhost")

    if not is_valid_host(target):
        return jsonify({"error": "Invalid monitoring target"}), 400

    is_local = target in {"localhost", "127.0.0.1", "::1"}

    data = {"cpu": [], "memory": [], "disk": [], "network": []}

    if is_local:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent

        data["cpu"] = [
            {
                "value": cpu,
                "timestamp": datetime.now().timestamp() * 1000,
                "isSpike": cpu > 80,
            }
        ]
        data["memory"] = [
            {
                "value": mem,
                "timestamp": datetime.now().timestamp() * 1000,
                "isSpike": mem > 80,
            }
        ]
        data["disk"] = [
            {
                "value": disk,
                "timestamp": datetime.now().timestamp() * 1000,
                "isSpike": disk > 90,
            }
        ]
        return jsonify(data)

    try:
        latency = ping_host(target, unit="ms", timeout=2)
        if latency is None:
            latency = 0
    except Exception:
        logger.info("Ping failed for monitoring target %s", target)
        latency = 0

    return jsonify(
        {
            "network": [
                {"value": latency, "timestamp": datetime.now().timestamp() * 1000}
            ],
            "is_agentless": True,
        }
    )


@app.route("/api/deploy/agent", methods=["POST"])
@clerk_authorized
def deploy_agent():
    data = _json_body()
    if data is None:
        return jsonify({"error": "A JSON object is required"}), 400

    target = data.get("target")
    os_type = data.get("os_type")
    username = data.get("username")
    password = data.get("password")
    agent_name = data.get("agent_name", f"agent-{target}")
    group = data.get("group", "default")
    manager_ip = data.get("manager_ip", request.host.split(":")[0])

    if not all(
        isinstance(value, str) and value
        for value in (target, os_type, username, password, manager_ip)
    ):
        return jsonify({"error": "Missing required deployment fields"}), 400

    if not is_valid_host(target) or not is_valid_host(manager_ip):
        return jsonify({"error": "Invalid deployment host"}), 400
    if not is_valid_identifier(agent_name) or not is_valid_identifier(group):
        return jsonify({"error": "Invalid agent name or group"}), 400
    if len(username) > 128 or "\x00" in username or len(password) > 4096:
        return jsonify({"error": "Invalid credentials format"}), 400

    if os_type == "linux":
        result = deployer.deploy_linux(
            target, username, password, manager_ip, agent_name, group
        )
    elif os_type == "windows":
        result = deployer.deploy_windows(
            target, username, password, manager_ip, agent_name, group
        )
    elif os_type == "mac":
        result = deployer.deploy_mac(
            target, username, password, manager_ip, agent_name, group
        )
    else:
        return jsonify({"error": "Invalid OS type"}), 400

    if result["status"] == "success":
        logger.info("User %s deployed agent to %s", g.user_id, target)
        return jsonify({"message": "Deployment successful"})

    return (
        jsonify(
            {
                "error": "Deployment failed",
                "reason": "An internal error occurred during deployment.",
            }
        ),
        500,
    )


@app.route("/api/deploy/node", methods=["POST"])
@clerk_authorized
def deploy_node():
    logger.warning(
        "User %s attempted disabled remote node deployment",
        g.user_id,
    )
    return (
        jsonify(
            {
                "error": "Remote node deployment is disabled.",
                "reason": (
                    "The previous implementation launched an unauthenticated "
                    "placeholder HTTP server. Deploy backend nodes with the "
                    "hardened install_backend.sh workflow instead."
                ),
            }
        ),
        501,
    )


def cleanup_stale_scans():
    stale_scans = Scan.query.filter(Scan.status.in_(["running", "submitted"])).all()
    for scan in stale_scans:
        scan.status = "failed"
        scan.results = json.dumps(
            {"error": "Scan was interrupted by a server restart."}
        )
    if stale_scans:
        db.session.commit()
        logger.info("Cleaned up %s stale scans", len(stale_scans))


if __name__ == "__main__":
    with app.app_context():
        cleanup_stale_scans()

    app.run(host="0.0.0.0", debug=False, port=5001)
