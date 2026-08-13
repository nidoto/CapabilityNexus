import json



class CapabilityManager:


    def __init__(self):

        self.capabilities = {}



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



        for capability in data.get(
            "capabilities",
            []
        ):


            cid = capability["id"]


            self.capabilities[cid]=capability



            print(
                "[Capability]",
                cid,
                capability
            )



    def get(
        self,
        capability_id
    ):


        return self.capabilities.get(
            capability_id
        )



    def exists(
        self,
        capability_id
    ):


        return capability_id in self.capabilities