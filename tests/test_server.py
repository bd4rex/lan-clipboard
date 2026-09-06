import errno
import hashlib
import http.client
import importlib.util
import io
import json
import socket
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lan_clipboard_server", PROJECT_ROOT / "server.py")
server_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = server_module
SPEC.loader.exec_module(server_module)


class QuietHandler(server_module.ClipboardHandler):
    def log_message(self, fmt, *args):
        pass


def multipart_body(contents, complete=True):
    boundary = "regression-boundary"
    chunks = []
    for index, content in enumerate(contents):
        chunks.append((
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="file-{index}.bin"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode())
        chunks.extend((content, b"\r\n"))
    if complete:
        chunks.append((
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="expiresInSeconds"\r\n\r\n'
            f"1800\r\n--{boundary}--\r\n"
        ).encode())
    body = b"".join(chunks)
    return body, {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
        "X-CSRF-Token": server_module.CSRF_TOKEN,
    }


class MultipartReaderTestCase(unittest.TestCase):
    def read_part(self, content, closing=True, delimiter_ending=b"\r\n"):
        boundary = b"--regression-boundary"
        delimiter = boundary + (b"--" if closing else b"") + delimiter_ending
        body = content + b"\r\n" + delimiter
        handler = object.__new__(server_module.ClipboardHandler)
        handler.rfile = io.BytesIO(body + b"next-part")
        remaining = [len(body)]
        data, is_done = handler.read_part_to_buffer(boundary, boundary + b"--", remaining, len(content))
        self.assertEqual(data, content)
        self.assertEqual(is_done, closing)
        self.assertEqual(remaining, [0])
        self.assertEqual(handler.rfile.read(), b"next-part")

    def test_all_chunk_offsets_preserve_binary_and_trailing_newlines(self):
        with patch.object(server_module, "STREAM_CHUNK_BYTES", 128):
            for offset in range(129):
                for suffix in (b"", b"\r", b"\n", b"\r\n"):
                    with self.subTest(offset=offset, suffix=suffix):
                        self.read_part(b"X" * (129 + offset) + suffix)
            self.read_part(bytes(range(256)) * 3)
            self.read_part(b"", closing=False)

    def test_boundary_prefixes_and_unanchored_delimiters_are_file_content(self):
        boundary = b"--regression-boundary"
        contents = (
            boundary + b"--\r\nstill file content",
            b"prefix\r\n" + boundary + b"-suffix\r\nend",
            b"prefix\r\n" + boundary + b"--suffix\r\nend",
            b"X" * 129 + boundary + b"--\r\nend",
        )
        with patch.object(server_module, "STREAM_CHUNK_BYTES", 128):
            for content in contents:
                with self.subTest(content=content):
                    self.read_part(content)

    def test_truncated_part_stops_at_content_length(self):
        handler = object.__new__(server_module.ClipboardHandler)
        handler.rfile = io.BytesIO(b"partial-bodyNEXT-REQUEST")
        remaining = [len(b"partial-body")]
        with self.assertRaises(ValueError):
            handler.read_part_to_buffer(b"--boundary", b"--boundary--", remaining, 1024)
        self.assertEqual(handler.rfile.read(), b"NEXT-REQUEST")

    def test_closing_delimiter_without_final_crlf(self):
        self.read_part(b"file content", delimiter_ending=b"")


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.originals = {
            "ACCESS_CODE": server_module.ACCESS_CODE,
            "CORS_ALLOWED_ORIGINS": server_module.CORS_ALLOWED_ORIGINS,
            "CSRF_TOKEN": server_module.CSRF_TOKEN,
            "DATA_DIR": server_module.DATA_DIR,
            "UPLOAD_DIR": server_module.UPLOAD_DIR,
            "DB_PATH": server_module.DB_PATH,
            "DOWNLOAD_TOKEN_SECRET": server_module.DOWNLOAD_TOKEN_SECRET,
            "CLEANUP_INTERVAL_SECONDS": server_module.CLEANUP_INTERVAL_SECONDS,
            "MEMORY_STORE_ENABLED": server_module.MEMORY_STORE_ENABLED,
            "MEMORY_RESERVE_BYTES": server_module.MEMORY_RESERVE_BYTES,
            "MEMORY_SAFETY_MULTIPLIER": server_module.MEMORY_SAFETY_MULTIPLIER,
            "MEMORY_STORE_MAX_BYTES": server_module.MEMORY_STORE_MAX_BYTES,
            "ORPHAN_GRACE_SECONDS": server_module.ORPHAN_GRACE_SECONDS,
            "available_memory_bytes": server_module.available_memory_bytes,
            "disk_usage_info": server_module.disk_usage_info,
        }
        root = Path(self.temp_dir.name)
        server_module.DATA_DIR = root / "data"
        server_module.UPLOAD_DIR = server_module.DATA_DIR / "uploads"
        server_module.DB_PATH = server_module.DATA_DIR / "clipboard.sqlite"
        server_module.ACCESS_CODE = ""
        server_module.CORS_ALLOWED_ORIGINS = set()
        server_module.CSRF_TOKEN = "test-csrf-token"
        server_module.DOWNLOAD_TOKEN_SECRET = b"test-download-key"
        server_module.MEMORY_FILES.clear()
        server_module.IN_FLIGHT_UPLOAD_NAMES.clear()
        server_module.MEMORY_RESERVED_BYTES = 0
        server_module.DISK_RESERVED_BYTES = 0
        server_module.ensure_storage()

        self.http_server = server_module.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.http_thread.start()

    def tearDown(self):
        self.http_server.shutdown()
        self.http_server.server_close()
        self.http_thread.join(timeout=2)
        server_module.MEMORY_FILES.clear()
        server_module.IN_FLIGHT_UPLOAD_NAMES.clear()
        server_module.MEMORY_RESERVED_BYTES = 0
        server_module.DISK_RESERVED_BYTES = 0
        for name, value in self.originals.items():
            setattr(server_module, name, value)
        self.temp_dir.cleanup()

    def request(self, method, path, body=None, headers=None):
        host, port = self.http_server.server_address
        connection = http.client.HTTPConnection(host, port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            payload = response.read()
            return response.status, {key.lower(): value for key, value in response.getheaders()}, payload
        finally:
            connection.close()

    def upload_files(self, contents):
        body, headers = multipart_body(contents)
        return self.request("POST", "/api/upload", body, headers)

    def assert_no_upload_leftovers(self):
        self.assertEqual(list(server_module.UPLOAD_DIR.iterdir()), [])
        self.assertEqual(server_module.MEMORY_FILES, {})
        self.assertEqual(server_module.IN_FLIGHT_UPLOAD_NAMES, set())
        self.assertEqual(server_module.storage_reservation_info(), (0, 0))
        with server_module.db() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM items").fetchone()[0], 0)

    def insert_disk_file(self, item_id="disk-file", content=b"0123456789", expires_at=None):
        stored_name = f"{item_id}.bin"
        (server_module.UPLOAD_DIR / stored_name).write_bytes(content)
        now = int(time.time())
        with server_module.db() as conn:
            conn.execute(
                """
                INSERT INTO items (
                    id, kind, filename, stored_name, storage_backend, mime_type, size, created_at, expires_at
                ) VALUES (?, 'file', ?, ?, 'disk', 'application/octet-stream', ?, ?, ?)
                """,
                (item_id, stored_name, stored_name, len(content), now, expires_at),
            )
        return stored_name

    def test_write_requests_require_csrf_token(self):
        with server_module.db() as conn:
            conn.execute(
                "INSERT INTO items (id, kind, text, size, created_at) VALUES ('text-item', 'text', 'hello', 5, ?)",
                (int(time.time()),),
            )

        status, headers, _ = self.request(
            "POST",
            "/api/clear",
            body=b"",
            headers={"Origin": "https://evil.example", "Content-Length": "0"},
        )
        with server_module.db() as conn:
            remaining = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        self.assertEqual(status, 403)
        self.assertNotIn("access-control-allow-origin", headers)
        self.assertEqual(remaining, 1)

        status, _, _ = self.request(
            "POST",
            "/api/clear",
            body=b"",
            headers={"X-CSRF-Token": server_module.CSRF_TOKEN, "Content-Length": "0"},
        )
        self.assertEqual(status, 200)

    def test_item_list_includes_server_time_for_countdowns(self):
        before = time.time()
        status, _, payload = self.request("GET", "/api/items")
        after = time.time()

        self.assertEqual(status, 200)
        data = json.loads(payload)
        self.assertEqual(data["items"], [])
        self.assertGreaterEqual(data["serverTime"], before)
        self.assertLessEqual(data["serverTime"], after)

    def test_file_retention_can_be_extended(self):
        original_expiry = int(time.time()) + 600
        self.insert_disk_file("extend-file", expires_at=original_expiry)
        body = json.dumps({"seconds": 1800}).encode()

        status, _, payload = self.request(
            "POST",
            "/api/items/extend-file/extend",
            body=body,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
                "X-CSRF-Token": server_module.CSRF_TOKEN,
            },
        )

        self.assertEqual(status, 200, payload)
        data = json.loads(payload)
        self.assertEqual(data["item"]["expiresAt"], original_expiry + 1800)
        self.assertIn("serverTime", data)

    def test_permanent_file_cannot_be_extended(self):
        self.insert_disk_file("permanent-file", expires_at=None)
        body = json.dumps({"seconds": 1800}).encode()

        status, _, payload = self.request(
            "POST",
            "/api/items/permanent-file/extend",
            body=body,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
                "X-CSRF-Token": server_module.CSRF_TOKEN,
            },
        )

        self.assertEqual(status, 409, payload)

    def test_file_extension_rejects_unsupported_duration(self):
        self.insert_disk_file("invalid-extension", expires_at=int(time.time()) + 600)
        body = json.dumps({"seconds": 60}).encode()

        status, _, payload = self.request(
            "POST",
            "/api/items/invalid-extension/extend",
            body=body,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
                "X-CSRF-Token": server_module.CSRF_TOKEN,
            },
        )

        self.assertEqual(status, 400, payload)

    def test_in_flight_memory_is_reserved_atomically(self):
        server_module.MEMORY_STORE_ENABLED = True
        server_module.MEMORY_STORE_MAX_BYTES = 0
        server_module.MEMORY_RESERVE_BYTES = 100
        server_module.MEMORY_SAFETY_MULTIPLIER = 1.0
        server_module.available_memory_bytes = lambda: 1000
        server_module.disk_usage_info = lambda: {
            "total": 1000,
            "used": 1000,
            "free": 0,
            "reserve": 0,
            "usable": 0,
        }

        first = server_module.reserve_upload_storage(600)
        second = server_module.reserve_upload_storage(600)
        self.assertIsNotNone(first)
        self.assertEqual(first.backend, "memory")
        self.assertIsNone(second)

        first.release()
        third = server_module.reserve_upload_storage(600)
        self.assertIsNotNone(third)
        self.assertEqual(third.backend, "memory")
        third.release()

    def test_in_flight_disk_is_reserved_atomically(self):
        server_module.MEMORY_STORE_ENABLED = False
        server_module.disk_usage_info = lambda: {
            "total": 1000,
            "used": 0,
            "free": 1000,
            "reserve": 0,
            "usable": 1000,
        }

        first = server_module.reserve_upload_storage(600)
        second = server_module.reserve_upload_storage(600)
        self.assertIsNotNone(first)
        self.assertEqual(first.backend, "disk")
        self.assertIsNone(second)

        first.release()
        third = server_module.reserve_upload_storage(600)
        self.assertIsNotNone(third)
        self.assertEqual(third.backend, "disk")
        third.release()

    def test_cleanup_removes_expired_and_orphan_files(self):
        expired_name = self.insert_disk_file("expired", b"expired", int(time.time()) - 1)
        orphan = server_module.UPLOAD_DIR / "orphan.bin"
        orphan.write_bytes(b"orphan")
        old_time = time.time() - 10
        orphan.touch()
        server_module.os.utime(orphan, (old_time, old_time))
        server_module.ORPHAN_GRACE_SECONDS = 1

        server_module.cleanup_storage_once()

        self.assertFalse((server_module.UPLOAD_DIR / expired_name).exists())
        self.assertFalse(orphan.exists())
        with server_module.db() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM items").fetchone()[0], 0)

    def test_cleanup_preserves_in_flight_upload_files(self):
        active_upload = server_module.UPLOAD_DIR / "active-upload.bin"
        active_upload.write_bytes(b"still uploading")
        old_time = time.time() - 10
        server_module.os.utime(active_upload, (old_time, old_time))
        server_module.ORPHAN_GRACE_SECONDS = 1
        server_module.protect_in_flight_upload(active_upload.name)

        server_module.cleanup_storage_once()
        self.assertTrue(active_upload.exists())

        server_module.release_in_flight_uploads({active_upload.name})
        server_module.cleanup_storage_once()
        self.assertFalse(active_upload.exists())

    def test_cleanup_worker_removes_expired_without_api_request(self):
        expired_name = self.insert_disk_file("worker-expired", b"expired", int(time.time()) - 1)
        server_module.CLEANUP_INTERVAL_SECONDS = 0.05
        stop_event = threading.Event()
        worker = threading.Thread(target=server_module.cleanup_worker, args=(stop_event,), daemon=True)
        worker.start()
        deadline = time.time() + 1
        target = server_module.UPLOAD_DIR / expired_name
        while target.exists() and time.time() < deadline:
            time.sleep(0.02)
        stop_event.set()
        worker.join(timeout=1)
        self.assertFalse(target.exists())

    def test_access_code_uses_short_lived_download_token(self):
        server_module.ACCESS_CODE = "sample-access-code"
        self.insert_disk_file("signed-file")
        with server_module.db() as conn:
            row = conn.execute("SELECT * FROM items WHERE id = 'signed-file'").fetchone()
        download_url = server_module.item_to_dict(row)["downloadUrl"]

        self.assertNotIn(server_module.ACCESS_CODE, download_url)
        self.assertNotIn("code=", download_url)
        self.assertIn("token=", download_url)
        bare_path = urlparse(download_url).path
        self.assertEqual(self.request("GET", bare_path)[0], 401)
        self.assertEqual(self.request("GET", download_url)[0], 200)

    def test_download_supports_single_byte_ranges(self):
        self.insert_disk_file()
        status, headers, payload = self.request(
            "GET",
            "/download/disk-file",
            headers={"Range": "bytes=2-5"},
        )
        self.assertEqual(status, 206)
        self.assertEqual(payload, b"2345")
        self.assertEqual(headers["accept-ranges"], "bytes")
        self.assertEqual(headers["content-range"], "bytes 2-5/10")

        status, headers, payload = self.request(
            "GET",
            "/download/disk-file",
            headers={"Range": "bytes=99-100"},
        )
        self.assertEqual(status, 416)
        self.assertEqual(headers["content-range"], "bytes */10")
        self.assertEqual(payload, b"")

    def test_file_upload_uses_csrf_and_releases_disk_reservation(self):
        server_module.MEMORY_STORE_ENABLED = False
        boundary = "test-boundary"
        file_content = b"uploaded-content"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="upload.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n"
        ).encode() + file_content + (
            f"\r\n--{boundary}\r\n"
            'Content-Disposition: form-data; name="expiresInSeconds"\r\n\r\n'
            f"1800\r\n--{boundary}--\r\n"
        ).encode()

        status, _, payload = self.request(
            "POST",
            "/api/upload",
            body=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
                "X-CSRF-Token": server_module.CSRF_TOKEN,
            },
        )
        self.assertEqual(status, 201, payload)
        self.assertEqual(server_module.storage_reservation_info(), (0, 0))
        self.assertEqual(server_module.IN_FLIGHT_UPLOAD_NAMES, set())
        with server_module.db() as conn:
            row = conn.execute("SELECT * FROM items WHERE filename = 'upload.txt'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual((server_module.UPLOAD_DIR / row["stored_name"]).read_bytes(), file_content)

    def test_upload_download_hashes_match_at_stream_boundaries(self):
        server_module.available_memory_bytes = lambda: 100 * 1024 ** 3
        chunk_size = server_module.STREAM_CHUNK_BYTES
        for use_memory in (False, True):
            server_module.MEMORY_STORE_ENABLED = use_memory
            for size in (chunk_size - 1, chunk_size, chunk_size + 1, 2 * chunk_size + 1):
                with self.subTest(memory=use_memory, size=size):
                    content = b"X" * size
                    status, _, payload = self.upload_files([content])
                    self.assertEqual(status, 201, payload)
                    item = json.loads(payload)["items"][0]
                    self.assertEqual(item["storageBackend"], "memory" if use_memory else "disk")
                    status, _, downloaded = self.request("GET", item["downloadUrl"])
                    self.assertEqual(status, 200)
                    self.assertEqual(item["size"], size)
                    self.assertEqual(len(downloaded), size)
                    self.assertEqual(hashlib.sha256(downloaded).digest(), hashlib.sha256(content).digest())

    def test_interrupted_upload_removes_current_partial_file(self):
        server_module.MEMORY_STORE_ENABLED = False
        body, headers = multipart_body([b"X" * (2 * server_module.STREAM_CHUNK_BYTES)], complete=False)
        connection = http.client.HTTPConnection(*self.http_server.server_address, timeout=3)
        try:
            connection.request("POST", "/api/upload", body, headers)
            connection.sock.shutdown(socket.SHUT_WR)
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 413)
        finally:
            connection.close()
        self.assert_no_upload_leftovers()

    def test_disk_full_cleans_current_and_previous_files(self):
        server_module.MEMORY_STORE_ENABLED = False
        original_reader = server_module.ClipboardHandler.read_part_to_file
        calls = []

        def disk_full(handler, target, *args):
            calls.append(target)
            if len(calls) == 2:
                target.write_bytes(b"partial write")
                raise OSError(errno.ENOSPC, "injected disk full")
            return original_reader(handler, target, *args)

        with patch.object(server_module.ClipboardHandler, "read_part_to_file", disk_full):
            status, _, payload = self.upload_files([b"first file", b"second file"])
        self.assertEqual(status, 507, payload)
        self.assertEqual(len(calls), 2)
        self.assert_no_upload_leftovers()

    def test_over_size_upload_removes_partial_file(self):
        server_module.MEMORY_STORE_ENABLED = False
        with patch.object(server_module, "MAX_UPLOAD_BYTES", 1024):
            status, _, payload = self.upload_files([(b"X" * 511 + b"\n") * 4])
        self.assertEqual(status, 413, payload)
        self.assert_no_upload_leftovers()

    def test_same_second_items_keep_the_newest_insert(self):
        now = int(time.time())
        with server_module.db() as conn:
            conn.executemany(
                "INSERT INTO items (id, kind, text, size, created_at) VALUES (?, 'text', 'old', 3, ?)",
                [(f"old-{index}", now) for index in range(server_module.MAX_ITEMS)],
            )
        with patch.object(server_module.time, "time", return_value=now):
            status, _, payload = self.request("POST", "/api/text", json.dumps({"content": "new text"}).encode(), {
                "Content-Type": "application/json", "X-CSRF-Token": server_module.CSRF_TOKEN,
            })
        self.assertEqual(status, 201, payload)
        new_id = json.loads(payload)["item"]["id"]
        status, _, payload = self.request("GET", "/api/items")
        self.assertEqual(status, 200)
        items = json.loads(payload)["items"]
        self.assertEqual(len(items), server_module.MAX_ITEMS)
        self.assertEqual(items[0]["id"], new_id)
        self.assertNotIn("old-0", {item["id"] for item in items})

    def test_batch_at_retention_limit_keeps_every_new_file(self):
        server_module.MEMORY_STORE_ENABLED = False
        with patch.object(server_module, "MAX_ITEMS", 3), \
             patch.object(server_module.time, "time", return_value=int(time.time())):
            old_name = self.insert_disk_file("old-file")
            contents = [b"first", b"second", b"third"]
            status, _, payload = self.upload_files(contents)
            self.assertEqual(status, 201, payload)
            items = json.loads(payload)["items"]
            self.assertEqual(len(items), 3)
            for item, content in zip(items, contents):
                status, _, downloaded = self.request("GET", item["downloadUrl"])
                self.assertEqual(status, 200)
                self.assertEqual(downloaded, content)
            status, _, payload = self.request("GET", "/api/items")
            self.assertEqual(status, 200)
            self.assertEqual([item["id"] for item in json.loads(payload)["items"]],
                             [item["id"] for item in reversed(items)])
            self.assertFalse((server_module.UPLOAD_DIR / old_name).exists())

    def test_over_limit_batch_is_rejected_without_evicting_existing_data(self):
        old_name = self.insert_disk_file("existing-file")
        server_module.available_memory_bytes = lambda: 100 * 1024 ** 3
        with patch.object(server_module, "MAX_ITEMS", 2):
            for use_memory in (False, True):
                with self.subTest(memory=use_memory):
                    server_module.MEMORY_STORE_ENABLED = use_memory
                    status, _, payload = self.upload_files([b"first", b"second", b"third"])
                    self.assertEqual(status, 413, payload)
                    self.assertEqual([path.name for path in server_module.UPLOAD_DIR.iterdir()], [old_name])
                    self.assertEqual(server_module.MEMORY_FILES, {})
                    self.assertEqual(server_module.IN_FLIGHT_UPLOAD_NAMES, set())
                    self.assertEqual(server_module.storage_reservation_info(), (0, 0))
                    with server_module.db() as conn:
                        self.assertEqual([row[0] for row in conn.execute("SELECT id FROM items")], ["existing-file"])

    def test_zero_retention_limit_lists_all_items(self):
        self.insert_disk_file()
        with patch.object(server_module, "MAX_ITEMS", 0):
            status, _, payload = self.request("GET", "/api/items")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(payload)["items"]), 1)

    def test_slow_list_response_does_not_block_another_client(self):
        send_started = threading.Event()
        release_send = threading.Event()
        original_send = server_module.ClipboardHandler.send_json

        def slow_send(handler, payload, *args):
            if handler.path == "/api/items":
                send_started.set()
                if not release_send.wait(5):
                    raise RuntimeError("response gate timed out")
            return original_send(handler, payload, *args)

        with patch.object(server_module.ClipboardHandler, "send_json", slow_send), \
             ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.request, "GET", "/api/items")
            try:
                self.assertTrue(send_started.wait(2))
                status, _, payload = self.request("POST", "/api/text", json.dumps({"content": "not blocked"}).encode(), {
                    "Content-Type": "application/json", "X-CSRF-Token": server_module.CSRF_TOKEN,
                })
                self.assertEqual(status, 201, payload)
            finally:
                release_send.set()
            self.assertEqual(future.result(timeout=3)[0], 200)

    def test_success_and_error_responses_release_write_transactions(self):
        self.insert_disk_file("permanent-file")
        original_send = server_module.ClipboardHandler.send_json
        lock_errors = []

        def check_lock(handler, payload, *args):
            probe = sqlite3.connect(server_module.DB_PATH, timeout=0)
            try:
                probe.execute("BEGIN IMMEDIATE")
                probe.rollback()
            except sqlite3.Error as exc:
                lock_errors.append((handler.path, str(exc)))
            finally:
                probe.close()
            return original_send(handler, payload, *args)

        cases = (
            ("GET", "/api/items", None, 200),
            ("POST", "/api/text", {"content": "test"}, 201),
            ("POST", "/api/items/missing/extend", {"seconds": 1800}, 404),
            ("POST", "/api/items/permanent-file/extend", {"seconds": 1800}, 409),
            ("DELETE", "/api/items/missing", None, 404),
            ("DELETE", "/api/items/permanent-file", None, 200),
            ("POST", "/api/clear", None, 200),
        )
        with patch.object(server_module.ClipboardHandler, "send_json", check_lock):
            for method, path, data, expected_status in cases:
                status, _, payload = self.request(method, path, json.dumps(data).encode() if data else b"", {
                    "Content-Type": "application/json", "X-CSRF-Token": server_module.CSRF_TOKEN,
                })
                self.assertEqual(status, expected_status, payload)
        self.assertEqual(lock_errors, [])

    def test_expiry_cleanup_waits_for_extension_to_commit(self):
        for backend in ("disk", "memory"):
            with self.subTest(backend=backend):
                self.check_extension_cleanup_race(backend)

    def check_extension_cleanup_race(self, backend):
        item_id = f"race-{backend}"
        expiry = int(time.time()) + 100
        content = b"keep this file"
        stored_name = self.insert_disk_file(item_id, content, expiry)
        if backend == "memory":
            server_module.MEMORY_FILES[item_id] = {"data": bytearray(content), "size": len(content)}
            with server_module.db() as conn:
                conn.execute("UPDATE items SET storage_backend='memory', stored_name=NULL WHERE id=?", (item_id,))
            (server_module.UPLOAD_DIR / stored_name).unlink()

        clock = [expiry - 1]
        update_ready = threading.Event()
        release_update = threading.Event()
        cleanup_started = threading.Event()
        cleanup_queries = []
        original_db = server_module.db

        class ObservedConnection:
            def __init__(self, conn):
                self.conn = conn

            def __getattr__(self, name):
                return getattr(self.conn, name)

            def execute(self, sql, parameters=()):
                if threading.current_thread().name.startswith("cleanup-regression"):
                    cleanup_queries.append(sql)
                    cleanup_started.set()
                cursor = self.conn.execute(sql, parameters)
                if sql.startswith("UPDATE items SET expires_at"):
                    update_ready.set()
                    if not release_update.wait(5):
                        raise RuntimeError("extension gate timed out")
                return cursor

        @contextmanager
        def observed_db():
            with original_db() as conn:
                yield ObservedConnection(conn)

        with patch.object(server_module, "db", observed_db), \
             patch.object(server_module.time, "time", side_effect=lambda: clock[0]), \
             ThreadPoolExecutor(max_workers=1) as requests, \
             ThreadPoolExecutor(max_workers=1, thread_name_prefix="cleanup-regression") as cleaners:
            extension = requests.submit(self.request, "POST", f"/api/items/{item_id}/extend",
                                        json.dumps({"seconds": 1800}).encode(), {
                                            "Content-Type": "application/json",
                                            "X-CSRF-Token": server_module.CSRF_TOKEN,
                                        })
            cleanup = None
            try:
                self.assertTrue(update_ready.wait(2))
                clock[0] = expiry
                cleanup = cleaners.submit(server_module.cleanup_storage_once)
                self.assertTrue(cleanup_started.wait(2))
                self.assertEqual(cleanup_queries[0], "BEGIN IMMEDIATE")
                if backend == "disk":
                    self.assertTrue((server_module.UPLOAD_DIR / stored_name).exists())
                else:
                    self.assertIn(item_id, server_module.MEMORY_FILES)
            finally:
                release_update.set()
            status, _, payload = extension.result(timeout=3)
            self.assertEqual(status, 200, payload)
            self.assertEqual(json.loads(payload)["item"]["expiresAt"], expiry + 1800)
            cleanup.result(timeout=3)
            with server_module.db() as conn:
                self.assertEqual(conn.execute("SELECT expires_at FROM items WHERE id=?", (item_id,)).fetchone()[0],
                                 expiry + 1800)
            status, _, downloaded = self.request("GET", f"/download/{item_id}")
            self.assertEqual(status, 200)
            self.assertEqual(downloaded, content)


if __name__ == "__main__":
    unittest.main()
