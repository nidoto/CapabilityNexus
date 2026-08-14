import json

from processors.factory import ProcessorFactory



class ProcessorManager:


    def __init__(
        self
    ):

        self.processors={}



    def load(
        self,
        path
    ):


        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            data=json.load(f)



        configs=data.get(
            "processors",
            {}
        )

        self.load_dict(configs)

    def load_dict(
        self,
        configs
    ):
        """从处理器配置字典加载（游戏专属配置复用）。"""

        for capability_id, pipeline in configs.items():


            self.processors[capability_id]=[]


            for config in pipeline:


                processor=ProcessorFactory.create(
                    config
                )


                self.processors[capability_id].append(
                    processor
                )


                print(
                    "[Processor Loaded]",
                    capability_id,
                    config
                )



    def process(
        self,
        capability_id,
        value
    ):


        if capability_id not in self.processors:

            return value



        for processor in self.processors[capability_id]:

            value=processor.process(
                value
            )


        return value