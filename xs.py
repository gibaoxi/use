import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from notify import telegram


# 从配置文件加载动态参数
def load_config():
    config_path = 'config.json'
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件未找到：{config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# 读取之前保存的内容
def read_previous_content():
    """读取之前的内容（保存的小说文件）"""
    try:
        if os.path.exists('novel.txt'):
            with open('novel.txt', 'r', encoding='utf-8') as file:
                return file.read().strip()
        return ""
    except Exception as e:
        print(f"[错误] 无法读取已保存文件 novel.txt：{e}")
        return ""


# 保存最新内容
def save_current_content(content):
    """保存当前内容到 novel.txt"""
    try:
        with open('novel.txt', 'w', encoding='utf-8') as file:
            file.write(content)
        print("[成功] 已保存新内容到 novel.txt")
    except Exception as e:
        print(f"[错误] 无法保存到 novel.txt：{e}")


def content_changed(old_content: str, new_content: str) -> bool:
    """检查 old_content 和 new_content 是否不同"""
    if not old_content:
        return True  # 如果没有旧内容，则认为内容有变化
    return old_content.strip() != new_content.strip()


# 从目标网站抓取内容
def fetch_content(url, content_list):
    """抓取给定站点内容并添加到目标列表"""
    try:
        print(f"正在访问网站：{url}")
        res = requests.get(url, timeout=10)
        res.encoding = 'gb2312'  # 根据页面实际编码设置
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
        print(f"[错误] 处理 {url} 失败：{e}")


# 加载配置
config = load_config()

if __name__ == '__main__':
    # 定义变量
    now = datetime.today().strftime('%Y-%m-%d')
    novel_data = {key: [] for key in config['urls']}  # 列表存储每个站点的结果

    # 读取之前保存的内容
    previous_content = read_previous_content()

    # 逐个站点抓取内容
    for name, url in config['urls'].items():
        fetch_content(url, novel_data[name])

    # 拼接当前内容（包括动态标题）
    TITLE = config.get("notify_title", "同人小说更新通知")
    current_content = f"【{TITLE}】\n"
   "

    # 输出对比信息
    print(f"旧内容长度: {len(previous_content)}")
    print(f"新内容长度: {len(current_content)}")

    # 检测内容是否变化
    if content_changed(previous_content, current_content):
        print("[更新检测] 内容发生了变化，准备发送通知...")
        # 发送通知
        telegram_result = telegram(current_content)
        print(f"[通知结果] Telegram 发送返回：{telegram_result}")
        # 保存新内容
        save_current_content(current_content)
    else:
        print("[更新检测] 内容无变化，不再发送通知。")