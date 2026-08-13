class Channel:


    def __init__(
        self,
        id,
        category,
        value,
        sequence=None,
        capability=None,
        processed=False
    ):

        self.id = id

        self.category = category

        self.value = value

        self.sequence = sequence

        self.capability = capability

        self.processed = processed



    def __repr__(self):

        return (
            "Channel("
            f"id='{self.id}', "
            #f"category='{self.category}', "
            f"value={self.value}, "
            f"processed={self.processed}"
            ")"
        )