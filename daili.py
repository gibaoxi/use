import json
import re
from notify import telegram

def send_from_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    proxies = sorted(list(set(data.get("ts", []))))
    message_lines = ["<b>🌐 代理直连列表 (点击配置)</b>"]

    for item in proxies:
        match = re.search(r'socks5://([\d\.]+):(\d+)', item)
        if match:
            host, port = match.group(1), match.group(2)
            # 构造 TG 专用协议链接
            link = f"tg://socks?server={host}&port={port}"
            # 使用 HTML 格式
            message_lines.append(f'• <a href="{link}">{host}:{port}</a>')

    final_message = "\n".join(message_lines)

    # 指定使用 HTML 模式发送
    telegram(final_message, parse_mode='HTML')

if __name__ == "__main__":
    send_from_json("./daili/result/socks5.json")