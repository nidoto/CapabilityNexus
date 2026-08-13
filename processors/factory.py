from processors.deadzone import DeadzoneProcessor
from processors.sensitivity import SensitivityProcessor
from processors.normalizer import NormalizerProcessor
from processors.clamp import ClampProcessor

class ProcessorFactory:


    @staticmethod
    def create(config):


        t=config["type"]


        if t=="deadzone":

            from processors.deadzone import DeadzoneProcessor

            return DeadzoneProcessor(
                config["value"]
            )


        elif t=="sensitivity":

            from processors.sensitivity import SensitivityProcessor

            return SensitivityProcessor(
                config["value"]
            )


        elif t=="normalizer":

            from processors.normalizer import NormalizerProcessor

            return NormalizerProcessor(

                config["input_min"],

                config["input_max"]

            )
            
        elif t=="clamp":
            
            from processors.clamp import ClampProcessor

            return ClampProcessor(

                config.get("minimum", -32768),

                config.get("maximum", 32767)

            )


        else:

            raise Exception(
                "Unknown processor"
            )