from digitalTwin_base import Vector, Entity, World, Orientation, TIMINGS
from digitalTwin_Entities import Stopper, Wall, Stack, Conveyer, Sensor, Spawner, Picker, PLC, PLC_OPCua

from pathlib import Path
import json

from tkinter import Tk, ttk, filedialog
import tkinter as tk

import cProfile, pstats, io
from pstats import SortKey
import time


class SaveFileEncoder(json.JSONEncoder):
    special_serializers = {Vector: lambda x: x.__repr__()}

    def default(self, o):
        if hasattr(o, '_to_json'):
            return o._to_json()
        elif type(o) in self.__class__.special_serializers.keys():
            return self.__class__.special_serializers[type(o)](o)


def debug(world):
    Conveyer(parent=world, pos=Vector(100,100), length=100, speed=3, orientation=Orientation.EAST)
    Conveyer(parent=world, pos=Vector(220,100), length=100, speed=1, orientation=Orientation.SOUTH)
    Conveyer(parent=world, pos=Vector(220,220), length=100, speed=2, orientation=Orientation.WEST)
    Conveyer(parent=world, pos=Vector(100,220), length=100, speed=1, orientation=Orientation.NORTH)
    
    Wall(parent=world, pos=Vector(120,120), size=Vector(80, 80))
    Wall(parent=world, pos=Vector(97,200), size=Vector(3, 20))
    
    Stopper(parent=world, pos=Vector(180, 70), orientation=Orientation.EAST)
    Stopper(parent=world, pos=Vector(100, 50), orientation=Orientation.SOUTH)
    Stopper(parent=world, pos=Vector(150, 50), orientation=Orientation.WEST)
    Stopper(parent=world, pos=Vector(200, 50), orientation=Orientation.NORTH)
    
    Sensor(parent=world, pos=Vector(155,80), orientation=Orientation.EAST)
    
    Stack(parent=world, pos=Vector(130, 110)).dont_save = False
    Stack(parent=world, pos=Vector(155, 110)).dont_save = False
    Stack(parent=world, pos=Vector(180, 110)).dont_save = False
    
    Spawner(parent=world, pos=Vector(77, 150), orientation=Orientation.EAST)
    Spawner(parent=world, pos=Vector(200, 300), orientation=Orientation.WEST)
    Spawner(parent=world, pos=Vector(100, 400), orientation=Orientation.SOUTH)
    Spawner(parent=world, pos=Vector(200, 400), orientation=Orientation.NORTH)
    
    Picker(parent=world, pos=Vector(200, 90), length=100, orientation=Orientation.EAST)


