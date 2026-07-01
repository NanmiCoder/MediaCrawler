"""
douyin_scraper.api.utils — API 安全工具函数
=============================================
提供路径遍历防护和符号链接检测，防止恶意用户通过 API 参数
访问 workspace 外的文件或通过符号链接逃逸。
"""

from pathlib import Path

from fastapi import HTTPException


def validate_path_in_workspace(path_str: str, workspace: Path) -> Path:
    """
    验证路径 resolve 后必须位于 workspace resolve 路径之下，
    否则抛出 HTTPException(400) 阻止路径遍历攻击。

    Args:
        path_str: 用户提供的路径字符串
        workspace: 允许的工作空间根目录

    Returns:
        resolve 后的合法 Path 对象

    Raises:
        HTTPException: 路径遍历攻击时返回 400
    """
    resolved_workspace = workspace.resolve()
    target = (resolved_workspace / path_str).resolve() if not Path(path_str).is_absolute() else Path(path_str).resolve()

    # 检查 target 是否以 workspace 开头
    try:
        target.relative_to(resolved_workspace)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"路径遍历攻击被阻止: '{path_str}' 不在工作空间 '{resolved_workspace}' 内",
        )

    return target


def validate_no_symlink(file_path: Path) -> Path:
    """
    确保文件不是符号链接，防止通过符号链接读取任意文件。

    Args:
        file_path: 要检查的文件路径

    Returns:
        原始 Path 对象（如果检查通过）

    Raises:
        HTTPException: 文件是符号链接时返回 400
    """
    file_path = Path(file_path)
    if file_path.exists() and file_path.is_symlink():
        raise HTTPException(
            status_code=400,
            detail=f"符号链接不允许: '{file_path}' 是一个符号链接",
        )
    return file_path
