import serial
import threading


class SerialDevice:


    def __init__(
        self,
        port,
        baudrate,
        callback
    ):

        self.port = port
        self.baudrate = baudrate
        self.callback = callback

        self.running = False
        self.thread = None
        self.serial = None



    def connect(self):

        self.serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=1
        )


        self.running = True


        self.thread = threading.Thread(
            target=self.read_loop,
            daemon=True
        )


        self.thread.start()


        print(
            "[Serial Connected]",
            self.port
        )



    def read_loop(self):


        while self.running:


            try:

                line = self.serial.readline()


                if not line:
                    continue


                data = line.decode(
                    "utf-8"
                ).strip()



                if data:

                    self.callback(
                        data
                    )


            except Exception as e:


                print(
                    "[Serial Error]",
                    e
                )



    def close(self):


        self.running = False


        if self.serial:

            self.serial.close()