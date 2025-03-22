## 同步本地Markdown至Typecho站点

本项目基于https://github.com/Sundae97/typecho-markdown-file-publisher

实现效果：

- [x] 将markdown发布到typecho
- [x] 发布前将markdown的图片资源上传到TencentCloud的COS中, 并替换markdown中的图片链接
- [x] 将md所在的文件夹名称作为post的category(mysql发布可以插入category, xmlrpc接口暂时不支持category操作)
- [x] 以title和category作为文章的唯一标识，如果数据库中已有该数据，将会更新现有文章，否则新增文章。

环境：Typecho1.2.1  php8.1.0

### 项目目录

![image-20250319173057792](https://pic.bitday.top/i/2025/03/21/qimsxc-2.png)

`typecho_markdown_upload/main.py`是上传md文件到站点的核心脚本

`transfer_md/transfer.py`是对md文件进行预处理的脚本。



### **核心思路**

**一、预先准备**

**图床服务器**

本人自己在服务器上搭建了私人图床——easyimage，该服务能够实现图片上传并返回公网 URL，这对于在博客中正常显示 Markdown 文件中的图片至关重要。

当然，也可以选择使用公共图床服务，如阿里云 OSS，但这里不做详细介绍。

需手动修改`transfer_md/upload_img.py`，配置url、token等信息。

参考博客：[【好玩儿的Docker项目】10分钟搭建一个简单图床——Easyimage-我不是咕咕鸽](https://blog.laoda.de/archives/docker-compose-install-easyimage)

github地址：[icret/EasyImages2.0: 简单图床 - 一款功能强大无数据库的图床 2.0版](https://github.com/icret/EasyImages2.0)



**picgo安装：**

使用 Typora + PicGo + Easyimage 组合，可以实现将本地图片直接粘贴到 Markdown 文件中，并自动上传至图床。

下载地址：[Releases · Molunerfinn/PicGo](https://github.com/Molunerfinn/PicGo/releases)

操作步骤如下：

1. 打开 PicGo，点击右下角的小窗口。
2. 进入插件设置，搜索并安装 `web-uploader 1.1.1` 插件（注意：旧版本可能无法搜索到，建议直接安装最新版本）。
3. 配置插件：在设置中填写 API 地址，该地址可在 Easyimage 的“设置-API设置”中获取。

配置完成后，即可实现图片自动上传，提升 Markdown 编辑体验。

<img src="https://pic.bitday.top/i/2025/03/21/qimwlg-2.png" alt="image-20250319180022461" style="zoom:67%;" />



**Typora 设置**

为了确保在博客中图片能正常显示，编辑 Markdown 文档时**必须将图片上传至图床**，而不是保存在本地。请按以下步骤进行配置：

1. 在 Typora 中，打开 **文件 → 偏好设置 → 图像** 选项。
2. 在 “插入图片时” 选项中，选择 **上传图片**。
3. 在 “上传服务设定” 中选择 **PicGo**，并指定 PicGo 的安装路径。

![image-20250319175707761](https://pic.bitday.top/i/2025/03/21/qin8gd-2.png)



**文件结构统一**：

```text
md_files
├── category1
│   ├── file1.md
│   └── file2.md
├── category2
│   ├── file3.md
│   └── file4.md
└── output
    ├── image1.png
    ├── image2.jpg
    └── ... (其他图片文件)

```

**注意**：category对应上传到typecho中的文章所属的分类。

如果你现有的图片分散在系统中，可以使用 `transfer_md/transfer.py` 脚本来统一处理。该脚本需要传入三个参数：

- **input_path：** 指定包含 Markdown 文件的根目录（例如上例中的 `md_files`）。
- **output_path：** 指定统一存放处理后图片的目标文件夹（例如上例中的 `output`）。
- **type_value**：
  - `1`：扫描 `input_path` 下所有 Markdown 文件，将其中引用的本地图片复制到 `output_path` 中，同时更新 Markdown 文件中的图片 URL 为 `output_path` 内的路径；
  - `2`：为每个 Markdown 文件建立单独的文件夹（以文件名命名），将 Markdown 文件及其依赖图片存入该文件夹中，图片存放在文件夹下的 `assets` 子目录中，整体保存在 `output_path` 内；
  - `3`：扫描 Markdown 文件中的本地图片，将其上传到图床（获取公网 URL），并将 Markdown 文件中对应的图片 URL 替换为公网地址。

对于本项目，需要将图片统一用公网URL表示。即`type_value=3`



**二、使用Git进行版本控制**

假设你在服务器上已经搭建了 Gitea (Github、Gitee都行)并创建了一个名为 `md_files` 的仓库，那么你可以在 `md_files` 文件夹下通过 Git Bash 执行以下步骤将本地文件提交到远程仓库：

**初始化本地仓库**：

```text
git init
```

**添加远程仓库**：

将远程仓库地址添加为 `origin`（请将 `http://xxx` 替换为你的实际仓库地址）：

```text
git remote add origin http://xxx
```

**添加文件并提交**：

```text
git add .
git commit -m "Initial commit"
```

**推送到远程仓库：**

```text
git push -u origin master
```

**后续更新（可写个.bat批量执行）：**

```text
git add .
git commit -m "更新了xxx内容"
git push
```



**三、在服务器上部署该脚本**

**1. 确保脚本能够连接到 Typecho 使用的数据库**

本博客使用 docker-compose 部署 Typecho（参考：[【好玩儿的Docker项目】10分钟搭建一个Typecho博客｜太破口！念念不忘，必有回响！-我不是咕咕鸽](https://blog.laoda.de/archives/docker-compose-install-typecho)）。为了让脚本能访问 Typecho 的数据库，我将 Python 应用pyapp也通过 docker-compose 部署，这样所有服务均在同一网络中，互相之间可以直接通信。

参考docker-compose.yml如下：

```text
services:
  nginx:
    image: nginx
    ports:
      - "4000:80"    # 左边可以改成任意没使用的端口
    restart: always
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - ./typecho:/var/www/html
      - ./nginx:/etc/nginx/conf.d
      - ./logs:/var/log/nginx
    depends_on:
      - php
    networks:
      - web

  php:
    build: php
    restart: always
    expose:
      - "9000"       # 不暴露公网，故没有写9000:9000
    volumes:
      - ./typecho:/var/www/html
    environment:
      - TZ=Asia/Shanghai
    depends_on:
      - mysql
    networks:
      - web
  pyapp:
    build: ./markdown_operation  # Dockerfile所在的目录
    restart: "no"
    volumes:
            - /home/zy123/md_files:/markdown_operation/md_files
    networks:
      - web
    env_file:
      - .env
    depends_on:
      - mysql
  mysql:
    image: mysql:5.7
    restart: always
    environment:
      - TZ=Asia/Shanghai
    expose:
      - "3306"  # 不暴露公网，故没有写3306:3306
    volumes:
      - ./mysql/data:/var/lib/mysql
      - ./mysql/logs:/var/log/mysql
      - ./mysql/conf:/etc/mysql/conf.d
    env_file:
      - mysql.env
    networks:
      - web

networks:
  web:
```

注意：如果你不是用docker部署的typecho，只要保证脚本能连上typecho所使用的数据库并操纵里面的表就行！



**2. 将 `md_files` 挂载到容器中，保持最新内容同步**

这样有几个优势：

- 不需要每次构建镜像或进入容器手动拉取；
- 本地更新 `md_files` 后，容器内自动同步，无需额外操作；
- 保持了宿主机上的 Git 版本控制和容器内的数据一致性。



**3.仅针对 `pyapp` 服务进行重构和启动，不影响其他服务的运行：**

`pyapp`是本Python应用在容器内的名称。

1.构建镜像：

```text
docker-compose build pyapp 
```

2.启动容器并进入 Bash：

```text
docker-compose run --rm -it pyapp /bin/bash
```

3.在容器内运行脚本：

```text
python typecho_markdown_upload/main.py
```

2、3两步可合并为：

```text
docker-compose run --rm pyapp python typecho_markdown_upload/main.py
```

![image-20250320103325650](https://pic.bitday.top/i/2025/03/20/h37pze-0.png)

此时可以打开博客验证一下是否成功发布文章了！

**如果失败，可以验证mysql数据库:**

1️⃣ 进入 MySQL 容器：

```text
docker-compose exec mysql mysql -uroot -p
# 输入你的 root 密码
```

2️⃣ 切换到 Typecho 数据库并列出表：

```text
USE typecho;
SHOW TABLES;
```

3️⃣ 查看 `typecho_contents` 表结构（文章表）：

```text
DESCRIBE typecho_contents;
```

```text
mysql> DESCRIBE typecho_contents;
+--------------+------------------+------+-----+---------+----------------+
| Field        | Type             | Null | Key | Default | Extra          |
+--------------+------------------+------+-----+---------+----------------+
| cid          | int(10) unsigned | NO   | PRI | NULL    | auto_increment |
| title        | varchar(150)     | YES  |     | NULL    |                |
| slug         | varchar(150)     | YES  | UNI | NULL    |                |
| created      | int(10) unsigned | YES  | MUL | 0       |                |
| modified     | int(10) unsigned | YES  |     | 0       |                |
| text         | longtext         | YES  |     | NULL    |                |
| order        | int(10) unsigned | YES  |     | 0       |                |
| authorId     | int(10) unsigned | YES  |     | 0       |                |
| template     | varchar(32)      | YES  |     | NULL    |                |
| type         | varchar(16)      | YES  |     | post    |                |
| status       | varchar(16)      | YES  |     | publish |                |
| password     | varchar(32)      | YES  |     | NULL    |                |
| commentsNum  | int(10) unsigned | YES  |     | 0       |                |
| allowComment | char(1)          | YES  |     | 0       |                |
| allowPing    | char(1)          | YES  |     | 0       |                |
| allowFeed    | char(1)          | YES  |     | 0       |                |
| parent       | int(10) unsigned | YES  |     | 0       |                |
| views        | int(11)          | YES  |     | 0       |                |
| agree        | int(11)          | YES  |     | 0       |                |
+--------------+------------------+------+-----+---------+----------------+
```

4️⃣ 查询当前文章数量（确认执行前后有无变化）：

```text
SELECT COUNT(*) AS cnt FROM typecho_contents;
```



### **自动化**

1.windows下写脚本自动/手动提交每日更新

2.远程仓库监测到更新自动实现钩子脚本,更新md_files并执行脚本



### TODO

- [ ] typecho_contents表中的slug字段代表链接中的日志缩略名，如wordpress风格 `/archives/{slug}.html`，目前是默认int自增，有需要的话可以在插入文章时手动设置该字段。

