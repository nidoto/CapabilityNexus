from core.stream import StreamData



class SerialParser:


    def __init__(
        self,
        event_bus
    ):

        self.event_bus = event_bus


        self.frame = None


        self.last_frame = -1



        self.mapping = {

            "X": "motion.yaw",

            "Y": "motion.pitch",

            "R": "motion.roll"

        }



    def parse(
        self,
        line
    ):


        line = line.strip()



        if not line:

            return



        #
        # FRAME
        #

        if line.startswith(
            "FRAME="
        ):


            frame = int(
                line.split("=")[1]
            )


            #
            # 丢弃旧帧
            #

            if frame < self.last_frame:

                print(
                    "[SerialParser] Frame counter reset, resync",
                    frame
                )

                self.last_frame = frame - 1



            self.last_frame = frame

            self.frame = frame



            print(
                "[Frame]",
                frame
            )


            return



        #
        # 没有FRAME不处理
        #

        if self.frame is None:

            return



        #
        # 数据
        #

        if "=" not in line:

            return



        key,value = line.split(
            "=",
            1
        )



        if key not in self.mapping:

            return



        try:

            value=float(value)


        except:

            return




        stream = StreamData(

            id=self.mapping[key],

            value=value

        )



        print(

            "[StreamData]",

            stream

        )



        self.event_bus.publish(

            stream

        )