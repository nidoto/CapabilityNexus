import json


class AutoRouter:

    #
    # 一键全路由：
    # 把设备的输入能力自动路由到虚拟 x360 输出。
    #
    # 命名约定（能力 id → x360 目标）：
    #   <device>.left_x        -> left_x
    #   <device>.left_y        -> left_y
    #   <device>.right_x       -> right_x
    #   <device>.right_y       -> right_y
    #   <device>.left_trigger  -> left_trigger
    #   <device>.right_trigger -> right_trigger
    #   <device>.a             -> button_a
    #   <device>.b             -> button_b
    #   ...
    #   <device>.dpad_up       -> button_dpad_up
    #
    # 无法自动匹配的能力（如震动马达 motor_*）返回为缺失项，
    # 提示用户手动路由。
    #

    AXIS_MAP = {
        "left_x": "left_x",
        "left_y": "left_y",
        "right_x": "right_x",
        "right_y": "right_y",
        "left_trigger": "left_trigger",
        "right_trigger": "right_trigger",
    }

    BUTTON_MAP = {
        "a": "button_a",
        "b": "button_b",
        "x": "button_x",
        "y": "button_y",
        "lb": "button_lb",
        "rb": "button_rb",
        "ls": "button_ls",
        "rs": "button_rs",
        "start": "button_start",
        "back": "button_back",
        "dpad_up": "button_dpad_up",
        "dpad_down": "button_dpad_down",
        "dpad_left": "button_dpad_left",
        "dpad_right": "button_dpad_right",
    }

    def route(self, capabilities, prefix=None):
        mappings = {}
        missing = []

        for cap in capabilities:
            capability_id = cap.get("id", "")
            category = cap.get("category")

            base = capability_id

            if "." in base:
                base = base.split(".", 1)[1]

            target = self._find_target(base, category)

            if target:
                mappings[capability_id] = {
                    "target": target,
                    "gain": 1.0,
                    "return_to_center": category == "axis",
                }
            else:
                missing.append(capability_id)

        return mappings, missing

    def _find_target(self, base, category):
        if category == "axis":
            if base in self.AXIS_MAP:
                return self.AXIS_MAP[base]

        if category == "button":
            if base in self.BUTTON_MAP:
                return self.BUTTON_MAP[base]

        if category == "trigger":
            if base in self.AXIS_MAP:
                return self.AXIS_MAP[base]

        return None
