from nonebot import get_plugin_config, on_command
from nonebot import require
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me
from nonebot.params import Event
from nonebot_plugin_waiter import waiter
from nonebot.adapters.onebot.v11 import PrivateMessageEvent

import json
import os
import time
import re
import subprocess
import shutil
import sqlite3
import requests
from jinja2 import Template

from .config import Config

require("imgrander")
import mynbwall.plugins.imgrander as imgrander

__plugin_meta__ = PluginMetadata(
    name="contribute",
    description="这是Onbwall的信息接收与初步处理插件",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)
current_milli_time = lambda: int(round(time.time() * 1000))
contributer = on_command("test", rule=to_me(), priority=5)
db_path = 'submissions/ONBWall.db'
RAWPOST_DIR = './submissions/rawpost'
ALLPOST_DIR = './submissions/all'
COMMU_DIR = './submissions/all/'
# 检查数据库文件是否存在
if not os.path.exists(db_path):
    # 连接到 SQLite 数据库（如果数据库不存在，将会自动创建）
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建 sender 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sender (
            senderid TEXT,
            receiver TEXT,
            ACgroup TEXT,
            rawmsg TEXT,
            modtime TEXT,
            processtime TEXT
        )
    ''')

    # 创建 preprocess 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS preprocess (
            tag INTEGER,
            senderid TEXT,
            nickname TEXT,
            receiver TEXT,
            ACgroup TEXT,
            AfterLM TEXT,
            comment TEXT,
            numnfinal INTEGER
        )
    ''')

    # 提交更改并关闭连接
    conn.commit()
    conn.close()

    print(f"Database and tables created at {db_path}")
else:
    print(f"Database already exists at {db_path}")


