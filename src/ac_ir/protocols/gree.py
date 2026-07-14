"""
格力 (Gree) 空调红外协议实现

协议分析 (基于 IRremoteESP8266 / Flipper Zero / 开源社区逆向):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
载波频率:   38 kHz
编码方式:   脉冲距离编码 (Pulse Distance)
数据长度:   8 字节 (State[0..7])，LSB first

时序:
    Header Mark   = 9000 µs
    Header Space  = 4500 µs
    Bit Mark      = 620 µs
    Zero Space    = 540 µs
    One Space     = 1680 µs
    Footer Mark   = 620 µs
    Gap Space     = 20000 µs

数据结构 (8 bytes):
    State[0] = [Mode(3)] [Power(1)] [Fan(2)] [SwingAuto(1)] [Sleep(1)]
    State[1] = [Temp - 16 (4)] [Timer(H) (4)]
    State[2] = [Timer(L) (8)]
    State[3] = 0x50 (固定 / 部分机型为0x20)
    State[4] = 0x20 (固定)
    State[5] = [XFan(1)] [Light(1)] [Turbo(1)] [Ionizer(1)] [0(4)]
    State[6] = [????]
    State[7] = Checksum = (State[0..6] 之和) & 0xFF

注记:
    - 比特顺序: LSB first (每个字节内先发低位)
    - 温度编码: 16°C = 0b0000, 30°C = 0b1110
    - 定时: 以半小时为单位 (值 N = N×30 分钟)
    - 格力不同子品牌/年代有细微差异，本实现覆盖最通用版本
"""

from typing import List, Tuple

from .base import (
    BaseProtocol, ACState, ACMode, FanSpeed, Brand
)


