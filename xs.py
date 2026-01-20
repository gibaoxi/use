import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from notify import telegram

def load_config():
    config_path = 'config.json'
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件未找到：{config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def read_previous_content(save_path):
    try:
        if os.path.exists(save_path):
            with open(save_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        return ""
    except Exception as e:
        print(f"[错误] 无法读取已保存文件 {save_path}：{e}")
        return ""

def save_current_content(content, save_path):
    try:
        with open(save_path, 'w', encoding='utf-8') as file:
            file.write(content)
        print("[成功] 已保存新内容到文件")
    except Exception as e:
        print(f"[错误] 无法保存到 {save_path}：{e}")

def content_changed(old_content: str, new_content: str) -> bool:
    if not old_content:
        return True
    return old_content.strip() != new_content.strip()

def fetch_content(url, site_name, config):
    """抓取网站内容"""
    try:
        print(f"正在访问网站：{site_name} - {url}")
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        res = requests.get(url, timeout=15, headers=headers)
        
        # 自动检测编码
        if res.encoding.lower() in ['gb2312', 'gbk', 'gb18030']:
            res.encoding = 'gbk'
        else:
            res.encoding = 'utf-8'
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 尝试多种可能的日期格式
        today_formats = [
            datetime.now().strftime('%Y-%m-%d'),
            datetime.now().strftime('%m-%d'),
            datetime.now().strftime('%Y/%m/%d')
        ]
        
        titles = []
        
        # 查找包含日期的元素
        date_elements = soup.find_all(class_=config['html_parsing']['label_date_class'])
        
        for date_elem in date_elements:
            date_text = date_elem.text.strip()
            
            # 检查是否匹配今天日期
            if any(today in date_text for today in today_formats):
                # 查找相邻的标题元素
                parent = date_elem.parent
                if parent:
                    # 尝试查找h3标题
                    title_elem = parent.find('h3') or parent.find('a') or date_elem.find_next_sibling()
                    if title_elem and title_elem.text.strip():
                        titles.append(title_elem.text.strip())
        
        print(f"[{site_name}] 找到 {len(titles)} 个今日更新")
        return titles
        
    except Exception as e:
        print(f"[错误] 处理 {site_name} 时出错：{e}")
        return []

def format_message(novel_data):
    """按照指定格式格式化消息"""
    message_lines = []
    
    for site_name, titles in novel_data.items():
        if titles:
            # 将标题列表格式化为字符串
            titles_str = ", ".join([f"'{title}'" for title in titles])
            message_lines.append(f"{site_name}[{titles_str}]")
        else:
            message_lines.append(f"{site_name}[]")
    
    return "\n".join(message_lines)

if __name__ == '__main__':
    # 加载配置
    config = load_config()
    
    # 定义变量
    save_path = "novel.txt"
    
    # 读取之前保存的内容
    previous_content = read_previous_content(save_path)
    
    # 存储所有网站的内容
    novel_data = {}
    
    # 逐个站点抓取内容
    for site_name, url in config['urls'].items():
        titles = fetch_content(url, site_name, config)
        novel_data[site_name] = titles
    
    # 格式化消息
    current_content = format_message(novel_data)
    
    # 输出调试信息
    print(f"旧内容长度: {len(previous_content)}")
    print(f"新内容长度: {len(current_content)}")
    print("抓取到的内容:")
    print(current_content)

    # 检测内容是否变化
    if content_changed(previous_content, current_content):
        print("[更新检测] 内容发生了变化，准备发送通知...")
        try:
            # 发送通知
            telegram_result = telegram(current_content)
            print(f"[通知结果] Telegram 发送返回：{telegram_result}")
        except Exception as e:
            print(f"[错误] 发送通知失败：{e}")
        # 保存新内容
        save_current_content(current_content, save_path)
    else:
        print("[更新检测] 内容无变化，不再发送通知。")
