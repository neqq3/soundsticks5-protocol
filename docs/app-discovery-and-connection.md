# HK One App 的发现、在线与控制连接

本页记录 HK One 2.5.4 在当前普通版 SoundSticks 5 上的实现边界。它来自 APK 静态分析、
3399 Android 动态状态和 BlueZ 对照，不代表其他 App/固件版本必然相同。

## 证据分级摘要

本页沿用 [FACTS.md](../FACTS.md) 的分级，尤其区分“代码中存在该策略”和“该策略已经被
运行态证明是稳定性的原因”：

| 等级 | 本页结论 |
|---|---|
| **CONFIRMED** | 已有独立 GATT 抓包确认 SoundSticks 5 使用会轮换的 RPA，旧地址不能作为长期连接目标；完整控制必须以协议 ACK 或状态回读验证。 |
| **OBSERVED** | HK One 2.5.4 的 APK 实现包含循环扫描、逻辑身份与当前地址分离、有效会话复用、串行命令队列和通知状态缓存；3399 运行态观察到持续扫描注册。 |
| **INFERRED** | 这些策略共同减少无意义的重连和查询，因此很可能是 App 控制较平稳的重要因素；当前没有逐项关闭策略的 App A/B 实验，不能把因果关系写成已确认。 |
| **UNKNOWN** | 当前用户手机在 MA/A2DP 播放期间实际走过的 secure-connect 分支、连接保持时长和最终释放触发条件仍未抓包确认。 |
| **SUPERSEDED** | “RPA 一变化就必须拆掉仍有效的 GATT”“离开产品页必然断开 GATT”“每次写操作后必须全量查询全部属性”均不能作为 App 行为描述或第三方实现要求。 |

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

## OBSERVED：App 2.5.4 的广告识别

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

## OBSERVED：扫描、逻辑身份与 RPA 更新

App 不是扫描一次后永久记住一个 BLE 地址。静态实现和 3399 的 Android 蓝牙统计均显示，
`BLEScanner` 使用 `BALANCED` 模式循环扫描：扫描窗口依次为 5 秒、10 秒、15 秒，停止约
2 秒后进入下一轮；另有每 30 秒一次的设备过期检查。已连接或正在配对的设备不会按普通
广告超时移除。

`OneBLEAdvParser` 会同时保存当前 Android 扫描地址和广告中的 `macAddressCRC`。
`OneBTDevice.getUUID()` 返回小写的 `macAddressCRC`，而 `bleAddress` 只代表当前可连接
地址。因此设备存储以产品广告提供的稳定线索合并同一逻辑设备，而不是把 RPA 当身份。
这套 CRC 是 App 内部模型字段，不是第三方客户端应硬编码的公开标识。

取得设备级 GATT 会话时，App 的处理规则是：

- 既有会话处于连接中或已连接：继续复用，即使刚扫描到另一个地址；
- 既有会话空闲、地址相同：复用会话对象；
- 既有会话空闲、地址改变：断开并销毁旧会话，再用新地址创建会话。

这避免了“有效链路尚在，却被后来一条不同地址的广告主动拆掉”的竞争。

## OBSERVED：GATT 与安全连接完成条件

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

基础连接使用 Android `connectGatt(context, false, callback, TRANSPORT_LE)`。处于
`CONNECTING` 或 `CONNECTED` 时再次请求连接会直接返回，不会创建第二个自身会话。连接
成功后约等待 500 ms 再发现 Service；通知准备后再约等待 500 ms 请求 MTU。通用同步
连接帮助函数默认最多尝试 2 次，每次超时 15 秒，但后台异步空闲连接并不在已连接或连接
中时重复建链。

## OBSERVED：会话所有权与命令调度

