#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘宝订单抓取与物流查询工具 - JSON格式专用版
只支持ck.js格式的账号数据
添加Cookie和日期自动更新功能
"""

import sys
import os
import requests
import re
import time
import random
import hashlib
import json
from datetime import datetime, timedelta
from urllib.parse import quote

# 基础路径配置
BASE_PATH = "/storage/emulated/0"
CACHE_PATH = os.path.join(BASE_PATH, "cache")
LOG_DIR = os.path.join(CACHE_PATH, "taobao_simple")

os.makedirs(LOG_DIR, exist_ok=True)

class TaobaoTester:
    def __init__(self, cookie_str=None, user_agent=None, account_name="未知账号"):
        self.session = requests.Session()
        self.account_name = account_name
        self.base_path = BASE_PATH
        self.save_path = os.path.join(self.base_path, "cache")
        
        # 添加token刷新时间记录
        self.last_token_refresh = 0  # 上次刷新token的时间戳
        self.min_refresh_interval = 3  # 最小刷新间隔（秒）
        
        # 统一设置请求头
        if user_agent:
            self.headers = {'User-Agent': user_agent}
        else:
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 13; V2272A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/142.0.7444.173 Mobile Safari/537.36'
            }
        
        self.app_key = "12574478"
        self.token = None
        self.token_enc = None

        if cookie_str:
            self.set_cookies(cookie_str)
            self._init_token_from_cookies()
        
        self.login_test_url = "https://buyertrade.taobao.com/trade/itemlist/list_bought_items.htm"
    
    def set_cookies(self, cookie_str):
        cookies = {}
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        self.session.cookies.update(cookies)
    
    def _init_token_from_cookies(self):
        cookies_dict = self.session.cookies.get_dict()
        tk = cookies_dict.get('_m_h5_tk')
        if tk and '_' in tk:
            self.token = tk.split('_')[0]
            self.token_enc = cookies_dict.get('_m_h5_tk_enc')
            print(f"[{self.account_name}] 已加载 Token: {self.token[:8]}...")
    
    def get_session_cookies(self):
        """获取当前session的cookies"""
        return self.session.cookies
    
    def save_response(self, response, suffix):
        """保存响应到文件，方便调试"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\-]', '_', self.account_name)
        ext = "html" if 'html' in response.headers.get('Content-Type', '').lower() else "json"
        filename = os.path.join(LOG_DIR, f"{safe_name}_{suffix}_{timestamp}.{ext}")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        return filename
    
    def calculate_sign(self, data_str, t=None):
        if not self.token:
            # 如果token为空，尝试刷新，但遵循频率限制
            if not self._refresh_token():
                print(f"[{self.account_name}] 无法获取有效token，签名计算失败")
                return None, None
        
        if t is None:
            t = str(int(time.time() * 1000))
        
        sign_str = f"{self.token}&{t}&{self.app_key}&{data_str}"
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest(), t
    
    def _refresh_token(self):
        """Token过期自动刷新，带有3秒频率限制"""
        current_time = time.time()
        
        # 检查是否在最小刷新间隔内
        if current_time - self.last_token_refresh < self.min_refresh_interval:
            remaining = self.min_refresh_interval - (current_time - self.last_token_refresh)
            print(f"[{self.account_name}] 刷新频率限制，请等待 {remaining:.1f} 秒后再试")
            return False
        
        # 更新最后刷新时间
        self.last_token_refresh = current_time
        
        url = "https://h5api.m.taobao.com/h5/mtop.relationrecommend.wirelessrecommend.recommend/2.0/"
        params = {
            "jsv": "2.7.4", "appKey": self.app_key, "t": str(int(time.time() * 1000)),
            "sign": "AA", "api": "mtop.relationrecommend.wirelessrecommend.recommend", "v": "2.0",
            "data": json.dumps({"appId": "300", "params": "{}"}, separators=(',', ':'))
        }
        try:
            r = self.session.get(url, params=params, timeout=10)
            
            # 检查响应内容判断Cookie失效类型
            response_text = r.text
            if "FAIL_SYS_SESSION_EXPIRED" in response_text or "SESSION_EXPIRED" in response_text:
                print(f"[{self.account_name}] 检测到 SESSION 已彻底过期，无法刷新 token，需要重新登录抓新 cookie")
                return False
            elif "FAIL_SYS_TOKEN_EXPIRED" in response_text:
                print(f"[{self.account_name}] 只是 token 过期，但长效 cookie 可能还在，刷新失败可能是风控或参数问题")
                return False
            elif "SUCCESS" not in response_text and "登录" in response_text:
                print(f"[{self.account_name}] 检测到需要登录，Cookie 可能已失效")
                return False
            
            # 如果刷新成功，更新token
            if '_m_h5_tk' in r.cookies:
                new_tk = r.cookies['_m_h5_tk']
                self.token = new_tk.split('_')[0]
                self.token_enc = r.cookies.get('_m_h5_tk_enc')
                print(f"[{self.account_name}] Token 刷新成功")
                return True
            else:
                print(f"[{self.account_name}] 刷新失败，未知原因，响应: {response_text[:200]}")
                return False
                
        except Exception as e:
            print(f"[{self.account_name}] 刷新token请求异常: {e}")
            return False

    def query_logistics_detail(self, order_id):
        """
        核心方法：查询物流轨迹
        集成了用户抓包提供的 jsv, ttid, originaljson 参数
        """
        api_name = "mtop.taobao.logistics.detailorlist.query"
        version = "1.0"
        
        data_dict = {"orderId": str(order_id)}
        data_str = json.dumps(data_dict, separators=(',', ':'))
        
        t = str(int(time.time() * 1000))
        sign, t = self.calculate_sign(data_str, t)
        
        # 如果签名计算失败，直接返回
        if sign is None:
            print(f"  [!] 无法计算签名，跳过订单 {order_id}")
            return None
        
        # 使用用户提供的抓包参数
        params = {
            "jsv": "2.7.0",
            "appKey": self.app_key,
            "t": t,
            "sign": sign,
            "api": api_name,
            "v": version,
            "type": "originaljson", # 必须是 originaljson
            "dataType": "json",
            "ttid": "#t#ip##_h5_web_default", # 必须是此 ttid
            "needLogin": "true",
            "data": data_str
        }
        
        url = f"https://h5api.m.taobao.com/h5/{api_name}/{version}/"
        headers = self.headers.copy()
        headers["Referer"] = "https://cdn.m.taobao.com/"
        
        try:
            print(f"  --> 正在请求接口...")
            response = self.session.get(url, params=params, headers=headers, timeout=15)
            self.save_response(response, f"logistics_{order_id}")
            
            result = response.json()
            ret = result.get("ret", [])
            
            # 检查响应中的错误信息
            response_text = str(result)
            if "FAIL_SYS_TOKEN_EXPIRED" in response_text:
                print(f"  [!] Token过期，尝试刷新...")
                if self._refresh_token():
                    # 刷新后重新尝试查询
                    return self.query_logistics_detail(order_id)
                else:
                    return None
                    
            elif "FAIL_SYS_SESSION_EXPIRED" in response_text or "SESSION_EXPIRED" in response_text:
                print(f"  [!] Session已彻底过期，无法查询物流")
                return None
                
            elif "需要登录" in response_text or "未登录" in response_text:
                print(f"  [!] 需要登录，Cookie已失效")
                return None
            
            if "SUCCESS" not in str(ret):
                print(f"  [!] 物流详情获取失败: {ret}")
                return None

            data = result.get("data", {})
            global_data = data.get("data", {})
            
            # 查找最新的物流轨迹（第一个logisticsDetailLine开头的字段）
            latest_logistics = None
            for key, value in global_data.items():
                if key.startswith("logisticsDetailLine_"):
                    # 只取第一个找到的，就是最新的
                    latest_logistics = value
                    break
            
            if not latest_logistics:
                print(f"  [i] 订单 {order_id}: 暂无轨迹")
                return {"message": "暂无轨迹", "update_time": "未知时间"}
            
            # 提取物流描述信息（拼接desc中的所有text）
            desc_list = latest_logistics.get("fields", {}).get("desc", [])
            latest_desc = ""
            
            if desc_list:
                for desc_item in desc_list:
                    text = desc_item.get("text", "")
                    if text:
                        latest_desc += text
            
            # 提取时间信息（从subTitle的text中获取）
            sub_title = latest_logistics.get("fields", {}).get("subTitle", {})
            latest_time = sub_title.get("text", "未知时间")
            
            if not latest_desc:
                latest_desc = "暂无物流信息"
                
            print(f"  [✓] 订单 {order_id} 最新物流: {latest_desc} (时间: {latest_time})")
            return {"message": latest_desc, "update_time": latest_time}
                
        except Exception as e:
            print(f"  [!] 请求异常: {e}")
            return None

    def get_orders(self):
        """
        获取订单列表并循环处理物流查询
        """
        print(f"\n[{self.account_name}] 正在抓取订单列表...")
        data_dict = {
            "tabCode": "all", "page": 1, "appName": "tborder",
            "appVersion": "3.0", "condition": "{}", "ttid": "201200@taobao_h5_9.18.0"
        }
        
        # 调用 mtop 发起订单列表请求
        api_name = "mtop.taobao.order.queryboughtlistV2"
        data_str = json.dumps(data_dict, separators=(',', ':'))
        t = str(int(time.time() * 1000))
        sign, t = self.calculate_sign(data_str, t)
        
        # 如果签名计算失败，直接返回
        if sign is None:
            print(f"[{self.account_name}] 无法计算签名，无法获取订单列表")
            return False
        
        params = {
            "jsv": "2.7.4", "appKey": self.app_key, "t": t, "sign": sign,
            "api": api_name, "v": "1.0", "type": "jsonp", "dataType": "jsonp",
            "callback": "mtopjsonp1", "data": data_str
        }
        
        try:
            r = self.session.get(f"https://h5api.m.taobao.com/h5/{api_name}/1.0/", params=params, headers=self.headers)
            text = r.text.strip()
            if text.startswith('mtopjsonp1('): text = text[11:-1]
            result = json.loads(text)
            
            # 检查API响应是否包含错误信息 - 增强判断逻辑
            response_text = str(result)
            if "FAIL_SYS_TOKEN_EXPIRED" in response_text:
                print(f"[{self.account_name}] Token已过期，尝试刷新...")
                if not self._refresh_token():
                    return False
                # 刷新后重新尝试请求
                return self.get_orders()  # 递归调用
                
            elif "FAIL_SYS_SESSION_EXPIRED" in response_text or "SESSION_EXPIRED" in response_text:
                print(f"[{self.account_name}] Session已彻底过期，需要重新登录")
                return False
                
            elif "需要登录" in response_text or "未登录" in response_text:
                print(f"[{self.account_name}] 检测到需要登录，Cookie已失效")
                return False
            
            res_str = result.get("data", {}).get("result", "{}")
            main_orders = json.loads(res_str).get("mainOrders", [])
            
            print(f"[{self.account_name}] 成功找到 {len(main_orders)} 个主订单")
            print("-" * 40)

            trace_orders = []  # 存储物流信息的订单列表
            
            for order in main_orders:
                order_id = order.get("id")
                status_info = order.get("statusInfo", {})
                order_status_text = status_info.get("text", "")

                sub = order.get("subOrders", [{}])[0]
                item_name = sub.get("itemInfo", {}).get("title", "未知商品")

                # 只处理非交易成功和交易关闭的订单
                if order_status_text not in ['交易成功', '交易关闭']:
                    print(f"订单: {order_id} | 状态: {order_status_text} | 商品: {item_name[:15]}")
                    # 执行物流查询
                    logistics_info = self.query_logistics_detail(order_id)
                    
                    if logistics_info:
                        # 添加到物流信息列表
                        trace_orders.append({
                            'goods_name': item_name,
                            'message': logistics_info.get('message', '未知状态'),
                            'update_time': logistics_info.get('update_time', '未知时间')
                        })
                    
                    # 设置延迟：关键安全设置，防止连续查询被封
                    delay_time = random.uniform(3.5, 7.5)
                    print(f"  [休息] 等待 {delay_time:.1f} 秒后处理下一个...")
                    time.sleep(delay_time)
                # 交易成功和交易关闭的订单直接跳过，不显示任何提示
            
            # 保存物流信息到wl.json
            if trace_orders:
                self.save_wl_data(trace_orders)
            else:
                # 如果没有物流信息，也要清空该账号的记录
                self.save_wl_data([])
            
            return True
        except Exception as e:
            print(f"[{self.account_name}] 列表获取异常: {e}")
            # 检查异常信息中是否包含token过期相关提示
            if "TOKEN_EXPIRED" in str(e) or "SESSION_EXPIRED" in str(e) or "登录" in str(e):
                print(f"[{self.account_name}] Cookie已失效")
            return False

    def save_wl_data(self, trace_orders):
        """
        按照PDD格式保存物流信息到wl.json
        格式: {账号名: [{商品名: [物流信息, 更新时间]}, ...]}
        """
        try:
            wl_path = os.path.join(self.save_path, 'wl.json')
            wl_data = {}
            
            # 读取现有数据
            if os.path.exists(wl_path):
                try:
                    with open(wl_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            wl_data = json.loads(content)
                except:
                    wl_data = {}
            
            # 删除该账号的旧数据
            if self.account_name in wl_data:
                del wl_data[self.account_name]
                print(f"已删除账号 {self.account_name} 的旧物流数据")
            
            # 如果有新的物流数据，则按照PDD格式保存
            if trace_orders:
                wl_data[self.account_name] = []
                
                for order in trace_orders:
                    goods_name = order.get('goods_name', f'未知商品_{int(time.time())}')
                    message = order.get('message', '未知状态')
                    update_time = order.get('update_time', '未知时间')
                    
                    # 按照PDD的数据结构格式：{商品名称: [物流信息, 更新时间]}
                    order_dict = {goods_name: [message, update_time]}
                    wl_data[self.account_name].append(order_dict)
                
                print(f"已保存账号 {self.account_name} 的物流数据到wl.json，订单数: {len(trace_orders)}")
            else:
                print(f"账号 {self.account_name} 没有物流数据，已清空该账号的物流记录")
            
            # 保存到文件
            with open(wl_path, 'w', encoding='utf-8') as f:
                json.dump(wl_data, f, ensure_ascii=False, indent=2)
            
            return True
                
        except Exception as e:
            print(f"保存物流信息到wl.json失败: {e}")
            return False

    def run_test(self):
        print(f"\n===== 开始账号测试: {self.account_name} =====")
        
        # 直接尝试获取订单列表来测试cookie有效性
        success = self.get_orders()
        
        if not success:
            print(f"[{self.account_name}] 错误：Cookie已失效或无法获取订单列表，请重新抓取")
            return False
        
        return True

def load_accounts_from_json():
    """从ck.js文件加载账号信息 - 只支持JSON格式"""
    file_path = os.path.join(BASE_PATH, "cache", "ck.js")
    accounts = []
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 解析JSON格式的账号数据
            accounts = parse_json_accounts(content, file_path)
            return accounts
        else:
            print(f"账号文件 {file_path} 不存在")
            return []
    except Exception as e:
        print(f"加载账号文件失败: {e}")
        return []

def parse_json_accounts(content, file_path):
    """解析JSON格式的账号数据"""
    accounts = []
    
    try:
        # 清理内容，移除可能的JavaScript变量声明
        cleaned_content = content
        
        # 如果是.js文件，尝试提取JSON部分
        if file_path.endswith('.js'):
            # 移除变量声明和分号
            json_match = re.search(r'=\s*({.*?});?\s*$', content, re.DOTALL)
            if json_match:
                cleaned_content = json_match.group(1)
            else:
                # 尝试直接查找JSON对象
                json_match = re.search(r'({.*})', content, re.DOTALL)
                if json_match:
                    cleaned_content = json_match.group(1)
        
        # 解析JSON数据
        data = json.loads(cleaned_content)
        
        # 提取tb账号列表（淘宝账号）
        tb_accounts = data.get('tb', [])
        
        for i, account in enumerate(tb_accounts, 1):
            user_agent = account.get('ua', '')
            name = account.get('name', f'淘宝账号{i}')
            cookie = account.get('cookie', '')
            date_str = account.get('date', '')  # 获取日期字段
            
            if user_agent and cookie:
                accounts.append({
                    'ua': user_agent,
                    'name': name,
                    'cookie': cookie,
                    'date': date_str,  # 保存日期字段
                    'original_data': account  # 保存原始数据用于更新
                })
                print(f"  ✅ 加载淘宝账号: {name} (日期: {date_str if date_str else '无记录'})")
        
        # 统计信息
        tb_count = len(tb_accounts)
        pdd_count = len(data.get('pdd', []))
        print(f"账号统计: 淘宝账号 {tb_count}个, 拼多多账号 {pdd_count}个")
        
        return accounts
        
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        print("请确保ck.js文件包含有效的JSON格式数据")
        return []
    except Exception as e:
        print(f"解析账号数据失败: {e}")
        return []

def update_account_cookie_and_date(account_index, account_info, session_cookies):
    """
    更新账号的Cookie和日期
    如果距离上次运行超过3天，则用新的Cookie替换旧的Cookie
    """
    file_path = os.path.join(BASE_PATH, "cache", "ck.js")
    
    try:
        # 读取原文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # 解析JSON数据
        cleaned_content = content
        if file_path.endswith('.js'):
            json_match = re.search(r'=\s*({.*?});?\s*$', content, re.DOTALL)
            if json_match:
                cleaned_content = json_match.group(1)
        
        data = json.loads(cleaned_content)
        
        # 获取tb账号列表
        tb_accounts = data.get('tb', [])
        
        if 0 <= account_index - 1 < len(tb_accounts):
            account = tb_accounts[account_index - 1]
            current_date = datetime.now().strftime("%Y%m%d")
            
            # 获取当前日期和账号中的日期
            today = datetime.now().date()
            account_date_str = account.get('date', '')
            
            # 检查是否需要更新
            need_update = False
            days_diff = 0
            
            if not account_date_str:
                # 如果没有日期字段，创建并设置为今天
                print("🔔🔔 首次运行此账号，创建日期字段")
                need_update = True
            else:
                try:
                    # 解析日期字符串
                    account_date = datetime.strptime(account_date_str, "%Y%m%d").date()
                    # 计算日期差
                    days_diff = (today - account_date).days
                    print(f"📅📅 距离上次运行 {days_diff} 天")
                    
                    if days_diff > 2:  # 改为3天
                        print("🔔🔔 距离上次运行超过3天，需要更新Cookie")
                        need_update = True
                    else:
                        print("✅ 距离上次运行不足3天，不需要更新Cookie")
                except ValueError:
                    # 日期格式错误，视为需要更新
                    print("⚠️ 日期格式错误，需要更新")
                    need_update = True
            
            if need_update:
                # 使用session中的最新cookies
                if session_cookies:
                    # 从session中获取最新的cookies
                    cookie_dict = session_cookies.get_dict()
                    cookie_str = '; '.join([f"{k}={v}" for k, v in cookie_dict.items()])
                    account['cookie'] = cookie_str
                    print("✅ 已使用session中的最新Cookie更新")
                
                # 更新日期为今天
                account['date'] = current_date
                print(f"✅ 日期已更新为: {current_date}")
                
                # 重新构建JSON内容
                updated_data = {
                    "pdd": data.get('pdd', []),  # 保留拼多多账号数据
                    "tb": tb_accounts
                }
                
                # 写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(updated_data, f, ensure_ascii=False, indent=2)
                
                print("✅ 账号信息已更新到ck.js")
                return True
            else:
                print("✅ 账号信息无需更新")
                return False
        else:
            print("❌❌ 账号编号超出范围")
            return False
            
    except Exception as e:
        print(f"❌❌ 更新账号信息过程中出错: {e}")
        return False

def main():
    # 从JSON文件加载账号信息
    accounts = load_accounts_from_json()
    
    if not accounts: 
        print("没有找到可用的淘宝账号，请检查ck.js文件")
        return
    
    while True:
        # 显示所有账号列表
        print("\n=== 检测到的淘宝账号列表 ===")
        for i, acc in enumerate(accounts, 1):
            print(f"{i}. {acc['name']}")
        print("0. 运行所有账号")
        print("直接按回车键退出程序")
        
        # 用户选择
        choice = input("\n请选择要运行的账号: ").strip()
        
        # 如果用户直接按回车(空输入)，则退出程序
        if choice == "":
            print("程序已退出")
            break
            
        if choice == "0":
            selected_accounts = accounts
            print("将运行所有账号")
        else:
            try:
                index = int(choice) - 1
                if 0 <= index < len(accounts):
                    selected_accounts = [accounts[index]]
                    print(f"将运行账号: {accounts[index]['name']}")
                else:
                    print("输入无效，请重新选择")
                    continue
            except ValueError:
                print("输入无效，请重新选择")
                continue
        
        # 运行选中的账号
        for i, acc in enumerate(selected_accounts):
            # 计算账号索引
            if choice == "0":
                # 运行所有账号时，使用原始索引
                account_index = i + 1
            else:
                # 运行单个账号时，使用用户选择的索引
                account_index = int(choice)
            
            print(f"\n======= 正在运行账号 {account_index}: {acc['name']} =======")
            
            # 创建测试器实例
            tester = TaobaoTester(acc['cookie'], acc['ua'], acc['name'])
            
            # 运行测试
            success = tester.run_test()
            
            # 获取session cookies
            session_cookies = tester.get_session_cookies()
            
            # 检查并更新Cookie和日期
            if success:
                print("\n" + "="*50)
                print("检查是否需要更新Cookie和日期")
                print("="*50)
                update_account_cookie_and_date(account_index, acc, session_cookies)
            
            print(f"\n======= 账号 {acc['name']} 运行完成 =======")
            
            # 如果不是最后一个账号，添加延迟
            if i < len(selected_accounts) - 1:
                delay = random.uniform(2, 5)
                print(f"等待 {delay:.1f} 秒后运行下一个账号...")
                time.sleep(delay)
        
        print("\n" + "="*80)
        print("所有账号运行完成，返回账号选择界面...\n")
        # 账号运行完成后，自动返回选择界面，不需要额外确认

if __name__ == "__main__":
    main()
