import rclpy
from rclpy.node import Node

import cv2
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


PHONE_STREAM="http://192.168.1.105:8080/video"
# replace with your phone IP


class PhoneCam(Node):

    def __init__(self):
        super().__init__("phone_cam")

        self.pub = self.create_publisher(
            Image,
            "/camera/image_raw",
            10
        )

        self.bridge= CvBridge()

        self.cap = cv2.VideoCapture(
            PHONE_STREAM
        )

        self.create_timer(
            0.05,
            self.publish_frame
        )

    def publish_frame(self):

        ret,frame=self.cap.read()

        if ret:
            msg=self.bridge.cv2_to_imgmsg(
                frame,
                encoding="bgr8"
            )

            self.pub.publish(msg)


def main():
    rclpy.init()
    node=PhoneCam()
    rclpy.spin(node)

if __name__=="__main__":
    main()