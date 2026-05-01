#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import socket
import threading

ESP32_IP   = "192.168.4.1"
ESP32_PORT = 8080


class ESP32Bridge(Node):
    def __init__(self):
        super().__init__("esp32_bridge")

        self.declare_parameter("esp32_ip",   ESP32_IP)
        self.declare_parameter("esp32_port", ESP32_PORT)

        self.ip   = self.get_parameter("esp32_ip").value
        self.port = self.get_parameter("esp32_port").value

        self.sock      = None
        self.connected = False
        self.lock      = threading.Lock()

        self.connect()

        self.create_subscription(Twist, "/cmd_vel", self.cmd_vel_callback, 10)
        self.create_timer(2.0, self.watchdog)

        self.get_logger().info("ESP32 Bridge -> {}:{}".format(self.ip, self.port))

    def connect(self):
        try:
            self.get_logger().info("Connecting to ESP32...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect((self.ip, self.port))
            s.settimeout(None)
            with self.lock:
                self.sock      = s
                self.connected = True
            self.get_logger().info("Connected!")
        except Exception as e:
            self.get_logger().error("Connection failed: {}".format(e))
            self.connected = False

    def watchdog(self):
        if not self.connected:
            self.get_logger().warn("Watchdog: reconnecting...")
            self.connect()

    def send_raw(self, packet):
        with self.lock:
            if not self.connected or self.sock is None:
                self.get_logger().warn("Not connected — dropping packet")
                return
            try:
                self.sock.sendall(packet.encode("utf-8"))
                self.get_logger().info("Sent: {}".format(packet.strip()))
            except Exception as e:
                self.get_logger().error("Send error: {}".format(e))
                self.connected = False

    def cmd_vel_callback(self, msg):
        lin     = msg.linear.x
        ang     = msg.angular.z
        speed   = msg.linear.y           # 0-8 speed level
        retrace = msg.linear.z == 1.0    # retrace flag

        flag   = "RETRACE" if retrace else ""
        # Packet format: "lin,ang,speed,flag\n"  (4 fields — ESP32 requires all 4)
        packet = "{:.3f},{:.3f},{:.0f},{}\n".format(lin, ang, speed, flag)
        self.send_raw(packet)

    def destroy_node(self):
        self.send_raw("0.000,0.000,0,\n")   # safe stop
        if self.sock:
            self.sock.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ESP32Bridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
