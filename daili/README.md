# 代理测试仓库

自动测试和验证HTTP、HTTPS、SOCKS4、SOCKS5代理

## 最新测试结果

**最后更新:** 2026-01-22 16:26:20

| 代理类型 | 成功数量 | 测试时间 |
|---------|---------|---------|
| HTTP | 10 | 16:26:20 |
| HTTPS | 1 | 16:26:20 |
| SOCKS4 | 98 | 16:26:20 |
| SOCKS5 | 8 | 16:26:20 |
| **总计** | **117** | **2分37秒** |

## 文件说明

- `proxy_tester.py` - 主测试脚本
- `source.txt` - 代理源配置
- `ym.txt` - 测试网站列表
- `http.txt` - HTTP代理列表
- `https.txt` - HTTPS代理列表
- `sock4.txt` - SOCKS4代理列表
- `sock5.txt` - SOCKS5代理列表
- `result/` - 测试结果目录

## 使用方法

### 自动运行
```bash
python proxy_tester.py
```

### 手动运行
```python
from proxy_tester import GitHubProxyTester
tester = GitHubProxyTester()
tester.auto_run()  # 自动运行完整流程
```

## 配置说明

### source.txt 格式
```json
[
  {"http": ["http://example.com/proxy.txt", "http://example2.com/proxy.txt"]},
  {"https": ["https://example.com/https.txt"]},
  {"socks4": ["http://example.com/socks4.txt"]},
  {"socks5": ["http://example.com/socks5.txt"]}
]
```

### ym.txt 格式
```
# 每行一个测试网站
https://www.google.com
https://www.bing.com
https://telegram.org
```

## 许可证
MIT License
