"""Container-level Redis/RQ/PostgreSQL integration probe for CI.

This file intentionally does not start with ``test_`` so unittest discovery does
not execute it without the required Redis and PostgreSQL services.
"""

import json
import sys
from pathlib import Path

# CI executes this file directly from /app/tests. Python therefore puts the
# tests directory, rather than the application root, at sys.path[0]. Add /app
# explicitly so the probe exercises the same application modules as Gunicorn
# and the RQ worker instead of depending on the caller's working directory.
APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import Scan, app, db
from scan_queue import enqueue_scan, get_queue_job_status, request_scan_stop

NORMAL_JOB_ID = "11111111-1111-1111-1111-111111111111"
CANCEL_JOB_ID = "22222222-2222-2222-2222-222222222222"


def _delete_existing_rows():
    Scan.query.filter(Scan.job_id.in_([NORMAL_JOB_ID, CANCEL_JOB_ID])).delete(
        synchronize_session=False
    )
    db.session.commit()


def seed():
    """Queue one real Nmap job and cancel a second queued job.

    The process exits after enqueueing, before an RQ worker starts. CI then
    starts the worker in a separate container, proving execution does not depend
    on the submitting/API process remaining alive.
    """

    with app.app_context():
        _delete_existing_rows()
        normal = Scan(
            job_id=NORMAL_JOB_ID,
            tool="nmap",
            target="127.0.0.1",
            scan_type="default",
            status="queued",
            progress=0,
        )
        canceled = Scan(
            job_id=CANCEL_JOB_ID,
            tool="nmap",
            target="127.0.0.1",
            scan_type="default",
            status="queued",
            progress=0,
        )
        db.session.add_all([normal, canceled])
        db.session.commit()

        enqueue_scan(NORMAL_JOB_ID, "nmap", "127.0.0.1", "default", None)
        enqueue_scan(CANCEL_JOB_ID, "nmap", "127.0.0.1", "default", None)

        cancel_result = request_scan_stop(CANCEL_JOB_ID)
        if cancel_result != "canceled":
            raise AssertionError(f"Expected queued cancellation, got {cancel_result!r}")

        canceled.status = "stopped"
        canceled.results = json.dumps(
            {
                "error": "Scan was canceled before execution.",
                "code": "scan_canceled",
            }
        )
        db.session.commit()

        queued_status = get_queue_job_status(NORMAL_JOB_ID)
        canceled_status = get_queue_job_status(CANCEL_JOB_ID)
        if queued_status != "queued":
            raise AssertionError(f"Expected normal job queued, got {queued_status!r}")
        if canceled_status != "canceled":
            raise AssertionError(
                f"Expected canceled queue state, got {canceled_status!r}"
            )


def verify():
    """Verify worker execution persisted terminal state in PostgreSQL."""

    with app.app_context():
        normal = Scan.query.filter_by(job_id=NORMAL_JOB_ID).one()
        canceled = Scan.query.filter_by(job_id=CANCEL_JOB_ID).one()

        if normal.status != "completed":
            raise AssertionError(f"Normal job status is {normal.status!r}, not completed")
        if normal.progress != 100:
            raise AssertionError(f"Normal job progress is {normal.progress!r}, not 100")
        payload = json.loads(normal.results or "{}")
        if not isinstance(payload, dict) or not payload:
            raise AssertionError("Normal job did not persist a non-empty JSON result")
        if canceled.status != "stopped":
            raise AssertionError(
                f"Canceled DB row status is {canceled.status!r}, not stopped"
            )
        if get_queue_job_status(NORMAL_JOB_ID) != "finished":
            raise AssertionError("Normal RQ job did not reach finished state")
        if get_queue_job_status(CANCEL_JOB_ID) != "canceled":
            raise AssertionError("Canceled RQ job did not remain canceled")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"seed", "verify"}:
        raise SystemExit("Usage: queue_integration_probe.py <seed|verify>")
    if sys.argv[1] == "seed":
        seed()
    else:
        verify()


if __name__ == "__main__":
    main()
