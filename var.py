from contextvars import ContextVar

request_keyword_var: ContextVar[str] = ContextVar("request_keyword", default="")
