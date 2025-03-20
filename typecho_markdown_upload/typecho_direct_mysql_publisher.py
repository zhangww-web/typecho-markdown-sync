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
        sql = "SELECT mid, name FROM %s WHERE type='category'" % self.__categories_table_name
        cursor.execute(sql)
        results = cursor.fetchall()
        self.__exist_categories = []
        for item in results:
            self.__exist_categories.append({
                'mid': item[0],
                'name': item[1]
            })

    def __get_category_id(self, category_name):
        """
        从 self.__exist_categories 查找匹配的分类 ID
        """
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
            "INSERT INTO %s "
            "(`name`, `slug`, `type`, `description`, `count`, `order`, `parent`) "
            "VALUES "
            "('%s', '%s', 'category', '', 0, 1, 0)"
        ) % (self.__categories_table_name, category_name, category_name)
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
            "INSERT INTO %s "
            "(`cid`, `mid`) "
            "VALUES "
            "(%d, %d)"
        ) % (self.__relationships_table_name, cid, mid)
        cursor.execute(insert_relationship_sql)

    def __update_category_count(self, cursor, mid):
        """
        分类下文章数 +1
        """
        update_category_count_sql = (
            "UPDATE %s SET `count`=`count`+1 WHERE mid=%d"
        ) % (self.__categories_table_name, mid)
        cursor.execute(update_category_count_sql)

    def publish_post(self, title, content, category):
        """
        如果同一分类下 (category) 已存在相同 title，则直接返回已存在的 cid；
        否则插入新文章并返回新 cid。
        """
        cursor = self.__db.cursor()

        # 1. 获取分类 ID（不存在则插入）
        mid = self.__get_category_id(category)
        if mid < 0:
            mid = self.__add_category(category)

        # 2. 查重：同一分类下 (mid) 是否已存在相同 title
        #    通过连接 contents & relationships 表判断
        check_sql = """
            SELECT c.cid
            FROM %s c
            JOIN %s r ON c.cid = r.cid
            WHERE c.title = '%s'
              AND r.mid = %d
            LIMIT 1
        """ % (
            self.__contents_table_name,
            self.__relationships_table_name,
            escape_string(title),
            mid
        )
        cursor.execute(check_sql)
        exist_row = cursor.fetchone()
        if exist_row:
            # 已有同标题文章，直接返回
            print(f"[INFO] 发现同一分类下已存在相同标题: {title}, cid={exist_row[0]}，跳过插入。")
            return exist_row[0]

        # 3. 插入新文章
        now_time_int = int(time.time())
        content = '<!--markdown-->' + content

        insert_sql = (
            "INSERT INTO %s "
            "(`title`, `slug`, `created`, `modified`, `text`, `order`, `authorId`, `template`, `type`, `status`, `password`, `commentsNum`, `allowComment`, `allowPing`, `allowFeed`, `parent`) "
            "VALUES "
            "('%s', NULL, %d, %d, '%s', 0, 1, NULL, 'post', 'publish', NULL, 0, '1', '1', '1', 0)"
        ) % (
            self.__contents_table_name,
            escape_string(title),
            now_time_int,
            now_time_int,
            escape_string(content)
        )
        cursor.execute(insert_sql)
        cid = cursor.lastrowid

        # 4. 更新 slug = cid
        update_slug_sql = (
            "UPDATE %s SET slug=%d WHERE cid=%d"
        ) % (self.__contents_table_name, cid, cid)
        cursor.execute(update_slug_sql)

        # 5. 建立文章与分类的关系
        self.__insert_relationship(cursor, cid, mid)

        # 6. 更新分类下文章数
        self.__update_category_count(cursor, mid)

        # 7. 提交
        self.__db.commit()

        print(f"[INFO] 插入新文章成功: title={title}, cid={cid}, category={category}")
        return cid
