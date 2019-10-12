#!/usr/bin/env python3
import logging
import os

from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B, SpeedPercent, MoveTank
from ev3dev2.sensor import INPUT_1
from ev3dev2.sensor.lego import TouchSensor, ColorSensor
from ev3dev2.led import Leds

from tornado.websocket import websocket_connect
import tornado.ioloop
from tornado.log import enable_pretty_logging
enable_pretty_logging()

import json

def command_stop():
    logging.info("Stopping")
    tank_drive = MoveTank(OUTPUT_A, OUTPUT_B)
    tank_drive.stop()

def command_followline():
    logging.info("Follow line")
    tank_drive = MoveTank(OUTPUT_A, OUTPUT_B)
    tank_drive.cs = ColorSensor()
    tank_drive.follow_line(kp=11.3, ki=0.05, kd=3.2,
        speed=SpeedPercent(30),)

def command_drive(keys):
    logging.info("Driving")
    tank_drive = MoveTank(OUTPUT_A, OUTPUT_B)
    directions = json.loads(keys)
    a_speed = 0
    b_speed = 0
    if "up" in directions:
        if "left" in directions:
            a_speed = SpeedPercent(50)
            b_speed = SpeedPercent(100)
        elif "right" in directions:
            a_speed = SpeedPercent(100)
            b_speed = SpeedPercent(50)
        else:
            a_speed = SpeedPercent(100)
            b_speed = SpeedPercent(100)
    elif "down" in directions:
        if "left" in directions:
            a_speed = SpeedPercent(-50)
            b_speed = SpeedPercent(-100)
        elif "right" in directions:
            a_speed = SpeedPercent(-100)
            b_speed = SpeedPercent(-50)
        else:
            a_speed = SpeedPercent(-100)
            b_speed = SpeedPercent(-100)
    elif "left" in directions:
        a_speed = SpeedPercent(-50)
        b_speed = SpeedPercent(100)
    elif "right" in directions:
        a_speed = SpeedPercent(100)
        b_speed = SpeedPercent(-50)
    tank_drive.on(a_speed,b_speed)

class Logic:

    def __init__(self):
        self.current = None
        self.conn = None
        self.colour_sensor = ColorSensor()

    async def read_messages(self):
        address = os.environ['ROBOT_BRAIN']
        url = "ws://%s:9000/robot" % address
        self.conn = await websocket_connect(url)
        while True:
            msg = await self.conn.read_message()
            if msg is None: break
            if msg.startswith("COMMAND:"):
                command = msg.replace("COMMAND: ", "")
                self.current = command
            else:
                logging.info("< %s" % msg)

    def run(self):
        if self.current:
            if self.current == "STOP":
                command_stop()
                self.conn.write_message("DONE")
            elif self.current.startswith("DRIVE"):
                command_drive(self.current.split(":")[1])
                self.conn.write_message("DONE")
            elif self.current == "FOLLOWLINE":
                command_followline()
                self.conn.write_message("DONE")
            else:
                logging.info("UNKNOWN: %s" % self.current)
            self.current = None

    def send_colour(self):
        if self.conn:
            colour = self.colour_sensor.reflected_light_intensity
            self.conn.write_message("COLOUR:%s" % colour)

def main():
    logging.info("hello from robot")

    logic = Logic()
    logic_processing = tornado.ioloop.PeriodicCallback(logic.run, 100)
    colour_processing = tornado.ioloop.PeriodicCallback(logic.send_colour, 100)
    tornado.ioloop.IOLoop.current().spawn_callback(logic.read_messages)
    logic_processing.start()
    colour_processing.start()
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
