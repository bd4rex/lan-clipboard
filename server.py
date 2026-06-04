#!/usr/bin/env python3
from __future__ import annotations

import argparse
import errno
import hmac
import json
import mimetypes
import os
import shutil
import socket
import sqlite3
import subprocess
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, unquote_to_bytes, urlparse


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "clipboard.sqlite"

ACCESS_CODE = os.getenv("ACCESS_CODE", "").strip()
MAX_UPLOAD_BYTES = int(float(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024)
MAX_UPLOAD_OVERHEAD_BYTES = 16 * 1024 * 1024
MAX_TEXT_BYTES = int(float(os.getenv("MAX_TEXT_MB", "2")) * 1024 * 1024)
MAX_ITEMS = int(os.getenv("MAX_ITEMS", "200"))
DEFAULT_TTL_SECONDS = int(float(os.getenv("DEFAULT_TTL_HOURS", "0.5")) * 3600)
MEMORY_STORE_ENABLED = os.getenv("MEMORY_STORE_ENABLED", "1").lower() not in {"0", "false", "no", "off"}
MEMORY_RESERVE_BYTES = int(float(os.getenv("MEMORY_RESERVE_MB", "1024")) * 1024 * 1024)
MEMORY_STORE_MAX_BYTES = int(float(os.getenv("MEMORY_STORE_MAX_MB", "0")) * 1024 * 1024)
MEMORY_SAFETY_MULTIPLIER = float(os.getenv("MEMORY_SAFETY_MULTIPLIER", "1.25"))
DISK_RESERVE_BYTES = int(float(os.getenv("DISK_RESERVE_MB", "1024")) * 1024 * 1024)
FIELD_MAX_BYTES = 64 * 1024
PART_HEADER_MAX_BYTES = 64 * 1024
STREAM_CHUNK_BYTES = 1024 * 1024

MEMORY_FILES: dict[str, dict[str, object]] = {}
MEMORY_FILES_LOCK = threading.RLock()


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL CHECK (kind IN ('text', 'file')),
                text TEXT,
                filename TEXT,
                stored_name TEXT,
                storage_backend TEXT NOT NULL DEFAULT 'disk',
                mime_type TEXT,
                size INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                expires_at INTEGER
            )
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(items)").fetchall()}
        if "storage_backend" not in columns:
            conn.execute("ALTER TABLE items ADD COLUMN storage_backend TEXT NOT NULL DEFAULT 'disk'")
        conn.execute("DELETE FROM items WHERE kind = 'file' AND storage_backend = 'memory'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_created ON items(created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_expires ON items(expires_at)")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def safe_filename(filename: str | None) -> str:
    cleaned = Path(filename or "download").name
    cleaned = "".join(ch for ch in cleaned if ch >= " " and ch not in {'"', "'", "\\", "/"})
    cleaned = cleaned.strip(" .")
    return cleaned[:160] or "download"


def parse_multipart_boundary(content_type: str) -> bytes | None:
    for segment in content_type.split(";")[1:]:
        key, _, value = segment.strip().partition("=")
        if key.lower() == "boundary":
            boundary = value.strip().strip('"')
            if boundary:
                return boundary.encode("utf-8")
    return None


def split_header_params(value: str) -> tuple[str, dict[str, str]]:
    parts: list[str] = []
    current: list[str] = []
    in_quote = False
    escape = False
    for char in value:
        if escape:
            current.append(char)
            escape = False
            continue
        if char == "\\" and in_quote:
            escape = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if char == ";" and not in_quote:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    parts.append("".join(current).strip())

    main_value = parts[0].lower() if parts else ""
    params: dict[str, str] = {}
    for part in parts[1:]:
        key, _, raw_value = part.partition("=")
        if key:
            params[key.strip().lower()] = raw_value.strip()
    return main_value, params


def decode_rfc5987(value: str) -> str:
    charset, first_sep, rest = value.partition("'")
    if not first_sep:
        return unquote(value)
    _, second_sep, encoded = rest.partition("'")
    if not second_sep:
        return unquote(value)
    try:
        return unquote_to_bytes(encoded).decode(charset or "utf-8", errors="replace")
    except LookupError:
        return unquote(encoded)


