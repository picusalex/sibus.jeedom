import re

import requests
import json
import logging
from deepdiff import DeepDiff

logger = logging.getLogger()

#################################################################################################
class JeedomJSONRPCWrapper():
    def __init__(self):
        self.previous_jeedom_objects = []
        self.jeedom_url = "http://rasp-jeedom/core/api/jeeApi.php"
        self.jeedom_key = "UdGGJS71NwBT4Oghp9fuLyBCqlPIaVRF"

    def rpc_request(self, method, params={}):

        params["apikey"] =  self.jeedom_key
        headers = {'content-type': 'application/json'}

        payload = {
            "method": method,
            "jsonrpc": "2.0",
            "id": 1,
            "params": params
        }
        response = requests.post(self.jeedom_url, data=json.dumps(payload), headers=headers)
        json_reponse = response.json()

        try:
            return json_reponse["result"]
        except:
            pass

    def get_jeedom_changes(self, callback=None):
        self.current_jeedom_objects = self.rpc_request("object::full")

        ddiff_verbose1 = DeepDiff({"result":self.previous_jeedom_objects},
                                  {"result":self.current_jeedom_objects})

        if "values_changed" in ddiff_verbose1:
            for change in ddiff_verbose1["values_changed"]:
                print change
                indexes = re.split(r"\W+", change)[2:-1]
                print len(indexes), indexes

                try:
                    if len(indexes) == 6:
                        object_idx = int(indexes[0])
                        eqLogic_idx = int(indexes[2])
                        command_idx = int(indexes[4])
                        command_key = indexes[5]

                        jeedom_object = self.object_byidx(object_idx=object_idx)
                        jeedom_eqLogic = self.eqLogic_byidx(object_idx=object_idx,
                                                            eqLogic_idx=eqLogic_idx)
                        jeedom_command = self.command_byidx(object_idx=object_idx,
                                                            eqLogic_idx=eqLogic_idx,
                                                            command_idx=command_idx)
                        jeedom_previous = self.command_byidx(object_idx=object_idx,
                                                            eqLogic_idx=eqLogic_idx,
                                                            command_idx=command_idx,
                                                            previous=True)

                        current_value = jeedom_command[command_key]
                        previous_value = jeedom_previous[command_key]

                        logger.info("Jeedom change detected: %s::%s::%s, old=%s, new=%s"%(jeedom_object["name"],
                                                                                          jeedom_eqLogic["name"],
                                                                                          jeedom_command["name"],
                                                                                          str(previous_value),
                                                                                          str(current_value)))
                        if callback is not None:
                            callback(command="%s::%s::%s"%(jeedom_object["name"],jeedom_eqLogic["name"],jeedom_command["name"]),
                                     previous=str(previous_value),
                                     value=str(current_value))

                        pass
                except Exception as e:
                    logger.error("Fail to parse jeedom changes in "+change+" ("+str(e)+")")

        self.previous_jeedom_objects = self.current_jeedom_objects

    def object_byidx(self, object_idx, previous=False):
        if previous is True:
            tmp = self.previous_jeedom_objects
        else:
            tmp = self.current_jeedom_objects

        if object_idx > -1 and object_idx < len(tmp):
            return tmp[object_idx]
        else:
            return None

    def eqLogic_byidx(self, object_idx, eqLogic_idx, previous=False):
        object = self.object_byidx(object_idx=object_idx, previous=previous)
        if object is None:
            return None

        eqLogics = object["eqLogics"]

        if eqLogic_idx > -1 and eqLogic_idx < len(eqLogics):
            return eqLogics[eqLogic_idx]
        else:
            return None

    def command_byidx(self, object_idx, eqLogic_idx, command_idx, previous=False):
        eqLogic = self.eqLogic_byidx(object_idx=object_idx, eqLogic_idx=eqLogic_idx, previous=previous)
        if eqLogic is None:
            return None

        cmds = eqLogic["cmds"]
        if command_idx > -1 and command_idx < len(cmds):
            return cmds[command_idx]
        else:
            return None

    def command_byname(self, name):
        try:
            (object_name, eqLogic_name, command_name) = name.split("::")
        except Exception as e:
            return None

        object = None
        for o in self.current_jeedom_objects:
            if o["name"] == object_name:
                object = o
                break
        if object is None:
            return None

        eqLogic = None
        for e in object["eqLogics"]:
            if e["name"] == eqLogic_name:
                eqLogic = e
                break
        if eqLogic is None:
            return None

        command = None
        for c in eqLogic["cmds"]:
            if c["name"] == command_name:
                command = c
                break

        return command

    def execute_command(self, command_name, value=None):
        command = self.command_byname(command_name)
        if command is None:
            raise Exception("Invalid command name: '%s'"%command_name)

        if command["type"] == "action":
            if value is None:
                self.rpc_request(method="cmd::execCmd", params={
                    "id":command["id"]
                })
            else:
                self.rpc_request(method="cmd::execCmd", params={
                    "id":command["id"],
                    "options":{command["subType"]: value}
                })
            return None
        elif command["type"] == "info":
            result = self.rpc_request(method="cmd::execCmd", params={
                "id": command["id"],
            })
            return result

        return None