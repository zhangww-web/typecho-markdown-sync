import os
import requests
# 加载 .env 文件中的环境变量
from dotenv import load_dotenv

load_dotenv()
def upload_image(img_path: str) -> str:
    """
    上传本地图片到 easyimage 图床，并返回图片的公网地址。

    参数:
      img_path: 本地图片路径

    返回:
      图片在图床上的公网地址

    API 参数说明：
      - API 地址: 图床提供的API
      - 图片文件对应的 POST 参数名: image
      - 自定义 body 参数: {"token": "xxxxxx"}
      - 响应 JSON 中的图片地址字段路径: url
    """
    url = os.getenv('IMG_URL')
    token = os.getenv('IMG_TOKEN')

    try:
        with open(img_path, "rb") as f:
            files = {"image": f}
            data = {"token": token}
            response = requests.post(url, files=files, data=data)

        # 检查响应状态码是否为 200 OK
        if response.status_code == 200:
            result = response.json()
            public_url = result.get("url")
            if public_url:
                return public_url
            else:
                raise ValueError("响应中未找到图片地址")
        else:
            raise Exception(f"上传失败，状态码: {response.status_code}, 响应内容: {response.text}")
    except Exception as e:
        raise Exception(f"上传过程中发生错误: {e}")


# 示例调用
if __name__ == "__main__":
    img_path = r"C:\Users\zhangsan\Pictures\社会实践\1.png"  # 替换为实际图片路径
    try:
        public_address = upload_image(img_path)
        print("图片上传成功，公网地址:", public_address)
    except Exception as err:
        print("图片上传失败:", err)
