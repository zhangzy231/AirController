"""
红外信号编码器

将协议脉冲序列转化为可发射的 IR 信号格式，
支持多种输出格式以适应不同平台。
"""

from typing import List, Tuple, Dict
from .protocols.base import BaseProtocol, ACState, ACMode, FanSpeed


class IRSignalEncoder:
    """
    红外信号编码器
    
    负责:
    1. 将协议生成的脉冲序列编码为各平台可用格式
    2. 支持 ConsumerIrManager (Android) 的 pattern 格式
    3. 支持 Arduino/ESP 的 raw 格式
    4. 支持 Pronto HEX 格式（用于分析/存档）
    """

    @staticmethod
    def to_android_pattern(protocol: BaseProtocol, state: ACState) -> List[int]:
        """
        生成 Android ConsumerIrManager.transmit() 所需的 pattern 数组
        
        Android pattern 格式:
            交替的 [pulse, space, pulse, space, ...] (µs)
        """
        freq, signal = protocol.build_ir_signal(state)
        return signal

    @staticmethod
    def to_arduino_raw(protocol: BaseProtocol, state: ACState) -> Dict:
        """
        生成 Arduino/ESP8266 兼容的 raw 数据
        
        Returns:
            {
                "freq": 38000,
                "raw": [9000, 4500, 620, 540, ...],
                "raw_len": 67
            }
        """
        freq, signal = protocol.build_ir_signal(state)
        return {
            "freq": freq,
            "raw": signal,
            "raw_len": len(signal),
        }

    @staticmethod
    def to_pronto_hex(protocol: BaseProtocol, state: ACState) -> str:
        """
        生成 Pronto HEX 格式 (用于 IrScrutinizer / 分析工具)
        
        Pronto格式:
        0000 <频率字> 0000 <脉冲对数量> <序列...>
        """
        freq, signal = protocol.build_ir_signal(state)
        
        # 计算频率字: freq_word = round(4145146 / frequency)
        freq_word = round(4145146 / freq)
        
        # 计算脉冲对数量 (一次性 burst 无重复)
        pairs = len(signal) // 2
        
        # 时序值转换为 Pronto 周期单位 (周期 ≈ 0.241246 µs)
        pronto_seq = []
        for val in signal:
            pronto_seq.append(round(val * freq / 1000000))
        
        # 组装
        parts = [f"0000 {freq_word:04X} 0000 {pairs:04X}"]
        for val in pronto_seq:
            parts.append(f"{val:04X}")
        
        return " ".join(parts)

    @staticmethod
    def to_pulse_sequence(protocol: BaseProtocol, state: ACState) -> str:
        """
        生成可读的脉冲序列字符串 (调试用)
        
        格式: "+9000 -4500 +620 -540 ..."
        """
        freq, signal = protocol.build_ir_signal(state)
        parts = []
        for i, val in enumerate(signal):
            prefix = "+" if i % 2 == 0 else "-"
            parts.append(f"{prefix}{val}")
        return " ".join(parts)


class ACController:
    """
    空调控制器 (高层 API)
    
    用法:
        controller = ACController(GreeProtocol())
        controller.power_on()
        controller.set_temperature(26)
        controller.set_mode(ACMode.COOL)
        pattern = controller.get_android_pattern()
    """

    def __init__(self, protocol: BaseProtocol):
        self.protocol = protocol
        self._state = ACState()  # 默认: 制冷 26°C 自动风
        self.encoder = IRSignalEncoder()

    # ── 状态修改 ──

    @property
    def state(self) -> ACState:
        return self._state

    def power_on(self):
        self._state.power = True

    def power_off(self):
        self._state.power = False

    def toggle_power(self):
        self._state.power = not self._state.power

    def set_mode(self, mode: ACMode):
        self._state.mode = mode

    def set_temperature(self, temp: int):
        self._state.temperature = temp

    def temp_up(self):
        if self._state.temperature < 30:
            self._state.temperature += 1

    def temp_down(self):
        if self._state.temperature > 16:
            self._state.temperature -= 1

    def set_fan_speed(self, speed: FanSpeed):
        self._state.fan_speed = speed

    def toggle_swing(self):
        self._state.swing_vertical = not self._state.swing_vertical

    def toggle_sleep(self):
        self._state.sleep = not self._state.sleep

    def toggle_turbo(self):
        self._state.turbo = not self._state.turbo

    def toggle_xfan(self):
        self._state.xfan = not self._state.xfan

    # ── 信号输出 ──

    def get_android_pattern(self) -> List[int]:
        """获取 Android IR blaster pattern"""
        return self.encoder.to_android_pattern(self.protocol, self._state)

    def get_arduino_raw(self) -> Dict:
        """获取 Arduino/ESP 原始数据"""
        return self.encoder.to_arduino_raw(self.protocol, self._state)

    def get_pronto_hex(self) -> str:
        """获取 Pronto HEX 格式"""
        return self.encoder.to_pronto_hex(self.protocol, self._state)

    def get_raw_bytes(self) -> List[int]:
        """获取协议原生字节 (调试用)"""
        return self.protocol.state_to_raw(self._state)

    def get_pulse_debug(self) -> str:
        """获取脉冲序列调试字符串"""
        return self.encoder.to_pulse_sequence(self.protocol, self._state)
