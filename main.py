print(
    "CapabilityNexus V1"
)


#
# Core
#

from core.event_bus import EventBus

from core.capability_registry import CapabilityRegistry

from core.stream_adapter import StreamAdapter

from core.channel import Channel

from core.processed_channel import ProcessedChannel

from core.system_event import OutputEvent

from core.stream import StreamData


#
# Package
#

from packages.manager import PackageManager


#
# Processor
#

from processors.manager import ProcessorManager


#
# Mapping
#

from mapping.mapper import MappingEngine


#
# Protocol
#

from protocols.umi_protocol import UMIParser


#
# Event Bus
#

event_bus = EventBus()



#
# Capability Registry
#

registry = CapabilityRegistry()



#
# Package Manager
#

package_manager = PackageManager(
    registry
)


package_manager.load(
    "packages"
)



#
# Stream Adapter
#

adapter = StreamAdapter(
    registry
)



#
# Processor Manager
#

processor_manager = ProcessorManager()


processor_manager.load(
    "config/processors.json"
)



#
# UMI Parser
#

umi_parser = UMIParser(
    event_bus
)



#
# StreamData -> Channel
#

from core.transport import TransportController

transport_controller = TransportController()


def stream_receive(
    stream
):


    channel = adapter.convert(
        stream
    )


    if channel is None:

        return


    if not transport_controller.should_send(
        channel
    ):

        return


    print(
        "[Channel]",
        channel
    )


    event_bus.publish(
        channel
    )



event_bus.subscribe(
    StreamData,
    stream_receive
)



#
# Channel -> ProcessedChannel
#

def channel_receive(
    channel
):


    #
    # 防止重复处理
    #

    if channel.processed:

        return



    processed_value = processor_manager.process(

        channel.id,

        channel.value

    )



    processed = ProcessedChannel(

        channel.id,

        channel.category,

        processed_value,

        capability=channel.capability

    )


    print(
        "[Processed]",
        processed
    )


    event_bus.publish(
        processed
    )



event_bus.subscribe(

    Channel,

    channel_receive

)



#
# Transform Layer（用户逻辑表）
#

from mapping.transform import TransformLayer

transform_layer = TransformLayer(
    event_bus
)


def transform_receive(
    processed
):


    outputs = transform_layer.process(
        processed
    )


    for output in outputs:

        if output is processed:

            continue


        print(
            "[Transform]",
            processed.id,
            "->",
            output.id
        )


        event_bus.publish(
            output
        )



event_bus.subscribe(
    ProcessedChannel,
    transform_receive
)



#
# Mapping Engine
#

mapping_engine = MappingEngine(

    event_bus

)


mapping_engine.load_profile(

    "profiles/default.json"

)



#
# 输出路由：用户启用的虚拟输出设备 + 真实设备输出
#

from output.manager import OutputDeviceManager
from output.router import OutputRouter

output_manager = OutputDeviceManager(
    event_bus=event_bus
)

output_manager.load()
output_manager.build_all()

output_router = OutputRouter(
    event_bus=event_bus,
    managed_instances=output_manager.get_instance,
)


#
# 需求处理：游戏请求（如震动）→ 映射或提示
#

import json as _json

with open(
    "profiles/default.json",
    "r",
    encoding="utf-8"
) as _f:

    _profile_data = _json.load(_f)


from output.request_handler import RequestHandler

request_handler = RequestHandler(
    event_bus,
    router=output_router,
    mappings=_profile_data.get(
        "mappings",
        {}
    ),
)


#
# Output
#

def output_receive(
    event
):


    print(

        "[Output]",

        event

    )


    output_router.send(

        event.target,

        event.value

    )



event_bus.subscribe(

    OutputEvent,

    output_receive

)



#
# 设备管理：自动识别 + 手动配置
#

from devices.device_manager import DeviceManager

device_manager = DeviceManager(
    event_bus
)


resolved = device_manager.discover()


device_manager.connect_all(
    resolved
)


print(
    "CapabilityNexus Ready"
)



#
# Console Test
#

while True:


    try:

        line = input(">")

    except EOFError:

        break



    if line == "Exit":

        break



    umi_parser.parse(

        line

    )