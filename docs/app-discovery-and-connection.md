# HK One App 的发现、在线与控制连接

本页记录 HK One 2.5.4 在当前普通版 SoundSticks 5 上的实现边界。它来自 APK 静态分析、
3399 Android 动态状态和 BlueZ 对照，不代表其他 App/固件版本必然相同。

## 三个不要混为一谈的状态

1. **广告被 App 识别**：扫描结果必须能解析出受支持的产品 PID，App 才会创建或更新
   `OneDevice`。
2. **首页显示在线**：当前数据模型中，`BLEOnline` 的基础条件是 `OneDevice` 持有一个
   当前解析出的 BLE 设备对象。缓存中有产品卡片并不等于在线。
3. **控制连接就绪**：需要 GATT 连接流程到达 `CONNECTED`；对需要认证的产品，还要完成
   App 的 secure-connect 状态机。

因此，下列组合是可能且已经观察到的：

- 音箱以匿名 RPA 广播 Fast Pair `FE2C:0000`；
- 通用 BLE 客户端可以枚举私有控制 Service、订阅和查询；
- HK One 首页仍把缓存的 SoundSticks 5 显示为“离线”。

“裸 GATT 可达”不能代替“App 在线”，App 离线也不能反推控制 Service 已停止。

## App 2.5.4 的广告识别

`BLEScanner.parseScanResult` 先调用 `parsePid`，再根据 PID 选择广告解析器。当前实现检查：

- manufacturer-specific data company ID `0x0057`、`0x0ECB`；
- service data UUID `0xFDDF`、`0xDFFD`；
- 提取出的 PID 是否存在于 App 的受支持产品配置中。

当前 3399 缓存的产品配置把普通版 SoundSticks 5 描述为：

| 字段 | 值 |
|---|---:|
| PID | `2131` |
| category | `home_bt` |
| advertisement format | `adv_format_4` |
| command format | `cmd_format_3` |
| authentication button | `plus` |

这些是 App 的产品路由元数据，不是私有控制协议帧，也不是稳定公开 API。第三方客户端仍
应动态扫描地址，并在连接后以私有 GATT Service UUID 识别控制通道；不要硬编码 MAC/RPA
或只依赖产品名。

## GATT 与安全连接完成条件

`BaseGattSession` 的基础流程为：

1. 建立 Android GATT link；
2. 发现 services；
3. 找到匹配的 Rx/Tx Service 与 characteristics；
4. 尝试启用通知；
5. 请求 MTU 500；
6. MTU 回调成功后将会话推进到 `CONNECTED`。

静态实现中，通知启用失败会记录警告，但在这一基础层没有立即中止整个连接流程。产品层
随后调用 `secureBleGattConnect`；它会检查既有 `isGattConnected`/`isSecureConnect`，并
处理 `PRE_PAIR`、`PAIRING`、`CONNECTED`、断开和认证回调。当前设备缓存标记为
`need_auth=1`、`encrypted=1`，因此“Android 链路已连上”仍不等于 App 的安全控制已就绪。

## 睡眠对照

在自动关闭剩余时间已经为 0 时：

- BlueZ 只观察到 Fast Pair service data `0000`，没有 App 产品解析所需的 PID/厂商字段；
- BlueZ 仍可建立私有 GATT 并读取自动关闭状态；
- 把自动关闭从 30 秒重新设置为 600 秒后，剩余时间立刻从 0 变为非零并递减；
- HK One 仍显示离线，Android 蓝牙连接历史没有出现新的 GATT 连接。

这说明自动关闭倒计时是否运行，不是 HK One 判定连接成功的条件，也不能单独作为物理灯、
音频电源域或整机唤醒的代理指标。

## 仍待验证

- 清醒、待机和更长时间休眠时的完整 `adv_format_4` 广告字段变化；
- secure-connect 中 SoundSticks 5 实际走过的认证分支和每一步协议消息；
- App 首页“在线”后到产品控制页可操作之间是否还存在设备专用健康查询；
- 不同地区、SKU、App 和固件版本是否使用其他 company ID、service-data UUID 或 PID。
