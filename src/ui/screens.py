"""
AirController Kivy UI 屏幕

包含:
- MainScreen: 主遥控器界面
- BrandSelectScreen: 品牌选择
- SettingsScreen: 设置
"""

from kivy.uix.screenmanager import Screen
from kivy.properties import (
    StringProperty, NumericProperty, BooleanProperty,
    ObjectProperty, ListProperty
)
from kivy.clock import Clock

from ..ac_ir.protocols.base import ACState, ACMode, FanSpeed, Brand
from ..ac_ir.protocols.gree import GreeProtocol
from ..ac_ir.encoder import ACController
from ..ac_ir.android_ir import get_ir_blaster


class MainScreen(Screen):
    """主遥控器界面"""

    # ── UI 绑定属性 ──
    temperature = NumericProperty(26)
    power_state = BooleanProperty(True)
    mode_text = StringProperty("制冷")
    fan_text = StringProperty("自动")
    swing_active = BooleanProperty(False)
    sleep_active = BooleanProperty(False)
    turbo_active = BooleanProperty(False)
    brand_text = StringProperty("格力")

    # 模式按钮颜色
    mode_colors = ListProperty([
        [0.2, 0.6, 1, 1],   # 自动
        [0.2, 0.6, 1, 1],   # 制冷
        [0.2, 0.6, 1, 1],   # 除湿
        [0.2, 0.6, 1, 1],   # 送风
        [0.2, 0.6, 1, 1],   # 制热
    ])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = ACController(GreeProtocol())
        self.ir_blaster = get_ir_blaster()
        self._sync_from_state()
        Clock.schedule_once(self._check_ir, 1)

    def _check_ir(self, dt):
        """检查红外是否可用"""
        if not self.ir_blaster.available:
            # 模拟模式 - 仍然可用，只是不实际发射
            pass

    # ── 状态同步 ──

    def _sync_from_state(self):
        """从 controller.state 同步到 UI 属性"""
        state = self.controller.state
        self.power_state = state.power
        self.temperature = state.temperature
        self.swing_active = state.swing_vertical
        self.sleep_active = state.sleep
        self.turbo_active = state.turbo

        # 模式文本
        mode_labels = {
            ACMode.AUTO: "自动",
            ACMode.COOL: "制冷",
            ACMode.DRY:  "除湿",
            ACMode.FAN:  "送风",
            ACMode.HEAT: "制热",
        }
        self.mode_text = mode_labels.get(state.mode, "??")

        # 风速文本
        fan_labels = {
            FanSpeed.AUTO:   "自动",
            FanSpeed.LOW:    "低风",
            FanSpeed.MEDIUM: "中风",
            FanSpeed.HIGH:   "高风",
        }
        self.fan_text = fan_labels.get(state.fan_speed, "??")

        # 更新模式按钮高亮
        self._update_mode_highlight()

    def _update_mode_highlight(self):
        """更新模式按钮高亮颜色"""
        active_color = [0.1, 0.5, 1, 1]    # 高亮蓝
        inactive_color = [0.35, 0.35, 0.4, 1]  # 暗灰
        colors = [inactive_color] * 5
        idx = int(self.controller.state.mode)
        if 0 <= idx < 5:
            colors[idx] = active_color
        self.mode_colors = colors

    def _transmit(self):
        """发射当前状态的红外信号"""
        self.ir_blaster.transmit_ac(self.controller)

    # ── 按钮回调 ──

    def on_power_toggle(self):
        """电源按钮"""
        self.controller.toggle_power()
        self._sync_from_state()
        self._transmit()

    def on_temp_up(self):
        """温度 +"""
        self.controller.temp_up()
        self._sync_from_state()
        self._transmit()

    def on_temp_down(self):
        """温度 -"""
        self.controller.temp_down()
        self._sync_from_state()
        self._transmit()

    def on_mode_select(self, mode_idx: int):
        """选择模式 (0=自动, 1=制冷, 2=除湿, 3=送风, 4=制热)"""
        mode_map = {
            0: ACMode.AUTO,
            1: ACMode.COOL,
            2: ACMode.DRY,
            3: ACMode.FAN,
            4: ACMode.HEAT,
        }
        self.controller.set_mode(mode_map.get(mode_idx, ACMode.COOL))
        self._sync_from_state()
        self._transmit()

    def on_fan_toggle(self):
        """循环切换风速"""
        fan_cycle = [FanSpeed.AUTO, FanSpeed.LOW, FanSpeed.MEDIUM, FanSpeed.HIGH]
        current = self.controller.state.fan_speed
        next_idx = (fan_cycle.index(current) + 1) % len(fan_cycle)
        self.controller.set_fan_speed(fan_cycle[next_idx])
        self._sync_from_state()
        self._transmit()

    def on_swing_toggle(self):
        """扫风开关"""
        self.controller.toggle_swing()
        self._sync_from_state()
        self._transmit()

    def on_sleep_toggle(self):
        """睡眠模式"""
        self.controller.toggle_sleep()
        self._sync_from_state()
        self._transmit()

    def on_turbo_toggle(self):
        """强劲模式"""
        self.controller.toggle_turbo()
        self._sync_from_state()
        self._transmit()


class BrandSelectScreen(Screen):
    """品牌选择界面"""
    brands = ListProperty([
        {"name": "格力", "brand": Brand.GREE, "icon": "❄️"},
        {"name": "美的", "brand": Brand.MIDEA, "icon": "🏠"},
        {"name": "海尔", "brand": Brand.HAIER, "icon": "🌊"},
        {"name": "TCL", "brand": Brand.TCL, "icon": "📺"},
        {"name": "奥克斯", "brand": Brand.AUX, "icon": "💨"},
        {"name": "海信", "brand": Brand.HISENSE, "icon": "📡"},
    ])

    def on_brand_select(self, brand: Brand):
        """选择品牌后返回主界面"""
        # TODO: 根据品牌切换控制器协议
        self.manager.current = "main"
