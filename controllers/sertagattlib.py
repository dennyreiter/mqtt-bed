from gattlib import GATTRequester


class Requester(GATTRequester):
    def on_notification(self, handle, data):
        return


class sertaBLEController:
    def __init__(self, addr, pretend=False):
        self.pretend = pretend
        self.addr = addr
        self.commands = {
            "Flat Preset": "e5fe1600000008fe",
            "ZeroG Preset": "e5fe1600100000f6",
            "TV Preset": "e5fe1600400000c6",
            "Head Up Preset": "e5fe160080000086",
            "Lounge Preset": "e5fe1600200000e6",
            "Massage Head Add": "e5fe1600080000fe",
            "Massage Head Min": "e5fe160000800086",
            "Massage Foot Add": "e5fe160004000002",
            "Massage Foot Min": "e5fe160000000105",
            "Head and Foot Massage On": "e5fe160001000005",
            "Massage Timer": "e5fe160002000004",
            "Lift Head": "e5fe160100000005",
            "Lower Head": "e5fe160200000004",
            "Lift Foot": "e5fe160400000002",
            "Lower Foot": "e5fe1608000000fe",
        }

    def sendCommand(self, name):
        self.req = Requester(self.addr)
        #        if not self.req.is_connected():
        #            self.req.connect(True)
        cmd = self.commands.get(name, None)
        if cmd is None:
            raise Exception("Command not found: " + str(name))

        if self.pretend:
            (" ".join(cmd_args))
            res = 0
        else:
            res = self.req.write_by_handle(0x0020, bytes.fromhex(cmd))
        #        self.req.disconnect()
        del self.req
        return res
