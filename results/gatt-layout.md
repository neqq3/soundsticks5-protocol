# GATT 枚举结果（去标识化）

以下布局由仓库中的 `gatt_discovery.py` 对一次成功连接的 btsnoop 抓包重新解析得到。地址、
设备序列号和主机信息未保留。handle 仅代表该次枚举。

## Services

| Handle range | UUID |
|---|---|
| `0x0001–0x000a` | Generic Attribute `0x1801` |
| `0x000b–0x0013` | Generic Access `0x1800` |
| `0x0021–0x0026` | Broadcast Audio Scan Service `0x184f` |
| `0x0062–0x0065` | `e49a1800-f69a-11e8-8eb2-f2801f1b9fd1` |
| `0x00ce–0x00de` | Fast Pair `0xfe2c` |
| `0x03e8–0x03ed` | SoundSticks private control service |

## Private control service

| Declaration | Value | Properties | UUID |
|---:|---:|---|---|
| `0x03e9` | `0x03ea` | `0x0c` (write + write without response) | `...0002` command |
| `0x03eb` | `0x03ec` | `0x12` (read + notify) | `...0001` notification |
| — | `0x03ed` | CCCD | `0x2902` |

完整 UUID：

```text
65786365-6c70-6f69-6e74-2e636f6d0000  service
65786365-6c70-6f69-6e74-2e636f6d0001  notification
65786365-6c70-6f69-6e74-2e636f6d0002  command
```

## Fast Pair characteristics observed

```text
fe2c1234-8366-4814-8eb0-01de32100bea
fe2c1235-8366-4814-8eb0-01de32100bea
fe2c1236-8366-4814-8eb0-01de32100bea
fe2c1237-8366-4814-8eb0-01de32100bea
fe2c1239-8366-4814-8eb0-01de32100bea
fe2c123a-8366-4814-8eb0-01de32100bea
```

这些 UUID 证明相应服务/characteristic 出现在当前设备枚举中，不证明内部 SoC 型号，也
不证明所有标准功能均已完整实现。

