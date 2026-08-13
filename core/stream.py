class StreamData:


    def __init__(
        self,
        id,
        value,
        capability=None
    ):

        self.id=id

        self.value=value

        self.capability=capability


    def __repr__(self):

        return f"StreamData(id='{self.id}', value={self.value})"