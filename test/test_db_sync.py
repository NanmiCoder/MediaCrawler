# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/test/test_db_sync.py
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

# @Author  : persist-1<persist1@126.com>
# @Time    : 2025/9/8 00:02
# @Desc    : 用于将orm映射模型（database/models.py）与两种数据库实际结构进行对比，并进行更新操作（连接数据库->结构比对->差异报告->交互式同步）
# @Tips    : 该脚本需要安装依赖'pymysql==1.1.0'

import os
import sys
from sqlalchemy import create_engine, inspect as sqlalchemy_inspect
from sqlalchemy.schema import MetaData

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.db_config import mysql_db_config, sqlite_db_config
from database.models import Base

def get_mysql_engine():
    """创建并返回一个MySQL数据库引擎"""
    conn_str = f"mysql+pymysql://{mysql_db_config['user']}:{mysql_db_config['password']}@{mysql_db_config['host']}:{mysql_db_config['port']}/{mysql_db_config['db_name']}"
    return create_engine(conn_str)

def get_sqlite_engine():
    """创建并返回一个SQLite数据库引擎"""
    conn_str = f"sqlite:///{sqlite_db_config['db_path']}"
    return create_engine(conn_str)

def get_db_schema(engine):
    """获取数据库的当前表结构"""
    inspector = sqlalchemy_inspect(engine)
    schema = {}
    for table_name in inspector.get_table_names():
        columns = {}
        for column in inspector.get_columns(table_name):
            columns[column['name']] = str(column['type'])
        schema[table_name] = columns
    return schema

def get_orm_schema():
    """获取ORM模型的表结构"""
    schema = {}
    for table_name, table in Base.metadata.tables.items():
        columns = {}
        for column in table.columns:
            columns[column.name] = str(column.type)
        schema[table_name] = columns
    return schema

def compare_schemas(db_schema, orm_schema):
    """比较数据库结构和ORM模型结构，返回差异"""
    db_tables = set(db_schema.keys())
    orm_tables = set(orm_schema.keys())

    added_tables = orm_tables - db_tables
    deleted_tables = db_tables - orm_tables
    common_tables = db_tables.intersection(orm_tables)

    changed_tables = {}

    for table in common_tables:
        db_cols = set(db_schema[table].keys())
        orm_cols = set(orm_schema[table].keys())
        added_cols = orm_cols - db_cols
        deleted_cols = db_cols - orm_cols

        modified_cols = {}
        for col in db_cols.intersection(orm_cols):
            if db_schema[table][col] != orm_schema[table][col]:
                modified_cols[col] = (db_schema[table][col], orm_schema[table][col])

        if added_cols or deleted_cols or modified_cols:
            changed_tables[table] = {
                "added": list(added_cols),
                "deleted": list(deleted_cols),
                "modified": modified_cols
            }

    return {
        "added_tables": list(added_tables),
        "deleted_tables": list(deleted_tables),
        "changed_tables": changed_tables
    }

def print_diff(db_name, diff):
    """打印差异报告"""
    print(f"--- {db_name} 数据库结构差异报告 ---")
    if not any(diff.values()):
        print("数据库结构与ORM模型一致，无需同步。")
        return

    if diff.get("added_tables"):
        print("\n[+] 新增的表:")
        for table in diff["added_tables"]:
            print(f"  - {table}")

    if diff.get("deleted_tables"):
        print("\n[-] 删除的表:")
        for table in diff["deleted_tables"]:
            print(f"  - {table}")

    if diff.get("changed_tables"):
        print("\n[*] 变动的表:")
        for table, changes in diff["changed_tables"].items():
            print(f"  - {table}:")
            if changes.get("added"):
                print("    [+] 新增字段:", ", ".join(changes["added"]))
            if changes.get("deleted"):
                print("    [-] 删除字段:", ", ".join(changes["deleted"]))
            if changes.get("modified"):
                print("    [*] 修改字段:")
                for col, types in changes["modified"].items():
                    print(f"      - {col}: {types[0]} -> {types[1]}")
    print("--- 报告结束 ---")


