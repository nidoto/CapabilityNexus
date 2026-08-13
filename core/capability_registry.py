class CapabilityRegistry:


    def __init__(self):

        self.registry = {}



    def register(
        self,
        package_name,
        capability
    ):

        capability_id = capability["id"]


        self.registry[capability_id] = {

            "package": package_name,

            "definition": capability

        }


        print(

            "[Capability Registered]",

            capability_id,

            "from",

            package_name

        )



    def get(
        self,
        capability_id
    ):

        return self.registry.get(
            capability_id
        )



    def exists(
        self,
        capability_id
    ):

        return capability_id in self.registry



    def list(
        self
    ):

        return self.registry