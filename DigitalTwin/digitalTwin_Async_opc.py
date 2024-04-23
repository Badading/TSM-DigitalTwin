from asyncua.sync import Server, ThreadLoop
from asyncua import ua

class PLC_OPCua:
    instances = list()
    TLOOP = None
    
    def __init__(self, name:str, endpoint:str="opc.tcp://localhost:7000"):
        if not PLC_OPCua.TLOOP:
            PLC_OPCua.TLOOP = ThreadLoop()
            PLC_OPCua.TLOOP.start()
        self._server = Server(tloop=PLC_OPCua.TLOOP)
        self._server.set_security_policy([
                        ua.SecurityPolicyType.NoSecurity,
                        ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
                        ua.SecurityPolicyType.Basic256Sha256_Sign])
        self._server.set_server_name(name)
        self._server.set_endpoint(endpoint)
        self._server.register_namespace("PLC_OPC")
        hs = self._server.nodes.objects.add_object('ns=2;s="HS"', "Handshake")
        
        self._start = hs.add_variable('ns=2;s="Start"', "start", False)
        self._ack = hs.add_variable('ns=2;s="Ack"', "ack", False)
        self._busy = hs.add_variable('ns=2;s="Busy"', "busy", False)
        self._ready = hs.add_variable('ns=2;s="Ready"', "ready", False)
        
        self._order = hs.add_variable('ns=2;s="Order"', "order", 0)
        self._msg = hs.add_variable('ns=2;s="Msg"', "msg", 0)
        
        self._start.set_writable()
        self._order.set_writable()
        
        self._state:int = 0

        self.order:int = 0
        self.start:bool = False
        
        self.msg:int = 0
        self.ack:bool = False
        self.busy:bool = False
        self.ready:bool = False
        
        self._server.start()
        PLC_OPCua.instances.append(self)
        
    def update_opc(self):
        self._ack.set_value(self.ack)
        self._busy.set_value(self.busy)
        self._ready.set_value(self.ready)
        self._msg.set_value(self.msg)
        
        self.start = self._start.get_value()
        
        self._handshake()
    
    def _handshake(self):
        if self._order.get_value() == 11:  # Reset handshake without Start
            self._state = 0
            
        if self.start and not self.busy and self.ready and not self._state:
            self.ack = True
            self.order = self._order.get_value()
            self.busy = True
            self._state = 1
            
        if self._state == 1 and not self.start:
            self.ack = False
            self._state = 2
        
        if self._state == 2 and not self.busy:
            self._state = 0
            self.order = 0
        
    def remove(self):
        self._server.stop()  # check if this has to be moved to __del__
        PLC_OPCua.instances.remove(self)
        if not PLC_OPCua.instances:  # shut down shared Async thread
            PLC_OPCua.TLOOP.stop()  # <-- blocking operation
            PLC_OPCua.TLOOP = None
            
