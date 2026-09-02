# 安全边界

逆向工具会连接真实硬件。即使是 GATT “write without response”，也可能触发持久设置或
设备状态变化。

## 初始版本允许的在线操作

- 全量 BLE 广告扫描；
- GATT service/characteristic discovery；
- 订阅已知通知 characteristic；
- 三个已观察为只读的查询：`aa 31 00`、`aa 41 00`、`aa e1 00`。

## 不在默认工具中提供

- OTA 或固件传输；
- 恢复出厂、解绑、产品匹配自动化；
- 未知 command 的模糊测试；
- 未设范围的任意 characteristic/handle 写入；
- 自动扫描并连接所有附近未知设备；
- ADB 自动操作官方 App。

## 使用前检查

- 确认地址来自刚刚完成的扫描；RPA 会轮换。
- 先枚举并确认控制 Service UUID，不根据名称或 MAC 猜设备身份。
- 不在医疗、安全告警或关键音频场景中测试。
- 保存当前灯光/EQ 状态；设置可能在客户端断开后保留。
- 遇到 0 services、`not found` 或超时时先重新扫描，不连续高频重连。

如果未来添加写入工具，应使用明确的子命令、参数范围验证、交互确认和 `--dry-run`，并将
高风险命令与普通设置分离。

