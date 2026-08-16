import importlib.util
import os


def load_custom_connection(callback, params):
    #
    # 用户自定义连接方式：
    # 用户写一个 Python 脚本 config/custom_connections.py
    # 提供 build_connection(callback, params) -> LineConnection
    #
    # 示例：
    #   def build_connection(callback, params):
    #       from devices.custom_example import MyConnection
    #       return MyConnection(callback, **params)
    #

    from tools.config_io import PROJECT_ROOT

    script = os.path.join(PROJECT_ROOT, "config", "custom_connections.py")

    if not os.path.exists(script):
        print("[CustomConnection] No config/custom_connections.py found")
        return None

    spec = importlib.util.spec_from_file_location("custom_connections", script)
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print("[CustomConnection] Load failed:", e)
        return None

    builder = getattr(module, "build_connection", None)

    if builder is None:
        print("[CustomConnection] No build_connection() function in script")
        return None

    try:
        return builder(callback, params)
    except Exception as e:
        print("[CustomConnection] Build failed:", e)
        return None
