from digitalTwin_Simulation import Simulation
from digitalTwin_Entities import *

from tkinter import Tk
import tkinter as tk
# pip install asyncua


@register_entity
class PLC1(PLC):
    def _init_sim(self):
        RenderContainer.create_rectangle(self, pos=Vector(0,0), size=Vector(275, 280)).lower_to_bottom()
        pos = self.pos + Vector(100, 20)
        
        self._sim_conveyer0 = Conveyer(self.parent, pos=pos+Vector(20, 110), length=800, speed=0, orientation=Orientation.EAST)
        Remover(self.parent, pos=pos+Vector(820, 110), size=Vector(20,20))
        
        self._sim_conveyer1 = Conveyer(self.parent, pos=pos+Vector(50, 30), length=80, speed=0, orientation=Orientation.SOUTH)
        Wall(self._sim_conveyer1, pos=Vector(0, 0), size=Vector(3, 80))
        Wall(self._sim_conveyer1, pos=Vector(-20, 0), size=Vector(-3, 80))
        
        self._sim_conveyer2 = Conveyer(self.parent, pos=pos+Vector(30, 210), length=80, speed=0, orientation=Orientation.NORTH)
        Wall(self._sim_conveyer2, pos=Vector(0, 0), size=Vector(-3, -80))
        Wall(self._sim_conveyer2, pos=Vector(20, 0), size=Vector(3, -80))

        self._sim_spawner1 = Spawner(self.parent, pos=pos+Vector(53, 7), orientation=Orientation.SOUTH, stack=[{"color": "blue"}])
        self._sim_spawner1._conveyer.speed = 2
        self._sim_spawner2 = Spawner(self.parent, pos=pos+Vector(27, 233), orientation=Orientation.NORTH, stack=[{"color": "red"}])
        self._sim_spawner2._conveyer.speed = 2
        
        self._sim_stopper1 = Stopper(self.parent, pos=pos+Vector(154, 80), orientation=Orientation.EAST, auto_close=False)
        
        Stack(self.parent, pos=pos+Vector(40, 40), stack=[{"color": "blue"}])
        Stack(self.parent, pos=pos+Vector(40, 60), stack=[{"color": "blue"}])
        Stack(self.parent, pos=pos+Vector(40, 80), stack=[{"color": "blue"}])
        Stack(self.parent, pos=pos+Vector(40, 100), stack=[{"color": "blue"}])
        
        Stack(self.parent, pos=pos+Vector(40, 140), stack=[{"color": "red"}])
        Stack(self.parent, pos=pos+Vector(40, 160), stack=[{"color": "red"}])
        Stack(self.parent, pos=pos+Vector(40, 180), stack=[{"color": "red"}])
        Stack(self.parent, pos=pos+Vector(40, 200), stack=[{"color": "red"}])
        
    def _init_plc(self):
        self.plc_order_trigger = 0
        
        # -- PLC internal Vars --
        self._sim_conveyer1._req_count = 0
        self._sim_conveyer2._req_count = 0
        
        self._sim_spawner1._req_count = 0
        self._sim_spawner2._req_count = 0
        
        # -- Triggers --
        def stop_conveyer(conveyer:Conveyer):
            conveyer.speed = 0
            conveyer._req_count -= 1

        def spawn_another(spawner:Spawner):
            if spawner._req_count:
                spawner.spawn_stack()
                spawner._req_count -= 1    
        
        self._sim_conveyer1.triggers[0].register(TriggerTypes.EXIT, func=lambda e: stop_conveyer(self._sim_conveyer1))
        self._sim_conveyer2.triggers[0].register(TriggerTypes.EXIT, func=lambda e: stop_conveyer(self._sim_conveyer2))

        self._sim_spawner1._conveyer.triggers[0].register(TriggerTypes.EXIT, func=lambda e: spawn_another(self._sim_spawner1))
        self._sim_spawner2._conveyer.triggers[0].register(TriggerTypes.EXIT, func=lambda e: spawn_another(self._sim_spawner2))
    
    def update_logic(self):
        def _helper_conveyer_logic(conveyer:Conveyer, spawner:Spawner):
            if not conveyer.is_occupied() and not spawner._req_count:
                spawner.spawn_stack()
                spawner._req_count = 3
                conveyer.speed = 1
            if conveyer._req_count or spawner._req_count or spawner._conveyer.is_occupied():
                conveyer.speed = 1
            else:
                conveyer.speed = 0

        _helper_conveyer_logic(self._sim_conveyer1, self._sim_spawner1)
        _helper_conveyer_logic(self._sim_conveyer2, self._sim_spawner2)

        self._sim_conveyer0.speed = 1 if self.status.ready else 0
        
        if self.status.order and not self.status.order == self.plc_order_trigger:
            if self.status.order == 1:
                self.request_top(1)
                self.status.msg = 1
            elif self.status.order == 2:
                self.request_bottom(1)
                self.status.msg = 2
            elif self.status.order == 3:
                self._sim_stopper1.request_stopper_close()
            elif self.status.order == 4:
                self._sim_stopper1.open_stopper()
            elif self.status.order == 10:
                pass  # Open and close Stopper1
        self.plc_order_trigger = self.status.order
        
        if not bool(self._sim_conveyer1._req_count + self._sim_conveyer2._req_count):
            self.status.busy = False
            self.status.msg = 0
        self.status.update()
        
    def request_top(self, amount=1):
        if amount < 1:
            return
        self._sim_conveyer1._req_count += amount
    
    def request_bottom(self, amount=1):
        if amount < 1:
            return
        self._sim_conveyer2._req_count += amount
        

