#!/usr/bin/env python
# -*- coding: utf-8 -*-

import signal
import sys
import time

from sibus_lib import BusElement, sibus_init, MessageObject
from jeedom_wrapper import JeedomJSONRPCWrapper

SERVICE_NAME = "sibus.jeedom"
logger, cfg_data = sibus_init(SERVICE_NAME)

def on_busmessage(message):
    logger.info(message)
    data = message.get_data()

    command_path = data["command"]
    if "value" in data:
        value = data["value"]
    else:
        value = None

    try:
        result = wrapper.execute_command(command_path, value)
    except Exception as e:
        message = MessageObject(data={
            "error": e.message
        }, topic="error.jeedom.command")
        busclient.publish(message)
        return

    if result is not None:
        publish_sibus(command_path, result["value"])

    pass


wrapper = JeedomJSONRPCWrapper()

busclient = BusElement(SERVICE_NAME, callback=on_busmessage)
busclient.register_topic("request.jeedom.command")
busclient.start()

def publish_sibus(command, value, previous=None):
    message = MessageObject(data={
        "command": command,
        "value": value,
        "previous": previous
    }, topic="info.jeedom.change")
    busclient.publish(message)

def sigterm_handler(_signo=None, _stack_frame=None):
    busclient.stop()
    logger.info("Program terminated correctly")
    sys.exit(0)

signal.signal(signal.SIGTERM, sigterm_handler)



try:
    while 1:
        wrapper.get_jeedom_changes(callback=publish_sibus)
        time.sleep(2)
except KeyboardInterrupt:
    logger.info("Ctrl+C detected !")
except Exception as e:
    busclient.stop()
    logger.exception("Program terminated incorrectly ! " + str(e))
    sys.exit(1)
finally:
    sigterm_handler()