async def gotohtml(file_path):
    html_file_path = f"{file_path.replace('_raw.json', '.html')}"
    if not os.path.exists(file_path):
        return "生成 HTML 失败：文件不存在。"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return "生成 HTML 失败：JSON 解析错误。"
        print("生成 HTML 失败：JSON 解析错误。")
    
    messages = []
    sessionID = ""
    
    for item in data:
        if "message" in item:
            messages.append(item["message"])
        if "sessionID" in item:
            sessionID = item["sessionID"]
    
    if not sessionID:
        return "生成 HTML 失败：未找到 sessionID。"
        print("生成 HTML 失败：未找到 sessionID。")
    # 处理消息，解析 CQ 码
    processed_messages = []
    for msg in messages:
        # 处理 CQ:image
        img_match = re.match(r'\[CQ:image,file=([^,]+),[^]]*\]', msg)
        if img_match:
            img_url = img_match.group(1)
            # 尝试提取 URL，如果有 url 参数
            url_match = re.search(r'url=([^,]+)', msg)
            if url_match:
                img_url = url_match.group(1)
            img_html = f'<img src="{img_url}" alt="Image">'
            processed_messages.append(img_html)
            continue
        
        # 处理 CQ:video
        video_match = re.match(r'\[CQ:video,file=([^,]+),[^]]*\]', msg)
        if video_match:
            video_url = video_match.group(1)
            # 尝试提取 URL，如果有 url 参数
            url_match = re.search(r'url=([^,]+)', msg)
            if url_match:
                video_url = url_match.group(1)
            video_html = f'<video controls autoplay muted><source src="{video_url}" type="video/mp4">您的浏览器不支持视频标签。</video>'
            processed_messages.append(video_html)
            continue
        
        # 处理纯文本消息，转义 HTML 特殊字符
        escaped_msg = (msg.replace("&", "&amp;")
                         .replace("<", "&lt;")
                         .replace(">", "&gt;")
                         .replace('"', "&quot;")
                         .replace("'", "&#039;"))
        # 换行符转为 <br/>
        escaped_msg = escaped_msg.replace("\n", "<br/>")
        processed_messages.append(f"<div>{escaped_msg}</div>")
    
    # 生成 HTML 内容
    html_content = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Session {sessionID}</title>
    <style>
        @page {{
          margin: 0 !important;
          size:4in 8in;
        }}
        body {{
            font-family: Arial, sans-serif;
            background-color: #f2f2f2;
            margin: 0;
            padding: 5px;
        }}
        .container {{
            width: 4in;
            margin: 0 auto;
            padding: 20px;
            border-radius: 10px;
            background-color: #f2f2f2;
            box-sizing: border-box;
        }}
        .header {{
            display: flex;
            align-items: center;
        }}
        .header img {{
            border-radius: 50%;
            width: 50px;
            height: 50px;
            margin-right: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
        }}
        .header-text {{
            display: block;
        }}
        .header h1 {{
            font-size: 24px;
            margin: 0;
        }}
        .header h2 {{
            font-size: 12px;
            margin: 0;
        }}
        .content {{
            margin-top: 20px;
        }}
        .content div{{
            display: block;
            background-color: #ffffff;
            border-radius: 10px;
            padding: 7px;
            margin-bottom: 10px;
            word-break: break-word;
            max-width: fit-content;
            line-height: 1.5;
        }}
        .content img, .content video {{
            display: block;
            border-radius: 10px;
            padding: 0px;
            margin-top: 10px;
            margin-bottom: 10px;
            max-width: 50%;
            max-height: 300px; 
        }}
        .content video {{
            background-color: transparent;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="http://q.qlogo.cn/headimg_dl?dst_uin=10000&spec=640&img_type=jpg" alt="Profile Image">
            <div class="header-text">
                <h1>{sessionID}</h1>
                <h2></h2>
            </div>
        </div>
        <div class="content">
            {''.join(processed_messages)}
        </div>
    </div>

    <script>
        window.onload = function() {{
            const container = document.querySelector('.container');
            const contentHeight = container.scrollHeight;
            const pageHeight4in = 364; // 4 inches in pixels (96px per inch)
        
            let pageSize = '';
        
            if (contentHeight <= pageHeight4in) {{
                pageSize = '4in 4in'; // 内容适合时使用 4in x 4in
            }} else if (contentHeight >= 2304){{
                pageSize = '4in 24in';
            }} else {{
                const containerHeightInInches = (contentHeight / 96 + 0.1);
                pageSize = `4in ${{containerHeightInInches}}in`; // 根据内容高度设置页面高度
            }}
        
            // 动态应用 @page 大小
            const style = document.createElement('style');
            style.innerHTML = `
                @page {{
                    size: ${{pageSize}};
                    margin: 0 !important;
                }}
            `;
            document.head.appendChild(style);
        }};
    </script>
</body>
</html>
"""
    
    # 定义 HTML 输出目录
    output_dir = os.path.join("ONBwall", "html")
    os.makedirs(output_dir, exist_ok=True)
    
    # 使用时间戳作为 HTML 文件名的一部分，确保唯一性
    
    try:
        with open(html_file_path, "w", encoding="utf-8") as html_file:
            html_file.write(html_content)
    except Exception as e:
        return "生成 HTML 失败：写入文件错误。"
        print("生成 HTML 失败：写入文件错误。")
    # 可选：将 HTML 文件路径返回或发送给用户
    return f"HTML 文件已生成：{html_file_path}"
    print(f"HTML 文件已生成：{html_file_path}")

async def gotojpg(file_path):
    """
    使用 Chrome 打印 HTML 到 PDF 并将 PDF 转换为 JPG，然后下载 JSON 中的所有图片到同一个文件夹。
    参数:
        file_name (str): JSON 文件的文件名，用于定位相关文件
    """
    # 文件夹和文件名的设置
    input_name = os.path.splitext(os.path.basename(file_path))[0]
    html_file_path = f"{file_path.replace('_raw.json', '.html')}"
    pdf_output_path = f"{file_path.replace('_raw.json', '.pdf')}"
    jpg_folder = f"{file_path.replace('_raw.json', '-img')}"
    json_file_path = file_path
    # 确保必要的目录存在
    os.makedirs(os.path.dirname(pdf_output_path), exist_ok=True)
    os.makedirs(jpg_folder, exist_ok=True)

    # 使用 Chrome 打印 HTML 到 PDF
    chrome_command = [
        "google-chrome-stable",
        "--headless",
        f"--print-to-pdf={pdf_output_path}",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        "--virtual-time-budget=2000",
        "--pdf-page-orientation=portrait",
        "--no-margins",
        "--enable-background-graphics",
        "--print-background=true",
        f"file://{os.path.abspath(html_file_path)}"
    ]

    # 执行 Chrome 打印命令
    subprocess.run(chrome_command, check=True)

    # 使用 ImageMagick 将 PDF 转换为 JPG
    convert_command = [
        "identify",
        "-format", "%n\n",
        pdf_output_path
    ]

    # 获取 PDF 的页数
    pages = subprocess.check_output(convert_command).decode("utf-8").strip().split("\n")[0]

    # 转换每一页 PDF 为 JPG
    for i in range(int(pages)):
        formatted_index = f"{i:02d}"
        convert_page_command = [
            "convert",
            "-density", "360",
            "-quality", "90",
            f"{pdf_output_path}[{i}]",
            f"{jpg_folder}/{input_name}-{formatted_index}.jpeg"
        ]
        subprocess.run(convert_page_command, check=True)

    # 下载 JSON 中的所有图片
    next_file_index = len(os.listdir(jpg_folder))
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for item in data:
            if "message" in item:
                msg = item["message"]
                # 查找所有 CQ:image 码
                cq_images = re.findall(r'\[CQ:image,([^\]]+)\]', msg)
                for cq_data in cq_images:
                    data_dict = {}
                    # 解析 CQ 码中的数据
                    for kv in cq_data.split(','):
                        if '=' in kv:
                            k, v = kv.split('=', 1)
                            data_dict[k] = v
                    img_url = data_dict.get("url", "")
                    if img_url:
                        formatted_index = f"{next_file_index:02d}"
                        image_output_path = f"{jpg_folder}/{input_name}-{formatted_index}.jpeg"
                        download_image(img_url, image_output_path)
                        next_file_index += 1

    # 重命名文件，去掉后缀名
    for file in os.listdir(jpg_folder):
        file_path = os.path.join(jpg_folder, file)
        if os.path.isfile(file_path):
            base_name = os.path.splitext(file)[0]
            os.rename(file_path, os.path.join(jpg_folder, base_name))


def download_image(url, output_path):
    """
    下载图片并保存到指定路径。
    参数:
        url (str): 图片的 URL 地址
        output_path (str): 保存图片的文件路径
    """
    #response = requests.get(url, stream=True)
    #if response.status_code == 200:
        #with open(output_path, "wb") as f:
         #   shutil.copyfileobj(response.raw, f)
    #else:
        #print(f"下载图片失败: {url}")
    print("download"f"{url}""to" f"{output_path}")

@contributer.handle()
async def handle():
    @waiter(waits=["message"], keep_session=True)
    async def get_content(event: PrivateMessageEvent):
        return event.get_message(), event.get_session_id()  # 返回消息和 sessionID


    async for resp in get_content(timeout=15, retry=200, prompt=""):
        if resp is None:
            await contributer.send("投稿时间结束")
            break
        print("resp")
        print(resp)
        message_segments, session_id = resp  # 解包消息和 sessionID

        # 遍历消息中的所有 MessageSegment
        # Inside the handle function, traversing the message_segments
        # 在 for 循环外创建 message 列表
        all_segments = []

        for segment in message_segments:
            # 检查每个 segment 类型和数据
            message_type = segment.type
            message_data = segment.data

            # 将提取的 segment 格式化并添加到 all_segments 列表中
            result = {"type": message_type, "data": message_data}
            all_segments.append(result)

        # 构建 simplified_data 字典，将所有 segments 添加到 message 中
        simplified_data = {
            "message_id": current_milli_time(),
            "message": all_segments,
            "time": int(time.time())
        }

        # 输出解析后的结果
        
        print(f"Simplified message: {simplified_data}")

        user_id = session_id
        nickname = user_id
        print(f"userid:{user_id}")
        self_id = "10000"
        #ACgroup = self_id_to_acgroup.get(self_id, 'Unknown')
        ACgroup = "notusenow"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if a record already exists for this sender and receiver
        cursor.execute('SELECT rawmsg FROM sender WHERE senderid=? AND receiver=?', (user_id, self_id))
        row = cursor.fetchone()
        # Inside the try block where you process and update the sender table

        if row:  # If the sender already exists in the database
            isfirst = "false"
            # If exists, load the existing rawmsg and append the new message
            rawmsg_json = row[0]
            try:
                message_list = json.loads(rawmsg_json)
                if not isinstance(message_list, list):
                    message_list = []
            except json.JSONDecodeError:
                message_list = []

            message_list.append(simplified_data)
            # Sort messages by time
            message_list = sorted(message_list, key=lambda x: x.get('time', 0))

            updated_rawmsg = json.dumps(message_list, ensure_ascii=False)
            print(updated_rawmsg)
            cursor.execute('''
                UPDATE sender 
                SET rawmsg=?, modtime=CURRENT_TIMESTAMP 
                WHERE senderid=? AND receiver=?
            ''', (updated_rawmsg, user_id, self_id))
            conn.commit()
        else:  # If the sender does not exist, create a new record
            isfirst = "true"
            # If not exists, insert a new record with the message
            message_list = [simplified_data]
            rawmsg_json = json.dumps(message_list, ensure_ascii=False)
            print("startwritingtodb")
            cursor.execute('''
                INSERT INTO sender (senderid, receiver, ACgroup, rawmsg, modtime) 
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, self_id, ACgroup, rawmsg_json))

            # Check the max tag from the preprocess table
            cursor.execute('SELECT MAX(tag) FROM preprocess')
            max_tag = cursor.fetchone()[0] or 0
            new_tag = max_tag + 1

            # Insert into preprocess table
            cursor.execute('''
                INSERT INTO preprocess (tag, senderid, nickname, receiver, ACgroup) 
                VALUES (?, ?, ?, ?, ?)
            ''', (new_tag, user_id, nickname, self_id, ACgroup))

            # Commit changes
            conn.commit()
            print("endwritingtodb")

        # At this point, only run imgrander.preprocess if it's the first message
        if isfirst == "true":
            try:
                imgrander.preprocess(new_tag)
                conn.commit()
                print(f"Preprocess done for tag {new_tag}.")
            except Exception as e:
                print(f"Preprocess error for tag {new_tag}: {e}")

        conn.close()

    await contributer.send("消息处理完毕")

    
    timestamp = int(time.time())
    directory = "submissions"  # 替换为你的目标目录
    file_name = f"{timestamp}_raw.json"
    file_path = os.path.join(directory, file_name)  # 合并目录和文件名

    # 确保目录存在，如果不存在则创建
    os.makedirs(directory, exist_ok=True)

    os.makedirs(directory, exist_ok=True)

    # 在获取消息的上下文外打开文件，以保持文件打开状态
    with open(file_path, "a", encoding="utf-8") as file:
        # 用于存储消息和 sessionID
        messages = []
        
        async for resp in get_content(timeout=10, retry=200, prompt=""):
            if resp is None:
                await contributer.send("等待超时")
                break
            
            message, sessionID = resp  # 解包消息和 sessionID
            
            # 将新消息包装为字典对象并添加到列表
            messages.append({"message": str(message)})

        # 写入所有消息
        file.write("[\n")
        json.dump(messages, file, ensure_ascii=False)
        file.write("\n")

        # 写入 sessionID
        if sessionID:  # 检查 sessionID 是否存在
            file.write(",\n")
            json.dump({"sessionID": str(sessionID)}, file, ensure_ascii=False)

        file.write("\n]")  # 结束 JSON 数组

    await gotohtml(file_path)
    await gotojpg(file_path)
    

