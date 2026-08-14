import os
from contextlib import contextmanager
from functools import lru_cache

from redis import Redis
from redis.exceptions import LockError, RedisError
from rq import Queue
from rq.serializers import JSONSerializer

SCAN_QUEUE_NAME = "scans"
_CANCEL_PREFIX = "cloudx:scan:cancel:"
_ENQUEUE_LOCK_KEY = "cloudx:scan:enqueue-lock"


class ScanQueueUnavailable(RuntimeError):
    """Raised when Redis/RQ cannot satisfy a scan queue operation."""


def _redis_url():
    value = os.getenv("REDIS_URL", "").strip()
    if not value:
        raise ScanQueueUnavailable("REDIS_URL is not configured")
    if not value.startswith(("redis://", "rediss://", "unix://")):
        raise ScanQueueUnavailable("REDIS_URL must use redis://, rediss://, or unix://")
    return value


@lru_cache(maxsize=1)
def get_redis_connection():
    return Redis.from_url(
        _redis_url(),
        socket_connect_timeout=3,
        socket_timeout=3,
        health_check_interval=30,
    )


def get_scan_queue():
    return Queue(
        SCAN_QUEUE_NAME,
        connection=get_redis_connection(),
        serializer=JSONSerializer,
        default_timeout=360,
    )


def assert_queue_available():
    try:
        if get_redis_connection().ping() is not True:
            raise ScanQueueUnavailable("Redis did not answer PING")
    except RedisError as exc:
        raise ScanQueueUnavailable("Redis is unavailable") from exc


@contextmanager
def enqueue_lock(timeout=10, blocking_timeout=5):
    """Serialize capacity checks across multiple API processes/instances."""

    try:
        lock = get_redis_connection().lock(
            _ENQUEUE_LOCK_KEY,
            timeout=timeout,
            blocking_timeout=blocking_timeout,
        )
        with lock:
            yield
    except (RedisError, LockError) as exc:
        raise ScanQueueUnavailable("Unable to acquire scan enqueue lock") from exc


def enqueue_scan(job_id, tool, target, scan_type, port=None):
    """Enqueue a scan using JSON-only RQ serialization and a stable job ID."""

    try:
        queue = get_scan_queue()
        return queue.enqueue(
            "scan_jobs.execute_scan",
            job_id,
            tool,
            target,
            scan_type,
            port,
            job_id=job_id,
            unique=True,
            job_timeout=360,
            result_ttl=24 * 60 * 60,
            failure_ttl=7 * 24 * 60 * 60,
        )
    except RedisError as exc:
        raise ScanQueueUnavailable("Unable to enqueue scan") from exc


def _status_value(status):
    value = getattr(status, "value", None)
    return value if isinstance(value, str) else str(status)


def request_scan_stop(job_id):
    """Cancel queued work or request cooperative cancellation of running work."""

    try:
        queue = get_scan_queue()
        job = queue.fetch_job(job_id)
        if job is None:
            return "missing"

        status = _status_value(job.get_status(refresh=True))
        if status in {
            "queued",
            "deferred",
            "scheduled",
            "ready_to_enqueue",
            "rate_limited",
        }:
            job.cancel()
            return "canceled"
        if status == "started":
            get_redis_connection().setex(f"{_CANCEL_PREFIX}{job_id}", 600, b"1")
            return "stopping"
        return status
    except RedisError as exc:
        raise ScanQueueUnavailable("Unable to stop scan") from exc


def is_cancel_requested(job_id):
    try:
        return bool(get_redis_connection().exists(f"{_CANCEL_PREFIX}{job_id}"))
    except RedisError as exc:
        raise ScanQueueUnavailable("Unable to read scan cancellation state") from exc


def clear_cancel_request(job_id):
    try:
        get_redis_connection().delete(f"{_CANCEL_PREFIX}{job_id}")
    except RedisError:
        # A finished scan should not be turned into a failure only because Redis
        # became unavailable while cleaning an expiring cancellation marker.
        pass


def get_queue_job_status(job_id):
    try:
        job = get_scan_queue().fetch_job(job_id)
        if job is None:
            return None
        return _status_value(job.get_status(refresh=True))
    except RedisError as exc:
        raise ScanQueueUnavailable("Unable to read queue job status") from exc
