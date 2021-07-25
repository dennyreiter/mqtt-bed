
import pygatt

class jiecangBLEController:
    def __init__(self, addr):
        self.addr = addr
        self.commands = {
            "Memory 1": "f1f10b01010d7e",
            "Memory 2": "f1f10d01010f7e",
            "Flat": "f1f10801010a7e",
            "Zero G": "f1f1070101097e",
        }
        self.adapter = pygatt.GATTToolBackend()

    def sendCommand(self, name):
        cmd = self.commands.get(name, None)
        if cmd is None:
            raise Exception("Command not found: " + str(name))
        try:
            self.adapter.start()
            device = self.adapter.connect(self.addr)
            res = device.char_write('0000ff01-0000-1000-8000-00805f9b34fb', bytes.fromhex(cmd), wait_for_response=False)
        finally:
            self.adapter.stop()
        return res

   
