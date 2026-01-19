# coding=utf-8
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from notify import telegram
import base64

now = datetime.today()
now = now.strftime('%Y-%m-%d')
qbt, tr, trx, jpx, bx, trs = [], [], [], [], [], []
url, url1, url2, url4, url3, url5 = 'https://qbtr.me/tongren/', 'https://tongrenquan.org/tongren/', 'https://trxs.cc/tongren/', 'https://jpxs123.cc/', 'https://bixiange.top/','https://www.tongrenshe.cc/'

def qbtr(urls_to_lists):  
    now = datetime.now().date()  
    for url, lb in urls_to_lists.items():  
        res = requests.get(url)  
        res.encoding = 'gb2312'  
        html = res.text  
        soup = BeautifulSoup(html, 'html.parser')  
        qbtr3 = soup.find_all('div', class_='infos')  
        for re in qbtr3:  
            r = re.find('label', class_='date')  
            if r is not None:  
                date = r.text  
                if date == str(now):  
                    p = re.find('h3')  
                    if p is not None:  
                        lb.append(p.text)

def read_previous_content():
    """读取之前保存的内容"""
    try:
        if os.path.exists('novel.txt'):
            with open('novel.txt', 'r', encoding='utf-8') as file:
                return file.read().strip()
        return ""
    except Exception as e:
        print(f"读取旧内容失败: {e}")
        return ""

def save_current_content(content):
    """保存当前内容"""
    try:
        with open('novel.txt', 'w', encoding='utf-8') as file:
            file.write(content)
        print("内容已保存到 novel.txt")
    except Exception as e:
        print(f"保存内容失败: {e}")

def content_changed(old_content, new_content):
    """比较内容是否发生变化"""
    if not old_content:
        return True  # 如果没有旧内容，视为有变化
    
    # 简单的字符串比较
    return old_content.strip() != new_content.strip()

if __name__ == '__main__':
    # 读取之前的内容
    previous_content = read_previous_content()
    
    urls_to_lists = {  
        url: qbt,  
        url1: tr,  
        url2: trx, 
        url4: jpx,
        url3: bx,
        url5: trs
    }  
    
    qbtr(urls_to_lists)
    
    TITLE = "同人小说"
    current_content = f'全本同人m{qbt}\n同人圈{tr}\n同人小说{trx}\n精品小说{jpx}\n笔仙阁m{bx}\n同人社{trs}'
    
    print(f"旧内容长度: {len(previous_content)}")
    print(f"新内容长度: {len(current_content)}")
    
    # 比较内容是否发生变化
    if content_changed(previous_content, current_content):
        print("内容发生变化，发送通知")
        
        # 发送通知
        telegram_result = telegram(current_content)
        print(f"Telegram发送结果: {telegram_result}")
        
        # 保存新内容
        save_current_content(current_content)
    else:
        print("内容无变化，不发送通知")