# 使用一个轻量的 Python 镜像
FROM python:3.8-slim

# 设置工作目录
WORKDIR /markdown_operation

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制整个项目到容器内
COPY . .

# 设置容器启动时运行的命令，比如运行 main.py
CMD ["/bin/bash"]
