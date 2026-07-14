#!/usr/bin/env python3
"""
AirController - 万能空调遥控器

基于 Kivy 的 Android 空调红外遥控应用。
支持格力等主流品牌空调。

运行方式:
    python main.py          # 桌面调试
    buildozer android debug # 构建 APK
"""

import os
import sys

# 确保 src 在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.config import Config

# 设置窗口大小 (桌面调试用)
Config.set("graphics", "width", "400")
Config.set("graphics", "height", "720")
Config.set("graphics", "resizable", False)

from src.ui.screens import MainScreen, BrandSelectScreen


class AirControllerApp(App):
    """AirController 主应用"""

    title = "AirController"
    icon = "assets/icon.png"

    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(BrandSelectScreen(name="brand_select"))
        return sm

    def on_start(self):
        """应用启动时初始化"""
        print("=" * 50)
        print("AirController - 万能空调遥控器")
        print("当前品牌: 格力 (Gree)")
        print("红外状态: 检查中...")
        print("=" * 50)


if __name__ == "__main__":
    AirControllerApp().run()
