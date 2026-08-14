"""SerialParser 测试：键值解析、FRAME 元数据、默认别名、自定义映射。"""

from core.stream import StreamData
from protocols.serial_protocol import SerialParser


class Collector:
    def __init__(self):
        self.streams = []

    def publish(self, stream):
        self.streams.append(stream)


def test_parse_key_value():
    collector = Collector()
    parser = SerialParser(collector)

    parser.parse("X=12.5")

    assert len(collector.streams) == 1
    assert collector.streams[0].id == "control.right_x"
    assert collector.streams[0].value == 12.5


def test_default_alias_y():
    collector = Collector()
    parser = SerialParser(collector)

    parser.parse("Y=-3.2")

    assert len(collector.streams) == 1
    assert collector.streams[0].id == "control.right_y"
    assert collector.streams[0].value == -3.2


def test_frame_line_ignored():
    """FRAME= 是传输元数据，不应产生能力流。"""
    collector = Collector()
    parser = SerialParser(collector, has_frame=True)

    parser.parse("FRAME=42")

    assert collector.streams == []


def test_frame_gating():
    """开启 has_frame 后，帧计数器出现前忽略数据行。"""
    collector = Collector()
    parser = SerialParser(collector, has_frame=True)

    parser.parse("X=1.0")
    assert collector.streams == []

    parser.parse("FRAME=1")
    parser.parse("X=1.0")
    assert len(collector.streams) == 1


def test_custom_mapping():
    collector = Collector()
    parser = SerialParser(
        collector,
        mapping={"A": "sensor.pressure"},
    )

    parser.parse("A=99")

    assert collector.streams[0].id == "sensor.pressure"
    assert collector.streams[0].value == 99


def test_unknown_key_ignored():
    collector = Collector()
    parser = SerialParser(collector, mapping={"A": "sensor.pressure"})

    parser.parse("B=1.0")

    assert collector.streams == []


def test_invalid_value_ignored():
    collector = Collector()
    parser = SerialParser(collector)

    parser.parse("X=not-a-number")

    assert collector.streams == []


def test_empty_line_ignored():
    collector = Collector()
    parser = SerialParser(collector)

    parser.parse("   ")
    parser.parse("")

    assert collector.streams == []
