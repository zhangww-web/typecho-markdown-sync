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
        cursor = self.__db.cursor()
        sql = f"SELECT mid, name FROM {self.__categories_table_name} WHERE type='category'"
        cursor.execute(sql)
        results = cursor.fetchall()
        self.__exist_categories = [{'mid': item[0], 'name': item[1]} for item in results]

    def __get_category_id(self, category_name):
        for item in self.__exist_categories:
            if item['name'] == category_name:
                return item['mid']
        return -1

    def __add_category(self, category_name):
        cursor = self.__db.cursor()
        sql = (
            f"INSERT INTO {self.__categories_table_name} "
            "(`name`, `slug`, `type`, `description`, `count`, `order`, `parent`) "
            f"VALUES ('{escape_string(category_name)}', '{escape_string(category_name)}', 'category', '', 0, 1, 0)"
        )
        cursor.execute(sql)
        mid = cursor.lastrowid
        self.__db.commit()
        self.__init_categories()
        return mid

    def __insert_relationship(self, cursor, cid, mid):
        insert_relationship_sql = (
            f"INSERT INTO {self.__relationships_table_name} (`cid`, `mid`) VALUES ({cid}, {mid})"
        )
        cursor.execute(insert_relationship_sql)

    def __update_category_count(self, cursor, mid):
        update_category_count_sql = (
            f"UPDATE {self.__categories_table_name} SET `count`=`count`+1 WHERE mid={mid}"
        )
        cursor.execute(update_category_count_sql)

    def normalize_content(self, content):
        return content.replace('\r\n', '\n').replace('\r', '\n').strip()

    def publish_post(self, title, content, category):
        cursor = self.__db.cursor()
        mid = self.__get_category_id(category)
        if mid < 0:
            mid = self.__add_category(category)

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
        content_with_mark = '<!--markdown-->' + content

        if exist_row:
            cid = exist_row[0]
            old_content = exist_row[1] or ""
            if self.normalize_content(old_content) == self.normalize_content(content_with_mark):
                print(f"[INFO] 文章已存在且内容未修改: title={title}, cid={cid}, category={category}，跳过更新。")
                return cid
            else:
                update_sql = f"""
                    UPDATE {self.__contents_table_name}
                    SET modified={now_time_int},
                        text='{escape_string(content_with_mark)}'
                    WHERE cid={cid}
                """
                cursor.execute(update_sql)
                print(f"[INFO] 更新文章成功: title={title}, cid={cid}, category={category}")

        else:
            insert_sql = (
                f"INSERT INTO {self.__contents_table_name} "
                "(`title`, `slug`, `created`, `modified`, `text`, `order`, `authorId`, "
                "`template`, `type`, `status`, `password`, `commentsNum`, `allowComment`, "
                "`allowPing`, `allowFeed`, `parent`) "
                f"VALUES ('{escape_string(title)}', NULL, {now_time_int}, {now_time_int}, '{escape_string(content_with_mark)}', "
                "0, 1, NULL, 'post', 'publish', NULL, 0, '1', '1', '1', 0)"
            )
            cursor.execute(insert_sql)
            cid = cursor.lastrowid
            update_slug_sql = f"UPDATE {self.__contents_table_name} SET slug={cid} WHERE cid={cid}"
            cursor.execute(update_slug_sql)
            self.__insert_relationship(cursor, cid, mid)
            self.__update_category_count(cursor, mid)
            print(f"[INFO] 插入新文章成功: title={title}, cid={cid}, category={category}")

        self.__db.commit()
        return cid
