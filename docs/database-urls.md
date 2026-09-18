# 数据库连接中的特殊字符

MySQL/PostgreSQL 的初始化连接与正式连接均使用 SQLAlchemy `URL.create()`。
用户名和密码可以直接包含 URL 保留字符，无需用户手工百分号编码。
SQLite 的路径也使用结构化 URL 传入。