@register_entity
class PLC2(PLC):
    def _init_sim(self):
        RenderContainer.create_rectangle(self, pos=Vector(0,0), size=Vector(275, 280)).lower_to_bottom()
        pos = self.pos + Vector(100, 20)
        
        self._sim_stopper1 = Stopper(self.parent, pos=pos + Vector(0, 80), auto_close=False)
        self._sim_stopper2 = Stopper(self.parent, pos=pos + Vector(55, 80), auto_close=True)
        
        self._sim_sensor1 = Sensor(self.parent, pos=pos + Vector(40, 85))
        self._sim_sensor2 = Sensor(self.parent, pos=pos + Vector(75, 85))
        
        self._sim_spawner1 = Spawner(self.parent, pos=pos + Vector(16, 135), orientation=Orientation.EAST, stack=[{'color': 'black'}])

        self._sim_picker1 = Picker(self.parent, pos=pos + Vector(70, 130), length=75, orientation=Orientation.SOUTH, render_head=True, confine_sled_target_pos=False)
        
        self._sim_stack1 = Stack(self.parent, pos=pos + Vector(50, 195), stack=DEFAULT_STACK, infinite_stack=True)
        self._sim_trigger1 = Trigger(self, collider=AABB_Collider(parent=self, pos=Vector(158, 135), size=Vector(2, 10)), check_group=World.layers[0], check_types=(Stack,))
        # Wall(parent=self, pos=Vector(158, 135), size=Vector(2, 10))

    def _init_plc(self):
        self.plc_order_trigger = 0
    
    def update_logic(self):
        # React to new order
        if self.status.order and not self.status.order == self.plc_order_trigger:
            if self.status.order == 1:  # Red
                self.status.msg = 1
                self._sim_picker1.sled_target_pos = 54
                self._sim_picker1.sled_in_pos = False
            elif self.status.order == 2:  # Black
                self.status.msg = 2
                self._sim_spawner1.spawn_stack()
                self._sim_picker1.sled_target_pos = 8
                self._sim_picker1.sled_in_pos = False
            elif self.status.order == 3:
                self._sim_stopper1.open_stopper()
                self.status.busy = False
            elif self.status.order == 4:
                self._sim_stopper1.request_stopper_close()
                self.status.busy = False
            elif self.status.order == 10:
                pass  # Open and close Stopper 1
        
        # Transport order
        elif self.status.order in (1,2) and self._sim_picker1.sled_in_pos and self.status.busy:
            if self._sim_picker1.sled_occupied and self._sim_trigger1.is_occupied():
                self._sim_picker1.put_down()
                self._sim_picker1.sled_target_pos = 0
                self._sim_picker1.sled_in_pos = False
                self._sim_stopper2.open_stopper()
                self.status.busy = False
                self.status.msg = 0
            elif not self._sim_spawner1._conveyer.is_occupied():
                self._sim_picker1.pick_up()
                self._sim_picker1.sled_target_pos = -20
                self._sim_picker1.sled_in_pos = False
        
        self.plc_order_trigger = self.status.order
        self.status.update()
        
        
