import os
import requests

# Server酱 通知
def serverchan(title, message):
    """
    使用 Server酱 发送通知
    :param title: 通知标题
    :param message: 通知内容
    """
    sendkey = os.getenv('SENDKEY')  # 从环境变量获取 SendKey
    if not sendkey:
        raise ValueError("请设置环境变量 SERVERCHAN_SENDKEY")

    url = f'https://sctapi.ftqq.com/{sendkey}.send'
    data = {
        'title': title,
        'desp': message
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print("Server酱 通知已发送！")
    else:
        print(f"Server酱 通知发送失败: {response.text}")

# PushPlus 通知
def pushplus(title, message):
    """
    使用 PushPlus 发送通知
    :param title: 通知标题
    :param message: 通知内容
    """
    token = os.getenv('PUSHPLUS_TOKEN')  # 从环境变量获取 Token
    if not token:
        raise ValueError("请设置环境变量 PUSHPLUS_TOKEN")

    url = 'http://www.pushplus.plus/send'
    data = {
        'token': token,
        'title': title,
        'content': message
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        print("PushPlus 通知已发送！")
    else:
        print(f"PushPlus 通知发送失败: {response.text}")

def telegram(message, parse_mode=None):  # <--- 增加默认参数 parse_mode
    bot_token = os.getenv('TG_BOT_TOKEN')
    chat_id = os.getenv('TG_USER_ID')

    if not bot_token or not chat_id:
        print("❌ 错误：环境变量 TG_BOT_TOKEN 或 TG_USER_ID 未设置")
        return False

    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': message,
        'disable_web_page_preview': True
    }
    
    # 如果传入了 parse_mode（比如 'HTML'），才加入到 payload 中
    if parse_mode:
        payload['parse_mode'] = parse_mode

    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        if response.status_code == 200 and result.get("ok"):
            print("✅ Telegram 通知已发送！")
            return True
        else:
            print(f"❌ 发送失败！原因: {result.get('description')}")
            return False
    except Exception as e:
        print(f"🔥 异常: {e}")
        return False

# Qmsg 通知
def qmsg(message, qq=None):
    """
    使用 Qmsg 发送通知
    :param message: 通知内容
    :param qq: 接收消息的 QQ 号（可选）
    """
    qmsg_key = os.getenv('QMSG_KEY')  # 从环境变量获取 Qmsg Key
    if not qmsg_key:
        raise ValueError("请设置环境变量 QMSG_KEY")

    url = f'https://qmsg.zendee.cn/send/{qmsg_key}'
    data = {
        'msg': message
    }
    if qq:
        data['qq'] = qq
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print("Qmsg 通知已发送！")
    else:
        print(f"Qmsg 通知发送失败: {response.text}")
