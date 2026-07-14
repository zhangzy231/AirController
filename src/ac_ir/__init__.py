"""
AirController - 万能空调红外遥控核心库
支持格力、美的、海尔、TCL 等主流品牌空调红外协议
"""

from .protocols.gree import GreeProtocol
from .protocols.base import ACState, ACMode, FanSpeed, Brand

__version__ = "1.0.0"
__all__ = ["GreeProtocol", "ACState", "ACMode", "FanSpeed", "Brand"]
