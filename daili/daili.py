#!/usr/bin/env python3
"""
GitHub自动代理测试脚本 - 支持HTTP、HTTPS、SOCKS4、SOCKS5代理测试
"""

import os
import sys
import time
import json
import socket
import requests
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import threading
import re
from urllib.parse import urlparse
import warnings

class GitHubProxyTester:
    def __init__(self):
        self.version = "1.0.0"
        self.total_tested = 0
        self.successful = 0
        self.failed = 0
        self.lock = threading.Lock()
        
        # GitHub仓库路径
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 代理文件映射
        self.proxy_files = {
            'http': {'name': 'HTTP', 'file': 'http.txt'},
            'https': {'name': 'HTTPS', 'file': 'https.txt'}, 
            'socks4': {'name': 'SOCKS4', 'file': 'socks4.txt'},
            'socks5': {'name': 'SOCKS5', 'file': 'socks5.txt'}
        }
        
        # 缓存测试网站
        self._test_urls = None
        
        # 确保必要的目录存在
        self.result_dir = os.path.join(self.base_dir, "result")
        os.makedirs(self.result_dir, exist_ok=True)
        
        print(f"🔧🔧🔧🔧 初始化GitHub代理测试器")
        print(f"📁📁📁📁 工作目录: {self.base_dir}")
        print(f"💾💾💾💾 结果目录: {self.result_dir}")
    
    def clean_and_validate_proxy(self, proxy_str):
        """合并清理和验证代理功能，返回清理后的代理或None（如果无效）"""
        if not proxy_str or not isinstance(proxy_str, str):
            return None
        
        proxy = proxy_str.strip()
        
        # 去掉/#后面的延迟信息
        if '/#' in proxy:
            proxy = proxy.split('/#')[0].strip()
        
        # 如果已经有协议头，直接返回
        if proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            return proxy if self._validate_proxy_format(proxy) else None
        
        # 使用urlparse解析代理格式
        if '://' not in proxy:
            test_url = 'http://' + proxy
        else:
            test_url = proxy
        
        try:
            parsed = urlparse(test_url)
            
            # 检查主机名
            hostname = parsed.hostname
            if not hostname:
                return None
            
            # 检查端口
            port = parsed.port
            if port is None:
                # 尝试从netloc中提取端口
                if ':' in parsed.netloc:
                    try:
                        port_str = parsed.netloc.split(':')[-1]
                        if '/' in port_str:
                            port_str = port_str.split('/')[0]
                        port = int(port_str)
                    except (ValueError, IndexError):
                        return None
            
            if port is not None and not (1 <= port <= 65535):
                return None
            
            # 验证IP地址格式（如果是IP的话）
            if hostname.replace('.', '').isdigit():
                try:
                    socket.inet_aton(hostname)
                except socket.error:
                    # 不是有效的IP地址，但可能是域名，所以仍然有效
                    pass
            
            # 返回清理后的代理格式
            if parsed.username or parsed.password:
                # 有认证信息的代理
                auth_part = ""
                if parsed.username:
                    auth_part = parsed.username
                    if parsed.password:
                        auth_part += ":" + parsed.password
                    auth_part += "@"
                
                if hostname and port:
                    return f"{auth_part}{hostname}:{port}"
                elif hostname:
                    return hostname
            else:
                # 没有认证信息的代理
                if ':' in proxy and '@' not in proxy:
                    return proxy
                elif hostname and port:
                    return f"{hostname}:{port}"
                elif hostname:
                    return hostname
            
            return proxy
            
        except Exception as e:
            # 如果urlparse解析失败，使用简单方法
            if ':' in proxy:
                parts = proxy.split(':')
                if len(parts) == 2:
                    ip = parts[0].strip()
                    port_str = parts[1].strip()
                    if '/' in port_str:
                        port_str = port_str.split('/')[0]
                    
                    try:
                        port = int(port_str)
                        if 1 <= port <= 65535:
                            return f"{ip}:{port}"
                    except ValueError:
                        pass
            
            return None
    
    def _validate_proxy_format(self, proxy):
        """内部验证代理格式是否有效"""
        if not proxy:
            return False
        
        # 测试URL用于解析
        if '://' not in proxy:
            test_url = 'http://' + proxy
        else:
            test_url = proxy
        
        try:
            parsed = urlparse(test_url)
            
            # 检查主机名
            hostname = parsed.hostname
            if not hostname:
                return False
            
            # 检查端口
            port = parsed.port
            if port is None:
                # 尝试从netloc中提取端口
                if ':' in parsed.netloc:
                    try:
                        port_str = parsed.netloc.split(':')[-1]
                        if '/' in port_str:
                            port_str = port_str.split('/')[0]
                        port = int(port_str)
                    except (ValueError, IndexError):
                        return False
            
            if port is not None and not (1 <= port <= 65535):
                return False
            
            # 验证IP地址格式（如果是IP的话）
            if hostname.replace('.', '').isdigit():
                try:
                    socket.inet_aton(hostname)
                except socket.error:
                    # 不是有效的IP地址，但可能是域名，所以仍然有效
                    pass
            
            return True
            
        except Exception:
            return False
    
    def get_proxy_url(self, proxy, proxy_type):
        """根据代理类型生成完整的代理URL"""
        if not proxy:
            return ""
        
        # 如果代理已经有协议头，检查是否需要转换
        if proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            current_protocol = proxy.split('://')[0] + '://'
            target_protocol = ""
            
            if proxy_type == "HTTP":
                target_protocol = "http://"
            elif proxy_type == "HTTPS":
                target_protocol = "https://"
            elif proxy_type == "SOCKS4":
                target_protocol = "socks4://"
            elif proxy_type == "SOCKS5":
                target_protocol = "socks5://"
            else:
                target_protocol = "http://"
            
            # 如果当前协议与目标协议不同，进行转换
            if current_protocol != target_protocol:
                return proxy.replace(current_protocol, target_protocol, 1)
            else:
                return proxy
        
        # 代理没有协议头，添加对应的协议
        if proxy_type == "HTTP":
            return f"http://{proxy}"
        elif proxy_type == "HTTPS":
            return f"https://{proxy}"
        elif proxy_type == "SOCKS4":
            return f"socks4://{proxy}"
        elif proxy_type == "SOCKS5":
            return f"socks5://{proxy}"
        else:
            return f"http://{proxy}"
    
    def extract_domain_info(self, url):
        """从URL中提取域名信息和check_string"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            if not domain:
                domain = url.split('/')[2] if '//' in url else url.split('/')[0]
            
            domain = domain.split(':')[0]
            parts = domain.split('.')
            
            if len(parts) >= 2:
                check_string = parts[-2]
                site_abbr = check_string[:3].lower()
                return check_string, site_abbr
            else:
                check_string = domain
                site_abbr = domain[:3].lower() if len(domain) >= 3 else domain.lower()
                return check_string, site_abbr
                
        except Exception as e:
            print(f"❌❌❌❌ 解析URL {url} 失败: {e}")
            return "website", "web"
    
    def load_test_urls(self):
        """加载测试网站列表"""
        if self._test_urls is not None:
            return self._test_urls
        
        ym_file = os.path.join(self.base_dir, "ym.txt")
        
        if not os.path.exists(ym_file):
            print(f"❌❌❌❌ ym.txt文件不存在: {ym_file}")
            return []
        
        test_urls = []
        
        try:
            with open(ym_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if not line.startswith(('http://', 'https://')):
                            line = 'https://' + line
                        
                        check_string, site_abbr = self.extract_domain_info(line)
                        
                        test_urls.append({
                            "url": line,
                            "name": f"网站{line_num}",
                            "timeout": 8,
                            "check_string": check_string,
                            "site_abbr": site_abbr
                        })
            
            # 去重
            unique_test_urls = []
            seen_urls = set()
            for site in test_urls:
                url_key = site["url"].rstrip('/')
                if url_key not in seen_urls:
                    seen_urls.add(url_key)
                    unique_test_urls.append(site)
            
            self._test_urls = unique_test_urls
            
            if unique_test_urls:
                print(f"✅ 从ym.txt加载了 {len(unique_test_urls)} 个测试网站")
            else:
                print("❌❌❌❌ 没有有效的测试网站")
            
            return self._test_urls
            
        except Exception as e:
            print(f"❌❌❌❌ 读取ym.txt失败: {e}")
            return []
    
    def get_test_urls(self):
        """获取测试网站列表"""
        if self._test_urls is None:
            return self.load_test_urls()
        return self._test_urls
    
    def import_previous_successful_proxies(self):
        """导入上次测试成功的代理到对应文件"""
        if not os.path.exists(self.result_dir):
            print("❌❌❌❌ result目录不存在，跳过导入")
            return
        
        imported_count = 0
        
        for proxy_type, info in self.proxy_files.items():
            result_file = os.path.join(self.result_dir, f"{proxy_type}.txt")
            
            if os.path.exists(result_file):
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        successful_proxies = []
                        
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # 使用合并的清理和验证功能
                                proxy = self.clean_and_validate_proxy(line)
                                if proxy:
                                    successful_proxies.append(proxy)
                    
                    if successful_proxies:
                        target_path = os.path.join(self.base_dir, info['file'])
                        existing_proxies = []
                        
                        if os.path.exists(target_path):
                            with open(target_path, 'r', encoding='utf-8') as f:
                                for line in f:
                                    line = line.strip()
                                    if line and not line.startswith('#'):
                                        # 使用合并的清理和验证功能
                                        proxy = self.clean_and_validate_proxy(line)
                                        if proxy:
                                            existing_proxies.append(proxy)
                        
                        all_proxies = list(set(existing_proxies + successful_proxies))
                        
                        with open(target_path, 'w', encoding='utf-8') as f:
                            f.write(f"# {info['name']}代理列表（包含导入的成功代理）\n")
                            f.write(f"# 总代理数: {len(all_proxies)}\n")
                            f.write(f"# 导入成功代理: {len(successful_proxies)}\n")
                            f.write("#" * 50 + "\n\n")
                            
                            for proxy in sorted(all_proxies):
                                f.write(f"{proxy}\n")
                        
                        print(f"✅ 导入 {len(successful_proxies)} 个成功{info['name']}代理")
                        imported_count += len(successful_proxies)
                        
                except Exception as e:
                    print(f"❌❌❌❌ 导入{info['name']}代理失败: {e}")
        
        if imported_count > 0:
            print(f"✅ 总共导入 {imported_count} 个成功代理")
        else:
            print("ℹℹℹℹ️ 没有找到可导入的成功代理")
    
    def download_proxy_list(self, url, proxy_type):
        """从指定URL下载代理列表"""
        print(f"🌐🌐🌐🌐 下载{proxy_type}代理: {url}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            # 下载代理列表时不使用代理，验证SSL证书
            response = requests.get(url, headers=headers, timeout=30, verify=True)
            
            if response.status_code == 200:
                proxies = []
                for line in response.text.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('//'):
                        # 使用合并的清理和验证功能
                        proxy = self.clean_and_validate_proxy(line)
                        if proxy:
                            proxies.append(proxy)
                
                print(f"✅ 下载到 {len(proxies)} 个{proxy_type}代理")
                return proxies
            else:
                print(f"❌❌❌❌ 下载失败: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌❌❌❌ 下载失败: {e}")
            return []
    
    def save_proxies_to_file(self, proxies, file_path, proxy_type):
        """保存代理列表到文件"""
        if not proxies:
            print(f"⚠️ 没有{proxy_type}代理可保存")
            return
        
        unique_proxies = list(set(proxies))
        print(f"📊📊📊📊 {proxy_type}代理去重后: {len(unique_proxies)} 个")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# {proxy_type}代理列表\n")
            f.write(f"# 总代理数: {len(unique_proxies)}\n")
            f.write("#" * 50 + "\n\n")
            
            for proxy in sorted(unique_proxies):
                f.write(f"{proxy}\n")
        
        print(f"💾💾💾💾 已保存到: {file_path}")
    
    def parse_source_file(self):
        """解析source.txt文件，提取下载链接"""
        source_file = os.path.join(self.base_dir, "source.txt")
        
        if not os.path.exists(source_file):
            print(f"❌❌❌❌ source.txt文件不存在: {source_file}")
            return {}
        
        print(f"📁📁📁📁 解析source.txt文件")
        
        proxy_type_mapping = {
            'http': 'http',
            'https': 'https', 
            'socks4': 'socks4',
            'socks5': 'socks5'
        }
        
        all_links = {
            'http': [],
            'https': [],
            'socks4': [],
            'socks5': []
        }
        
        try:
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().strip()
                
                try:
                    data = json.loads(content)
                    
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                for proxy_type, urls in item.items():
                                    if proxy_type.lower() in proxy_type_mapping:
                                        mapped_type = proxy_type_mapping[proxy_type.lower()]
                                        
                                        if isinstance(urls, str):
                                            if urls.startswith('[') and urls.endswith(']'):
                                                try:
                                                    url_list = json.loads(urls)
                                                    if isinstance(url_list, list):
                                                        for url in url_list:
                                                            all_links[mapped_type].append(url)
                                                except:
                                                    all_links[mapped_type].append(urls)
                                            else:
                                                all_links[mapped_type].append(urls)
                                        elif isinstance(urls, list):
                                            for url in urls:
                                                all_links[mapped_type].append(url)
                    
                    print(f"✅ 解析成功，找到 {sum(len(links) for links in all_links.values())} 个链接")
                    
                except json.JSONDecodeError as e:
                    print(f"❌❌❌❌ JSON解析失败: {e}")
                    return {}
            
            total_links = sum(len(links) for links in all_links.values())
            print(f"📊📊📊📊 总共找到 {total_links} 个下载链接")
            
            return all_links
            
        except Exception as e:
            print(f"❌❌❌❌ 解析source.txt文件失败: {e}")
            return {}
    
    def download_and_classify_proxies(self):
        """从source.txt下载代理并分类保存"""
        print("\n" + "="*60)
        print("📥📥📥📥 开始下载代理并分类")
        print("="*60)
        
        all_links = self.parse_source_file()
        
        if not any(all_links.values()):
            print("❌❌❌❌ 没有找到有效的下载链接")
            return
        
        total_downloaded = 0
        
        for proxy_type, links in all_links.items():
            if not links:
                continue
                
            print(f"\n📥📥📥📥 处理{proxy_type.upper()}代理...")
            
            all_proxies = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_url = {
                    executor.submit(self.download_proxy_list, url, proxy_type): url 
                    for url in links
                }
                
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        proxies = future.result()
                        all_proxies.extend(proxies)
                    except Exception as e:
                        print(f"❌❌❌❌ 下载失败: {e}")
            
            if all_proxies:
                file_path = os.path.join(self.base_dir, self.proxy_files[proxy_type]['file'])
                self.save_proxies_to_file(all_proxies, file_path, proxy_type.upper())
                total_downloaded += len(all_proxies)
            else:
                print(f"❌❌❌❌ 没有下载到有效的{proxy_type}代理")
        
        print(f"\n📥📥📥📥 下载完成，开始导入上次测试成功的代理...")
        self.import_previous_successful_proxies()
        
        print(f"\n✅ 下载和导入完成! 总共下载 {total_downloaded} 个代理")
        return total_downloaded
    
    def load_proxies(self, file_path, limit=0):
        """从文件加载代理列表"""
        print(f"📁📁📁📁 加载代理文件: {os.path.basename(file_path)}")
        
        if not os.path.exists(file_path):
            print(f"❌❌❌❌ 文件不存在!")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                proxies = []
                lines = 0
                
                for line in f:
                    line = line.strip()
                    
                    if not line or line.startswith('#') or line.startswith('//'):
                        continue
                    
                    # 使用合并的清理和验证功能
                    proxy = self.clean_and_validate_proxy(line)
                    if proxy:
                        proxies.append(proxy)
                        lines += 1
                    
                    if limit > 0 and lines >= limit:
                        break
                
                print(f"✅ 成功加载 {len(proxies)} 个代理")
                if limit > 0 and lines >= limit:
                    print(f"📊📊📊📊 只加载前 {limit} 个代理")
                
                return proxies
                
        except Exception as e:
            print(f"❌❌❌❌ 读取文件失败: {e}")
            return []
    
    def test_single_url(self, proxy, test_config, proxy_type):
        """测试单个URL - 只在requests.get中使用verify=False"""
        result = {
            'proxy': proxy,
            'proxy_type': proxy_type,
            'test_name': test_config['name'],
            'test_url': test_config['url'],
            'success': False,
            'latency_ms': 0,
            'status_code': 0,
            'error': None,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'site_abbr': test_config.get('site_abbr', 'web')
        }
        
        # 生成代理URL
        proxy_url = self.get_proxy_url(proxy, proxy_type)
        
        # 设置代理
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        try:
            start_time = time.time()
            
            # 只在测试代理时禁用SSL验证
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                response = requests.get(
                    test_config['url'],
                    proxies=proxies,
                    timeout=test_config.get('timeout', 8),
                    headers=headers,
                    verify=False,  # 只在测试代理时禁用SSL验证
                    allow_redirects=True
                )
            
            latency = time.time() - start_time
            result['latency_ms'] = latency * 1000
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                check_string = test_config.get('check_string', '')
                if check_string:
                    if check_string.lower() in response.text.lower():
                        result['success'] = True
                        result['error'] = None
                    else:
                        # 检查页面是否包含常见HTML标记
                        page_text = response.text.lower()
                        common_indicators = ['html', 'http', 'www', 'com', 'net', 'org', 'title', 'body', 'head']
                        indicators_found = sum(1 for indicator in common_indicators if indicator in page_text)
                        
                        if indicators_found >= 2:  # 提高阈值减少误判
                            result['success'] = True
                            result['error'] = f"未找到 '{check_string}' 但页面有效"
                        else:
                            result['error'] = f"未找到 '{check_string}' 且页面无效"
                else:
                    result['success'] = True
                    result['error'] = None
            else:
                result['error'] = f"HTTP {response.status_code}"
                
        except requests.exceptions.ConnectTimeout:
            result['error'] = '连接超时'
        except requests.exceptions.ReadTimeout:
            result['error'] = '读取超时'
        except requests.exceptions.ConnectionError as e:
            error_str = str(e)
            if 'timed out' in error_str.lower():
                result['error'] = '连接超时'
            elif 'reset' in error_str.lower():
                result['error'] = '连接被重置'
            elif 'refused' in error_str.lower():
                result['error'] = '连接被拒绝'
            else:
                result['error'] = f'连接错误: {error_str[:30]}'
        except requests.exceptions.ProxyError as e:
            error_str = str(e)
            if 'timed out' in error_str.lower():
                result['error'] = '代理超时'
            elif 'socks' in error_str.lower():
                result['error'] = 'SOCKS代理错误'
            else:
                result['error'] = f'代理错误: {error_str[:30]}'
        except requests.exceptions.SSLError as e:
            result['error'] = f'SSL错误: {str(e)[:30]}'
        except socket.timeout:
            result['error'] = 'Socket超时'
        except Exception as e:
            error_str = str(e)
            result['error'] = f'其他错误: {error_str[:30]}'
        
        return result
    
    def test_proxy_connectivity(self, proxy, proxy_type):
        """测试单个代理的连通性"""
        test_urls = self.get_test_urls()
        best_result = None
        
        for test_config in test_urls:
            result = self.test_single_url(proxy, test_config, proxy_type)
            
            if result['success']:
                return result
            
            if best_result is None or (result.get('status_code', 0) > 0 and best_result.get('status_code', 0) == 0):
                best_result = result
            
            if result.get('status_code', 0) > 0:
                break
        
        return best_result or {
            'proxy': proxy,
            'proxy_type': proxy_type,
            'success': False,
            'error': '所有测试都失败',
            'latency_ms': 0,
            'test_name': '综合测试',
            'test_url': '多个URL',
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'site_abbr': 'unk'
        }
    
    def batch_test_proxies(self, proxies, proxy_type, max_workers=20):
        """批量测试代理"""
        if not proxies:
            return [], []
        
        print(f"\n🚀🚀🚀🚀 开始测试 {len(proxies)} 个{proxy_type}代理")
        print(f"📊📊📊📊 并发线程: {max_workers}")
        print(f"⏱⏱⏱⏱⏱⏱⏱⏱⏱ 超时时间: 8秒")
        print("-"*50)
        
        all_results = []
        successful_results = []
        
        def worker(proxy):
            result = self.test_proxy_connectivity(proxy, proxy_type)
            
            with self.lock:
                all_results.append(result)
                
                if result['success']:
                    successful_results.append(result)
                
                self.total_tested += 1
                if result['success']:
                    self.successful += 1
                else:
                    self.failed += 1
                
                if self.total_tested % 10 == 0 or self.total_tested == len(proxies):
                    percentage = self.total_tested / len(proxies) * 100
                    print(f"\r📈📈📈📈 进度: {self.total_tested}/{len(proxies)} "
                          f"[{percentage:.1f}%] | "
                          f"✅: {self.successful} | "
                          f"❌❌❌❌: {self.failed}", end="")
            
            return result
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(worker, proxy): proxy for proxy in proxies}
            for future in concurrent.futures.as_completed(futures):
                pass
        
        total_time = time.time() - start_time
        
        print()
        print(f"⏱⏱⏱⏱⏱⏱⏱⏱⏱ 总耗时: {total_time:.1f}秒")
        print(f"📊📊📊📊 平均速度: {len(proxies)/total_time:.1f}个/秒")
        
        return all_results, successful_results
    
    def display_results(self, all_results, successful_results, proxy_type):
        """显示测试结果"""
        print("\n" + "="*60)
        print("📊📊📊📊 测试结果汇总")
        print("="*60)
        
        total = len(all_results)
        success_rate = (self.successful / total * 100) if total > 0 else 0
        
        print(f"代理类型: {proxy_type}")
        print(f"总代理数: {total}")
        print(f"成功代理: {self.successful} ({success_rate:.1f}%)")
        print(f"失败代理: {total - self.successful}")
        
        if successful_results:
            site_stats = {}
            for result in successful_results:
                site_abbr = result.get('site_abbr', 'unk')
                site_stats[site_abbr] = site_stats.get(site_abbr, 0) + 1
            
            print(f"\n🌐🌐🌐🌐 成功网站分布:")
            for site_abbr, count in site_stats.items():
                print(f"  {site_abbr.upper()}成功: {count}个")
        
        if successful_results:
            latencies = [r['latency_ms'] for r in successful_results]
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            print(f"\n⏱⏱⏱⏱⏱⏱⏱⏱⏱ 延迟统计:")
            print(f"  平均延迟: {avg_latency:.0f}ms")
            print(f"  最快延迟: {min_latency:.0f}ms")
            print(f"  最慢延迟: {max_latency:.0f}ms")
            
            print(f"\n📈📈📈📈 延迟分布:")
            latency_ranges = [
                (0, 100, "极快 <100ms"),
                (100, 200, "快速 100-200ms"),
                (200, 500, "中等 200-500ms"),
                (500, 1000, "较慢 500ms-1s"),
                (1000, 3000, "慢 1-3s"),
                (3000, float('inf'), "很慢 >3s")
            ]
            
            for min_r, max_r, label in latency_ranges:
                count = sum(1 for r in successful_results if min_r <= r['latency_ms'] < max_r)
                if count > 0:
                    percentage = count / len(successful_results) * 100
                    bar_length = int(percentage / 5)
                    bar = "█" * bar_length
                    print(f"  {label:15s}: {count:3d}个 ({percentage:5.1f}%) {bar}")
        
        if successful_results:
            fastest = sorted(successful_results, key=lambda x: x['latency_ms'])[:5]
            
            print(f"\n🚀🚀🚀🚀 最快的5个代理:")
            for i, result in enumerate(fastest, 1):
                latency = result['latency_ms']
                site_abbr = result.get('site_abbr', 'unk')
                
                if latency < 100:
                    indicator = "🟢🟢🟢🟢🟢🟢🟢🟢🟢"
                elif latency < 200:
                    indicator = "🟡🟡🟡🟡🟡🟡🟡🟡🟡"
                elif latency < 500:
                    indicator = "🟠🟠🟠🟠🟠🟠🟡🟡🟡"
                elif latency < 1000:
                    indicator = "🔴🔴🔴🔴"
                else:
                    indicator = "⚫⚫⚫⚫"
                
                print(f"  {i}. {indicator} {result['proxy']:20s} | {latency:5.0f}ms | {site_abbr}")
        
        failed_results = [r for r in all_results if not r['success']]
        if failed_results:
            error_stats = {}
            for r in failed_results:
                error = r.get('error', '未知错误')
                error_key = error.split(':')[0] if ':' in error else error
                error_stats[error_key] = error_stats.get(error_key, 0) + 1
            
            print(f"\n❌❌❌❌ 失败原因分析 ({len(failed_results)} 个):")
            for error, count in sorted(error_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                percentage = count / len(failed_results) * 100
                print(f"  {error:30s}: {count:3d}个 ({percentage:5.1f}%)")
    
    def extract_proxy_info_from_txt(self, txt_file_path, proxy_type):
        """从txt文件中提取代理信息，去掉协议头"""
        proxies_list = []
        
        try:
            with open(txt_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 提取/#之前的所有内容
                        if '/#' in line:
                            full_proxy = line.split('/#')[0].strip()
                        else:
                            full_proxy = line
                        
                        # 使用合并的清理和验证功能
                        proxy = self.clean_and_validate_proxy(full_proxy)
                        if proxy:
                            proxies_list.append(proxy)
            
            print(f"✅ 从txt文件中提取了 {len(proxies_list)} 个{proxy_type}代理")
            return proxies_list
            
        except Exception as e:
            print(f"❌❌❌❌ 从txt文件提取代理信息失败: {e}")
            return []
    
    def save_results(self, all_results, successful_results, proxy_type):
        """保存测试结果到result文件夹"""
        if successful_results:
            successful_sorted = sorted(successful_results, key=lambda x: x['latency_ms'])
            
            # 1. 保存为txt格式（原有格式）
            result_txt_file = os.path.join(self.result_dir, f"{proxy_type.lower()}.txt")
            
            with open(result_txt_file, 'w', encoding='utf-8') as f:
                f.write(f"# {proxy_type}代理测试结果 - 有效代理列表\n")
                f.write(f"# 总测试数: {len(all_results)}\n")
                f.write(f"# 成功代理: {len(successful_results)}\n")
                f.write(f"# 成功率: {len(successful_results)/len(all_results)*100:.1f}%\n")
                f.write(f"# 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 格式: 协议://IP:端口/#延迟ms%20网站缩写\n")
                f.write("#"*60 + "\n\n")
                
                for i, result in enumerate(successful_sorted, 1):
                    proxy = result['proxy']
                    latency = result['latency_ms']
                    site_abbr = result.get('site_abbr', 'unk')
                    
                    if latency.is_integer():
                        latency_str = f"{int(latency)}ms"
                    else:
                        latency_str = f"{latency:.1f}ms"
                    
                    proxy_url = self.get_proxy_url(proxy, proxy_type)
                    f.write(f"{proxy_url}/#{latency_str}%20{site_abbr}\n")
            
            print(f"💾💾💾💾 TXT结果已保存: {result_txt_file}")
            
            # 2. 从txt文件中提取代理信息并保存为JSON格式
            json_proxies = self.extract_proxy_info_from_txt(result_txt_file, proxy_type)
            
            if json_proxies:
                result_json_file = os.path.join(self.result_dir, f"{proxy_type.lower()}.json")
                json_data = {"ts": json_proxies}
                
                with open(result_json_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                
                print(f"💾💾💾💾 JSON结果已保存: {result_json_file}")
                print(f"📋📋📋📋 JSON格式: {{'ts': [代理列表]}}")
            
            return result_txt_file
        else:
            print(f"❌❌❌❌ 没有有效的{proxy_type}代理，未保存结果")
            return None
    
    def test_proxy_type(self, proxy_type, max_workers=20, limit=0):
        """测试特定类型的代理"""
        if proxy_type not in self.proxy_files:
            print(f"❌❌❌❌ 无效的代理类型: {proxy_type}")
            return
        
        info = self.proxy_files[proxy_type]
        file_path = os.path.join(self.base_dir, info['file'])
        
        if not os.path.exists(file_path):
            print(f"❌❌❌❌ 代理文件不存在: {file_path}")
            return
        
        print(f"\n" + "="*60)
        print(f"🎯🎯🎯🎯 开始测试 {info['name']} 代理")
        print(f"📁📁📁📁 代理文件: {file_path}")
        print("="*60)
        
        # 重置计数器
        self.total_tested = 0
        self.successful = 0
        self.failed = 0
        
        # 加载代理
        proxies = self.load_proxies(file_path, limit)
        
        if not proxies:
            print("❌❌❌❌ 没有找到有效的代理，跳过测试")
            return
        
        # 测试代理
        all_results, successful_results = self.batch_test_proxies(
            proxies=proxies,
            proxy_type=info['name'],
            max_workers=max_workers
        )
        
        # 显示结果
        self.display_results(all_results, successful_results, info['name'])
        
        # 保存结果
        saved_file = self.save_results(all_results, successful_results, info['name'])
        
        if successful_results:
            fastest = min(successful_results, key=lambda x: x['latency_ms'])
            
            print(f"\n🎯🎯🎯🎯 使用示例:")
            proxy_url = self.get_proxy_url(fastest['proxy'], info['name'])
            print(f"  # 在终端中使用:")
            print(f"  curl -x {proxy_url} {fastest.get('test_url', 'https://example.com')}")
            
            print(f"\n  # 在Python中使用:")
            print(f"  import requests")
            print(f"  proxies = {{'http': '{proxy_url}', 'https': '{proxy_url}'}}")
            print(f"  response = requests.get('{fastest.get('test_url', 'https://example.com')}', proxies=proxies)")
        
        print(f"\n{'='*60}")
        print(f"✅ {info['name']}代理测试完成!")
        print(f"📅📅📅📅 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        return len(successful_results)
    
    def auto_run(self):
        """自动运行完整的测试流程"""
        print("🚀🚀🚀🚀 开始GitHub自动代理测试")
        print(f"📁📁📁📁 工作目录: {self.base_dir}")
        print(f"💾💾💾💾 结果目录: {self.result_dir}")
        print("="*60)
        
        start_time = time.time()
        
        # 1. 下载代理
        print("\n📥📥📥📥 步骤1: 下载代理")
        downloaded_count = self.download_and_classify_proxies()
        
        # 2. 导入上次成功的代理
        print("\n📥📥📥📥 步骤2: 导入上次成功的代理")
        self.import_previous_successful_proxies()
        
        # 3. 依次测试各种类型的代理
        print("\n🧪🧪🧪🧪 步骤3: 开始测试代理")
        
        test_results = {}
        proxy_types = ['http', 'https', 'socks4', 'socks5']
        
        for proxy_type in proxy_types:
            if proxy_type in self.proxy_files:
                info = self.proxy_files[proxy_type]
                file_path = os.path.join(self.base_dir, info['file'])
                
                if os.path.exists(file_path):
                    print(f"\n" + "="*60)
                    print(f"🧪🧪🧪🧪 测试 {info['name']} 代理")
                    print("="*60)
                    
                    successful_count = self.test_proxy_type(proxy_type, max_workers=20, limit=0)
                    test_results[proxy_type] = successful_count
                    
                    # 短暂暂停，避免请求过于密集
                    time.sleep(2)
                else:
                    print(f"❌❌❌❌ 跳过{info['name']}代理测试，文件不存在: {file_path}")
                    test_results[proxy_type] = 0
            else:
                print(f"❌❌❌❌ 未知代理类型: {proxy_type}")
                test_results[proxy_type] = 0
        
        # 4. 生成测试报告
        print("\n" + "="*60)
        print("📊📊📊📊 测试报告")
        print("="*60)
        
        total_successful = sum(test_results.values())
        print(f"📈📈📈📈 总成功代理数: {total_successful}")
        
        for proxy_type, count in test_results.items():
            if proxy_type in self.proxy_files:
                info = self.proxy_files[proxy_type]
                print(f"  {info['name']}: {count} 个")
        
        total_time = time.time() - start_time
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)
        
        print(f"\n⏱⏱⏱⏱⏱⏱⏱⏱⏱ 总耗时: {minutes}分{seconds}秒")
        print(f"💾💾💾💾 结果文件保存在: {self.result_dir}")
        
        print("\n✅ GitHub自动代理测试完成!")

def main():
    """主函数"""
    tester = GitHubProxyTester()
    
    try:
        # 自动运行完整流程
        tester.auto_run()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断程序")
    except Exception as e:
        print(f"\n❌❌❌❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
