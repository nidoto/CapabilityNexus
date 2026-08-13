from core.stream import StreamData


class UMIParser:


    def __init__(
        self,
        event_bus
    ):

        self.event_bus = event_bus



    def parse(
        self,
        line
    ):


        if not isinstance(
            line,
            str
        ):
            return



        line = line.strip()



        if not line.startswith(
            "UMI_DATA"
        ):

            return



        try:

            payload = line.split(
                " ",
                1
            )[1]


            key,value = payload.split(
                "=",
                1
            )


            value = float(
                value
            )


        except Exception as e:


            print(
                "[UMI Parse Error]",
                e
            )

            return



        stream = StreamData(

            key,

            value

        )


        print(
            "[UMI]",
            stream
        )


        self.event_bus.publish(
            stream
        )