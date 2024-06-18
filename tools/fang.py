import pymysql

# head
tables=["bilibili_video_comment","douyin_aweme_comment","kuaishou_video_comment","weibo_note_comment","xhs_note_comment"]
MERGE='merge'
# body
conn=pymysql.connect(
    host='localhost',
    port=3306,
    user='root',
    password='Pettis+1',
    charset='utf8',
    database='media_crawler'
)   # 连接数据库,database对应数据库
try:
    with conn.cursor() as cursor:  # 建立游标对象,用来执行各种操作
        cursor.execute(f"""DROP TABLE IF EXISTS {MERGE}""")    # 保证删除merge表
        cursor.execute(f"""CREATE TABLE {MERGE}(
            `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
            `content` longtext COMMENT '评论内容',
            `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
            `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
            PRIMARY KEY (`ID`)
        )""")  # 创建merge表
        for table in tables:    # 将全部评论放到一张表中
            cursor.execute(f"""create table fang.{table} as select * from {table}""")   # 复制所哟评论表到fang中
            sql=f"""SELECT `content`,`add_ts`,`last_modify_ts` FROM {table}"""  # 提取评论和时间戳
            cursor.execute(sql)
            rows = cursor.fetchall()    # 一个大元组,里面是小元组(content,add_ts)
            for row in rows:    # 开始插入数据
                cursor.execute(f"""INSERT INTO {MERGE} (`content`,`add_ts`) VALUES (%s,%s)""",row)
        # 删除原来表中的内容
            cursor.execute(f"""truncate table {table}""")
    conn.commit()
finally:
    conn.close()