@register_entity
class PLC3a(PLC):
    def _init_sim(self):
        RenderContainer.create_rectangle(self, pos=Vector(0,0), size=Vector(275, 460)).lower_to_bottom()
        pos = self.pos + Vector(25, 100) 
        
        self._sim_sensor1 = Sensor(self.parent, pos=pos + Vector(-5, 85))
        self._sim_stopper1 = Stopper(self.parent, pos=pos + Vector(10, 80), auto_close=False)
        self._sim_sensor2 = Sensor(self.parent, pos=pos + Vector(30, 85))
        
        self._sim_stopper2 = Stopper(self.parent, pos=pos + Vector(170, 80), auto_close=False)
        self._sim_sensor3 = Sensor(self.parent, pos=pos + Vector(200, 85))
        self._sim_stopper3 = Stopper(self.parent, pos=pos + Vector(215, 80), auto_close=True)
        
        RenderContainer.create_rectangle(self, pos=pos + Vector(-2, 48), size=Vector(222, 24), fill="lightgrey")  # TODO: Check why this line isn't working
        self._sim_conveyer0 = Conveyer(self.parent, pos=pos + Vector(0, 50), length=220, speed=0, orientation=Orientation.EAST, animated=False)
        self._sim_spawner1 = Spawner(self.parent, pos=pos + Vector(35, 27), orientation=Orientation.SOUTH, stack=[{'color': 'black'}])
        self._sim_spawner2 = Spawner(self.parent, pos=pos + Vector(65, 27), orientation=Orientation.SOUTH, stack=[{'color': 'blue'}])
        self._sim_spawner3 = Spawner(self.parent, pos=pos + Vector(95, 27), orientation=Orientation.SOUTH, stack=[{'color': 'red'}])

        self._sim_picker1 = Picker(self.parent, pos=pos + Vector(230, 50), length=80, orientation=Orientation.SOUTH, render=False, render_head=True)
        self._sim_trigger1 = Trigger(self, collider=AABB_Collider(self, pos=pos-self.pos+Vector(218, 50), size=Vector(2, 20)), check_group=World.layers[0], check_types=(Stack,))
        self._sim_trigger2 = Trigger(self, collider=AABB_Collider(self, pos=pos-self.pos+Vector(218, 110), size=Vector(2, 20)), check_group=World.layers[0], check_types=(Stack,))
        Wall(self.parent, pos=pos + Vector(220, 50), size=Vector(1, 20), render=False)
        #Wall(self, pos=pos-self.pos+Vector(218, 110), size=Vector(2, 20), render=True)

    def _init_plc(self):
        self.plc_order_trigger = 0

    def update_logic(self):
        if self.status.order and not self.status.order == self.plc_order_trigger:
            if self.status.order == 1:
                self._sim_spawner3.spawn_stack()
                self._sim_conveyer0.speed = 1
            elif self.status.order == 2:
                self._sim_spawner2.spawn_stack()
                self._sim_conveyer0.speed = 1
            elif self.status.order == 3:
                self._sim_spawner1.spawn_stack()
                self._sim_conveyer0.speed = 1
                
            elif self.status.order == 4:
                self._sim_stopper2.open_stopper()
                self._sim_stopper2.auto_close = False
            elif self.status.order == 5:
                self._sim_stopper2.request_stopper_close()
                self._sim_stopper2.auto_close = True
                
            elif self.status.order == 6:
                self._sim_stopper3.open_stopper()
                self._sim_stopper3.auto_close = False
            elif self.status.order == 7:
                self._sim_stopper3.request_stopper_close()
                self._sim_stopper3.auto_close = True
            
            elif self.status.order == 8:
                self._sim_stopper1.open_stopper()
                self._sim_stopper1.auto_close = False
            elif self.status.order == 9:
                self._sim_stopper1.request_stopper_close()
                self._sim_stopper1.auto_close = True
            elif self.status.order == 10:
                pass  # Testfunktion (Tore auf/zu)
        self.plc_order_trigger = self.status.order
        
        if self._sim_trigger1.is_occupied() and self._sim_picker1.sled_in_pos and not self._sim_picker1.sled_occupied:
            self._sim_picker1.pick_up()
            self._sim_picker1.sled_target_pos = self._sim_picker1.sled_max_pos
        elif self._sim_trigger2.is_occupied() and self._sim_picker1.sled_in_pos and self._sim_picker1.sled_occupied:
            self._sim_picker1.put_down()
            self._sim_picker1.sled_target_pos = self._sim_picker1.sled_min_pos
            self._sim_stopper3.open_stopper()
            self._sim_conveyer0.speed = 0
        
        if self._sim_sensor3.activated:
            self.status.msg = 2
        elif self._sim_sensor2.activated:
            self.status.msg = 1
        
        if not self._sim_conveyer0.speed and not(
            self._sim_spawner1._conveyer.is_occupied() or
            self._sim_spawner2._conveyer.is_occupied() or
            self._sim_spawner3._conveyer.is_occupied() or
            self._sim_conveyer0.is_occupied() or
            self._sim_picker1.sled_occupied):
                self.status.busy = False
        self.status.update()