GATT 会话保存在逻辑设备对象中，而不是产品控制页面中。当前分析到的控制页 Activity 和
ViewModel 在 `onPause`/`onDestroy` 中注销扫描观察者、页面监听器和 UI 资源，没有在这些
生命周期方法里主动断开设备 GATT。异常或明确要求释放时，基础会话才执行
`disconnect()` 和 `close()`。当前调用关系里，产品列表的全量蓝牙会话清理由系统蓝牙
状态变化处理入口调用，并在蓝牙关闭时执行；进程终止和链路异常仍会由系统或基础会话
释放。

产品列表还实现了一个最多容纳两个逻辑设备的 BLE 自动连接队列；第三个设备进入时会移出
并断开最旧项。该上限是 App 自身的资源政策，不能外推为音箱固件的并发能力。

普通和安全命令各自通过单线程执行器写入；允许合并的同命令 ID 会取消尚在队列中的旧任务，
分片写入等待 Android characteristic-write 回调后再继续。查询结果和状态通知写入
`OneBTDevice` 的缓存字段。因此 App 不需要在每个设置命令之后立即重新查询灯光、音量、
EQ、反馈音和自动关闭等全部状态。

产品列表的空闲自动 GATT 连接还带有门控：只有设备不在 Wi-Fi 在线路径、App 的 BT
身份/连接判定与 BR/EDR 会话均满足、GATT 尚未连接/连接中且当前不是安全会话时，才尝试
建立非安全 GATT。这为“手机不承载当前媒体但仍保持经典蓝牙端点连接时可建立 BLE 控制”
提供了一种与实现相容的解释；是否确为用户当前手机的实时状态，仍需手机侧 HCI/系统状态
确认，控制页也可能存在其他显式连接入口。

## INFERRED：对第三方常驻控制器的含义

HK One 表现出的稳定性与会话复用、RPA 更新、写入串行和通知缓存相容；静态分析没有发现
一个可以绕过多 central 竞争的特殊连接命令。尚未逐项对 App 做 A/B 实验，因此这些机制
对稳定性的贡献比例仍是推断。第三方常驻控制器若固定周期断开重连、在一次刷新中连续查询
所有属性、失败后立即成组重试，会制造 App 静态实现主动避免的竞争和控制器压力。

但 Home Assistant 也不应机械复制手机 App 的永久占用策略：现有对照中第二 central 的
CCCD/完整控制存在顺序相关冲突。更合适的默认策略是按需连接、同一批操作内复用、短暂
空闲后释放、依靠匹配通知更新状态，并把“长期保持 BLE”作为用户明确选择；同时在有效
连接期间忽略后来广告造成的地址变化，断开后才采用最新扫描地址重连。

## CONFIRMED/OBSERVED：睡眠对照

在自动关闭剩余时间已经为 0 时：

- BlueZ 只观察到 Fast Pair service data `0000`，没有 App 产品解析所需的 PID/厂商字段；
- BlueZ 仍可建立私有 GATT 并读取自动关闭状态；
- 把自动关闭从 30 秒重新设置为 600 秒后，剩余时间立刻从 0 变为非零并递减；
- HK One 仍显示离线，Android 蓝牙连接历史没有出现新的 GATT 连接。

这说明自动关闭倒计时是否运行，不是 HK One 判定连接成功的条件，也不能单独作为物理灯、
音频电源域或整机唤醒的代理指标。

## UNKNOWN：仍待验证

- 清醒、待机和更长时间休眠时的完整 `adv_format_4` 广告字段变化；
- secure-connect 中 SoundSticks 5 实际走过的认证分支和每一步协议消息；
- App 首页“在线”后到产品控制页可操作之间是否还存在设备专用健康查询；
- 手机在 MA/Sendspin 承载 A2DP 时是否仍保留自己的 BR/EDR 链路，以及这是否触发了 App
  的空闲自动 GATT 连接；
- App 被系统退到后台更长时间后由哪个生命周期或系统事件最终释放 GATT；
- 不同地区、SKU、App 和固件版本是否使用其他 company ID、service-data UUID 或 PID。
