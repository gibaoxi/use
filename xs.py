import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from notify import telegram

# 从配置文件加载动态参数
def load_config():
    config_path = './config/xs.json'
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件未找到：{config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 读取之前保存的内容
def read_previous_content(save_path):
    try:
        if os.path.exists(save_path):
            with open(save_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        return ""
    except Exception as e:
        print(f"[错误] 无法读取已保存文件：{e}")
        return ""

# 保存最新内容
def save_current_content(content, save_path):
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as file:
            file.write(content)
        print("[成功] 已保存新内容到记录文件")
    except Exception as e:
        print(f"[错误] 无法保存到文件：{e}")

# 比较内容是否发生变化
def content_changed(old_content: str, new_content: str) -> bool:
    if not old_content:
        return True
    return old_content.strip() != new_content.strip()

# 从目标网站抓取内容
def fetch_content(url, content_list, config):
    try:
        print(f"🔍 正在访问网站：{url}")
        res = requests.get(url, timeout=15)
        # 自动识别页面编码，防止小说名乱码
        res.encoding = res.apparent_encoding 
        
        soup = BeautifulSoup(res.text, 'html.parser')
        info_divs = soup.find_all('div', class_=config['html_parsing']['infos_div_class'])
        
        today = datetime.now().strftime('%Y-%m-%d')
        for div in info_divs:
            date_label = div.find('label', class_=config['html_parsing']['label_date_class'])
            if date_label and date_label.text.strip() == today:
                title = div.find('h3')
                if title:
                    content_list.append(title.text.strip())
    except Exception as e:
        print(f"[错误] 无法处理 {url}：{e}")

# 格式化消息为指定格式
def format_message(novel_data):
    """格式：站点名['小说名', '小说名']"""
    message_lines = []
    for site_name, titles in novel_data.items():
        titles_str = ", ".join([f"'{title}'" for title in titles])
        message_lines.append(f"{site_name}[{titles_str}]")
    return "\n".join(message_lines)

if __name__ == '__main__':
    # 1. 初始化
    config = load_config()
    save_path = "./results/xs.txt"
    novel_data = {key: [] for key in config['urls']}

    # 2. 读取历史记录
    previous_content = read_previous_content(save_path)

    # 3. 抓取各站点内容
    for name, url in config['urls'].items():
        fetch_content(url, novel_data[name], config)

    # 4. 格式化当前内容
    current_content = format_message(novel_data)

    print(f"📊 旧内容长度: {len(previous_content)} | 新内容长度: {len(current_content)}")

    # 5. 检测变化并发送通知
    if content_changed(previous_content, current_content):
        print("🔔 [更新检测] 内容发生了变化，尝试发送 Telegram 通知...")
        
        # 调用通知函数并接收返回值
        telegram_result = telegram(current_content)
        print(f"📢 [通知结果] Telegram 发送返回：{telegram_result}")

        # 核心逻辑：只有发送成功了，才更新本地记录
        # 这样如果这次发送失败，下次脚本运行时还会判定为有变化，从而再次尝试发送
        if telegram_result is True:
            save_current_content(current_content, save_path)
        else:
            print("⚠️ [警告] 由于发送通知失败，本地记录未更新，将在下次运行时重试。")
    else:
        print("😴 [更新检测] 内容无变化，跳过。")