import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from notify import telegram
import base64

# 从配置文件加载动态内容
def load_config():
    config_file = 'config.json'
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"无法找到配置文件: {config_file}")
    with open(config_file, 'r', encoding='utf-8') as file:
        return json.load(file)

config = load_config()

now = datetime.today().strftime('%Y-%m-%d')
novel_data = {key: [] for key in config['urls']}  # 动态创建存储字典

def fetch_content(url, target_list):
    """抓取 URL 内容并解析数据"""
    try:
        res = requests.get(url, timeout=10)
        res.encoding = 'gb2312'  # 可用 res.apparent_encoding 代替
        html = res.text
        soup = BeautifulSoup(html, 'html.parser')
        divs = soup.find_all('div', class_=config['html_parsing']['infos_div_class'])
        for div in divs:
            date_label = div.find('label', class_=config['html_parsing']['label_date_class'])
            if date_label and date_label.text == now:  # 日期匹配
                title = div.find('h3')
                if title:
                    target_list.append(title.text.strip())
    except Exception as e:
        print(f"抓取 {url} 时发生错误: {e}")

def main():
    # 读取之前的内容
    previous_content = read_previous_content()
    
    # 动态读取 URL 并抓取内容
    for name, url in config['urls'].items():
        fetch_content(url, novel_data[name])

    current_content = '\n'.join([f"{name}: {data}" for name, data in novel_data.items()])

    # 打印内容信息
    print(f"旧内容长度: {len(previous_content)}")
    print(f"新内容长度: {len(current_content)}")
    
    # 比较内容并发送通知
    if content_changed(previous_content, current_content):
        print("内容发生变化，发送通知")
        telegram_result = telegram(current_content)  # Telegram 通知
        print(f"Telegram 发送结果: {telegram_result}")
        save_current_content(current_content)
    else:
        print("内容无变化，不发送通知")

main()