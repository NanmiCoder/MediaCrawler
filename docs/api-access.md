# WebUI API 访问边界

默认运行 `uv run python -m api.main`，仅监听 `127.0.0.1:8080`。
浏览器通过 `http://localhost:8080` 或 `http://127.0.0.1:8080` 使用 WebUI，无需额外配置。
API 校验回环客户端、Host 与浏览器 Origin；本机 Vite 3000/5173 端口仍可访问。
HTTP 与 WebSocket 使用同一个访问边界，CORS 不是身份验证。

需要远程 API 时，在服务进程环境中设置随机的 `MEDIACRAWLER_API_TOKEN`，
并在每个 HTTP 请求和 WebSocket 握手中发送 `Authorization: Bearer <token>`。
设置 token 后，本机客户端也必须携带它。请在可信 TLS 反向代理后暴露服务，
不要把 token 放入 URL 查询参数或源码。当前 WebUI 没有 token 输入功能；
远程使用浏览器界面可通过 SSH 本地端口转发访问默认回环服务。

命令行自行使用 `uvicorn --host ...` 不会移除 API 的访问检查。反向代理必须可靠地
覆盖转发头；不能通过伪造 Host 或 X-Forwarded-For 将远程匿名请求当成本机请求。
没有 token 时不要把一个把全部用户代理为回环客户端的服务暴露到公网。
