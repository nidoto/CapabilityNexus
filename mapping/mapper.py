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
        target
    ):

        self.mapping[source]=target


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



        for source,target in mappings.items():


            self.add_mapping(
                source,
                target
            )


            print(
                "[Profile]",
                source,
                "->",
                target
            )

    

    def receive(
        self,
        channel
    ):






        if channel.id not in self.mapping:

            return



        target=self.mapping[channel.id]



        event=OutputEvent(

            target,

            channel.value



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