class Simulation(tk.Frame):
    def __init__(self, master:tk.Frame):
        tk.Frame.__init__(self, master=master)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(self)
        self.canvas.grid(row=0, column=0, sticky="NSEW")
        self.world = World(self.canvas)
        
        self.profiler = None
        self.profiler_ticks = 0
        
        self.mouse_select_pos:Vector = None
        self.mouse_selection:Entity = None
        self.mouse_pos_str:tk.StringVar = tk.StringVar(self)
        self.timing_info:tk.StringVar = tk.StringVar(self)
        
        f = tk.Frame(master=self)
        f.grid(row=1, column=0, sticky="SEW")
        f.columnconfigure(100, weight=1)
        tk.Label(master=f, textvariable=self.mouse_pos_str).grid(row=0, column=101, sticky="SE")
        tk.Label(master=f, textvariable=self.timing_info, anchor="w", justify="left", width=20).grid(row=0, column=102, sticky="SE")
        tk.Button(master=f, text="Save", command=self.save).grid(row=0, column=0, sticky="SW")
        tk.Button(master=f, text="Load", command=self.load).grid(row=0, column=1, sticky="SW")
        tk.Button(master=f, text="Clear", command=self.clear).grid(row=0, column=2, sticky="SW")
        tk.Button(master=f, text="Debug", command=lambda: debug(self.world)).grid(row=0, column=50, sticky="SW")
        tk.Button(master=f, text="Start/Stop Profiler", command=self.enable_profiler).grid(row=0, column=51, sticky="SW")
        self.canvas.bind('<Motion>', self.motion)
        self.canvas.bind('<Button-1>', self.button_1)  # left click
        self.canvas.bind('<Button-3>', self.button_3)  # right click
        self.canvas.bind('<Up>', self.button_up)
        self.canvas.bind('<Down>', self.button_down)
        self.canvas.bind('<Left>', self.button_left)
        self.canvas.bind('<Right>', self.button_right)
        
        # self.canvas.bind('<KeyPress>', self.key_down)
        
    def enable_profiler(self):
        if not self.profiler:
            self.profiler = cProfile.Profile()
            self.profiler.enable()
            self.profiler_ticks = 1000
            print("Profiler Started")
    
    def disable_profiler(self):
        if self.profiler:
            self.profiler.disable()
            s = io.StringIO()
            sortby = SortKey.CUMULATIVE
            ps = pstats.Stats(self.profiler, stream=s).sort_stats(sortby)
            ps.print_stats()
            with open("profiler_stats.log", "w") as f:
                f.write(s.getvalue())
            self.profiler = None
            self.profiler_ticks = 0
            print("Profiler Output Saved")
        
    def key_down(self, event):
        print(event.char)

    def motion(self, event):
        self.mouse_pos = Vector(event.x, event.y)
        self.mouse_pos_str.set(f"x: {event.x}  y: {event.y}")
        
        if self.mouse_selection:
            self.mouse_selection.pos = self.mouse_pos
            self.mouse_selection.update()
            
    def button_1(self, event):
        self.mouse_pos = Vector(event.x, event.y)
        if self.mouse_selection:
            self.mouse_selection = None
            self.mouse_select_pos = None
        else:
            for entity in self.world.children:
                if (self.mouse_pos-entity.pos).length < 5:
                    self.mouse_select_pos = entity.pos
                    self.mouse_selection = entity
                    
    def button_3(self, event):
        self.mouse_pos = Vector(event.x, event.y)
        for entity in self.world.children:
                if (self.mouse_pos-entity.pos).length > 5:
                    continue
                if isinstance(entity, Stopper):
                    entity.toggle_stopper()
                elif isinstance(entity, Spawner):
                    entity.spawn_stack()
                    
    def button_up(self, event):
        if self.mouse_selection:
            self.mouse_selection.pos += Vector(0, -1)
            self.mouse_selection.update()
            
    def button_down(self, event):
        if self.mouse_selection:
            self.mouse_selection.pos += Vector(0, 1)
            self.mouse_selection.update()
    
    def button_left(self, event):
        if self.mouse_selection:
            self.mouse_selection.pos += Vector(-1, 0)
            self.mouse_selection.update()
            
    def button_right(self, event):
        if self.mouse_selection:
            self.mouse_selection.pos += Vector(1, 0)
            self.mouse_selection.update()
                    
    def save(self):
        with filedialog.asksaveasfile(mode="w", initialdir=Path(__file__).parent) as f:
            f.write(json.dumps(self.world.save(),  cls=SaveFileEncoder, indent=4, separators=(',', ': ')))
    
    def load(self):
        with filedialog.askopenfile(mode="r", initialdir=Path(__file__).parent) as f:
            self.world.load(json.loads(f.read()))
        [x.update() for x in self.world.children]
        
    def clear(self):
        [x.remove() for x in list(self.world.children)]
        
    def start(self):
        def animation():
            if self.profiler_ticks:
                self.profiler_ticks -= 1
                if not self.profiler_ticks:
                    self.disable_profiler()
            TIMINGS["t_start"] = time.process_time()
            World.update_world()  # update simulation
            TIMINGS["t_world"] = time.process_time()
            self.canvas.focus_set()
            [x.update_logic() for x in PLC.instances]
            TIMINGS["t_logic"] = time.process_time()
            [x.update_opc() for x in PLC_OPCua.instances]
            TIMINGS["t_opc"] = time.process_time()
            
            def timings(t1, t2):
                res = int((TIMINGS[t1]-TIMINGS[t2])*1000)
                TIMINGS[t1+t2] = max(res, TIMINGS.get(t1+t2, 0))
                return (res, TIMINGS[t1+t2])
            total = int((TIMINGS["t_opc"]-TIMINGS["t_start"])*1000)
            
            self.timing_info.set("\n".join((
                                        f'Total: {timings("t_opc", "t_start")}',
                                        f'  World: {timings("t_world", "t_start")}',
                                        f'    Trigger: {timings("t_trigger", "t_start")}',
                                        f'    Events: {timings("t_events", "t_trigger")}',
                                        f'    Updates: {timings("t_updates", "t_events")}',
                                        f'    Render: {timings("t_render", "t_updates")}',
                                        f'  Logic: {timings("t_logic", "t_world")}',
                                        f'Entities: {len(self.world.layers[0])}',
                                        f'Profiler: {self.profiler_ticks}',
                                        )))
            self.after(100-min(total, 99), animation)
        self.after(0, animation)


if __name__ == '__main__':
    root = Tk()
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    
    app = Simulation(root)
    app.grid(row=0, column=0, sticky="NSEW")

    
    def animation():
        World.update_world()  # update simulation
        app.canvas.focus_set()
        root.after(100, animation)
        
    animation()
    root.mainloop()
