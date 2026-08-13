class OutputDevice:


    def __init__(
        self,
        device_id=0
    ):

        self.device_id = device_id


    def send(
        self,
        target,
        value
    ):

        raise NotImplementedError(
            "OutputDevice.send()"
        )


    def set_axis(
        self,
        axis,
        value
    ):

        raise NotImplementedError(
            "OutputDevice.set_axis()"
        )


    def set_button(
        self,
        button,
        pressed
    ):

        raise NotImplementedError(
            "OutputDevice.set_button()"
        )


    def set_trigger(
        self,
        trigger,
        value
    ):

        raise NotImplementedError(
            "OutputDevice.set_trigger()"
        )


    def close(
        self
    ):

        pass
