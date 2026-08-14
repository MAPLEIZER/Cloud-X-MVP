import os
import unittest
from unittest.mock import Mock, patch

import scan_queue


class FakeJob:
    def __init__(self, status):
        self.status = status
        self.cancelled = False

    def get_status(self, refresh=False):
        self.refresh = refresh
        return self.status

    def cancel(self):
        self.cancelled = True


class FakeQueue:
    def __init__(self, job=None):
        self.job = job
        self.enqueue_calls = []

    def fetch_job(self, job_id):
        self.job_id = job_id
        return self.job

    def enqueue(self, *args, **kwargs):
        self.enqueue_calls.append((args, kwargs))
        return {"queued": True}


class ScanQueueTests(unittest.TestCase):
    def test_queued_job_is_canceled_without_running_worker_signal(self):
        job = FakeJob("queued")
        queue = FakeQueue(job)
        redis = Mock()

        with (
            patch.object(scan_queue, "get_scan_queue", return_value=queue),
            patch.object(scan_queue, "get_redis_connection", return_value=redis),
        ):
            result = scan_queue.request_scan_stop("job-1")

        self.assertEqual(result, "canceled")
        self.assertTrue(job.cancelled)
        redis.setex.assert_not_called()

    def test_running_job_uses_cooperative_redis_cancel_marker(self):
        job = FakeJob("started")
        queue = FakeQueue(job)
        redis = Mock()

        with (
            patch.object(scan_queue, "get_scan_queue", return_value=queue),
            patch.object(scan_queue, "get_redis_connection", return_value=redis),
        ):
            result = scan_queue.request_scan_stop("job-2")

        self.assertEqual(result, "stopping")
        self.assertFalse(job.cancelled)
        redis.setex.assert_called_once_with("cloudx:scan:cancel:job-2", 600, b"1")

    def test_enqueue_uses_dotted_job_function_and_stable_job_id(self):
        queue = FakeQueue()
        with patch.object(scan_queue, "get_scan_queue", return_value=queue):
            scan_queue.enqueue_scan(
                "11111111-1111-1111-1111-111111111111",
                "nmap",
                "127.0.0.1",
                "default",
                None,
            )

        args, kwargs = queue.enqueue_calls[0]
        self.assertEqual(args[0], "scan_jobs.execute_scan")
        self.assertEqual(args[1], "11111111-1111-1111-1111-111111111111")
        self.assertEqual(kwargs["job_id"], "11111111-1111-1111-1111-111111111111")
        self.assertTrue(kwargs["unique"])

    def test_missing_or_invalid_redis_url_fails_closed(self):
        with patch.dict(os.environ, {"REDIS_URL": ""}, clear=False):
            with self.assertRaises(scan_queue.ScanQueueUnavailable):
                scan_queue._redis_url()

        with patch.dict(os.environ, {"REDIS_URL": "http://redis:6379"}, clear=False):
            with self.assertRaises(scan_queue.ScanQueueUnavailable):
                scan_queue._redis_url()

        with patch.dict(os.environ, {"REDIS_URL": "redis://redis:6379/0"}, clear=False):
            self.assertEqual(scan_queue._redis_url(), "redis://redis:6379/0")


if __name__ == "__main__":
    unittest.main()
