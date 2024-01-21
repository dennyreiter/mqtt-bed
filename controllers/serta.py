import pygatt


class sertaBLEController:
    def __init__(self, addr):
        self.addr = addr
        self.manufacturer = "Serta"
        self.model = "Motion Perfect III"
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
        self.adapter = pygatt.GATTToolBackend()

    def send_command(self, name):
        cmd = self.commands.get(name, None)
        if cmd is None:
            raise Exception("Command not found: " + str(name))
        try:
            self.adapter.start()
            device = self.adapter.connect(self.addr)
            res = device.char_write_handle(0x0020, bytes.fromhex(cmd))
        finally:
            self.adapter.stop()
        return res