@register_entity
class PLC3b(PLC):
    def _init_sim(self):
        # RenderContainer.create_rectangle(self, pos=Vector(0,0), size=Vector(275, 280+160)).lower_to_bottom()
        pos = self.pos + Vector(25, -95) 
        
        self._sim_conveyer1 = Conveyer(self.parent, pos=pos + Vector(0, 0), length=220, speed=-1, orientation=Orientation.EAST, animated=True)
        RenderContainer.create_rectangle(self, pos=pos + Vector(-2, 23), size=Vector(222, 24), fill="lightgrey")  # TODO: Check why this line isn't working
        self._sim_conveyer0 = Conveyer(self.parent, pos=pos + Vector(0, 25), length=220, orientation=Orientation.EAST, animated=False)
        self._sim_spawner1 = Spawner(self.parent, pos=pos + Vector(9, 68), orientation=Orientation.NORTH, stack=[{'color': 'black'}])
        self._sim_spawner2 = Spawner(self.parent, pos=pos + Vector(39, 68), orientation=Orientation.NORTH, stack=[{'color': 'blue'}])
        self._sim_spawner3 = Spawner(self.parent, pos=pos + Vector(69, 68), orientation=Orientation.NORTH, stack=[{'color': 'red'}])

        self._sim_picker1 = Picker(self.parent, pos=pos + Vector(230, -25), length=70, orientation=Orientation.SOUTH, render=False, render_head=True)
        self._sim_picker1.sled_actual_pos = self._sim_picker1.sled_max_pos-1  # Change start position
        self._sim_picker1.sled_target_pos = self._sim_picker1.sled_max_pos
        
        self._sim_trigger1 = Trigger(self, collider=AABB_Collider(self, pos=pos-self.pos+Vector(218, 25), size=Vector(2, 20)), check_group=World.layers[0], check_types=(Stack,))
        self._sim_trigger2 = Trigger(self, collider=AABB_Collider(self, pos=pos-self.pos+Vector(218, -25), size=Vector(2, 20)), check_group=World.layers[0], check_types=(Stack,))
        #Wall(self, pos=pos-self.pos+Vector(218, -25), size=Vector(2, 20), render=True)

        Wall(self.parent, pos=pos + Vector(220, 0), size=Vector(1, 45), render=False)

    def _init_plc(self):
        self.plc_order_trigger = 0
        
    def update_logic(self):
        if self.status.order and not self.status.order == self.plc_order_trigger:
            if self.status.order == 1:
                self._sim_spawner3.spawn_stack()
                self._sim_conveyer0.speed = 1
            elif self.status.order == 2:
                self._sim_spawner2.spawn_stack()
                self._sim_conveyer0.speed = 1
            elif self.status.order == 3:
                self._sim_spawner1.spawn_stack()
                self._sim_conveyer0.speed = 1
        self.plc_order_trigger = self.status.order
        
        if self._sim_trigger1.is_occupied() and self._sim_picker1.sled_in_pos and not self._sim_picker1.sled_occupied:
            self._sim_picker1.pick_up()
            self._sim_picker1.sled_target_pos = self._sim_picker1.sled_min_pos
        elif self._sim_trigger2.is_occupied() and self._sim_picker1.sled_in_pos and self._sim_picker1.sled_occupied:
            self._sim_picker1.put_down()
            self._sim_picker1.sled_target_pos = self._sim_picker1.sled_max_pos
            self.status.busy = False
            self._sim_conveyer0.speed = 0
            # self._sim_stopper3.open_stopper()
        
        if not self._sim_conveyer0.speed and not(
            self._sim_spawner1._conveyer.is_occupied() or
            self._sim_spawner2._conveyer.is_occupied() or
            self._sim_spawner3._conveyer.is_occupied() or
            self._sim_conveyer0.is_occupied() or
            self._sim_picker1.sled_occupied):
                self.status.busy = False
        
        self.status.update()


if __name__ == "__main__":
    root = Tk()
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)
    root.geometry('1000x700')
    
    sim = Simulation(master=root)
    sim.grid(row=0, column=0, sticky="NSEW")
    
    plc1 = PLC1(parent=sim.world, pos=Vector(20, 100), endpoint="opc.tcp://localhost:7000", name="Module 1")
    plc2 = PLC2(parent=sim.world, pos=Vector(300, 100), endpoint="opc.tcp://localhost:7001", name="Module 2")
    plc3a = PLC3a(parent=sim.world, pos=Vector(580, 20), endpoint="opc.tcp://localhost:7002", name="Module 3a")
    plc3a = PLC3b(parent=sim.world, pos=Vector(580, 350), endpoint="opc.tcp://localhost:7003", name="Module 3b")
    
    sim.start()
        
    root.protocol("WM_DELETE_WINDOW", lambda: sim.clear() or root.destroy())
        
    # animation()
    root.mainloop()
    
