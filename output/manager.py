import json
import os


class OutputDeviceManager:

    #
    # 输出设备管理器：
    # 管理用户启用的虚拟输出设备（可多个并存）。
    #
    # config/outputs.json:
    #   { "outputs": [ { "id": "virtual_x360", "type": "xinput", "name": "..." } ] }
    #

    BACKENDS = {
        "xinput": "output.virtual_xinput.VirtualXInput",
        "keyboard": "output.virtual_keyboard.VirtualKeyboard",
        "mouse": "output.virtual_mouse.VirtualMouse",
        "ds4": "output.virtual_ds4.VirtualDS4",
    }

    def __init__(self, config_path=None, event_bus=None):
        self.config_path = config_path or os.path.join("config", "outputs.json")
        self.event_bus = event_bus

        self.outputs = []
        self._instances = {}

    def load(self):
        if not os.path.exists(self.config_path):
            self.outputs = []
            return self.outputs

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.outputs = data.get("outputs", [])
        return self.outputs

    def save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"outputs": self.outputs}, f, ensure_ascii=False, indent=4)

    def add(self, output_id, output_type, name=None):
        self.outputs.append({
            "id": output_id,
            "type": output_type,
            "name": name or output_id,
        })
        self.save()

    def remove(self, output_id):
        self.outputs = [o for o in self.outputs if o.get("id") != output_id]
        self.save()

    def get_config(self, output_id):
        for o in self.outputs:
            if o.get("id") == output_id:
                return o
        return None

    def instantiate(self, config):
        backend_path = self.BACKENDS.get(config.get("type"))

        if not backend_path:
            print("[OutputManager] Unknown output type:", config.get("type"))
            return None

        module_name, class_name = backend_path.rsplit(".", 1)

        try:
            import importlib

            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)

            instance = cls()
            return instance
        except Exception as e:
            print("[OutputManager] Instantiate failed:", config.get("id"), e)
            return None

    def build_all(self):
        self._instances = {}

        for config in self.outputs:
            instance = self.instantiate(config)

            if instance:
                self._instances[config["id"]] = instance

        return self._instances

    def get_instance(self, output_id):
        return self._instances.get(output_id)

    def close_all(self):
        for instance in self._instances.values():
            try:
                instance.close()
            except Exception:
                pass

        self._instances = {}
