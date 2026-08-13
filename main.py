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
# Output
#

from output.virtual_xinput import VirtualXInput


#
# Protocol
#

from protocols.umi_protocol import UMIParser

from protocols.serial_protocol import SerialParser


#
# Device
#

from devices.serial_device import SerialDevice



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
# Serial Parser (ESP32)
#

serial_parser = SerialParser(
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
# Virtual XInput
#

#
# 根据你的 virtual_xinput.py
# 如果需要 device_id，
# 修改这里
#

xinput = VirtualXInput(
    "CNX"
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


    xinput.send(

        event.target,

        event.value

    )


    xinput.update()



event_bus.subscribe(

    OutputEvent,

    output_receive

)



#
# Serial Device
#

def serial_input(
    line
):

    serial_parser.parse(
        line
    )



serial_device = SerialDevice(

    port="COM3",

    baudrate=115200,

    callback=serial_input

)



#
# ESP32阶段开启
#

serial_device.connect()


#
# Xbox One 手柄输入源
#

from devices.xinput_device import XInputDevice

xinput_device = XInputDevice(
    event_bus
)

xinput_device.connect()



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