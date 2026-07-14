"""
Android 红外发射接口

通过 pyjnius 调用 Android ConsumerIrManager API，
实现手机红外发射功能。

前置条件:
    - 手机必须有红外发射硬件 (IR blaster)
    - 需要 FEATURE_CONSUMER_IR 权限
"""

from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class AndroidIRBlaster:
    """
    Android 红外发射器
    
    封装 Android ConsumerIrManager，提供跨平台安全调用。
    在非 Android 平台会自动降级为模拟模式。
    """

    def __init__(self):
        self._ir_manager = None
        self._has_ir = False
        self._init_ir()

    def _init_ir(self):
        """初始化红外管理器"""
        try:
            from jnius import autoclass, JavaException
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()
            
            # 获取 ConsumerIrManager 系统服务
            ir_service = context.getSystemService('consumer_ir')
            
            if ir_service is None:
                logger.warning("❌ 此设备没有红外发射硬件 (ConsumerIrManager 不可用)")
                self._has_ir = False
                return
            
            self._ir_manager = ir_service
            self._has_ir = ir_service.hasIrEmitter()
            
            if self._has_ir:
                # 获取载波频率范围
                try:
                    frequencies = ir_service.getCarrierFrequencies()
                    freq_list = []
                    for freq in frequencies:
                        freq_list.append(f"{freq.getMinFrequency()}-{freq.getMaxFrequency()}Hz")
                    logger.info(f"✅ 红外发射器可用，支持频率: {', '.join(freq_list)}")
                except Exception:
                    logger.info("✅ 红外发射器可用")
            else:
                logger.warning("❌ 设备硬件不支持红外发射")
                
        except ImportError:
            logger.warning("⚠️ 非 Android 环境，红外发射将使用模拟模式")
            self._has_ir = False
        except Exception as e:
            logger.error(f"❌ 红外初始化失败: {e}")
            self._has_ir = False

    @property
    def available(self) -> bool:
        """红外发射是否可用"""
        return self._has_ir and self._ir_manager is not None

    def transmit(self, carrier_freq: int, pattern: List[int]) -> bool:
        """
        发射红外信号
        
        Args:
            carrier_freq: 载波频率 (Hz)，通常 38000
            pattern: 脉冲序列 [mark, space, mark, space, ...] (µs)
        
        Returns:
            发射成功返回 True
        """
        if not self.available:
            logger.info(f"🔊 [模拟] 发射红外信号: 频率={carrier_freq}Hz, 脉冲数={len(pattern)}")
            self._print_pattern(pattern)
            return False  # 非错误，仅表示未实际发射
        
        try:
            self._ir_manager.transmit(carrier_freq, pattern)
            logger.debug(f"📡 红外信号已发射: {carrier_freq}Hz, {len(pattern)} 个脉冲")
            return True
        except Exception as e:
            logger.error(f"❌ 红外发射失败: {e}")
            return False

    def transmit_ac(self, controller) -> bool:
        """
        发射空调红外信号 (便捷方法)
        
        Args:
            controller: ACController 实例
        
        Returns:
            发射成功返回 True
        """
        pattern = controller.get_android_pattern()
        freq = controller.protocol.CARRIER_FREQUENCY
        return self.transmit(freq, pattern)

    def _print_pattern(self, pattern: List[int]):
        """打印脉冲序列 (调试用)"""
        parts = []
        for i, val in enumerate(pattern[:20]):  # 只打印前20个
            prefix = "+" if i % 2 == 0 else "-"
            parts.append(f"{prefix}{val}")
        if len(pattern) > 20:
            parts.append(f"... (共 {len(pattern)} 个脉冲)")
        logger.info(f"   脉冲: {' '.join(parts)}")


# ── 全局单例 ──
_ir_blaster: Optional[AndroidIRBlaster] = None


def get_ir_blaster() -> AndroidIRBlaster:
    """获取红外发射器单例"""
    global _ir_blaster
    if _ir_blaster is None:
        _ir_blaster = AndroidIRBlaster()
    return _ir_blaster
