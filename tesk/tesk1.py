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
            print("📄📄 首次运行，创建数据文件...")
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
                print(f"📂📂 已加载上一次数据: new={len(self.previous_data.get('new', {}))}个, old={len(self.previous_data.get('old', {}))}个")
                return True
            except Exception as e:
                print(f"❌❌ 加载上一次数据失败: {e}")
                self.previous_data = {"new": {}, "old": {}}
        return False

    def test_tcp_connection(self, ip: str, port: str, timeout: int = 5) -> bool:
        """测试TCP连接"""
        try:
            print(f"🔍🔍 测试TCP连接: {ip}:{port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, int(port)))
            sock.close()

            if result == 0:
                print(f"✅ TCP连接成功: {ip}:{port}")
                return True
            else:
                print(f"❌❌ TCP连接失败: {ip}:{port}")
                return False
        except Exception as e:
            print(f"❌❌ TCP连接异常: {ip}:{port}, 错误: {e}")
            return False

    def test_socks5_proxy(self, ip: str, port: str, timeout: int = 10) -> bool:
        """测试SOCKS5代理访问"""
        try:
            print(f"🔍🔍 测试SOCKS5代理: {ip}:{port}")

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
            print(f"❌❌ 代理测试失败: {e}")
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

            print(f"🧪🧪 开始测试 {country} 的代理 ({len(proxies)}个)")

            for proxy in proxies:
                print(f"🎯🎯 测试代理: {proxy['ip_port']}")

                if self.test_proxy_comprehensive(proxy):
                    print(f"✅ 代理测试通过: {proxy['ip_port']}")
                    tested_proxies[country].append(proxy)
                else:
                    print(f"❌❌ 代理测试失败: {proxy['ip_port']}")

            print(f"📊📊 {country} 测试结果: {len(tested_proxies[country])}/{len(proxies)} 个通过")

        return {k: v for k, v in tested_proxies.items() if v}

    def load_telegram_config(self):
        """从环境变量加载Telegram配置"""
        try:
            # 从环境变量读取配置
            self.telegram_bot_token = os.environ.get('TG_BOT_TOKEN')
            self.telegram_chat_id = os.environ.get('TGG1')

            # 检查配置是否完整
            if not self.telegram_bot_token:
                print("❌❌ 未找到环境变量 TG_BOT_TOKEN")
                return False

            if not self.telegram_chat_id:
                print("❌❌ 未找到环境变量 TGG1")
                return False

            print("✅ Telegram配置加载成功")
            return True

        except Exception as e:
            print(f"❌❌ 加载Telegram配置失败: {e}")
            return False

    def send_telegram_message(self, message: str):
        """发送Telegram消息"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            print("❌❌ Telegram配置不完整，无法发送消息")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }

            response = requests.post(url, data=data, timeout=30)
            if response.status_code == 200:
                print("✅ Telegram消息发送成功")
                return True
            else:
                print(f"❌❌ Telegram消息发送失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌❌ 发送Telegram消息失败: {e}")
            return False

    def fetch_proxies(self):
        """获取代理数据"""
        try:
            api_url = "https://mtpro.xyz/api?type=socks"
            response = self.session.get(api_url, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌❌ 获取代理失败: {e}")
            return []

    def process_proxies(self, proxies):
        """处理代理数据，存储所有代理"""
        self.all_current_proxies = []

        for proxy in proxies:
            country = proxy.get("country", "UNKNOWN")
            ip = proxy.get("ip", "")
            port = proxy.get("port", "")
            ping = proxy.get("ping", 9999)

            if ip and port:
                proxy_info = {
                    "ip_port": f"{ip}:{port}",
                    "ping": ping,
                    "ip": ip,
                    "port": port,
                    "country": country
                }
                self.all_current_proxies.append(proxy_info)

        # 按ping值排序
        self.all_current_proxies.sort(key=lambda x: x["ping"])

    def find_new_target_proxies(self, target_country_proxies):
        """找出新增的SG/HK/KR/JP代理（与上一次的new数据对比）"""
        new_proxies_by_country = {}

        # 获取上一次的new数据，如果没有则为空字典
        previous_new = self.previous_data.get("new", {}) if self.previous_data else {}

        # 对比找出新增代理
        for country, current_proxies in target_country_proxies.items():
            # 从上一次new数据中提取该国家的ip_port列表
            previous_ip_ports = []
            if country in previous_new:
                for old_proxy in previous_new[country]:
                    if isinstance(old_proxy, dict):
                        previous_ip_ports.append(old_proxy.get("ip_port", ""))
                    else:
                        previous_ip_ports.append(old_proxy)

            # 找出新增代理（当前有而上一次没有的）
            new_proxies = []
            for proxy in current_proxies:
                if proxy["ip_port"] not in previous_ip_ports:
                    new_proxies.append(proxy)

            if new_proxies:
                new_proxies_by_country[country] = new_proxies

        return new_proxies_by_country

    def find_common_proxies(self, all_current_proxies_by_country):
        """找出新旧数据中都有的代理（与上一次的old数据对比），按国家分组"""
        # 获取上一次的old数据，如果没有则为空字典
        previous_old = self.previous_data.get("old", {}) if self.previous_data else {}

        # 找出共同代理（当前和上一次都有的）
        common_proxies_by_country = {}

        for country, current_proxies in all_current_proxies_by_country.items():
            # 从上一次old数据中提取该国家的ip_port列表
            previous_ip_ports = []
            if country in previous_old:
                for old_proxy in previous_old[country]:
                    if isinstance(old_proxy, dict):
                        previous_ip_ports.append(old_proxy.get("ip_port", ""))
                    else:
                        previous_ip_ports.append(old_proxy)

            # 找出共同的代理（当前和上一次都有的）
            common_proxies = []
            for proxy in current_proxies:
                if proxy["ip_port"] in previous_ip_ports:
                    common_proxies.append(proxy)

            if common_proxies:
                common_proxies_by_country[country] = common_proxies

        return common_proxies_by_country

    def create_telegram_proxy_link(self, ip: str, port: str) -> str:
        """创建Telegram代理链接"""
        return f"tg://socks?server={ip}&port={port}"

    def format_proxy_list_for_message(self, proxies_by_country):
        """格式化代理列表用于消息发送"""
        message_parts = []
        
        for country, proxies in proxies_by_country.items():
            if country not in self.target_countries:
                continue
                
            message_parts.append(f"{country} ({len(proxies)}个):\n")
            
            for i, proxy in enumerate(proxies, 1):
                telegram_link = self.create_telegram_proxy_link(proxy["ip"], proxy["port"])
                ping = proxy["ping"]
                
                if telegram_link:
                    message_parts.append(f'  {i}. <a href="{telegram_link}">{proxy["ip_port"]}</a> {ping}ms\n')
                else:
                    message_parts.append(f'  {i}. {proxy["ip_port"]} {ping}ms\n')
            
            message_parts.append("\n")
        
        return "".join(message_parts)

    def save_to_file(self, new_proxies_by_country, common_proxies_by_country, all_proxies_by_country):
        """保存代理数据到文件"""
        filepath = os.path.join(self.save_dir, self.filename)

        try:
            os.makedirs(self.save_dir, exist_ok=True)

            # 确定要保存的new数据
            if new_proxies_by_country:
                new_data_to_save = new_proxies_by_country
            else:
                new_data_to_save = self.previous_data.get("new", {}) if self.previous_data else {}

            # 确定要保存的old数据
            if common_proxies_by_country:
                old_data_to_save = common_proxies_by_country
            else:
                old_data_to_save = all_proxies_by_country

            # 构建保存数据
            save_data = {
                "new": new_data_to_save,
                "old": old_data_to_save
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"❌❌ 保存文件失败: {e}")
            return False

    def run(self):
        """主程序"""
        print("=" * 60)
        print("SOCKS5代理监控 - 目标国家版 (SG/HK/KR/JP)")
        print("=" * 60)

        # 1. 检查文件是否存在，如果不存在则创建
        filepath = os.path.join(self.save_dir, self.filename)
        if not os.path.exists(filepath):
            print("📄📄 首次运行，创建数据文件...")
            os.makedirs(self.save_dir, exist_ok=True)
            initial_data = {"new": {}, "old": {}}
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            self.previous_data = initial_data
            print("✅ 数据文件创建完成")
        else:
            # 加载现有数据
            self.load_previous_data()

        # 2. 加载Telegram配置
        telegram_ready = self.load_telegram_config()

        # 3. 获取新数据
        proxies = self.fetch_proxies()
        if not proxies:
            if telegram_ready:
                self.send_telegram_message("❌❌ 无法获取SOCKS5代理数据")
            return

        # 4. 处理代理数据
        self.process_proxies(proxies)

        # 5. 如果没有获取到代理，直接返回
        if not self.all_current_proxies:
            print("ℹℹ️ 没有获取到任何代理")
            return

        # 6. 对当前所有代理进行测试
        print("🧪🧪 开始代理测试...")

        # 将当前所有代理按国家分组进行测试
        all_proxies_by_country = {}
        for proxy in self.all_current_proxies:
            country = proxy["country"]
            if country not in all_proxies_by_country:
                all_proxies_by_country[country] = []
            all_proxies_by_country[country].append(proxy)

        # 测试所有代理
        tested_proxies_by_country = self.filter_tested_proxies(all_proxies_by_country)

        # 如果没有测试成功的代理，直接返回
        if not tested_proxies_by_country:
            print("ℹℹ️ 没有测试成功的代理")
            return

        # 更新当前代理列表为测试通过的代理
        self.all_current_proxies = []
        for proxies_list in tested_proxies_by_country.values():
            self.all_current_proxies.extend(proxies_list)

        # 7. 提取目标国家的代理
        target_country_proxies = {}
        for country in self.target_countries:
            if country in tested_proxies_by_country:
                target_country_proxies[country] = tested_proxies_by_country[country]

        # 8. 找出新增的目标国家代理（与上一次new数据对比）
        new_proxies_by_country = self.find_new_target_proxies(target_country_proxies)

        # 9. 找出稳定代理（与上一次old数据对比）
        common_proxies_by_country = self.find_common_proxies(tested_proxies_by_country)

        # 10. 计算总数
        total_new = sum(len(p) for p in new_proxies_by_country.values()) if new_proxies_by_country else 0
        total_common = sum(len(p) for p in common_proxies_by_country.values()) if common_proxies_by_country else 0

        # 11. 先保存数据
        self.save_to_file(new_proxies_by_country, common_proxies_by_country, tested_proxies_by_country)

        # 12. 检查是否需要发送通知
        if (total_new > 0 or total_common > 0) and telegram_ready:
            # 读取刚刚保存的ts.json文件
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    current_data = json.load(f)
                
                # 构建消息
                message_parts = []
                
                # 第一行：统计信息
                message_parts.append(f"🆕 新增代理: {total_new}个 | 🔁 稳定代理: {total_common}个\n")
                
                # 添加new部分
                if current_data.get("new"):
                    message_parts.append("\n🆕 新增代理:\n")
                    message_parts.append(self.format_proxy_list_for_message(current_data["new"]))
                
                # 添加old部分
                if current_data.get("old"):
                    message_parts.append("\n🔁 稳定代理:\n")
                    message_parts.append(self.format_proxy_list_for_message(current_data["old"]))
                
                # 发送消息
                full_message = "".join(message_parts)
                self.send_telegram_message(full_message)
                print("✅ 通知已发送")
            except Exception as e:
                print(f"❌❌ 读取保存的文件失败: {e}")
        elif (total_new > 0 or total_common > 0) and not telegram_ready:
            print("ℹℹ️ 有更新但Telegram未配置，跳过通知")
        else:
            print("ℹℹ️ 没有新增代理和稳定代理，不发送通知")

        # 13. 显示统计信息
        print(f"🆕🆕🆕 新增代理: {total_new} 个")
        print(f"🔁🔁 稳定代理: {total_common} 个")
        print(f"🌍🌍 总代理数: {len(self.all_current_proxies)} 个")
        print(f"🎯🎯 目标国家代理: {sum(len(p) for p in target_country_proxies.values())} 个")

        print("=" * 40)
        print("✅ 程序执行完成")

if __name__ == "__main__":
    collector = Socks5ProxyCollectorWithNotify()
    collector.run()
