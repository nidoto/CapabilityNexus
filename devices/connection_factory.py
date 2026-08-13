from devices.serial_connection import SerialConnection
from devices.tcp_connection import TcpConnection
from devices.udp_connection import UdpConnection


class ConnectionFactory:

    @staticmethod
    def create(callback, params):
        connection_type = params.get("type", "serial")

        if connection_type == "serial":
            return SerialConnection(
                callback,
                port=params.get("port"),
                baudrate=params.get("baudrate", 115200),
            )

        if connection_type == "tcp":
            return TcpConnection(
                callback,
                host=params.get("host"),
                port=params.get("port"),
            )

        if connection_type == "udp":
            return UdpConnection(
                callback,
                host=params.get("host", "0.0.0.0"),
                port=params.get("port", 8888),
            )

        if connection_type == "bluetooth":
            from devices.bluetooth_connection import BluetoothConnection

            return BluetoothConnection(
                callback,
                device=params.get("device"),
                channel=params.get("channel", 1),
            )

        if connection_type == "custom":
            from devices.custom_connection import load_custom_connection

            connection = load_custom_connection(callback, params.get("params", {}))
            if connection is None:
                raise Exception("Custom connection not configured")
            return connection

        raise Exception(f"Unknown connection type: {connection_type}")