def content_disposition_info(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    disposition, params = split_header_params(value)
    if disposition != "form-data":
        return None, None
    name = params.get("name")
    filename = params.get("filename*")
    if filename:
        filename = decode_rfc5987(filename)
    else:
        filename = params.get("filename")
    return name, filename


def stored_path(stored_name: str | None) -> Path | None:
    if not stored_name:
        return None
    path = (UPLOAD_DIR / stored_name).resolve()
    try:
        path.relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        return None
    return path


def memory_files_size() -> int:
    with MEMORY_FILES_LOCK:
        return sum(int(entry.get("size", 0)) for entry in MEMORY_FILES.values())


def available_memory_bytes() -> int | None:
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        for line in meminfo.read_text(errors="replace").splitlines():
            if line.startswith("MemAvailable:"):
                parts = line.split()
                if len(parts) >= 2:
                    return int(parts[1]) * 1024
    try:
        output = subprocess.check_output(["vm_stat"], text=True, stderr=subprocess.DEVNULL, timeout=1)
        page_size = 4096
        available_pages = 0
        for line in output.splitlines():
            if "page size of" in line:
                words = line.replace(".", "").split()
                for index, word in enumerate(words):
                    if word == "of" and index + 1 < len(words):
                        page_size = int(words[index + 1])
                        break
            key, _, raw_value = line.partition(":")
            if key.strip() in {"Pages free", "Pages inactive", "Pages speculative", "Pages purgeable"}:
                available_pages += int(raw_value.strip().strip(".").replace(".", ""))
        if available_pages > 0:
            return available_pages * page_size
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    try:
        pages = os.sysconf("SC_AVPHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
    except (AttributeError, OSError, ValueError):
        return None
    if isinstance(pages, int) and isinstance(page_size, int) and pages > 0 and page_size > 0:
        return pages * page_size
    return None


def disk_usage_info() -> dict[str, int]:
    usage_target = DATA_DIR if DATA_DIR.exists() else BASE_DIR
    usage = shutil.disk_usage(usage_target)
    usable = max(0, usage.free - DISK_RESERVE_BYTES)
    return {
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "reserve": DISK_RESERVE_BYTES,
        "usable": usable,
    }


def should_store_in_memory(content_length: int) -> bool:
    if not MEMORY_STORE_ENABLED or content_length <= 0:
        return False
    if MEMORY_STORE_MAX_BYTES > 0 and content_length > MEMORY_STORE_MAX_BYTES:
        return False
    available = available_memory_bytes()
    if available is None:
        return False
    needed = int(content_length * MEMORY_SAFETY_MULTIPLIER)
    return available - MEMORY_RESERVE_BYTES - memory_files_size() >= needed


def remove_memory_file(item_id: str | None) -> None:
    if not item_id:
        return
    with MEMORY_FILES_LOCK:
        MEMORY_FILES.pop(item_id, None)


def remove_upload(stored_name: str | None) -> None:
    path = stored_path(stored_name)
    if path and path.is_file():
        path.unlink(missing_ok=True)


def remove_item_storage(row: sqlite3.Row) -> None:
    backend = row["storage_backend"] or "disk"
    if backend == "memory":
        remove_memory_file(row["id"])
    else:
        remove_upload(row["stored_name"])


def cleanup_expired(conn: sqlite3.Connection) -> None:
    now = int(time.time())
    rows = conn.execute(
        "SELECT id, stored_name, storage_backend FROM items WHERE expires_at IS NOT NULL AND expires_at <= ?",
        (now,),
    ).fetchall()
    for row in rows:
        remove_item_storage(row)
    conn.execute("DELETE FROM items WHERE expires_at IS NOT NULL AND expires_at <= ?", (now,))


def trim_items(conn: sqlite3.Connection) -> None:
    if MAX_ITEMS <= 0:
        return
    rows = conn.execute(
        """
        SELECT id, stored_name, storage_backend
        FROM items
        WHERE id NOT IN (
            SELECT id FROM items ORDER BY created_at DESC LIMIT ?
        )
        """,
        (MAX_ITEMS,),
    ).fetchall()
    for row in rows:
        remove_item_storage(row)
    conn.execute(
        """
        DELETE FROM items
        WHERE id NOT IN (
            SELECT id FROM items ORDER BY created_at DESC LIMIT ?
        )
        """,
        (MAX_ITEMS,),
    )


def expires_from_value(value: object, now: int) -> int | None:
    if value in (None, ""):
        seconds = DEFAULT_TTL_SECONDS
    else:
        try:
            seconds = int(float(value))
        except (TypeError, ValueError):
            seconds = DEFAULT_TTL_SECONDS
    if seconds <= 0:
        return None
    return now + min(seconds, 365 * 24 * 3600)


def item_to_dict(row: sqlite3.Row) -> dict[str, object]:
    item = {
        "id": row["id"],
        "kind": row["kind"],
        "size": row["size"],
        "createdAt": row["created_at"],
        "expiresAt": row["expires_at"],
    }
    if row["kind"] == "text":
        item["content"] = row["text"] or ""
    else:
        item.update(
            {
                "filename": row["filename"] or "download",
                "mimeType": row["mime_type"] or "application/octet-stream",
                "downloadUrl": f"/download/{quote(row['id'])}",
                "storageBackend": row["storage_backend"] or "disk",
            }
        )
    return item


def get_lan_ip() -> str | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


class ClipboardHandler(BaseHTTPRequestHandler):
    server_version = "LanClipboard/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/health":
            return self.send_json({"ok": True})
        if path == "/api/config":
            disk_info = disk_usage_info()
            return self.send_json(
                {
                    "requiresAccessCode": bool(ACCESS_CODE),
                    "maxUploadBytes": MAX_UPLOAD_BYTES,
                    "maxTextBytes": MAX_TEXT_BYTES,
                    "defaultTtlSeconds": DEFAULT_TTL_SECONDS,
                    "maxItems": MAX_ITEMS,
                    "memoryStorageEnabled": MEMORY_STORE_ENABLED,
                    "memoryReserveBytes": MEMORY_RESERVE_BYTES,
                    "memoryStoreMaxBytes": MEMORY_STORE_MAX_BYTES,
                    "availableMemoryBytes": available_memory_bytes(),
                    "diskTotalBytes": disk_info["total"],
                    "diskUsedBytes": disk_info["used"],
                    "diskFreeBytes": disk_info["free"],
                    "diskReserveBytes": disk_info["reserve"],
                    "diskUsableBytes": disk_info["usable"],
                    "diskWarning": disk_info["usable"] < MAX_UPLOAD_BYTES,
                }
            )
        if path == "/api/items":
            if not self.require_auth(parsed):
                return
            return self.handle_list_items()
        if path.startswith("/download/"):
            if not self.require_auth(parsed):
                return
            return self.handle_download(path.removeprefix("/download/"))
        return self.serve_static(path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not self.require_auth(parsed):
            return
        if parsed.path == "/api/text":
            return self.handle_add_text()
        if parsed.path == "/api/upload":
            return self.handle_upload()
        if parsed.path == "/api/clear":
            return self.handle_clear()
        self.send_error_json(HTTPStatus.NOT_FOUND, "接口不存在")

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if not self.require_auth(parsed):
            return
        if parsed.path.startswith("/api/items/"):
            return self.handle_delete(parsed.path.removeprefix("/api/items/"))
        self.send_error_json(HTTPStatus.NOT_FOUND, "接口不存在")

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,X-Access-Code")

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"error": message}, status)

    def require_auth(self, parsed: object | None = None) -> bool:
        if not ACCESS_CODE:
            return True
        supplied = self.headers.get("X-Access-Code", "")
        if not supplied:
            parsed_path = parsed if parsed is not None else urlparse(self.path)
            supplied = parse_qs(parsed_path.query).get("code", [""])[0]
        if hmac.compare_digest(supplied, ACCESS_CODE):
            return True
        self.send_error_json(HTTPStatus.UNAUTHORIZED, "需要正确的访问码")
        return False

    def read_limited_body(self, max_bytes: int) -> bytes | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error_json(HTTPStatus.LENGTH_REQUIRED, "缺少 Content-Length")
            return None
        if length <= 0:
            return b""
        if length > max_bytes:
            self.send_error_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "内容超过大小限制")
            return None
        return self.rfile.read(length)

    def read_upload_line(self, remaining: list[int]) -> bytes:
        line = self.rfile.readline(STREAM_CHUNK_BYTES + 1)
        if not line:
            return b""
        remaining[0] -= len(line)
        if remaining[0] < 0:
            raise ValueError("上传内容超过大小限制")
        return line

    def read_part_headers(self, remaining: list[int]) -> dict[str, str]:
        headers: dict[str, str] = {}
        total = 0
        while True:
            line = self.read_upload_line(remaining)
            if line in (b"\r\n", b"\n", b""):
                return headers
            total += len(line)
            if total > PART_HEADER_MAX_BYTES:
                raise ValueError("上传头部过大")
            try:
                decoded = line.decode("utf-8")
            except UnicodeDecodeError:
                decoded = line.decode("iso-8859-1", errors="replace")
            key, _, value = decoded.partition(":")
            if key:
                headers[key.strip().lower()] = value.strip()

    def read_part_to_memory(
        self,
        boundary_line: bytes,
        closing_boundary_line: bytes,
        remaining: list[int],
        max_bytes: int,
    ) -> tuple[bytes, bool]:
        pending: bytes | None = None
        chunks: list[bytes] = []
        total = 0
        while True:
            line = self.read_upload_line(remaining)
            if not line:
                raise ValueError("上传内容不完整")
            if line.startswith(boundary_line):
                if pending is not None:
                    if pending.endswith(b"\r\n"):
                        pending = pending[:-2]
                    elif pending.endswith(b"\n"):
                        pending = pending[:-1]
                    total += len(pending)
                    if total > max_bytes:
                        raise ValueError("表单字段过大")
                    chunks.append(pending)
                return b"".join(chunks), line.startswith(closing_boundary_line)
            if pending is not None:
                total += len(pending)
                if total > max_bytes:
                    raise ValueError("表单字段过大")
                chunks.append(pending)
            pending = line

    def read_part_to_file(
        self,
        target: Path,
        boundary_line: bytes,
        closing_boundary_line: bytes,
        remaining: list[int],
    ) -> tuple[int, bool]:
        pending: bytes | None = None
        total = 0
        with target.open("wb") as file_obj:
            while True:
                line = self.read_upload_line(remaining)
                if not line:
                    raise ValueError("上传内容不完整")
                if line.startswith(boundary_line):
                    if pending is not None:
                        if pending.endswith(b"\r\n"):
                            pending = pending[:-2]
                        elif pending.endswith(b"\n"):
                            pending = pending[:-1]
                        total += len(pending)
                        if total > MAX_UPLOAD_BYTES:
                            raise ValueError("文件超过大小限制")
                        file_obj.write(pending)
                    return total, line.startswith(closing_boundary_line)
                if pending is not None:
                    total += len(pending)
                    if total > MAX_UPLOAD_BYTES:
                        raise ValueError("文件超过大小限制")
                    file_obj.write(pending)
                pending = line

    def read_part_to_buffer(
        self,
        boundary_line: bytes,
        closing_boundary_line: bytes,
        remaining: list[int],
        max_bytes: int,
    ) -> tuple[bytearray, bool]:
        pending: bytes | None = None
        data = bytearray()
        total = 0
        while True:
            line = self.read_upload_line(remaining)
            if not line:
                raise ValueError("上传内容不完整")
            if line.startswith(boundary_line):
                if pending is not None:
                    if pending.endswith(b"\r\n"):
                        pending = pending[:-2]
                    elif pending.endswith(b"\n"):
                        pending = pending[:-1]
                    total += len(pending)
                    if total > max_bytes:
                        raise ValueError("文件超过大小限制")
                    data.extend(pending)
                return data, line.startswith(closing_boundary_line)
            if pending is not None:
                total += len(pending)
                if total > max_bytes:
                    raise ValueError("文件超过大小限制")
                data.extend(pending)
            pending = line

    def handle_list_items(self) -> None:
        with db() as conn:
            cleanup_expired(conn)
            rows = conn.execute("SELECT * FROM items ORDER BY created_at DESC LIMIT ?", (MAX_ITEMS,)).fetchall()
            self.send_json({"items": [item_to_dict(row) for row in rows]})

    def handle_add_text(self) -> None:
        body = self.read_limited_body(MAX_TEXT_BYTES + 4096)
        if body is None:
            return
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self.send_error_json(HTTPStatus.BAD_REQUEST, "JSON 格式不正确")

        content = str(payload.get("content", ""))
        if not content.strip():
            return self.send_error_json(HTTPStatus.BAD_REQUEST, "文本不能为空")
        size = len(content.encode("utf-8"))
        if size > MAX_TEXT_BYTES:
            return self.send_error_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "文本超过大小限制")

        now = int(time.time())
        item_id = uuid.uuid4().hex
        with db() as conn:
            cleanup_expired(conn)
            conn.execute(
                """
                INSERT INTO items (id, kind, text, size, created_at, expires_at)
                VALUES (?, 'text', ?, ?, ?, ?)
                """,
                (item_id, content, size, now, expires_from_value(payload.get("expiresInSeconds"), now)),
            )
            trim_items(conn)
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            self.send_json({"item": item_to_dict(row)}, HTTPStatus.CREATED)

    def handle_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("multipart/form-data"):
            return self.send_error_json(HTTPStatus.BAD_REQUEST, "请使用 multipart/form-data 上传文件")

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.send_error_json(HTTPStatus.LENGTH_REQUIRED, "缺少 Content-Length")
        if content_length <= 0:
            return self.send_error_json(HTTPStatus.BAD_REQUEST, "上传内容为空")
        if content_length > MAX_UPLOAD_BYTES + MAX_UPLOAD_OVERHEAD_BYTES:
            return self.send_error_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "上传内容超过大小限制")

        boundary = parse_multipart_boundary(content_type)
        if not boundary:
            return self.send_error_json(HTTPStatus.BAD_REQUEST, "上传边界无效")

        remaining = [content_length]
        boundary_line = b"--" + boundary
        closing_boundary_line = boundary_line + b"--"
        fields: dict[str, str] = {}
        files: list[dict[str, object]] = []
        written_paths: list[Path] = []
        memory_ids: list[str] = []
        use_memory = should_store_in_memory(content_length)
        if not use_memory:
            disk_info = disk_usage_info()
            if disk_info["usable"] < content_length:
                message = "硬盘剩余空间不足，无法保存本次上传。请删除旧文件、等待自动清理，或扩容后再试。"
                return self.send_error_json(HTTPStatus.INSUFFICIENT_STORAGE, message)

        try:
            first_line = self.read_upload_line(remaining)
            if not first_line.startswith(boundary_line):
                raise ValueError("上传内容不是 multipart")

            is_done = first_line.startswith(closing_boundary_line)
            while not is_done:
                headers = self.read_part_headers(remaining)
                name, filename = content_disposition_info(headers.get("content-disposition"))
                mime_type = headers.get("content-type", "application/octet-stream")

                if filename:
                    item_id = uuid.uuid4().hex
                    stored_name = None
                    storage_backend = "memory" if use_memory else "disk"
                    if use_memory:
                        data, is_done = self.read_part_to_buffer(
                            boundary_line,
                            closing_boundary_line,
                            remaining,
                            MAX_UPLOAD_BYTES,
                        )
                        size = len(data)
                        with MEMORY_FILES_LOCK:
                            MEMORY_FILES[item_id] = {"data": data, "size": size, "created_at": time.time()}
                        memory_ids.append(item_id)
                    else:
                        stored_name = f"{item_id}.bin"
                        upload_path = stored_path(stored_name)
                        if not upload_path:
                            raise ValueError("文件路径创建失败")
                        size, is_done = self.read_part_to_file(
                            upload_path,
                            boundary_line,
                            closing_boundary_line,
                            remaining,
                        )
                        written_paths.append(upload_path)
                    if size <= 0:
                        raise ValueError("不能上传空文件")
                    files.append(
                        {
                            "id": item_id,
                            "filename": safe_filename(filename),
                            "stored_name": stored_name,
                            "storage_backend": storage_backend,
                            "mime_type": mime_type,
                            "size": size,
                        }
                    )
                else:
                    value_bytes, is_done = self.read_part_to_memory(
                        boundary_line,
                        closing_boundary_line,
                        remaining,
                        FIELD_MAX_BYTES,
                    )
                    if name:
                        fields[name] = value_bytes.decode("utf-8", errors="replace")
        except ValueError as exc:
            for path in written_paths:
                path.unlink(missing_ok=True)
            for item_id in memory_ids:
                remove_memory_file(item_id)
            return self.send_error_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, str(exc))
        except OSError as exc:
            for path in written_paths:
                path.unlink(missing_ok=True)
            for item_id in memory_ids:
                remove_memory_file(item_id)
            if exc.errno == errno.ENOSPC:
                message = "硬盘已满，文件写入失败。请删除旧文件、等待自动清理，或扩容后再试。"
                return self.send_error_json(HTTPStatus.INSUFFICIENT_STORAGE, message)
            return self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "文件写入失败")

        if not files:
            return self.send_error_json(HTTPStatus.BAD_REQUEST, "没有收到文件")

        now = int(time.time())
        created: list[dict[str, object]] = []
        try:
            with db() as conn:
                cleanup_expired(conn)
                for file_info in files:
                    conn.execute(
                        """
                        INSERT INTO items (
                            id, kind, filename, stored_name, storage_backend, mime_type, size, created_at, expires_at
                        )
                        VALUES (?, 'file', ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            file_info["id"],
                            file_info["filename"],
                            file_info["stored_name"],
                            file_info["storage_backend"],
                            file_info["mime_type"],
                            file_info["size"],
                            now,
                            expires_from_value(fields.get("expiresInSeconds"), now),
                        ),
                    )
                    row = conn.execute("SELECT * FROM items WHERE id = ?", (file_info["id"],)).fetchone()
                    created.append(item_to_dict(row))
                trim_items(conn)
        except sqlite3.Error:
            for path in written_paths:
                path.unlink(missing_ok=True)
            for item_id in memory_ids:
                remove_memory_file(item_id)
            return self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "记录文件失败")
        self.send_json({"items": created}, HTTPStatus.CREATED)

    def handle_delete(self, raw_id: str) -> None:
        item_id = unquote(raw_id)
        with db() as conn:
            row = conn.execute(
                "SELECT id, stored_name, storage_backend FROM items WHERE id = ?",
                (item_id,),
            ).fetchone()
            if not row:
                return self.send_error_json(HTTPStatus.NOT_FOUND, "内容不存在")
            remove_item_storage(row)
            conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        self.send_json({"ok": True})

    def handle_clear(self) -> None:
        with db() as conn:
            rows = conn.execute("SELECT id, stored_name, storage_backend FROM items").fetchall()
            for row in rows:
                remove_item_storage(row)
            conn.execute("DELETE FROM items")
        self.send_json({"ok": True})

    def handle_download(self, raw_id: str) -> None:
        item_id = unquote(raw_id)
        with db() as conn:
            cleanup_expired(conn)
            row = conn.execute("SELECT * FROM items WHERE id = ? AND kind = 'file'", (item_id,)).fetchone()
        if not row:
            return self.send_error_json(HTTPStatus.NOT_FOUND, "文件不存在或已过期")

        filename = row["filename"] or "download"
        ascii_name = filename.encode("ascii", errors="ignore").decode("ascii") or "download"
        disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"

        backend = row["storage_backend"] or "disk"
        if backend == "memory":
            with MEMORY_FILES_LOCK:
                memory_entry = MEMORY_FILES.get(row["id"])
                data = memory_entry.get("data") if memory_entry else None
            if data is None:
                with db() as conn:
                    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
                return self.send_error_json(HTTPStatus.NOT_FOUND, "内存文件已失效")
            self.send_response(HTTPStatus.OK)
            self.send_cors_headers()
            self.send_header("Content-Type", row["mime_type"] or "application/octet-stream")
            self.send_header("Content-Disposition", disposition)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return

        path = stored_path(row["stored_name"])
        if not path or not path.is_file():
            return self.send_error_json(HTTPStatus.NOT_FOUND, "文件不存在")

        self.send_response(HTTPStatus.OK)
        self.send_cors_headers()
        self.send_header("Content-Type", row["mime_type"] or "application/octet-stream")
        self.send_header("Content-Disposition", disposition)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with path.open("rb") as file_obj:
            shutil.copyfileobj(file_obj, self.wfile)

    def serve_static(self, path: str) -> None:
        if path == "/":
            target = STATIC_DIR / "index.html"
        elif path.startswith("/static/"):
            target = STATIC_DIR / unquote(path.removeprefix("/static/"))
        else:
            return self.send_error_json(HTTPStatus.NOT_FOUND, "页面不存在")

        target = target.resolve()
        try:
            target.relative_to(STATIC_DIR.resolve())
        except ValueError:
            return self.send_error_json(HTTPStatus.FORBIDDEN, "禁止访问")
        if not target.is_file():
            return self.send_error_json(HTTPStatus.NOT_FOUND, "文件不存在")

        body = target.read_bytes()
        mime_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix == ".html":
            mime_type = "text/html; charset=utf-8"
        elif target.suffix == ".css":
            mime_type = "text/css; charset=utf-8"
        elif target.suffix == ".js":
            mime_type = "text/javascript; charset=utf-8"

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if target.suffix == ".html" else "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="内网文本和小文件中转站")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8765")))
    args = parser.parse_args()

    ensure_storage()
    server = ThreadingHTTPServer((args.host, args.port), ClipboardHandler)
    actual_host, actual_port = server.server_address[:2]
    local_url = f"http://127.0.0.1:{actual_port}"
    lan_ip = get_lan_ip()

    print("内网中转站已启动")
    print(f"本机访问: {local_url}")
    if lan_ip:
        print(f"内网访问: http://{lan_ip}:{actual_port}")
    print(f"数据目录: {DATA_DIR}")
    print(f"上传限制: {MAX_UPLOAD_BYTES // 1024 // 1024} MB")
    print("访问码: " + ("已启用" if ACCESS_CODE else "未启用"))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止服务")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
