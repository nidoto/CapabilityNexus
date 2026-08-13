from core.channel import Channel



class ProcessedChannel(Channel):


    def __init__(
        self,
        id,
        category,
        value,
        sequence=None,
        capability=None
    ):


        super().__init__(

            id,

            category,

            value,

            sequence,

            capability,

            True

        )



    def __repr__(self):


        return (

            "ProcessedChannel("

            f"id='{self.id}', "

            f"category='{self.category}', "

            f"value={self.value}, "

            f"processed={self.processed}"

            ")"

        )