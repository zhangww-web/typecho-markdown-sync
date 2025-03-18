import os
import re
import shutil
import uuid
from transfer_md.upload_img import upload_image
from transfer_md.download_img import download_image

def extract_image_paths(content):
    """
    从 Markdown 内容中提取所有图片路径（支持 Markdown 和 HTML 格式）
    """
    pattern_md = re.compile(r'!\[.*?\]\((.*?)\)')
    pattern_html = re.compile(r'<img\s+[^>]*src\s*=\s*"(.*?)"')
    return set(pattern_md.findall(content) + pattern_html.findall(content))

def process_local_image_copy(abs_img_path, dest_folder):
    """
    复制本地图片到目标文件夹，并返回新文件名（使用 UUID 命名，保留扩展名）
    """
    ext = os.path.splitext(abs_img_path)[1]
    new_filename = f"{uuid.uuid4()}{ext}"
    dest_path = os.path.join(dest_folder, new_filename)
    shutil.copy2(abs_img_path, dest_path)
    return new_filename

def process_md_file_local(md_file, output_path):
    """
    处理一个 Markdown 文件：
    - 提取 Markdown 和 HTML 格式的图片路径
    - 复制本地图片到 output_path，并修改 md 文件中的图片引用路径
    - 下载网络图片到 output_path，并修改 md 文件中的图片引用路径
    - 图片复制时使用 UUID 作为文件名（保留扩展名）
    - 更新后的图片路径为绝对路径
    """
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用抽离的函数提取图片路径
    img_paths = extract_image_paths(content)

    # 获取当前 md 文件所在目录
    md_dir = os.path.dirname(md_file)

    for img_path in img_paths:
        # 判断图片路径是本地路径还是网络 URL
        if img_path.startswith(('http://', 'https://')):
            # 处理网络图片
            new_filename = download_image(img_path, output_path)
            if new_filename:
                # 使用绝对路径替换
                new_ref = os.path.join(output_path, new_filename).replace('\\', '/')
                content = content.replace(img_path, new_ref)
        else:
            # 处理本地图片
            if os.path.isabs(img_path):
                abs_img_path = img_path
            else:
                abs_img_path = os.path.normpath(os.path.join(md_dir, img_path))

            if os.path.exists(abs_img_path):
                if os.path.isfile(abs_img_path):  # 确保是文件而不是文件夹
                    # 使用抽离的复制函数处理图片
                    new_filename = process_local_image_copy(abs_img_path, output_path)
                    dest_path = os.path.join(output_path, new_filename)
                    print(f"已复制: {abs_img_path} → {dest_path}")
                    # 使用绝对路径替换
                    new_ref = dest_path.replace('\\', '/')
                    content = content.replace(img_path, new_ref)
                else:
                    print(f"警告: 跳过文件夹 {abs_img_path}")
            else:
                print(f"警告: 图片文件不存在 {abs_img_path}")

    # 写回修改后的内容
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"已更新: {md_file}")

def process_md_file_with_assets(md_file, output_base_path):
    """
    处理单个 Markdown 文件，将其拷贝到 output_base_path/<md_name>/ 下，
    并在该文件夹中建立 assets 文件夹保存相关图片。
    同时更新 md 文件中图片的引用路径为相对路径 assets/<new_filename>
    """
    # 创建对应的输出文件夹及 assets 子文件夹
    md_filename = os.path.basename(md_file)
    md_name, _ = os.path.splitext(md_filename)
    target_folder = os.path.join(output_base_path, md_name)
    assets_folder = os.path.join(target_folder, "assets")
    os.makedirs(assets_folder, exist_ok=True)

    # 读取 Markdown 文件内容
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用抽离的函数提取图片路径
    img_paths = extract_image_paths(content)

    # 获取 md 文件所在目录（用于处理相对路径的本地图片）
    md_dir = os.path.dirname(md_file)

    # 遍历所有图片路径
    for img_path in img_paths:
        new_filename = None
        if img_path.startswith(('http://', 'https://')):
            # 处理网络图片：下载图片到 assets_folder
            try:
                # 处理网络图片：下载图片到 assets_folder
                new_filename = download_image(img_path, assets_folder)
            except Exception as e:
                print(f"错误: 下载图片 {img_path} 时出错: {e}")
        else:
            # 处理本地图片
            if os.path.isabs(img_path):
                abs_img_path = img_path
            else:
                abs_img_path = os.path.normpath(os.path.join(md_dir, img_path))
            if os.path.exists(abs_img_path) and os.path.isfile(abs_img_path):
                try:
                    # 使用抽离的复制函数处理图片
                    new_filename = process_local_image_copy(abs_img_path, assets_folder)
                    print(f"已复制: {abs_img_path} → {os.path.join(assets_folder, new_filename)}")
                except PermissionError as e:
                    print(f"错误: 无法复制文件 {abs_img_path}，权限被拒绝: {e}")
            else:
                print(f"警告: 图片文件不存在或不是文件 {abs_img_path}")

        # 如果成功处理图片，则替换 md 文件中的引用路径
        if new_filename:
            new_ref = f"assets/{new_filename}"
            content = content.replace(img_path, new_ref)

    # 将更新后的 md 内容写入目标文件夹中的 md 文件
    target_md_path = os.path.join(target_folder, md_filename)
    with open(target_md_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"已更新: {target_md_path}")

