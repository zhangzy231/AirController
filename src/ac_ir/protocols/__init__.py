"""
空调红外协议实现
每个品牌对应一个协议模块，继承自 BaseProtocol
"""

from .gree import GreeProtocol

__all__ = ["GreeProtocol"]
