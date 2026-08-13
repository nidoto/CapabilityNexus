from processors.base import Processor



class SensitivityProcessor(Processor):


    def __init__(
        self,
        sensitivity=1.0
    ):

        self.sensitivity=sensitivity



    def process(
        self,
        value
    ):

        return value * self.sensitivity