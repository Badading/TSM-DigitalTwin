from tkinter import ttk, Tk
import tkinter as tk
from asyncua.sync import Client, ThreadLoop
from asyncua import ua


def ua_setter(var, val):
    var.set_value(ua.DataValue(ua.Variant(val, var.get_data_type_as_variant_type())))


class PLC_OPCua:
    instances:list["PLC_OPCua"] = list()
    TLOOP = None
    
    def __init__(self, url:str="opc.tcp://localhost:7000"):
        if not PLC_OPCua.TLOOP:
            PLC_OPCua.TLOOP = ThreadLoop()
            PLC_OPCua.TLOOP.start()
        self._client = Client(tloop=PLC_OPCua.TLOOP, url=url)
        self._url = url
        self._client.connect()
        self._start = self._client.get_node(nodeid='ns=2;s="Start"')
        self._acknowledge = self._client.get_node(nodeid='ns=2;s="Ack"')
        self._busy = self._client.get_node(nodeid='ns=2;s="Busy"')
        self._ready = self._client.get_node(nodeid='ns=2;s="Ready"')
        
        self._order = self._client.get_node(nodeid='ns=2;s="Order"')
        self._msg = self._client.get_node(nodeid='ns=2;s="Msg"')
        
        self._state = 0
        self.__order = 0
        self.msg = 0
        
        self.instances.append(self)
        
    @property
    def order(self):
        return self.__order
        
    @order.setter
    def order(self, value:int):
        if self._state:
            return
        self.__order = value
        self._set_state(1)
        
    def update_state(self):
        self.msg = self._msg.get_value()
        
        if self._state == 1 and self._ready.get_value():
            ua_setter(self._order, self.__order)
            ua_setter(self._start, True)
            if self._acknowledge.get_value():
                self._set_state(2)
        if self._state == 2:
            ua_setter(self._start, False)
            if not self._acknowledge.get_value():
                self._set_state(3)
        if self._state == 3:
            if not self._busy.get_value():
                self._set_state(0)
    
    def _set_state(self, state):
        print(self._url, "State set to:", state)
        self._state = state
    
    def place_order(self, order):
        self.order = order


class Module1(ttk.Frame, PLC_OPCua):
    def __init__(self, master, *args, **kwargs):
        ttk.Frame.__init__(self, master=master, *args, **kwargs)
        PLC_OPCua.__init__(self, url="opc.tcp://localhost:7000")
        
        self.__init_widgets__()
    
    def __init_widgets__(self):
        tk.Button(self, text="Order Blue", command=lambda: self.place_order(1)).grid(row=0, column=0)
        tk.Button(self, text="Order Red", command=lambda: self.place_order(2)).grid(row=1, column=0)
        tk.Button(self, text="Close Stopper", command=lambda: self.place_order(3)).grid(row=2, column=0)
        tk.Button(self, text="Open Stopper", command=lambda: self.place_order(4)).grid(row=3, column=0)
        

class Module2(ttk.Frame, PLC_OPCua):
    def __init__(self, master, *args, **kwargs):
        ttk.Frame.__init__(self, master=master, *args, **kwargs)
        PLC_OPCua.__init__(self, url="opc.tcp://localhost:7001")
        
        self.__init_widgets__()
        
    def __init_widgets__(self):
        tk.Button(self, text="Order Red", command=lambda: self.place_order(1)).grid(row=0, column=0)
        tk.Button(self, text="Order Black", command=lambda: self.place_order(2)).grid(row=1, column=0)
        tk.Button(self, text="Open Stopper", command=lambda: self.place_order(3)).grid(row=2, column=0)
        tk.Button(self, text="Close Stopper", command=lambda: self.place_order(4)).grid(row=3, column=0)
        

class Module3a(ttk.Frame, PLC_OPCua):
    def __init__(self, master, *args, **kwargs):
        ttk.Frame.__init__(self, master=master, *args, **kwargs)
        PLC_OPCua.__init__(self, url="opc.tcp://localhost:7002")
        
        self.__init_widgets__()
        
    def __init_widgets__(self):
        tk.Button(self, text="Order Red", command=lambda: self.place_order(1)).grid(row=0, column=0)
        tk.Button(self, text="Order Blue", command=lambda: self.place_order(2)).grid(row=1, column=0)
        tk.Button(self, text="Order Black", command=lambda: self.place_order(3)).grid(row=2, column=0)
        
        tk.Button(self, text="Open Stopper RFID", command=lambda: self.place_order(4)).grid(row=3, column=0)
        tk.Button(self, text="Close Stopper RFID", command=lambda: self.place_order(5)).grid(row=4, column=0)
        
        tk.Button(self, text="Open Stopper Auslauf", command=lambda: self.place_order(6)).grid(row=5, column=0)
        tk.Button(self, text="Close Stopper Auslauf", command=lambda: self.place_order(7)).grid(row=6, column=0)
        
        tk.Button(self, text="Open Stopper Einlauf", command=lambda: self.place_order(8)).grid(row=7, column=0)
        tk.Button(self, text="Close Stopper Einlauf", command=lambda: self.place_order(9)).grid(row=8, column=0)


class Module3b(ttk.Frame, PLC_OPCua):
    def __init__(self, master, *args, **kwargs):
        ttk.Frame.__init__(self, master=master, *args, **kwargs)
        PLC_OPCua.__init__(self, url="opc.tcp://localhost:7003")
        
        self.__init_widgets__()
        
    def __init_widgets__(self):
        tk.Button(self, text="Order Red", command=lambda: self.place_order(1)).grid(row=0, column=0)
        tk.Button(self, text="Order Blue", command=lambda: self.place_order(2)).grid(row=1, column=0)
        tk.Button(self, text="Order Black", command=lambda: self.place_order(3)).grid(row=2, column=0)


if __name__ == "__main__":
    root = Tk()
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    
    Module1(master=root).grid(row=0, column=0, sticky="NSEW")
    Module2(master=root).grid(row=0, column=1, sticky="NSEW")
    Module3a(master=root).grid(row=0, column=2, sticky="NSEW")
    Module3b(master=root).grid(row=0, column=3, sticky="NSEW")
    
    def update_opc():
        for x in PLC_OPCua.instances:
            x.update_state()
        root.after(100, update_opc)
        
    update_opc()
    root.mainloop()
    