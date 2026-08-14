import json
import logging
from datetime import datetime

from rq import Worker

from app import Scan, app, db
from scan_queue import clear_cancel_request, is_cancel_requested
from scanners import network_scanners as scanners

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {"completed", "failed", "stopped"}


def _load_scan(job_id):
    return Scan.query.filter_by(job_id=job_id).first()


def _save_scan(job_id, *, status=None, progress=None, results=None):
    with app.app_context():
        scan = _load_scan(job_id)
        if scan is None:
            return None
        if status is not None:
            scan.status = status
        if progress is not None:
            scan.progress = max(0, min(int(progress), 100))
        if results is not None:
            scan.results = json.dumps(results)
        scan.updated_at = datetime.utcnow()
        db.session.commit()
        return scan.status


def _finish_stopped(job_id, reason="Scan was stopped by an operator."):
    return _save_scan(
        job_id,
        status="stopped",
        results={"error": reason, "code": "scan_stopped"},
    )


def execute_scan(job_id, tool, target, scan_type="default", port=None):
    """RQ job entry point. All durable scan state is persisted in PostgreSQL."""

    with app.app_context():
        scan = _load_scan(job_id)
        if scan is None:
            logger.warning("Ignoring queue job %s because its Scan row no longer exists", job_id)
            return {"status": "missing"}
        if scan.status in _TERMINAL_STATUSES:
            return {"status": scan.status}
        if is_cancel_requested(job_id):
            _finish_stopped(job_id)
            clear_cancel_request(job_id)
            return {"status": "stopped"}
        scan.status = "running"
        scan.progress = max(scan.progress or 0, 1)
        scan.updated_at = datetime.utcnow()
        db.session.commit()

    terminal_status = None
    try:
        scan_generator = scanners.run_scan(
            tool,
            target,
            scan_type,
            port=port,
            cancel_check=lambda: is_cancel_requested(job_id),
        )

        for update in scan_generator:
            update_type = update.get("type")
            value = update.get("value")

            if update_type == "process":
                # The process handle belongs to this isolated RQ work horse only.
                # It is intentionally never stored in the API process or database.
                continue
            if update_type == "progress":
                _save_scan(job_id, status="running", progress=value)
                continue
            if update_type == "result":
                _save_scan(
                    job_id,
                    status="completed",
                    progress=100,
                    results=value,
                )
                terminal_status = "completed"
                break
            if update_type == "cancelled":
                _finish_stopped(job_id)
                terminal_status = "stopped"
                break
            if update_type == "error":
                _save_scan(
                    job_id,
                    status="failed",
                    results={"error": str(value), "code": "scanner_error"},
                )
                terminal_status = "failed"
                break

        if terminal_status is None:
            _save_scan(
                job_id,
                status="failed",
                results={
                    "error": "Scanner ended without a terminal result.",
                    "code": "scanner_incomplete",
                },
            )
            terminal_status = "failed"

        return {"status": terminal_status}
    except Exception:
        logger.exception("Unhandled exception while executing queued scan %s", job_id)
        _save_scan(
            job_id,
            status="failed",
            results={"error": "The queued scan failed internally.", "code": "queue_job_error"},
        )
        raise
    finally:
        clear_cancel_request(job_id)


def work_horse_killed_handler(job, retpid, ret_val, rusage):
    """Persist a terminal DB state when an RQ work horse dies unexpectedly."""

    del retpid, ret_val, rusage
    try:
        with app.app_context():
            scan = _load_scan(job.id)
            if scan is None or scan.status in _TERMINAL_STATUSES:
                return
            scan.status = "failed"
            scan.results = json.dumps(
                {
                    "error": "Scan worker terminated unexpectedly.",
                    "code": "worker_terminated",
                }
            )
            scan.updated_at = datetime.utcnow()
            db.session.commit()
    except Exception:
        logger.exception("Failed to persist work-horse termination for scan %s", job.id)


class CloudXWorker(Worker):
    """RQ worker that reconciles hard work-horse termination into PostgreSQL."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("work_horse_killed_handler", work_horse_killed_handler)
        super().__init__(*args, **kwargs)
