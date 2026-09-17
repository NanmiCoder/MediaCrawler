# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/media_server.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""媒体下载测试用的本地 HTTP 服务器。

基于标准库 ``ThreadingHTTPServer``，不引入额外依赖；覆盖下载器需要面对的各种
CDN 行为：Range 续传、忽略 Range、chunked、响应截断、5xx 抖动、302 跳转、
无扩展名但带 Content-Type、慢响应、空响应体等。

所有请求都会记录到 ``server.requests``，用于断言"跳过已下载时不发请求"
"403 只请求一次"这类行为。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlsplit

# 可识别的字节模式，便于断言续传后拼接结果正确
DEFAULT_CONTENT = bytes(range(256)) * 16  # 4096 字节
DEFAULT_CONTENT_TYPE = "image/jpeg"


@dataclass
class RequestRecord:
    """一次进入服务器的请求"""

    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)


class _MediaRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "MediaTestServer/1.0"

    # 静音默认的 stderr 访问日志
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return

    # ------------------------------------------------------------------ 工具方法

    @property
    def media_server(self) -> "MediaTestServer":
        return self.server.media_server  # type: ignore[attr-defined]

    def _record(self) -> None:
        self.media_server.requests.append(
            RequestRecord(
                method=self.command,
                path=self.path,
                headers={key.lower(): value for key, value in self.headers.items()},
            )
        )

    def _content_for(self, name: str) -> bytes:
        custom = self.media_server.contents.get(name)
        return custom if custom is not None else DEFAULT_CONTENT

    def _send_body(self, status: int, body: bytes, content_type: str, extra_headers=None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _parse_range(self) -> Optional[int]:
        """解析 ``Range: bytes=N-``，返回起始偏移；不合法或不存在返回 None"""
        raw = self.headers.get("range", "")
        if not raw.startswith("bytes="):
            return None
        spec = raw[len("bytes=") :].split(",")[0].strip()
        if not spec.endswith("-"):
            return None
        start = spec[:-1].strip()
        return int(start) if start.isdigit() else None

    # ------------------------------------------------------------------ 路由

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 约定
        self._record()
        parsed = urlsplit(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            if path.startswith("/status/"):
                code = int(path.rsplit("/", 1)[-1])
                self._send_body(code, b"", "text/plain")
            elif path.startswith("/ok/") or path.startswith("/redirected/"):
                self._handle_ok(path.rsplit("/", 1)[-1], query)
            elif path.startswith("/no-range/"):
                self._handle_no_range(path.rsplit("/", 1)[-1])
            elif path.startswith("/wrong-range/"):
                self._handle_wrong_range(path.rsplit("/", 1)[-1], query)
            elif path.startswith("/poison-206/"):
                self._handle_poison_206(path.rsplit("/", 1)[-1], query)
            elif path.startswith("/gzip/"):
                self._handle_gzip(path.rsplit("/", 1)[-1], query)
            elif path.startswith("/unknown-total/"):
                self._handle_unknown_total(path.rsplit("/", 1)[-1])
            elif path.startswith("/no-content-range/"):
                self._handle_no_content_range(path.rsplit("/", 1)[-1])
            elif path.startswith("/chunked-bogus-cl/"):
                self._handle_chunked_with_bogus_content_length(path.rsplit("/", 1)[-1])
            elif path.startswith("/chunked/"):
                self._handle_chunked(path.rsplit("/", 1)[-1])
            elif path.startswith("/truncated/"):
                self._handle_truncated(path.rsplit("/", 1)[-1], query)
            elif path.startswith("/flaky/"):
                self._handle_flaky(path.rsplit("/", 1)[-1], query)
            elif path.startswith("/redirect/"):
                self._handle_redirect(path.rsplit("/", 1)[-1])
            elif path.startswith("/ctyped/"):
                self._handle_ctyped(path.rsplit("/", 1)[-1])
            elif path.startswith("/slow/"):
                self._handle_slow(path.rsplit("/", 1)[-1], query)
            elif path.startswith("/empty/"):
                self._send_body(200, b"", DEFAULT_CONTENT_TYPE)
            else:
                self._send_body(404, b"not found", "text/plain")
        except (BrokenPipeError, ConnectionResetError):  # 客户端主动断开
            self.close_connection = True

    # ------------------------------------------------------------------ 各路由实现

    def _handle_ok(self, name: str, query) -> None:
        """正常文件，支持 Range 续传"""
        content = self._content_for(name)
        total = len(content)
        start = self._parse_range()

        if start is not None:
            if start >= total:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{total}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            body = content[start:]
            content_type = query.get("ct", [DEFAULT_CONTENT_TYPE])[0]
            self._send_body(
                206,
                body,
                content_type,
                {"Content-Range": f"bytes {start}-{total - 1}/{total}"},
            )
            return

        self._send_body(200, content, query.get("ct", [DEFAULT_CONTENT_TYPE])[0])

    def _handle_wrong_range(self, name: str, query) -> None:
        """返回 206 但 Content-Range 起点与请求不一致（模拟按关键帧对齐的加速节点）。

        ``?fail=N``：前 N 次返回错位响应，之后恢复正常，
        用于验证"下载器丢弃片段重下后能成功"。
        """
        fail_times = int(query.get("fail", ["1000"])[0])
        counter_key = f"/wrong-range/{name}"
        with self.media_server.lock:
            seen = self.media_server.counters.get(counter_key, 0)
            self.media_server.counters[counter_key] = seen + 1

        if seen >= fail_times:
            self._handle_ok(name, query)
            return

        content = self._content_for(name)
        total = len(content)
        requested = self._parse_range() or 0
        delta = int(query.get("delta", ["100"])[0])
        start = min(requested + delta, total - 1)
        self._send_body(
            206,
            content[start:],
            DEFAULT_CONTENT_TYPE,
            {"Content-Range": f"bytes {start}-{total - 1}/{total}"},
        )

    def _handle_poison_206(self, name: str, query) -> None:
        """206 声明非 0 起点，但 body 长度**恰好等于 total**（内容是错位的）。

        这是唯一能单独验证"起点守卫"的响应：长度自洽，大小校验拦不住，
        只有比对 Content-Range 起点才能发现异常。
        """
        content = self._content_for(name)
        total = len(content)
        start = int(query.get("start", ["100"])[0])
        body = content[start:] + b"\x00" * start
        self._send_body(
            206,
            body,
            DEFAULT_CONTENT_TYPE,
            {"Content-Range": f"bytes {start}-{total - 1}/{total}"},
        )

    def _handle_gzip(self, name: str, query) -> None:
        """无视 Accept-Encoding: identity，强制返回 gzip 压缩体"""
        import gzip

        content = self._content_for(name)
        compressed = gzip.compress(content)
        self.send_response(200)
        self.send_header("Content-Type", DEFAULT_CONTENT_TYPE)
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(compressed)))
        self.end_headers()
        self.wfile.write(compressed)

    def _handle_unknown_total(self, name: str) -> None:
        """206 只返回区间的一部分，且 Content-Range 的 total 为 *（不告知总长）"""
        content = self._content_for(name)
        start = self._parse_range() or 0
        chunk = content[start : start + 1024]
        self._send_body(
            206,
            chunk,
            DEFAULT_CONTENT_TYPE,
            {"Content-Range": f"bytes {start}-{start + len(chunk) - 1}/*"},
        )

    def _handle_no_content_range(self, name: str) -> None:
        """206 但缺少 Content-Range（违反 RFC 9110），且回的是全量体"""
        content = self._content_for(name)
        self._send_body(206, content, DEFAULT_CONTENT_TYPE)

    def _handle_chunked_with_bogus_content_length(self, name: str) -> None:
        """chunked 传输同时带一个错误的 Content-Length（RFC 7230 要求忽略后者）"""
        content = self._content_for(name)
        self.send_response(200)
        self.send_header("Content-Type", DEFAULT_CONTENT_TYPE)
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Content-Length", "999")
        self.end_headers()
        self.wfile.write(f"{len(content):X}\r\n".encode("ascii"))
        self.wfile.write(content)
        self.wfile.write(b"\r\n0\r\n\r\n")
        self.wfile.flush()

    def _handle_no_range(self, name: str) -> None:
        """声明支持 Range 但始终返回全量 200（模拟不支持续传的 CDN）"""
        content = self._content_for(name)
        self._send_body(200, content, DEFAULT_CONTENT_TYPE, {"Accept-Ranges": "bytes"})

    def _handle_chunked(self, name: str) -> None:
        """chunked 传输：无 Content-Length"""
        content = self._content_for(name)
        self.send_response(200)
        self.send_header("Content-Type", DEFAULT_CONTENT_TYPE)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        for offset in range(0, len(content), 1024):
            chunk = content[offset : offset + 1024]
            self.wfile.write(f"{len(chunk):X}\r\n".encode("ascii"))
            self.wfile.write(chunk)
            self.wfile.write(b"\r\n")
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    def _handle_truncated(self, name: str, query) -> None:
        """声明完整长度但只发送一半后断开连接。

        ``?fail=N``：前 N 次截断，之后恢复正常（支持 Range），
        用于验证"断流 -> 重试 -> 带 Range 续传 -> 拼接完整"。
        """
        fail_times = int(query.get("fail", ["1000"])[0])
        counter_key = f"/truncated/{name}"
        with self.media_server.lock:
            seen = self.media_server.counters.get(counter_key, 0)
            self.media_server.counters[counter_key] = seen + 1

        if seen >= fail_times:
            self._handle_ok(name, query)
            return

        content = self._content_for(name)
        self.send_response(200)
        self.send_header("Content-Type", DEFAULT_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content[: len(content) // 2])
        self.wfile.flush()
        self.close_connection = True
        try:
            self.connection.shutdown(2)  # SHUT_RDWR
        except OSError:
            pass

    def _handle_flaky(self, name: str, query) -> None:
        """前 N 次请求返回 500，之后正常（服务端计数）"""
        fail_times = int(query.get("fail", ["1"])[0])
        counter_key = f"/flaky/{name}"
        with self.media_server.lock:
            seen = self.media_server.counters.get(counter_key, 0)
            self.media_server.counters[counter_key] = seen + 1
        if seen < fail_times:
            self._send_body(500, b"server error", "text/plain")
            return
        content = self._content_for(name)
        self._send_body(200, content, DEFAULT_CONTENT_TYPE)

    def _handle_redirect(self, name: str) -> None:
        self.send_response(302)
        self.send_header("Location", f"/ok/{name}")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _handle_ctyped(self, name: str) -> None:
        """URL 无扩展名，靠 Content-Type 推断"""
        content_type = self.media_server.content_types.get(name, "image/webp")
        self._send_body(200, self._content_for(name), content_type)

    def _handle_slow(self, name: str, query) -> None:
        delay = float(query.get("s", ["1"])[0])
        time.sleep(delay)
        self._send_body(200, self._content_for(name), DEFAULT_CONTENT_TYPE)


class MediaTestServer(ThreadingHTTPServer):
    """带请求记录能力的本地测试服务器"""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _MediaRequestHandler)
        # handler 通过 server.media_server 反向访问这些状态
        self.media_server: "MediaTestServer" = self
        self.requests: List[RequestRecord] = []
        self.counters: Dict[str, int] = {}
        self.contents: Dict[str, bytes] = {}
        self.content_types: Dict[str, str] = {}
        self.lock = threading.Lock()

    # ------------------------------------------------------------------ 测试辅助

    @property
    def base_url(self) -> str:
        host, port = self.server_address[:2]
        return f"http://{host}:{port}"

    def url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def reset(self) -> None:
        """清空请求记录与计数器（内容配置保留）"""
        with self.lock:
            self.requests.clear()
            self.counters.clear()

    def set_content(self, name: str, content: bytes) -> None:
        self.contents[name] = content

    def set_content_type(self, name: str, content_type: str) -> None:
        self.content_types[name] = content_type

    @property
    def request_count(self) -> int:
        return len(self.requests)

    def paths(self) -> List[str]:
        return [record.path for record in self.requests]

    def last_request(self) -> Optional[RequestRecord]:
        return self.requests[-1] if self.requests else None


def start_server() -> Tuple[MediaTestServer, threading.Thread]:
    """在后台线程启动服务器，返回 (server, thread)"""
    server = MediaTestServer()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread
