#!/usr/bin/env python3
import logging

from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B, SpeedPercent, MoveTank
from ev3dev2.sensor import INPUT_1
from ev3dev2.sensor.lego import TouchSensor
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

def command_drive(directions):
    logging.info("Driving")
    tank_drive = MoveTank(OUTPUT_A, OUTPUT_B)
    tank_drive.on(SpeedPercent(100),SpeedPercent(100))

class Logic:

    def __init__(self):
        self.current = None
        self.conn = None

    async def read_messages(self):
        url = "ws://localhost:9000/robot"
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
                command_drive(self.current)
                self.conn.write_message("DONE")
            else:
                logging.info("UNKNOWN: %s" % self.current)

def main():
    logging.info("hello from robot")

    logic = Logic()
    logic_processing = tornado.ioloop.PeriodicCallback(logic.run, 1000)
    tornado.ioloop.IOLoop.current().spawn_callback(logic.read_messages)
    logic_processing.start()
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
