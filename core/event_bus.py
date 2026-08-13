class EventBus:


    def __init__(self):

        self.subscribers = []



    def subscribe(
        self,
        event_type,
        callback
    ):


        print(

            "[EventBus Subscribe]",

            event_type,

            callback

        )


        self.subscribers.append(

            (
                event_type,
                callback
            )

        )



    def publish(
        self,
        event
    ):


        print(

            "[EventBus Publish]",

            type(event)

        )


        for registered_type, callback in self.subscribers:


            print(

                "[EventBus Check]",

                registered_type,

                callback

            )


            if isinstance(
                event,
                registered_type
            ):


                print(

                    "[EventBus Call]",

                    callback

                )


                callback(event)