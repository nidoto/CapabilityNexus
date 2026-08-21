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

    def unregister(self, capability_id):
        """移除已注册的能力（精确 id 或通配模式前缀均可）。

        返回是否实际移除了某条记录。
        """
        removed = False
        if capability_id in self.registry:
            del self.registry[capability_id]
            removed = True

        # 通配模式以 "*" 结尾，存储为 prefix；按 "prefix*" 或裸 prefix 均可移除。
        if capability_id.endswith("*"):
            prefix = capability_id[:-1]
        else:
            prefix = capability_id
        if prefix in self.patterns:
            del self.patterns[prefix]
            removed = True

        return removed

    def list(self):
        return self.registry

    def list_all(self):
        result = dict(self.registry)
        for prefix, info in self.patterns.items():
            result[prefix + "*"] = info
        return result
