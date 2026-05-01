#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import sys
import tty
import termios

ARROW_UP    = "\x1b[A"
ARROW_DOWN  = "\x1b[B"
ARROW_RIGHT = "\x1b[C"
ARROW_LEFT  = "\x1b[D"
SPACE       = " "
RETRACE_KEY = "r"
SPEED_UP    = "+"
SPEED_DOWN  = "-"
QUIT        = "q"

MIN_SPEED = 0
MAX_SPEED = 8

MSG = """
+======================================+
|      ESP32 Arrow Key Teleop          |
+======================================+
|   UP    = Forward                    |
|   DOWN  = Backward                   |
|   LEFT  = Turn Left                  |
|   RIGHT = Turn Right                 |
|  SPACE  = Stop                       |
|    r    = Retrace path               |
|    +    = Speed Up   (step 2)        |
|    -    = Speed Down (step 2)        |
|    q    = Quit                       |
+======================================+
"""


class ArrowTeleop(Node):
    def __init__(self):
        super().__init__("arrow_teleop")
        self.pub   = self.create_publisher(Twist, "/cmd_vel", 10)
        self.speed = 4
        self.get_logger().info("Arrow Teleop ready.")

    def get_key(self):
        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch += sys.stdin.read(2)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def send(self, lin=0.0, ang=0.0, retrace=False):
        msg = Twist()
        msg.linear.x  = float(lin)
        msg.angular.z = float(ang)
        msg.linear.y  = float(self.speed)        # speed level 0-8
        msg.linear.z  = 1.0 if retrace else 0.0  # retrace flag
        self.pub.publish(msg)

    def run(self):
        print(MSG)
        print("Speed: {}/8".format(self.speed), end="", flush=True)

        while rclpy.ok():
            key = self.get_key()

            if   key == ARROW_UP:    self.send( 1.0,  0.0); action = "FORWARD"
            elif key == ARROW_DOWN:  self.send(-1.0,  0.0); action = "BACKWARD"
            elif key == ARROW_LEFT:  self.send( 0.0,  1.0); action = "LEFT"
            elif key == ARROW_RIGHT: self.send( 0.0, -1.0); action = "RIGHT"
            elif key == SPACE:       self.send();            action = "STOP"
            elif key == RETRACE_KEY: self.send(retrace=True); action = "RETRACE"
            elif key == SPEED_UP:
                self.speed = min(self.speed + 2, MAX_SPEED)
                self.send()
                action = "SPEED UP -> {}/8".format(self.speed)
            elif key == SPEED_DOWN:
                self.speed = max(self.speed - 2, MIN_SPEED)
                self.send()
                action = "SPEED DOWN -> {}/8".format(self.speed)
            elif key in (QUIT, "\x03"):
                self.send()
                print("\nQuitting...")
                break
            else:
                continue

            print("\rAction: {:30s} | Speed: {}/8  ".format(action, self.speed),
                  end="", flush=True)


def main(args=None):
    rclpy.init(args=args)
    node = ArrowTeleop()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.send()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