class GreeProtocol(BaseProtocol):
    """格力空调红外协议"""

    CARRIER_FREQUENCY = 38000

    # ── 时序参数 (µs) ──
    HEADER_MARK  = 9000
    HEADER_SPACE = 4500
    BIT_MARK     = 620
    ZERO_SPACE   = 540
    ONE_SPACE    = 1680
    FOOTER_MARK  = 620
    GAP_SPACE    = 20000

    STATE_SIZE = 8

    # ── 模式映射 ──
    MODE_MAP = {
        ACMode.AUTO: 0b000,
        ACMode.COOL: 0b001,
        ACMode.DRY:  0b010,
        ACMode.FAN:  0b011,
        ACMode.HEAT: 0b100,
    }

    MODE_REVERSE = {v: k for k, v in MODE_MAP.items()}

    # ── 风速映射 ──
    FAN_MAP = {
        FanSpeed.AUTO:   0b00,
        FanSpeed.LOW:    0b01,
        FanSpeed.MEDIUM: 0b10,
        FanSpeed.HIGH:   0b11,
    }

    FAN_REVERSE = {v: k for k, v in FAN_MAP.items()}

    @property
    def brand(self) -> Brand:
        return Brand.GREE

    # ═══════════════════════════════════════════════════════════════
    # 编码: ACState → IR 原始字节
    # ═══════════════════════════════════════════════════════════════

    def state_to_raw(self, state: ACState) -> List[int]:
        """
        将通用 ACState 编码为格力 8 字节红外数据。

        Byte 0: [Mode(3)] [Power(1)] [Fan(2)] [SwingAuto(1)] [Sleep(1)]
        Byte 1: [Temperature(4)] [Timer半小时(H)(4)]
        Byte 2: [Timer半小时(L)(8)]
        Byte 3-4: 固定值
        Byte 5: [XFan(1)][Light(1)][Turbo(1)][Ionizer(1)][0(4)]
        Byte 6: 保留
        Byte 7: Checksum
        """
        raw = [0] * 8

        # ── Byte 0: Mode + Power + Fan + Swing + Sleep ──
        mode_bits = self.MODE_MAP[state.mode] & 0b111          # bits 0-2
        power_bit = (1 if state.power else 0) << 3             # bit 3
        fan_bits = (self.FAN_MAP[state.fan_speed] & 0b11) << 4 # bits 4-5
        swing_bit = (1 if state.swing_vertical else 0) << 6    # bit 6
        sleep_bit = (1 if state.sleep else 0) << 7             # bit 7
        raw[0] = mode_bits | power_bit | fan_bits | swing_bit | sleep_bit

        # ── Byte 1: Temperature (bits 0-3) + Timer高4位 (bits 4-7) ──
        temp_val = state.temperature - 16
        # 格力可用定时 = timer_off（以关机定时为主）
        timer_half_hours = state.timer_off // 30  # 0x00 表示无定时
        if timer_half_hours > 0xFF:
            timer_half_hours = 0xFF
        raw[1] = (temp_val & 0x0F) | ((timer_half_hours & 0xF0))  # 高4位在 bits 4-7

        # ── Byte 2: Timer低8位 ──
        raw[2] = timer_half_hours & 0xFF

        # ── Byte 3-4: 固定值 ──
        raw[3] = 0x50   # 默认值 (某些机型为 0x20 或 0x00)
        raw[4] = 0x20   # 默认值

        # ── Byte 5: XFan + Light + Turbo + Ionizer ──
        xfan_bit     = (1 if state.xfan   else 0) << 0  # bit 0
        light_bit    = (1 if state.light  else 0) << 1  # bit 1
        turbo_bit    = (1 if state.turbo  else 0) << 2  # bit 2
        ionizer_bit  = (1 if state.ionizer else 0) << 3  # bit 3
        raw[5] = xfan_bit | light_bit | turbo_bit | ionizer_bit

        # ── Byte 6: 保留 ──
        raw[6] = 0x00

        # ── Byte 7: Checksum ──
        raw[7] = self._calc_checksum(raw[0:7])

        return raw

    # ═══════════════════════════════════════════════════════════════
    # 解码: IR 原始字节 → ACState
    # ═══════════════════════════════════════════════════════════════

    def raw_to_state(self, raw: List[int]) -> ACState:
        """从格力8字节红外数据解析为 ACState"""
        if len(raw) < 8:
            raise ValueError(f"格力协议数据至少8字节，收到: {len(raw)}")

        # Byte 0
        mode_val    = raw[0] & 0b00000111          # bits 0-2
        power_val   = (raw[0] >> 3) & 0b1           # bit 3
        fan_val     = (raw[0] >> 4) & 0b11          # bits 4-5
        swing_val   = (raw[0] >> 6) & 0b1           # bit 6
        sleep_val   = (raw[0] >> 7) & 0b1           # bit 7

        # Byte 1
        temp_val    = raw[1] & 0x0F                  # bits 0-3
        timer_high  = (raw[1] >> 4) & 0x0F           # bits 4-7

        # Byte 2
        timer_low   = raw[2] & 0xFF

        # Byte 5
        xfan_val    = raw[5] & 0b00000001           # bit 0
        light_val   = (raw[5] >> 1) & 0b1           # bit 1
        turbo_val   = (raw[5] >> 2) & 0b1           # bit 2
        ionizer_val = (raw[5] >> 3) & 0b1           # bit 3

        # 定时 = (timer_high << 8 | timer_low) × 30 分钟
        timer_half = (timer_high << 8) | timer_low
        timer_off = timer_half * 30 if timer_half > 0 else 0

        return ACState(
            power=bool(power_val),
            mode=self.MODE_REVERSE.get(mode_val, ACMode.AUTO),
            temperature=temp_val + 16,
            fan_speed=self.FAN_REVERSE.get(fan_val, FanSpeed.AUTO),
            swing_vertical=bool(swing_val),
            sleep=bool(sleep_val),
            xfan=bool(xfan_val),
            light=bool(light_val),
            turbo=bool(turbo_val),
            ionizer=bool(ionizer_val),
            timer_off=timer_off,
        )

    # ═══════════════════════════════════════════════════════════════
    # 调试 & 可视化
    # ═══════════════════════════════════════════════════════════════

    def format_raw(self, raw: List[int]) -> str:
        """格式化打印原始数据"""
        hex_str = " ".join(f"{b:02X}" for b in raw)
        bin_str = " ".join(f"{b:08b}" for b in raw)
        return (
            f"Gree RAW ({len(raw)} bytes)\n"
            f"  HEX: {hex_str}\n"
            f"  BIN: {bin_str}\n"
            f"  Checksum: {'OK' if raw[7] == self._calc_checksum(raw[:7]) else 'BAD'}"
        )

    def state_summary(self, state: ACState) -> str:
        """格式化打印状态摘要"""
        power_icon = "🟢 开" if state.power else "🔴 关"
        return (
            f"格力空调状态\n"
            f"  {power_icon}\n"
            f"  模式: {state.mode.name}\n"
            f"  温度: {state.temperature}°C\n"
            f"  风速: {state.fan_speed.name}\n"
            f"  扫风: {'✅' if state.swing_vertical else '❌'}\n"
            f"  睡眠: {'✅' if state.sleep else '❌'}\n"
            f"  干燥: {'✅' if state.xfan else '❌'}\n"
            f"  灯光: {'✅' if state.light else '❌'}\n"
            f"  强劲: {'✅' if state.turbo else '❌'}\n"
            f"  负离子: {'✅' if state.ionizer else '❌'}\n"
            f"  定时关: {state.timer_off}分钟" if state.timer_off else f"  无定时"
        )
