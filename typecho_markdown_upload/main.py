#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

from transfer_md.transfer import process_md_file_remote, scan_files, format_mdfile  # 假设该模块中实现了相应函数
from typecho_xmlrpc_publisher import TypechoXmlRpcPublisher
from typecho_direct_mysql_publisher import TypechoDirectMysqlPublisher

# 初始化发布器，直接使用 os.getenv 获取环境变量
typecho_publisher = TypechoXmlRpcPublisher(
    os.getenv('WEBSITE_XMLRPC_URL'),
    os.getenv('WEBSITE_USERNAME'),
    os.getenv('WEBSITE_PASSWORD')
)

mysql_publisher = TypechoDirectMysqlPublisher(
    os.getenv('MYSQL_HOST'),
    int(os.getenv('MYSQL_PORT', 3306)),
    os.getenv('MYSQL_USERNAME'),
    os.getenv('MYSQL_PASSWORD'),
    os.getenv('MYSQL_TYPECHO_DATABASE'),
    os.getenv('MYSQL_TYPECHO_TABLE_PREFIX')
)

def execute_flow_with_typecho_xmlrpc(file_path):
    """
    使用 XML-RPC 接口发布文章。
    这里 process_md_file_remote 用于处理 Markdown 文件（上传本地图片并替换 URL）
    """
    # 先对 Markdown 文件进行处理：上传本地图片并替换为公网地址
    process_md_file_remote(file_path)

    with open(file_path, 'r', encoding='utf-8') as file:
        file_base_name = os.path.splitext(os.path.basename(file_path))[0]
        md_source_text = file.read()
    # 注意：XML-RPC 方式不需要 category_name 参数
    post_id = typecho_publisher.publish_post(file_base_name, md_source_text)
    logging.info('发布成功 --> %s - %s', file_base_name, post_id)


def execute_flow_with_typecho_mysql(file_path):
    """
    使用 MySQL 直连方式发布文章。
    这里 process_md_file_remote 用于处理 Markdown 文件（上传本地图片并替换为公网地址）。
    分类名称将从文件路径的上一级目录中获取。
    """
    format_mdfile(file_path)  #对 Markdown 文件进行处理，会对公式块和代码块进行格式化，可注释这行
    process_md_file_remote(file_path)  #上传本地图片并替换为公网地址

    with open(file_path, 'r', encoding='utf-8') as file:
        file_base_name = os.path.splitext(os.path.basename(file_path))[0]
        md_source_text = file.read()
    # 从文件的上一级目录获取分类名称
    category_name = os.path.basename(os.path.dirname(file_path))
    logging.info(f"category_name：{category_name} file_base_name:{file_base_name}")
    post_id = mysql_publisher.publish_post(file_base_name, md_source_text, category_name)
    logging.info('发布成功 --> %s - %s', file_base_name, post_id)


if __name__ == '__main__':
    # 设置日志级别为 INFO，这样可以看到 INFO 级别的日志输出
    logging.basicConfig(level=logging.INFO)

    # 获取 base_folder 和 exclude_folders 配置
    base_folder = os.getenv('BASE_FOLDER')
    exclude_folders = os.getenv('EXCLUDE_FOLDERS', '').split(',')

    files = scan_files(base_folder, exclude_folders)

    for md_file in files:
        # 根据需要选择使用哪种发布方式：
        # execute_flow_with_typecho_xmlrpc(md_file)
        execute_flow_with_typecho_mysql(md_file)
