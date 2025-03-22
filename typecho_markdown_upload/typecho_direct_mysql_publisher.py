import pymysql
import time
from pymysql.converters import escape_string

class TypechoDirectMysqlPublisher:
    def __init__(self, host, port, user, password, database, table_prefix):
        self.__table_prefix = table_prefix
        self.__categories_table_name = table_prefix + 'metas'
        self.__relationships_table_name = table_prefix + 'relationships'
        self.__contents_table_name = table_prefix + 'contents'
        self.__db = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        self.__init_categories()

    def __init_categories(self):
        """
        初始化分类列表到 self.__exist_categories
        """
        cursor = self.__db.cursor()
        sql = f"SELECT mid, name FROM {self.__categories_table_name} WHERE type='category'"
        cursor.execute(sql)
        results = cursor.fetchall()
        self.__exist_categories = []
        for item in results:
            self.__exist_categories.append({
                'mid': item[0],
                'name': item[1]
            })

    def __get_category_id(self, category_name):
        for item in self.__exist_categories:
            if item['name'] == category_name:
                return item['mid']
        return -1

    def __add_category(self, category_name):
        """
        如果分类不存在，则插入一条新分类
        """
        cursor = self.__db.cursor()
        sql = (
            f"INSERT INTO {self.__categories_table_name} "
            "(`name`, `slug`, `type`, `description`, `count`, `order`, `parent`) "
            f"VALUES ('{category_name}', '{category_name}', 'category', '', 0, 1, 0)"
        )
        cursor.execute(sql)
        mid = cursor.lastrowid
        self.__db.commit()

        # 重新初始化分类缓存，避免重复插入
        self.__init_categories()
        return mid

    def __insert_relationship(self, cursor, cid, mid):
        """
        在 typecho_relationships 中插入文章与分类的关联
        """
        insert_relationship_sql = (
            f"INSERT INTO {self.__relationships_table_name} "
            f"(`cid`, `mid`) "
            f"VALUES ({cid}, {mid})"
        )
        cursor.execute(insert_relationship_sql)

    def __update_category_count(self, cursor, mid):
        """
        分类下文章数 +1
        """
        update_category_count_sql = (
            f"UPDATE {self.__categories_table_name} SET `count`=`count`+1 WHERE mid={mid}"
        )
        cursor.execute(update_category_count_sql)

    def normalize_content(content):
        return content.replace('\r\n', '\n').replace('\r', '\n').strip()

    def publish_post(self, title, content, category):
        """
        如果 (category, title) 已存在，则对比旧内容与新内容：
            - 若内容相同，则跳过更新
            - 若内容不同，则更新
        否则插入新文章
        """
        cursor = self.__db.cursor()

        # 1. 获取分类 ID（若不存在则新建）
        mid = self.__get_category_id(category)
        if mid < 0:
            mid = self.__add_category(category)

        # 2. 查找同一分类下，是否已存在相同 title 的文章
        check_sql = f"""
            SELECT c.cid, c.text
            FROM {self.__contents_table_name} c
            JOIN {self.__relationships_table_name} r ON c.cid = r.cid
            WHERE c.title = '{escape_string(title)}'
              AND r.mid = {mid}
            LIMIT 1
        """
        cursor.execute(check_sql)
        exist_row = cursor.fetchone()

        now_time_int = int(time.time())
        content_with_mark = '<!--markdown-->' + content  # 新内容加上标记
        escaped_content = escape_string(content_with_mark)

        if exist_row:
            # ========== 执行更新逻辑 ==========
            cid = exist_row[0]
            old_content = exist_row[1] or ""

            if self.normalize_content(old_content) == self.normalize_content(content_with_mark):
                # 内容相同，不更新
                print(f"[INFO] 文章已存在且内容未修改: title={title}, cid={cid}, category={category}，跳过更新。")
                return cid
            else:
                # 内容不同，执行更新
                update_sql = f"""
                    UPDATE {self.__contents_table_name}
                    SET modified={now_time_int},
                        text='{escaped_content}'
                    WHERE cid={cid}
                """
                cursor.execute(update_sql)
                print(f"[INFO] 更新文章成功: title={title}, cid={cid}, category={category}")

        else:
            # ========== 执行插入逻辑 ==========
            insert_sql = (
                f"INSERT INTO {self.__contents_table_name} "
                "(`title`, `slug`, `created`, `modified`, `text`, `order`, `authorId`, `template`, `type`, `status`, `password`, `commentsNum`, `allowComment`, `allowPing`, `allowFeed`, `parent`) "
                f"VALUES ('{escape_string(title)}', NULL, {now_time_int}, {now_time_int}, '{escaped_content}', 0, 1, NULL, 'post', 'publish', NULL, 0, '1', '1', '1', 0)"
            )
            cursor.execute(insert_sql)
            cid = cursor.lastrowid

            # slug = cid
            update_slug_sql = f"UPDATE {self.__contents_table_name} SET slug={cid} WHERE cid={cid}"
            cursor.execute(update_slug_sql)

            # 建立文章与分类的关系
            self.__insert_relationship(cursor, cid, mid)

            # 分类下文章数 +1
            self.__update_category_count(cursor, mid)

            print(f"[INFO] 插入新文章成功: title={title}, cid={cid}, category={category}")

        # 3. 提交事务
        self.__db.commit()
        return cid
