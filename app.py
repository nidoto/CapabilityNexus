import os

from core.event_bus import EventBus
from core.capability_registry import CapabilityRegistry
from core.stream_adapter import StreamAdapter
from core.channel import Channel
from core.processed_channel import ProcessedChannel
from core.system_event import OutputEvent
from core.stream import StreamData

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
        self.event_bus = EventBus()
        self.registry = CapabilityRegistry()

        self._build_pipeline()
        self._build_outputs()
        self._build_devices()

        print("CapabilityNexus Ready")

    def _build_pipeline(self):
        # 能力包
        self.package_manager = PackageManager(self.registry)
        self.package_manager.load("packages")

        # 数据适配
        self.adapter = StreamAdapter(self.registry)

        # 处理器
        self.processor_manager = ProcessorManager()
        self.processor_manager.load("config/processors.json")

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

        if os.path.exists("config/transforms.json"):
            self.transform_layer.load("config/transforms.json")

        def transform_receive(processed):
            outputs = self.transform_layer.process(processed)

            for output in outputs:
                if output is processed:
                    continue

                self.event_bus.publish(output)

        self.event_bus.subscribe(ProcessedChannel, transform_receive)

        # Mapping
        self.mapping_engine = MappingEngine(self.event_bus)
        self.mapping_engine.load_profile("profiles/default.json")

    def _build_outputs(self):
        # 输出设备（用户启用）
        self.output_manager = OutputDeviceManager(event_bus=self.event_bus)
        self.output_manager.load()
        self.output_manager.build_all()

        # 输出路由
        self.output_router = OutputRouter(
            event_bus=self.event_bus,
            managed_instances=self.output_manager.get_instances,
        )

        # 需求处理（游戏请求 -> 映射或提示）
        import json as _json

        with open("profiles/default.json", "r", encoding="utf-8") as _f:
            _profile_data = _json.load(_f)

        self.request_handler = RequestHandler(
            self.event_bus,
            router=self.output_router,
            mappings=_profile_data.get("mappings", {}),
        )

        # OutputEvent -> 路由
        def output_receive(event):
            self.output_router.send(event.target, event.value)

        self.event_bus.subscribe(OutputEvent, output_receive)

    def _build_devices(self):
        # 设备识别 + 连接
        self.device_manager = DeviceManager(self.event_bus)

        resolved = self.device_manager.discover()
        self.device_manager.connect_all(resolved)

    def close(self):
        try:
            self.device_manager.close_all()
        except Exception:
            pass

        try:
            self.output_manager.close_all()
        except Exception:
            pass
