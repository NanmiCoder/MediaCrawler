# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tools/file_header_manager.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

"""
File header copyright declaration management tool

Features:
- Automatically add standardized copyright declaration and disclaimer to Python files
- Intelligently detect existing file headers (encoding declaration, author info, disclaimer, etc.)
- Insert copyright info at appropriate position without breaking existing content
- Support batch processing and single file check mode
"""

import os
import re
import sys
from typing import List, Tuple

# Project configuration
REPO_URL = "https://github.com/NanmiCoder/MediaCrawler"
GITHUB_PROFILE = "https://github.com/NanmiCoder"
EMAIL = "relakkes@gmail.com"
COPYRIGHT_YEAR = "2025"
LICENSE_TYPE = "NON-COMMERCIAL LEARNING LICENSE 1.1"

# Disclaimer standard text
DISCLAIMER = """# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。"""


def get_file_relative_path(file_path: str, project_root: str) -> str:
    """
    Get file path relative to project root

    Args:
        file_path: File absolute path
        project_root: Project root directory

    Returns:
        Relative path string
    """
    return os.path.relpath(file_path, project_root)


def generate_copyright_header(relative_path: str) -> str:
    """
    Generate copyright declaration header

    Args:
        relative_path: File path relative to project root

    Returns:
        Formatted copyright declaration string
    """
    file_url = f"{REPO_URL}/blob/main/{relative_path}"

    header = f"""# Copyright (c) {COPYRIGHT_YEAR} {EMAIL}
#
# This file is part of MediaCrawler project.
# Repository: {file_url}
# GitHub: {GITHUB_PROFILE}
# Licensed under {LICENSE_TYPE}
#"""

    return header


def has_copyright_header(content: str) -> bool:
    """
    Check if file already contains copyright declaration

    Args:
        content: File content

    Returns:
        True if already contains copyright declaration
    """
    # Check if contains Copyright keyword
    return "Copyright (c)" in content and "MediaCrawler project" in content


def has_disclaimer(content: str) -> bool:
    """
    Check if file already contains disclaimer

    Args:
        content: File content

    Returns:
        True if already contains disclaimer
    """
    return "声明：本代码仅供学习和研究目的使用" in content


def find_insert_position(lines: List[str]) -> Tuple[int, bool]:
    """
    Find position to insert copyright declaration

    Args:
        lines: List of file content lines

    Returns:
        (insert line number, whether encoding declaration needs to be added)
    """
    insert_pos = 0
    has_encoding = False

    # Check if first line is shebang
    if lines and lines[0].startswith('#!'):
        insert_pos = 1

    # Check encoding declaration (usually on line 1 or 2)
    for i in range(insert_pos, min(insert_pos + 2, len(lines))):
        if i < len(lines):
            line = lines[i].strip()
            # Match # -*- coding: utf-8 -*- or # coding: utf-8 etc.
            if re.match(r'#.*coding[:=]\s*([-\w.]+)', line):
                has_encoding = True
                insert_pos = i + 1
                break

    return insert_pos, has_encoding


def process_file(file_path: str, project_root: str, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Process single Python file

    Args:
        file_path: File path
        project_root: Project root directory
        dry_run: Check only without modification

    Returns:
        (whether modification needed, status message)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines(keepends=True)

        # Skip if already has copyright header
        if has_copyright_header(content):
            return False, f"✓ Already has copyright header: {file_path}"

        # Get relative path
        relative_path = get_file_relative_path(file_path, project_root)

        # Generate copyright header
        copyright_header = generate_copyright_header(relative_path)

        # Find insert position
        insert_pos, has_encoding = find_insert_position(lines)

        # Build new file content
        new_lines = []

        # Add encoding declaration if not present
        if not has_encoding:
            new_lines.append("# -*- coding: utf-8 -*-\n")

        # Add front part (shebang and encoding declaration)
        new_lines.extend(lines[:insert_pos])

        # Add copyright header
        new_lines.append(copyright_header + "\n")

        # Add disclaimer if file doesn't have one
        if not has_disclaimer(content):
            new_lines.append(DISCLAIMER + "\n")

        # Add empty line (if next line is not empty)
        if insert_pos < len(lines) and lines[insert_pos].strip():
            new_lines.append("\n")

        # Add remaining content
        new_lines.extend(lines[insert_pos:])

        # Write to file if not dry run
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True, f"✓ Updated: {file_path}"
        else:
            return True, f"→ Would update: {file_path}"

    except Exception as e:
        return False, f"✗ Error processing {file_path}: {str(e)}"


def find_python_files(root_dir: str, exclude_patterns: List[str] = None) -> List[str]:
    """
    Find all Python files

    Args:
        root_dir: Root directory
        exclude_patterns: Directory patterns to exclude

    Returns:
        List of Python file paths
    """
    if exclude_patterns is None:
        exclude_patterns = ['venv', '.venv', 'node_modules', '__pycache__', '.git', 'build', 'dist', '.eggs']

    python_files = []

    for root, dirs, files in os.walk(root_dir):
        # Exclude specific directories
        dirs[:] = [d for d in dirs if d not in exclude_patterns and not d.startswith('.')]

        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    return sorted(python_files)


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Python file header copyright declaration management tool')
    parser.add_argument('files', nargs='*', help='File paths to process (optional, defaults to all .py files)')
    parser.add_argument('--dry-run', action='store_true', help='Check only without modifying files')
    parser.add_argument('--project-root', default=None, help='Project root directory (defaults to current directory)')
    parser.add_argument('--check', action='store_true', help='Check mode, return non-zero exit code if files missing copyright declaration')

    args = parser.parse_args()

    # Determine project root directory
    if args.project_root:
        project_root = os.path.abspath(args.project_root)
    else:
        # Assume this script is in tools/ directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print(f"Project root: {project_root}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'UPDATE'}")
    print("-" * 60)

    # Get list of files to process
    if args.files:
        # Process specified files
        files_to_process = [os.path.abspath(f) for f in args.files if f.endswith('.py')]
    else:
        # Process all Python files
        files_to_process = find_python_files(project_root)

    print(f"Found {len(files_to_process)} Python files to process\n")

    # Process files
    updated_count = 0
    skipped_count = 0
    error_count = 0

    for file_path in files_to_process:
        modified, message = process_file(file_path, project_root, args.dry_run or args.check)
        print(message)

        if "Error" in message:
            error_count += 1
        elif modified:
            updated_count += 1
        else:
            skipped_count += 1

    # Print summary
    print("\n" + "=" * 60)
    print(f"Summary:")
    print(f"  Total files: {len(files_to_process)}")
    print(f"  Updated/Need update: {updated_count}")
    print(f"  Already compliant: {skipped_count}")
    print(f"  Errors: {error_count}")
    print("=" * 60)

    # Return non-zero exit code in check mode if files need update
    if args.check and updated_count > 0:
        sys.exit(1)
    elif error_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
