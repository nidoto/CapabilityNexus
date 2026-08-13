from processors.base import Processor



class DeadzoneProcessor(Processor):


    def __init__(
        self,
        deadzone=5
    ):

        self.deadzone = deadzone



    def process(
        self,
        value
    ):


        if abs(value) < self.deadzone:

            return 0


        return value