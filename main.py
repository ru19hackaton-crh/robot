#!/usr/bin/env python3
import logging
import os

from ev3dev2.auto import *

from tornado.websocket import websocket_connect
import tornado.ioloop
from tornado.log import enable_pretty_logging
enable_pretty_logging()

import json
from datetime import timedelta

def command_stop():
    logging.info("Stopping")
    tank_drive = MoveTank(OUTPUT_A, OUTPUT_B)
    tank_drive.stop()

def command_drive_to_maze():
    logging.info("Driving to maze")
    tank_drive = MoveTank(OUTPUT_A, OUTPUT_B)
    tank_drive.on_for_seconds(SpeedPercent(100),SpeedPercent(100), 5)

def command_drive_on_white():
    logging.info("Driving on white")
    tank_drive = MoveTank(OUTPUT_A, OUTPUT_B)
    tank_drive.on(SpeedPercent(100),SpeedPercent(100))

def command_find_white():
    logging.info("Find white")
    tank_drive = MoveTank(OUTPUT_A, OUTPUT_B)
    tank_drive.on_for_rotations(SpeedPercent(10),SpeedPercent(30), 1)
    tank_drive.on_for_rotations(SpeedPercent(30),SpeedPercent(10), 1)

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

def limits(val):
    if val > 100:
        return 100
    elif val < -100:
        return -100
    return val

class Logic:

    def __init__(self):
        self.current = None
        self.conn = None
        self.colour_sensor = ColorSensor()
        self.pid = tornado.ioloop.PeriodicCallback(self.linefollow,10)
        self.initPID()
        self.left_motor = LargeMotor(OUTPUT_A)
        self.right_motor = LargeMotor(OUTPUT_B)

    def initPID(self):
        self.Kp = 350
        self.Ki = 9
        self.Kd = 1000
        self.offset = 45
        self.Tp = 30
        self.integral = 0
        self.lastError = 0
        self.derivative = 0

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
            elif self.current == "DRIVE_TO_MAZE":
                command_drive_to_maze()
                tornado.ioloop.IOLoop.current().add_timeout(timedelta(seconds=5), self.send_done)
            elif self.current == "FOLLOWLINE":
                self.left_motor.run_direct()
                self.right_motor.run_direct()
                self.pid.start()
            elif self.current == "STOPFOLLOWLINE":
                self.pid.stop()
                self.initPID()
                self.left_motor.stop()
                self.right_motor.stop()
            elif self.current == "DRIVE_ON_WHITE":
                command_drive_on_white()
            elif self.current == "FIND_WHITE":
                command_find_white()
            elif self.current.startswith("DRIVE"):
                command_drive(self.current.split(":")[1])
            else:
                logging.info("UNKNOWN: %s" % self.current)
            self.current = None

    def send_done(self):
        logging.info("Done")
        self.conn.write_message("DONE")

    def linefollow(self):
        LightValue = self.colour_sensor.reflected_light_intensity
        error = LightValue - self.offset
        self.integral = self.integral + error
        self.derivative = error - self.lastError
        Turn = self.Kp * error + self.Ki*self.integral + self.Kd*self.derivative
        Turn = Turn / 100
        powerA = self.Tp + Turn
        powerB = self.Tp - Turn
        self.left_motor.duty_cycle_sp = limits(powerA)
        self.right_motor.duty_cycle_sp = limits(powerB)
        self.lastError = error

    def send_colour(self):
        if self.conn:
            colour = self.colour_sensor.reflected_light_intensity
            self.conn.write_message("COLOUR:%s" % colour)

def main():
    logging.info("hello from robot")

    logic = Logic()
    logic_processing = tornado.ioloop.PeriodicCallback(logic.run, 10)
    colour_processing = tornado.ioloop.PeriodicCallback(logic.send_colour, 10)
    tornado.ioloop.IOLoop.current().spawn_callback(logic.read_messages)
    logic_processing.start()
    colour_processing.start()
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
