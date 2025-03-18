import uuid
import requests
from urllib.parse import urlparse
import os
import shutil
def download_image(url, output_path):
    """
    从网络下载图片并保存到指定路径
    """
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            # 获取图片扩展名
            parsed_url = urlparse(url)
            ext = os.path.splitext(parsed_url.path)[1]
            if not ext:
                ext = '.png'  # 默认使用 .png 扩展名

            # 生成新的文件名
            new_filename = f"{uuid.uuid4()}{ext}"
            dest_path = os.path.join(output_path, new_filename)

            # 保存图片
            with open(dest_path, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            print(f"已下载: {url} → {dest_path}")
            return new_filename
        else:
            print(f"警告: 无法下载图片 {url}，状态码: {response.status_code}")
    except Exception as e:
        print(f"错误: 下载图片 {url} 时出错: {e}")
    return None