"""
空调红外协议基类 & 通用状态模型

定义了所有空调协议共用的数据结构和接口。
"""

from dataclasses import dataclass, field
from enum import IntEnum, Enum
from typing import List, Tuple, Optional


class ACMode(IntEnum):
    """空调运行模式"""
    AUTO = 0   # 自动
    COOL = 1   # 制冷
    DRY = 2    # 除湿
    FAN = 3    # 送风
    HEAT = 4   # 制热


class FanSpeed(IntEnum):
    """风扇风速"""
    AUTO = 0   # 自动
    LOW = 1    # 低风
    MEDIUM = 2 # 中风
    HIGH = 3   # 高风


class Brand(Enum):
    """支持的空调品牌"""
    GREE = "gree"       # 格力
    MIDEA = "midea"      # 美的 (待实现)
    HAIER = "haier"      # 海尔 (待实现)
    TCL = "tcl"           # TCL (待实现)
    AUX = "aux"           # 奥克斯 (待实现)
    HISENSE = "hisense"  # 海信 (待实现)


@dataclass
class ACState:
    """
    空调状态数据类
    
    作为所有品牌协议的通用状态表示，各协议实现负责
    将自己的原生格式与 ACState 互相转换。
    """
    # 基础控制
    power: bool = True          # 开关机
    mode: ACMode = ACMode.COOL  # 运行模式
    temperature: int = 26       # 温度 (16-30)
    fan_speed: FanSpeed = FanSpeed.AUTO  # 风速
    
    # 高级功能
    swing_vertical: bool = False    # 上下扫风
    swing_horizontal: bool = False  # 左右扫风 (部分机型支持)
    turbo: bool = False             # 强劲/超强模式
    sleep: bool = False             # 睡眠模式
    xfan: bool = False              # 干燥/防霉 (部分品牌)
    light: bool = True              # 显示屏灯光
    ionizer: bool = False           # 负离子/清新 (部分品牌)
    energy_save: bool = False       # 节能模式
    
    # 定时 (单位: 分钟, 0 表示无定时)
    timer_on: int = 0              # 定时开机 (30分钟步进)
    timer_off: int = 0             # 定时关机 (30分钟步进)
    
    def __post_init__(self):
        self._validate()
    
    def _validate(self):
        """校验状态参数合法性"""
        if not 16 <= self.temperature <= 30:
            raise ValueError(f"温度范围 16-30°C，当前值: {self.temperature}")
        if self.timer_on % 30 != 0 or self.timer_off % 30 != 0:
            raise ValueError("定时必须以30分钟为步进")
        if self.timer_on < 0 or self.timer_on > 1440:  # 最大24小时
            raise ValueError(f"定时开机时间无效: {self.timer_on}")
        if self.timer_off < 0 or self.timer_off > 1440:
            raise ValueError(f"定时关机时间无效: {self.timer_off}")
    
    def to_dict(self) -> dict:
        """转换为字典，便于UI绑定"""
        return {
            "power": self.power,
            "mode": self.mode.name,
            "temperature": self.temperature,
            "fan_speed": self.fan_speed.name,
            "swing_vertical": self.swing_vertical,
            "swing_horizontal": self.swing_horizontal,
            "turbo": self.turbo,
            "sleep": self.sleep,
            "xfan": self.xfan,
            "light": self.light,
            "ionizer": self.ionizer,
            "energy_save": self.energy_save,
            "timer_on": self.timer_on,
            "timer_off": self.timer_off,
        }
    
    def copy(self) -> "ACState":
        """深拷贝"""
        return ACState(
            power=self.power,
            mode=self.mode,
            temperature=self.temperature,
            fan_speed=self.fan_speed,
            swing_vertical=self.swing_vertical,
            swing_horizontal=self.swing_horizontal,
            turbo=self.turbo,
            sleep=self.sleep,
            xfan=self.xfan,
            light=self.light,
            ionizer=self.ionizer,
            energy_save=self.energy_save,
            timer_on=self.timer_on,
            timer_off=self.timer_off,
        )


class BaseProtocol:
    """
    空调红外协议基类
    
    所有品牌协议必须实现:
        state_to_raw(state) -> List[int]: 将 ACState 转换为原生IR数据
        raw_to_state(raw)  -> ACState:    将原生IR数据转换为 ACState
        build_ir_signal(state) -> Tuple[int, List[int]]: 构建完整红外信号
    """
    
    # 红外载波频率 (Hz)
    CARRIER_FREQUENCY: int = 38000
    
    # 各协议必须定义自己的时序参数
    HEADER_MARK: int = 0     # 起始高电平 (µs)
    HEADER_SPACE: int = 0    # 起始低电平 (µs)
    BIT_MARK: int = 0        # 比特高电平 (µs)
    ZERO_SPACE: int = 0      # 比特0低电平 (µs)
    ONE_SPACE: int = 0       # 比特1低电平 (µs)
    FOOTER_MARK: int = 0     # 结束高电平 (µs)
    GAP_SPACE: int = 0       # 帧间隔 (µs)
    
    # 数据长度 (字节/半字节数)
    STATE_SIZE: int = 0
    
    @property
    def brand(self) -> Brand:
        raise NotImplementedError
    
    def state_to_raw(self, state: ACState) -> List[int]:
        """将通用状态转为协议原生字节数组"""
        raise NotImplementedError
    
    def raw_to_state(self, raw: List[int]) -> ACState:
        """从协议原生字节数组解析为通用状态"""
        raise NotImplementedError
    
    def _calc_checksum(self, data: List[int]) -> int:
        """计算校验和 (默认使用低8位累加和)"""
        return sum(data) & 0xFF
    
    def _bits_to_bytes(self, bits: List[int]) -> List[int]:
        """将比特流转为字节数组 (LSB first)"""
        result = []
        for i in range(0, len(bits), 8):
            chunk = bits[i:i+8]
            if len(chunk) < 8:
                chunk += [0] * (8 - len(chunk))
            byte = 0
            for j, b in enumerate(chunk):
                byte |= (b & 1) << j  # LSB first
            result.append(byte)
        return result
    
    def _bytes_to_bits(self, data: List[int], num_bits: int = None) -> List[int]:
        """将字节数组转为比特流 (LSB first)"""
        if num_bits is None:
            num_bits = len(data) * 8
        bits = []
        for byte in data:
            for j in range(8):
                bits.append((byte >> j) & 1)
        return bits[:num_bits]
    
    def build_ir_signal(self, state: ACState) -> Tuple[int, List[int]]:
        """
        构建完整红外信号
        
        Returns:
            Tuple[频率, [时长序列]] 
            时长序列交替为 [mark, space, mark, space, ...]
            单位为微秒 (µs)
        """
        raw_data = self.state_to_raw(state)
        bits = self._bytes_to_bits(raw_data)
        
        # 构建脉冲序列
        signal = []
        # Header
        signal.append(self.HEADER_MARK)
        signal.append(self.HEADER_SPACE)
        
        # Data bits
        for bit in bits:
            signal.append(self.BIT_MARK)
            if bit:
                signal.append(self.ONE_SPACE)
            else:
                signal.append(self.ZERO_SPACE)
        
        # Footer
        signal.append(self.FOOTER_MARK)
        signal.append(self.GAP_SPACE)
        
        return (self.CARRIER_FREQUENCY, signal)
    
    def build_repeat_signal(self) -> Tuple[int, List[int]]:
        """构建重发信号 (部分协议支持)"""
        return (self.CARRIER_FREQUENCY, [
            self.HEADER_MARK,
            self.HEADER_SPACE,
            self.BIT_MARK,
            self.GAP_SPACE,
        ])
