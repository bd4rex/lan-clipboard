import http.client
import importlib.util
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
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
        server_module.MEMORY_RESERVED_BYTES = 0
        server_module.DISK_RESERVED_BYTES = 0
        for name, value in self.originals.items():
            setattr(server_module, name, value)
        self.temp_dir.cleanup()

    def request(self, method, path, body=None, headers=None):
        host, port = self.http_server.server_address
        connection = http.client.HTTPConnection(host, port, timeout=3)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = response.read()
        result = response.status, {key.lower(): value for key, value in response.getheaders()}, payload
        connection.close()
        return result

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
        with server_module.db() as conn:
            row = conn.execute("SELECT * FROM items WHERE filename = 'upload.txt'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual((server_module.UPLOAD_DIR / row["stored_name"]).read_bytes(), file_content)


if __name__ == "__main__":
    unittest.main()