def sync_database(engine, diff):
    """将ORM模型同步到数据库"""
    metadata = Base.metadata

    # Alembic的上下文配置
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    conn = engine.connect()
    ctx = MigrationContext.configure(conn)
    op = Operations(ctx)

    # 处理删除的表
    for table_name in diff['deleted_tables']:
        op.drop_table(table_name)
        print(f"已删除表: {table_name}")

    # 处理新增的表
    for table_name in diff['added_tables']:
        table = metadata.tables.get(table_name)
        if table is not None:
            table.create(engine)
            print(f"已创建表: {table_name}")

    # 处理字段变更
    for table_name, changes in diff['changed_tables'].items():
        # 删除字段
        for col_name in changes['deleted']:
            op.drop_column(table_name, col_name)
            print(f"在表 {table_name} 中已删除字段: {col_name}")
        # 新增字段
        for col_name in changes['added']:
            table = metadata.tables.get(table_name)
            column = table.columns.get(col_name)
            if column is not None:
                op.add_column(table_name, column)
                print(f"在表 {table_name} 中已新增字段: {col_name}")

        # 修改字段
        for col_name, types in changes['modified'].items():
            table = metadata.tables.get(table_name)
            if table is not None:
                column = table.columns.get(col_name)
                if column is not None:
                    op.alter_column(table_name, col_name, type_=column.type)
                    print(f"在表 {table_name} 中已修改字段: {col_name} (类型变为 {column.type})")


def main():
    """主函数"""
    orm_schema = get_orm_schema()

    # 处理 MySQL
    try:
        mysql_engine = get_mysql_engine()
        mysql_schema = get_db_schema(mysql_engine)
        mysql_diff = compare_schemas(mysql_schema, orm_schema)
        print_diff("MySQL", mysql_diff)
        if any(mysql_diff.values()):
            choice = input(">>> 需要人工确认：是否要将ORM模型同步到MySQL数据库? (y/N): ")
            if choice.lower() == 'y':
                sync_database(mysql_engine, mysql_diff)
                print("MySQL数据库同步完成。")
    except Exception as e:
        print(f"处理MySQL时出错: {e}")


    # 处理 SQLite
    try:
        sqlite_engine = get_sqlite_engine()
        sqlite_schema = get_db_schema(sqlite_engine)
        sqlite_diff = compare_schemas(sqlite_schema, orm_schema)
        print_diff("SQLite", sqlite_diff)
        if any(sqlite_diff.values()):
            choice = input(">>> 需要人工确认：是否要将ORM模型同步到SQLite数据库? (y/N): ")
            if choice.lower() == 'y':
                # 注意：SQLite不支持ALTER COLUMN来修改字段类型，这里简化处理
                print("警告：SQLite的字段修改支持有限，此脚本不会执行修改字段类型的操作。")
                sync_database(sqlite_engine, sqlite_diff)
                print("SQLite数据库同步完成。")
    except Exception as e:
        print(f"处理SQLite时出错: {e}")


if __name__ == "__main__":
    main()

######################### Feedback example #########################
# [*] 变动的表:
#   - kuaishou_video:
#     [*] 修改字段:
#       - user_id: TEXT -> VARCHAR(64)
#   - xhs_note_comment:
#     [*] 修改字段:
#       - comment_id: BIGINT -> VARCHAR(255)
#   - zhihu_content:
#     [*] 修改字段:
#       - created_time: BIGINT -> VARCHAR(32)
#       - content_id: BIGINT -> VARCHAR(64)
#   - zhihu_creator:
#     [*] 修改字段:
#       - user_id: INTEGER -> VARCHAR(64)
#   - tieba_note:
#     [*] 修改字段:
#       - publish_time: BIGINT -> VARCHAR(255)
#       - tieba_id: INTEGER -> VARCHAR(255)
#       - note_id: BIGINT -> VARCHAR(644)
# --- 报告结束 ---
# >>> 需要人工确认：是否要将ORM模型同步到MySQL数据库? (y/N): y
# 在表 kuaishou_video 中已修改字段: user_id (类型变为 VARCHAR(64))
# 在表 xhs_note_comment 中已修改字段: comment_id (类型变为 VARCHAR(255))
# 在表 zhihu_content 中已修改字段: created_time (类型变为 VARCHAR(32))
# 在表 zhihu_content 中已修改字段: content_id (类型变为 VARCHAR(64))
# 在表 zhihu_creator 中已修改字段: user_id (类型变为 VARCHAR(64))
# 在表 tieba_note 中已修改字段: publish_time (类型变为 VARCHAR(255))
# 在表 tieba_note 中已修改字段: tieba_id (类型变为 VARCHAR(255))
# 在表 tieba_note 中已修改字段: note_id (类型变为 VARCHAR(644))
# MySQL数据库同步完成。
