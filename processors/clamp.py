class ClampProcessor:


    def __init__(
        self,
        minimum=-32768,
        maximum=32767
    ):

        self.minimum = minimum

        self.maximum = maximum



    def process(
        self,
        value
    ):


        if value < self.minimum:

            value = self.minimum


        elif value > self.maximum:

            value = self.maximum



        return int(value)