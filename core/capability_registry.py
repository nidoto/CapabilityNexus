class CapabilityRegistry:

    def __init__(self):
        self.registry = {}
        self.patterns = {}

    def register(self, package_name, capability):
        capability_id = capability["id"]

        if capability_id.endswith("*"):
            prefix = capability_id[:-1]
            self.patterns[prefix] = {
                "package": package_name,
                "definition": capability,
            }
            print(
                "[Capability Pattern]",
                capability_id,
                "from",
                package_name,
            )
        else:
            self.registry[capability_id] = {
                "package": package_name,
                "definition": capability,
            }
            print(
                "[Capability Registered]",
                capability_id,
                "from",
                package_name,
            )

    def get(self, capability_id):
        if capability_id in self.registry:
            return self.registry[capability_id]

        for prefix, info in self.patterns.items():
            if capability_id.startswith(prefix):
                definition = dict(info["definition"])
                definition["id"] = capability_id
                return {
                    "package": info["package"],
                    "definition": definition,
                }

        return None

    def exists(self, capability_id):
        return self.get(capability_id) is not None

    def list(self):
        return self.registry

    def list_all(self):
        result = dict(self.registry)
        for prefix, info in self.patterns.items():
            result[prefix + "*"] = info
        return result
