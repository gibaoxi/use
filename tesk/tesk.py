import requests
import json
import os
import time
import socket
from datetime import datetime
import urllib3

# 禁用SSL证书验证警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Socks5ProxyCollectorWithNotify:
    def __init__(self):
        self.socks5_url = "https://mtpro.xyz/socks5"
        self.save_dir = "./tesk"
        self.filename = "ts.json"
        self.target_countries = ["SG", "HK", "KR", "JP"]  # 只关注这四个国家
        
        # 测试配置
        self.test_url = "https://httpbin.org/ip"
        
        # 存储当前获取的所有代理（不区分国家）
        self.all_current_proxies = []
        
        # 存储从文件读取的上一次数据
        self.previous_data = None
        
        self.telegram_bot_token = None
        self.telegram_chat_id = None
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 检查文件是否存在，不存在则创建
        self.init_data_file()
    
    def init_data_file(self):
        """初始化数据文件，如果不存在则创建"""
        filepath = os.path.join(self.save_dir, self.filename)
        if not os.path.exists(filepath):
            print("📄 首次运行，创建数据文件...")
            os.makedirs(self.save_dir, exist_ok=True)
            initial_data = {"new": {}, "old": {}}
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            self.previous_data = initial_data
            print("✅ 数据文件创建完成")
        else:
            # 加载现有数据
            self.load_previous_data()
    
    def load_previous_data(self):
        """加载上一次保存的数据"""
        filepath = os.path.join(self.save_dir, self.filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.previous_data = json.load(f)
                print(f"📂 已加载上一次数据: new={len(self.previous_data.get('new', {}))}个, old={len(self.previous_data.get('old', {}))}个")
                return True
            except Exception as e:
                print(f"❌ 加载上一次数据失败: {e}")
                self.previous_data = {"new": {}, "old": {}}
        return False
    
    def test_tcp_connection(self, ip: str, port: str, timeout: int = 5) -> bool:
        """测试TCP连接"""
        try:
            print(f"🔍 测试TCP连接: {ip}:{port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, int(port)))
            sock.close()
            
            if result == 0:
                print(f"✅ TCP连接成功: {ip}:{port}")
                return True
            else:
                print(f"❌ TCP连接失败: {ip}:{port}")
                return False
        except Exception as e:
            print(f"❌ TCP连接异常: {ip}:{port}, 错误: {e}")
            return False
    
    def test_socks5_proxy(self, ip: str, port: str, timeout: int = 10) -> bool:
        """测试SOCKS5代理访问"""
        try:
            print(f"🔍 测试SOCKS5代理: {ip}:{port}")
            
            proxies = {
                'http': f'socks5://{ip}:{port}',
                'https': f'socks5://{ip}:{port}'
            }
            
            start_time = datetime.now()
            response = requests.get(
                self.test_url, 
                proxies=proxies, 
                timeout=timeout,
                verify=False
            )
            end_time = datetime.now()
            
            response_time = (end_time - start_time).total_seconds()
            print(f"✅ 代理测试成功! 响应时间: {response_time:.2f}秒")
            return True
            
        except Exception as e:
            print(f"❌ 代理测试失败: {e}")
            return False
    
    def test_proxy_comprehensive(self, proxy_info: dict) -> bool:
        """综合测试代理（TCP + SOCKS5）"""
        ip = proxy_info.get("ip", "")
        port = proxy_info.get("port", "")
        
        if not ip or not port:
            return False
        
        # 先测试TCP连接
        tcp_success = self.test_tcp_connection(ip, port)
        if not tcp_success:
            return False
        
        # TCP连接成功，继续测试SOCKS5代理功能
        return self.test_socks5_proxy(ip, port)
    
    def filter_tested_proxies(self, proxies_by_country: dict) -> dict:
        """过滤并测试代理，只返回测试通过的代理"""
        tested_proxies = {}
        
        for country, proxies in proxies_by_country.items():
            tested_proxies[country] = []
            
            print(f"🧪 开始测试 {country} 的代理 ({len(proxies)}个)")
            
            for proxy in proxies:
                print(f"🎯 测试代理: {proxy['ip_port']}")
                
                if self.test_proxy_comprehensive(proxy):
                    print(f"✅ 代理测试通过: {proxy['ip_port']}")
                    tested_proxies[country].append(proxy)
                else:
                    print(f"❌ 代理测试失败: {proxy['ip_port']}")
            
            print(f"📊 {country} 测试结果: {len(tested_prox