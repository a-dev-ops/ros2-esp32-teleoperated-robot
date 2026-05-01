from setuptools import setup
import os
from glob import glob

package_name = "esp32_robot"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages",
            ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"),
            glob("launch/*.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    entry_points={
        "console_scripts": [
            "esp32_bridge = esp32_robot.esp32_bridge:main",
	    "arrow_teleop  = esp32_robot.arrow_teleop:main"
        ],
    },
)
