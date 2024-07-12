from httpx import RequestError


class DataFetchError(RequestError):
    """something error when fetch"""
    # 取回时出错


class IPBlockError(RequestError):
    """fetch so fast that the server block us ip"""
    # 获取太快以至于服务器阻塞了我们的IP
