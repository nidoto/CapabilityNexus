class NormalizerProcessor:


    def __init__(
        self,
        input_min,
        input_max,
        output_min=-32768,
        output_max=32767
    ):

        self.input_min=input_min
        self.input_max=input_max

        self.output_min=output_min
        self.output_max=output_max



    def process(
        self,
        value
    ):


        if value < self.input_min:

            value=self.input_min


        if value > self.input_max:

            value=self.input_max



        ratio=(

            value-self.input_min

        ) / (

            self.input_max-self.input_min

        )


        return (

            self.output_min +

            ratio *

            (
                self.output_max-self.output_min
            )

        )