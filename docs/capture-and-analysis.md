# 抓取与分析方法

## 推荐实验原则

1. 一次只改变一个变量：App 连接、A2DP、AUX、灯光操作等不要同时改变。
2. 先记录静置基线，再执行单一动作。
3. 保存设备/SKU、固件、操作系统、蓝牙后端、时间线和预期结果。
4. 地址先去标识化；RPA 不是稳定身份，也没有必要公开。
5. 结论至少区分 CONFIRMED、OBSERVED 和 INFERRED。

## Android btsnoop

不同 Android 厂商的开启方式和文件位置不同。标准 Android HCI snoop 文件通常以
`btsnoop\0` 开头，但不要假设固定设备路径，也不要把本机 ADB 路径或设备序列号写进脚本。

建议工作流：

1. 在设备开发者选项中启用 Bluetooth HCI snoop log；
2. 重启蓝牙或按系统要求重启设备；
3. 记录抓包文件当前大小/时间；
4. 执行单一 UI 操作；
5. 导出抓包的副本；
6. 在提交前去除与研究无关的邻近设备流量和个人标识。

本仓库不会自动操作官方 App，也不附带 APK。

## 离线 ATT 提取

```bash
python tools/att_extract.py capture.btsnoop
python tools/att_extract.py capture.btsnoop --aa-only
python tools/att_extract.py capture.btsnoop --stats
python tools/gatt_discovery.py capture.btsnoop
```

方向来自 btsnoop record flags：`tx` 表示主机到控制器，`rx` 表示控制器到主机。ATT
通知中的 value 是否来自音箱，还应结合连接角色确认，不能只看箭头名称。

## AA 帧分析

```bash
python tools/frame_decode.py "aa 31 00"
python tools/frame_decode.py "aa 42 11 00 41 01 01 42 01 1c 43 01 00 44 00 45 00 36 01 01"
```

解析规则：

- 首先验证 magic、LEN 和截断；
- 只有已知 TLV 上下文才从 DATA 偏移 1 解析；
- 重复 tag 必须保留为列表；
- 未知 tag 输出 hex，不猜语义；
- 对 `0xad` 等嵌套/日志帧不要强制套普通 TLV 模型。

## 可复现实验记录模板

```markdown
### 标题

- 设备/SKU：
- 固件（如可读）：
- 主机与蓝牙后端：
- 初始状态：
- 唯一操作：
- 原始请求/通知：
- 重复次数：
- 对照组：
- 结果：
- 证据等级：CONFIRMED / OBSERVED / INFERRED
- 仍无法排除：
```

