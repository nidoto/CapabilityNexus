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

def stream_receive(
    stream
):


    channel = adapter.convert(
        stream
    )


    if channel is None:

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
# Mapping Engine
#

mapping_engine = MappingEngine(

    event_bus

)


mapping_engine.load_profile(

    "profiles/default.json"

)



#
# 输出路由：虚拟 x360 + 真实设备输出
#

from output.router import OutputRouter

output_router = OutputRouter()


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