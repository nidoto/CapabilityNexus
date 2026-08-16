import os

from core.event_bus import EventBus
from core.capability_registry import CapabilityRegistry
from core.stream_adapter import StreamAdapter
from core.channel import Channel
from core.processed_channel import ProcessedChannel
from core.system_event import OutputEvent
from core.stream import StreamData
from core.status_monitor import StatusMonitor

from packages.manager import PackageManager
from processors.manager import ProcessorManager
from mapping.mapper import MappingEngine
from mapping.transform import TransformLayer
from output.manager import OutputDeviceManager
from output.router import OutputRouter
from output.request_handler import RequestHandler
from protocols.umi_protocol import UMIParser
from devices.device_manager import DeviceManager


class CapabilityNexusApp:

    def __init__(self):
        self.project_root = self._project_root()
        self.event_bus = EventBus()
        self.registry = CapabilityRegistry()

        self.status_monitor = StatusMonitor(self.event_bus)
        self.status_monitor.start()

        self._build_pipeline()
        # Discover physical inputs before creating the virtual XInput output.
        # Otherwise Windows reports our own virtual pad as a real controller.
        self._build_devices()
        self._build_outputs()
        self._closed = False

        print("CapabilityNexus Ready")

    @staticmethod
    def _project_root():
        import sys as _sys

        if getattr(_sys, "frozen", False):
            return getattr(_sys, "_MEIPASS", None) or os.path.dirname(_sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def _load_active_profile(self):
        """读取一次当前激活的游戏配置并缓存，供处理器/映射/输出复用。"""
        from tools.config_io import load_profile

        self._profile_data = load_profile()

    def _build_pipeline(self):
        # 能力包（只读，frozen 下从内嵌 _MEIPASS/packages 加载）
        self.package_manager = PackageManager(self.registry)
        self.package_manager.load(os.path.join(self.project_root, "packages"))

        # 数据适配
        self.adapter = StreamAdapter(self.registry)

        # 处理器（全局 + 游戏专属覆盖）—— 用户配置与 GUI 同源（exe 同级 config）
        from tools.config_io import PROJECT_ROOT as _cfg_root

        self.processor_manager = ProcessorManager()
        self.processor_manager.load(
            os.path.join(_cfg_root, "config", "processors.json")
        )
        self._load_active_profile()
        self._load_game_processors()

        # UMI 解析器（控制台测试用）
        self.umi_parser = UMIParser(self.event_bus)

        # StreamData -> Channel
        def stream_receive(stream):
            channel = self.adapter.convert(stream)
            if channel is None:
                return
            self.event_bus.publish(channel)

        self.event_bus.subscribe(StreamData, stream_receive)

        # Channel -> ProcessedChannel
        def channel_receive(channel):
            if channel.processed:
                return

            processed_value = self.processor_manager.process(
                channel.id,
                channel.value,
            )

            processed = ProcessedChannel(
                channel.id,
                channel.category,
                processed_value,
                capability=channel.capability,
            )

            self.event_bus.publish(processed)

        self.event_bus.subscribe(Channel, channel_receive)

        # Transform Layer（用户逻辑表）
        self.transform_layer = TransformLayer(self.event_bus)

        transforms_path = os.path.join(_cfg_root, "config", "transforms.json")
        if os.path.exists(transforms_path):
            self.transform_layer.load(transforms_path)

        def transform_receive(processed):
            outputs = self.transform_layer.process(processed)

            for output in outputs:
                if output is processed:
                    continue

                self.event_bus.publish(output)

        self.event_bus.subscribe(ProcessedChannel, transform_receive)

        # Mapping
        self.mapping_engine = MappingEngine(self.event_bus)
        self.mapping_engine.load_mappings(self._profile_data.get("mappings", {}))

    def _load_game_processors(self):
        """加载当前激活游戏配置中的处理器覆盖。"""
        processors = self._profile_data.get("processors")
        if processors:
            self.processor_manager.load_dict(processors)

    def reload_processors(self):
        """运行时重载处理器（全局 + 当前游戏配置）。"""
        from tools.config_io import PROJECT_ROOT as _cfg_root

        self.processor_manager.processors.clear()
        self.processor_manager.load(
            os.path.join(_cfg_root, "config", "processors.json")
        )
        self._load_active_profile()
        self._load_game_processors()

    def _build_outputs(self):
        # 输出设备（用户启用）——用绝对路径，兼容打包 exe（相对路径会解析失败）
        from tools.config_io import PROJECT_ROOT as _cfg_root

        self.output_manager = OutputDeviceManager(
            event_bus=self.event_bus,
            config_path=os.path.join(_cfg_root, "config", "outputs.json"),
        )
        self.output_manager.load()
        self.output_manager.build_all()

        # 输出路由
        self.output_router = OutputRouter(
            event_bus=self.event_bus,
            managed_instances=self.output_manager.get_instances,
        )

        # 需求处理（游戏请求 -> 映射或提示）
        self.request_handler = RequestHandler(
            self.event_bus,
            router=self.output_router,
            mappings=self._profile_data.get("mappings", {}),
        )

        # OutputEvent -> 路由
        def output_receive(event):
            self.output_router.send(event.target, event.value)

        self.event_bus.subscribe(OutputEvent, output_receive)

    def _build_devices(self):
        # 设备识别 + 连接。用户设备配置与 GUI 同源（exe 同级 config/devices.json），
        # frozen 下不能读内嵌 _MEIPASS（那是发布默认，不含用户/方案添加的设备）。
        from tools.config_io import CONFIG_PATH

        self.device_manager = DeviceManager(
            self.event_bus,
            config_path=CONFIG_PATH,
        )

        resolved = self.device_manager.discover()
        self.device_manager.connect_all(resolved)

    def close(self):
        if self._closed:
            return
        self._closed = True

        try:
            self.status_monitor.stop()
        except Exception:
            pass

        try:
            self.device_manager.close_all()
        except Exception:
            pass

        try:
            self.output_manager.close_all()
        except Exception:
            pass

        try:
            self.output_router.close()
        except Exception:
            pass
