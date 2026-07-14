"""
格力 (Gree) 空调红外协议测试

验证:
1. ACState -> IR 数据编码 正确性
2. IR 数据 -> ACState 解码 正确性
3. 红外信号脉冲序列生成
4. 校验和计算
5. 各种模式组合
6. ACController 高级 API
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ac_ir.protocols.gree import GreeProtocol
from src.ac_ir.protocols.base import ACState, ACMode, FanSpeed
from src.ac_ir.encoder import ACController, IRSignalEncoder


class TestGreeProtocol:
    """格力协议测试套件"""

    def __init__(self):
        self.protocol = GreeProtocol()
        self.controller = ACController(self.protocol)
        self.encoder = IRSignalEncoder()
        self.passed = 0
        self.failed = 0

    def assert_equal(self, name, actual, expected):
        if actual == expected:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed += 1
            print(f"  [FAIL] {name}: expected {expected!r}, got {actual!r}")

    def test_default_state(self):
        """测试默认状态编码"""
        print("\n--- Test: Default State ---")
        state = ACState()
        raw = self.protocol.state_to_raw(state)
        self.assert_equal("raw length", len(raw), 8)
        # Byte 0: mode=001(cool), power=1(bit3), fan=00(bits4-5), swing=0, sleep=0
        self.assert_equal("Byte 0 (mode+cool+power+fan)", raw[0], 0b00001001)
        # Byte 1: temp=26 => 26-16=10 (0b1010)
        self.assert_equal("Byte 1 (temperature)", raw[1] & 0x0F, 0x0A)
        expected_cs = sum(raw[0:7]) & 0xFF
        self.assert_equal("Byte 7 (checksum)", raw[7], expected_cs)
        print(f"  Raw bytes: {' '.join(f'{b:02X}' for b in raw)}")

    def test_power_off(self):
        """测试关机状态"""
        print("\n--- Test: Power Off ---")
        state = ACState(power=False, mode=ACMode.COOL, temperature=26)
        raw = self.protocol.state_to_raw(state)
        self.assert_equal("Byte 0 (power=0)", raw[0], 0b00000001)
        print(f"  Raw bytes: {' '.join(f'{b:02X}' for b in raw)}")

    def test_heat_mode(self):
        """测试制热模式"""
        print("\n--- Test: Heat Mode ---")
        state = ACState(power=True, mode=ACMode.HEAT, temperature=30,
                        fan_speed=FanSpeed.HIGH)
        raw = self.protocol.state_to_raw(state)
        # heat(100) + power(1)<<3 + high_fan(11)<<4 = 0b00111100 = 60
        self.assert_equal("Byte 0 (heat+high fan)", raw[0], 0b00111100)
        self.assert_equal("Byte 1 (temp=30)", raw[1] & 0x0F, 0x0E)
        print(f"  Raw bytes: {' '.join(f'{b:02X}' for b in raw)}")

    def test_all_modes(self):
        """测试所有模式编码"""
        print("\n--- Test: All Modes ---")
        for mode in ACMode:
            state = ACState(power=True, mode=mode, temperature=25,
                            fan_speed=FanSpeed.AUTO)
            raw = self.protocol.state_to_raw(state)
            mode_bits = raw[0] & 0b111
            expected = self.protocol.MODE_MAP[mode]
            self.assert_equal(f"Mode {mode.name} bits", mode_bits, expected)

    def test_temperature_range(self):
        """测试温度范围 16-30C"""
        print("\n--- Test: Temperature Range ---")
        for temp in range(16, 31):
            state = ACState(power=True, mode=ACMode.COOL, temperature=temp)
            raw = self.protocol.state_to_raw(state)
            temp_bits = raw[1] & 0x0F
            expected = temp - 16
            self.assert_equal(f"Temp {temp}C", temp_bits, expected)

    def test_encode_decode_roundtrip(self):
        """测试编码解码往返一致性"""
        print("\n--- Test: Encode/Decode Roundtrip ---")
        original = ACState(
            power=True, mode=ACMode.COOL, temperature=24,
            fan_speed=FanSpeed.MEDIUM, swing_vertical=True,
            sleep=True, turbo=True, xfan=True, light=False,
        )
        raw = self.protocol.state_to_raw(original)
        decoded = self.protocol.raw_to_state(raw)
        self.assert_equal("power", decoded.power, original.power)
        self.assert_equal("mode", decoded.mode, original.mode)
        self.assert_equal("temperature", decoded.temperature, original.temperature)
        self.assert_equal("fan_speed", decoded.fan_speed, original.fan_speed)
        self.assert_equal("swing", decoded.swing_vertical, original.swing_vertical)
        self.assert_equal("sleep", decoded.sleep, original.sleep)
        self.assert_equal("turbo", decoded.turbo, original.turbo)
        self.assert_equal("xfan", decoded.xfan, original.xfan)
        print(f"  Raw: {' '.join(f'{b:02X}' for b in raw)}")

    def test_signal_generation(self):
        """测试红外信号生成"""
        print("\n--- Test: IR Signal Generation ---")
        state = ACState(power=True, mode=ACMode.COOL, temperature=26)
        freq, signal = self.protocol.build_ir_signal(state)
        self.assert_equal("carrier frequency", freq, 38000)
        self.assert_equal("signal length even", len(signal) % 2, 0)
        self.assert_equal("header mark", signal[0], 9000)
        self.assert_equal("header space", signal[1], 4500)
        self.assert_equal("total signal length", len(signal), 132)
        print(f"  Signal length: {len(signal)} pulses")

    def test_controller_api(self):
        """测试 ACController API"""
        print("\n--- Test: ACController API ---")
        self.assert_equal("initial temp", self.controller.state.temperature, 26)
        self.controller.power_off()
        self.assert_equal("power off", self.controller.state.power, False)
        self.controller.power_on()
        self.assert_equal("power on", self.controller.state.power, True)
        self.controller.set_temperature(18)
        self.assert_equal("temp set 18", self.controller.state.temperature, 18)
        self.controller.temp_up()
        self.assert_equal("temp up->19", self.controller.state.temperature, 19)
        self.controller.temp_down()
        self.assert_equal("temp down->18", self.controller.state.temperature, 18)
        self.controller.set_temperature(30)
        self.controller.temp_up()
        self.assert_equal("temp max 30", self.controller.state.temperature, 30)
        self.controller.set_temperature(16)
        self.controller.temp_down()
        self.assert_equal("temp min 16", self.controller.state.temperature, 16)
        self.controller.set_mode(ACMode.HEAT)
        self.assert_equal("mode heat", self.controller.state.mode, ACMode.HEAT)
        pattern = self.controller.get_android_pattern()
        self.assert_equal("pattern not empty", len(pattern) > 0, True)

    def test_checksum(self):
        """测试校验和"""
        print("\n--- Test: Checksum ---")
        state = ACState(power=True, mode=ACMode.COOL, temperature=26)
        raw = self.protocol.state_to_raw(state)
        calc_cs = sum(raw[0:7]) & 0xFF
        self.assert_equal("checksum match", raw[7], calc_cs)
        bad_raw = raw.copy()
        bad_raw[0] = 0xFF
        bad_cs = sum(bad_raw[0:7]) & 0xFF
        self.assert_equal("tampered mismatch", bad_raw[7] == bad_cs, False)

    def run_all(self):
        print("=" * 60)
        print("格力 (Gree) 空调红外协议测试")
        print("=" * 60)
        self.test_default_state()
        self.test_power_off()
        self.test_heat_mode()
        self.test_all_modes()
        self.test_temperature_range()
        self.test_encode_decode_roundtrip()
        self.test_signal_generation()
        self.test_controller_api()
        self.test_checksum()
        print("\n" + "=" * 60)
        total = self.passed + self.failed
        print(f"结果: {self.passed}/{total} 通过, {self.failed} 失败")
        print("=" * 60)
        return self.failed == 0


if __name__ == "__main__":
    test = TestGreeProtocol()
    success = test.run_all()
    sys.exit(0 if success else 1)
