# SoundSticks 5 协议逆向研究

Harman Kardon SoundSticks 5 的非官方 BLE/GATT 控制协议研究与验证工具。

本项目与 Harman Kardon、HARMAN International 或其关联公司没有隶属、授权、赞助或
背书关系。产品名和商标归各自权利人所有。

## 范围

仓库只包含：

- 已分级的逆向事实和仍待验证的问题；
- BLE/GATT 布局与 `AA/CMD/LEN/DATA`、TLV 帧格式；
- 官方 App 控件、滑条、灯效默认值、颜色重置和 EQ 数据的协议对照；
- 安全的只读状态查询与服务发现工具；
- btsnoop/HCI/ATT 离线解析工具；
- 去标识化的实验摘要和协议样本。

不包含官方 App、APK、固件、官方素材、Home Assistant 集成、ESP32 产品实现或大量原始
抓包。危险或破坏性操作（OTA、恢复出厂、解绑等）也不作为公开工具提供。

## 当前适用范围

研究主要基于一台普通版（非 Wi-Fi 版）SoundSticks 5 和当时的测试固件。不同地区、SKU、
Wi-Fi 版本和未来固件可能不同。任何结论都应结合 [FACTS.md](FACTS.md) 的证据等级阅读。

控制协议使用 BLE GATT；音频使用经典蓝牙 A2DP/AVRCP。因此设备不是 “BLE-only”。

## 快速开始

需要 Python 3.10 或更新版本。

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

全量扫描广告（不要只依赖设备名）：

```bash
python tools/ss5_ble.py scan --timeout 15
```

对刚刚扫描到的地址枚举 GATT（只读，不发送应用命令）：

```bash
python tools/ss5_ble.py discover --address <CURRENT_ADDRESS>
```

确认控制 Service UUID 后，订阅通知并发送只读综合状态查询 `aa 41 00`：

```bash
python tools/ss5_ble.py query --address <CURRENT_ADDRESS> --kind aggregate
```

SoundSticks 5 使用会轮换的 BLE 随机私有地址（RPA）。不要硬编码 MAC/RPA，也不要把
历史地址当作设备身份。设备名可能缺失；GATT 控制 Service UUID 是更可靠的最终识别依据：

```text
65786365-6c70-6f69-6e74-2e636f6d0000
```

离线解析帧或抓包：

```bash
python tools/frame_decode.py "aa 42 11 00 41 01 01 42 01 1c 43 01 00 44 00 45 00 36 01 01"
python tools/att_extract.py capture.btsnoop --aa-only
python tools/gatt_discovery.py capture.btsnoop
```

离线生成与 App 操作等价的十六进制帧（只打印，不连接或发送）：

```bash
python tools/app_actions.py brightness 50
python tools/app_actions.py color ocean 50
python tools/app_actions.py playback pause
python tools/app_actions.py feedback-tone on
python tools/app_actions.py auto-off 10m
python tools/app_actions.py reset-color ocean
python tools/app_actions.py reset-eq
```

亮度和颜色直接使用整数 `0..100`，第三方 UI 的 50% 应发送 50。App 的触摸像素取整不应
复制成协议行为。EQ 任意增益的 App 标尺仍未完整标定；详情见 App 属性文档。

## 文档导航

- [FACTS.md](FACTS.md)：最高优先级事实基线
- [docs/protocol.md](docs/protocol.md)：协议结构和已确认命令
- [docs/app-reference.md](docs/app-reference.md)：App 属性、主题、默认值和 EQ 参考
- [docs/audio-volume.md](docs/audio-volume.md)：AVRCP 音量标尺与无声步进实验
- [docs/capture-and-analysis.md](docs/capture-and-analysis.md)：可复现抓取与分析方法
- [docs/safety.md](docs/safety.md)：安全边界
- [docs/research-questions.md](docs/research-questions.md)：待复核问题与建议实验
- [results/experiment-summary.md](results/experiment-summary.md)：去标识化实验摘要
- [results/reference-values.json](results/reference-values.json)：机器可读参考值
- [tools/README.md](tools/README.md)：工具说明

## 贡献规则

新增结论应同时给出设备/SKU、固件上下文、操作步骤、期望与实际结果，并按
`CONFIRMED / OBSERVED / INFERRED / UNKNOWN / SUPERSEDED` 分类。原始抓包应先去标识化，
默认不要提交大型二进制。发现冲突时降低结论强度，不要用新猜测覆盖旧证据。

## 许可证

- 代码、脚本和工具：Apache License 2.0，见 [LICENSE-CODE](LICENSE-CODE)
- 文档和研究文字：Creative Commons Attribution 4.0 International，见
  [LICENSE-DOCS](LICENSE-DOCS)