def process_md_file_remote(md_file):
    """
    处理一个 Markdown 文件：
    - 提取 Markdown 和 HTML 格式的图片路径
    - 对于本地图片，调用 upload_image 上传到 easyimage 图床，
      并替换 md 文件中的图片引用路径为返回的公网地址
    - 对于网络图片，保持不变
    """
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用抽离的函数提取图片路径
    img_paths = extract_image_paths(content)

    # 获取当前 md 文件所在目录
    md_dir = os.path.dirname(md_file)

    for img_path in img_paths:
        # 判断是否为本地图片（非网络 URL）
        if not img_path.startswith(('http://', 'https://')):
            if os.path.isabs(img_path):
                abs_img_path = img_path
            else:
                abs_img_path = os.path.normpath(os.path.join(md_dir, img_path))

            if os.path.exists(abs_img_path) and os.path.isfile(abs_img_path):
                try:
                    public_url = upload_image(abs_img_path)
                    print(f"图片已上传: {abs_img_path} → {public_url}")
                    content = content.replace(img_path, public_url)
                except Exception as e:
                    print(f"错误: 图片上传失败 {abs_img_path}: {e}")
            else:
                print(f"警告: 图片文件不存在 {abs_img_path}")
        else:
            print(f"跳过网络图片: {img_path}")

    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"已更新: {md_file}")


def scan_files(base_folder, exclude_folders):
    """
    扫描 base_folder 目录下所有 Markdown 文件，
    并排除路径中包含 exclude_folders 中任一字符串的目录
    """
    md_files = []
    for root, dirs, files in os.walk(base_folder):
        # 如果当前目录中包含需要排除的文件夹，则跳过该目录
        if any(exclude in root for exclude in exclude_folders):
            continue
        for file in files:
            if file.lower().endswith('.md'):
                md_files.append(os.path.join(root, file))
    return md_files

def process_md_files(input_path, output_path, type, exclude_folders=None):
    """
    处理输入目录下所有 Markdown 文件，并将处理后的图片保存到 output_path。
    type 参数决定了使用哪种处理方式：
        type == 1: process_md_file_local
        type == 2: process_md_file_with_assets
        type == 3: process_md_file_remote
    """
    # 创建输出目录（如果不存在）
    os.makedirs(output_path, exist_ok=True)

    # 获取 Markdown 文件列表
    if exclude_folders is None:
        exclude_folders = []
    md_files = scan_files(input_path, exclude_folders)

    # 遍历处理所有 Markdown 文件
    for md_file in md_files:
        if type == 1:
            process_md_file_local(md_file, output_path)   #url改为本地，图片存output_path
        elif type == 2:
            process_md_file_with_assets(md_file, output_path)  #url改为本地，图片和md都存output_path
        elif type == 3:
            process_md_file_remote(md_file)    #url改公网链接
        else:
            print(f"未知的处理类型: {type}")

    print("处理完成！所有图片已保存至:", os.path.abspath(output_path))


if __name__ == "__main__":
    type=1
    input_path = r'D:\folder\study\md_files\Java\zbparse'
    output_path = r'D:\folder\test\output'
    process_md_files(input_path,output_path,type)