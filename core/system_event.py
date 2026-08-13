from dataclasses import dataclass



@dataclass
class OutputEvent:

    target:str

    value:float



@dataclass
class DeviceRequestEvent:

    #
    # 游戏/外部应用对虚拟设备的请求（如震动）
    # source: 请求来源虚拟设备（如 "virtual_x360"）
    # target: 请求的能力名（如 "xbox.motor_left"）
    # value:  请求强度（0~65535）
    #

    source: str

    target: str

    value: float