from core.channel import Channel



class StreamAdapter:


    def __init__(
        self,
        registry
    ):

        self.registry = registry



    def convert(
        self,
        stream
    ):


        capability_info = self.registry.get(

            stream.id

        )


        if capability_info is None:


            print(

                "[Unknown Capability]",

                stream.id

            )


            return None



        capability = capability_info["definition"]



        channel = Channel(

            id=stream.id,

            category=capability["category"],

            value=stream.value,

            capability=capability

        )


        return channel