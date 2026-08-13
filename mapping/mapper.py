from core.processed_channel import ProcessedChannel
from core.system_event import OutputEvent
import json


class MappingEngine:


    def __init__(
        self,
        event_bus
    ):

        self.mapping={}

        self.event_bus=event_bus


        event_bus.subscribe(
            ProcessedChannel,
            self.receive
        )



    def add_mapping(
        self,
        source,
        target,
        gain=1.0,
        return_to_center=False
    ):

        self.mapping[source] = {
            "target": target,
            "gain": gain,
            "return_to_center": return_to_center,
        }


    def load_profile(
    self,
    path
):


        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:


            data=json.load(f)


        mappings=data.get(
            "mappings",
            {}
        )


        for source, mapping in mappings.items():


            target = mapping

            gain = 1.0

            return_to_center = False


            if isinstance(
                mapping,
                dict
            ):

                target = mapping.get(
                    "target",
                    "?"
                )

                gain = mapping.get(
                    "gain",
                    1.0
                )

                return_to_center = mapping.get(
                    "return_to_center",
                    False
                )


            self.add_mapping(
                source,
                target,
                gain=gain,
                return_to_center=return_to_center
            )


            print(
                "[Profile]",
                source,
                "->",
                target,
                "gain=",
                gain,
                "return_to_center=",
                return_to_center
            )

    

    def receive(
        self,
        channel
    ):






        if channel.id not in self.mapping:

            return



        config = self.mapping[channel.id]

        target = config["target"]

        value = channel.value * config["gain"]



        event=OutputEvent(

            target,

            value

        )


        print(

            "[Mapping]",

            channel.id,

            "->",

            target

        )


        self.event_bus.publish(

            event

        )