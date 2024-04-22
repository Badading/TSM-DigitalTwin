from digitalTwin_base import Vector, Entity, World, Orientation, Trigger, TriggerTypes
from digitalTwin_base import RenderContainer, AABB_Collider, Sphere_Collider, register_entity
from digitalTwin_Async_opc import PLC_OPCua

import math
import tkinter as tk


DEFAULT_STACK = [{'color': "red"},]


@register_entity
class Wall(Entity):
    def __init__(self, parent:Entity, pos:Vector, size:Vector, layer:int=0, render=True):
        Entity.__init__(self, parent=parent, pos=pos, layer=layer)
        self.collisions_enabled = True
        self.size = Vector(*size) if not isinstance(size, Vector) else size  # DEBUG
        self.render = render
        
        self._init_render_containers()
        self.update()
                
    def _init_render_containers(self):
        if self.render:
            RenderContainer.create_rectangle(self, pos=Vector(0,0), size=self.size, fill="lightgrey")
        AABB_Collider(self, pos=Vector(0, 0), size=self.size)
        
        
@register_entity
class Sensor(Entity):
    add_to_layers = False
    
    def __init__(self, parent:Entity, pos:Vector, orientation:Orientation=Orientation.EAST, layer:int=0):
        Entity.__init__(self, parent=parent, pos=pos, layer=layer)
        self.orientation:Vector = orientation.value if isinstance(orientation, (Orientation, Vector)) else Vector(*orientation)
        
        self.activated = False
        self.occupation_indicator = None
        
        self._init_render_containers()
        self.update()
        
    def _init_render_containers(self):
        pos, size = Vector(0,0).norm_box(Vector(10,20).rotate(self.orientation.angle))
        RenderContainer.create_rectangle(self, pos=pos, size=size)
        pos, size = Vector(0,0).norm_box(Vector(10, 5).rotate(self.orientation.angle))
        self.occupation_indicator = RenderContainer.create_rectangle(self, pos=pos, size=size)
        pos, size = Vector(5,20).rotate(self.orientation.angle).norm_box(Vector(0,10).rotate(self.orientation.angle))
        RenderContainer.create_line(self, pos=pos, size=size, dash=(3,3))
        trigger = Trigger(self, collider=AABB_Collider(self, pos=pos, size=size), check_group=World.layers[self.layer], check_types=(Stack,))
        trigger.register(type=TriggerTypes.OCCUPANCY, func=self._trigger_occupancy)
    
    def _trigger_occupancy(self, occupancy):
        self.activated = occupancy
        self.occupation_indicator.set_color("green" if self.activated else "white")


@register_entity
class Stack(Entity):
    RADIUS = 9
    dont_save = True  # this can be overridden on a per Stack basis
    
    def __init__(self, parent:Entity, pos:Vector, stack=DEFAULT_STACK, layer:int=0, infinite_stack=False):
        Entity.__init__(self, parent=parent, pos=pos, layer=layer)
        self.collisions_enabled = True
        self.infinite_stack = infinite_stack
        
        self.stack:list[dict] = list(stack)
        self._last_collider_cash = None
        
        self._init_render_containers()
        
    def _init_render_containers(self):
        r = self.RADIUS
        RenderContainer.create_oval(self, pos=Vector(-r-1, -r-1), size=Vector(r*2+1, r*2+1), fill=self.stack[-1].get("color", "red"))
        Sphere_Collider(self, pos=Vector(0,0), radius=r+0.5)
        
    def change_layer(self, new_layer: int):
        self._last_collider_cash = None
        return super().change_layer(new_layer)
        
    def move(self, vector:Vector, ignore=tuple()) -> bool:
        old_pos = self.pos
        self.pos += vector
        if (self._last_collider_cash and 
            not self._last_collider_cash in ignore and 
            self.collision_check(other=self._last_collider_cash)):
                self.pos = old_pos  # Movement cancelled
                return False
        for other in World.layers[self.layer]:
            if other == self:
                continue
            if other in ignore:
                continue
            if self.collision_check(other=other):
                self._last_collider_cash = other
                self.pos = old_pos  # Movement cancelled
                return False
        self.update()
        return True
    
    def _update_color(self):
        self.renders[0].set_color(self.stack[-1].get("color", "red"))
        
    def unstack(self) -> "Stack":
        if len(self.stack)-1 or self.infinite_stack:
            stack = self.stack[-1:]
            if not self.infinite_stack:
                del self.stack[-1]
            self._update_color()
            return Stack(self.parent, self.pos, stack=stack)
        return self

    def stack_on(self, other:"Stack") -> "Stack":
        other.stack += self.stack
        other._update_color()
        self.remove()
        return other
    
    def remove(self):
        self._last_collider_cash = None
        return super().remove()
    
    def __contains__(self, other):
        if isinstance(other, Stack) and other.colliders and self.colliders:
            return self.colliders[0] in other.colliders[0]
        return super().__contains__(other)


@register_entity
class Conveyer(Entity):
    WIDTH = 20
    add_to_layers = False
    
    def __init__(self, parent:Entity, pos:Vector, length:float=60, speed:float=1, orientation:Orientation=Orientation.EAST, animated:bool=True):
        Entity.__init__(self, parent=parent, pos=pos)
        
        self.orientation:Vector = orientation.value if isinstance(orientation, (Orientation, Vector)) else Vector(*orientation)
        self.length:float = length
        self._speed:float = speed
        self.animated = animated
        self.ignored_colliders:list[Entity] = list()
        self._animation_conveyer = 0
        self._animation_obj:RenderContainer = None
        self._animation_pos:Vector = None
        
        self._move_vector = self.orientation * self._speed
        
        self._init_render_containers()
        if self.animated:
            World.animations.append(self._conveyer_animation)
        
        self.update()
        
    @property
    def speed(self):
        return self._speed
    
    @speed.setter
    def speed(self, value):
        self._speed = value
        self._move_vector = self.orientation * value
        
    def _init_render_containers(self):
        # body
        pos, size = Vector(0,0).norm_box(Vector(self.length, Conveyer.WIDTH).rotate(self.orientation.angle))
        # pos, size = (Vector(0,5).rotate(self.conveyer_orientation.angle)).norm_box(Vector(self.conveyer_length, 10).rotate(self.conveyer_orientation.angle))
        RenderContainer.create_rectangle(self, pos=pos, size=size, fill="white")
        # create trigger
        trigger = Trigger(self, collider=AABB_Collider(self, pos=pos, size=size), check_group=World.layers[self.layer], check_types=(Stack,))
        trigger.register(TriggerTypes.PRESENT, self._trigger_present_move)
        # line
        pos, size = Vector(-1, -1).norm_box(self.orientation.rotate(math.pi/2) * Conveyer.WIDTH)
        self._animation_obj = RenderContainer.create_line(parent=self, pos=pos, size=size)
        self._animation_pos = pos
        
    def remove(self):
        if self._conveyer_animation in World.animations:
            World.animations.remove(self._conveyer_animation)
        Entity.remove(self)
        
    def is_occupied(self) -> bool:
        return self.triggers[0].is_occupied()
        
    def _trigger_present_move(self, entity:Stack):
        if isinstance(entity, Stack):
            entity.move(self._move_vector, ignore=self.ignored_colliders)
        
    def _conveyer_animation(self):
        self._animation_conveyer += self._speed
        if self._animation_conveyer < 0:
            self._animation_conveyer += self.length
        elif self._animation_conveyer > self.length:
            self._animation_conveyer -= self.length
            
        self._animation_obj.pos = self._animation_pos + self.orientation * self._animation_conveyer
        self._animation_obj.render()
     
   
@register_entity
class Stopper(Entity):
    def __init__(self, parent:Entity, pos:Vector, orientation:Orientation=Orientation.EAST, auto_close:bool=True):
        Entity.__init__(self, parent=parent, pos=pos)
        self.collisions_enabled = True
        
        self.orientation:Vector = orientation.value if isinstance(orientation, (Orientation, Vector)) else Vector(*orientation)
        self.auto_close = auto_close
        self._close_requested = False
        
        self._animation_obj:RenderContainer = None
        self._animation_stopper = 0
        self._animation_speed = 2 if auto_close else -2
        self._animation_pos:Vector = None
        
        self._init_render_containers()
        World.animations.append(self._stopper_animation)
        
        self.update()
        
    def _init_render_containers(self):
        # body
        pos, size = Vector(0, 0).norm_box(Vector(15, 30).rotate(self.orientation.angle))
        RenderContainer.create_rectangle(self, pos=pos, size=size, fill="lightgrey")
        # stopper
        pos, size = Vector(5, 5).rotate(self.orientation.angle).norm_box(Vector(5, 25).rotate(self.orientation.angle))
        self._animation_obj = RenderContainer.create_rectangle(self, pos=pos, size=size, fill="grey")
        self._animation_pos = pos
        # wall
        pos, size = Vector(4, 30).rotate(self.orientation.angle).norm_box(Vector(1, 20).rotate(self.orientation.angle))
        collider = AABB_Collider(self, pos=pos, size=size)
        Trigger(self, collider, World.layers[0], check_types=(Stack,)).register(TriggerTypes.EXIT, func=self._trigger_auto_close_stopper)
        
    def _stopper_animation(self):
        self._animation_stopper += self._animation_speed
        self.collisions_enabled = True
        if self._animation_stopper < 0:
            self.collisions_enabled = False
            self._animation_stopper = 0
        elif self._animation_stopper > 20:
            self._animation_stopper = 20
        self._animation_obj.pos = self._animation_pos + self.orientation.value.rotate(math.pi/2) * self._animation_stopper 
        self._animation_obj.render()
        
    def remove(self):
        World.animations.remove(self._stopper_animation)
        Entity.remove(self)
        
    def _trigger_auto_close_stopper(self, *args):
        if self.auto_close or self._close_requested:
            self.close_stopper()
    
    def toggle_stopper(self, *args):
        self._animation_speed *= -1
        
    def request_stopper_close(self):
        self._close_requested = True
        
    def close_stopper(self, *args):
        self.collisions_enabled = True
        self._close_requested = False
        if self._animation_speed < 0:
            self.toggle_stopper()
            
    def open_stopper(self, *args):
        if self._animation_speed > 0:
            self.toggle_stopper()


@register_entity
class Spawner(Entity):
    add_to_layers = True
    
    def __init__(self, parent:Entity, pos:Vector, orientation:Orientation=Orientation.EAST, stack=DEFAULT_STACK):
        Entity.__init__(self, parent=parent, pos=pos)
        self.collisions_enabled = True
        self.orientation:Vector = orientation.value if isinstance(orientation, (Orientation, Vector)) else Vector(*orientation)
        self.stack=list(stack)
        
        self.spawned = list()
        
        self._init_render_containers()
        
        self.update()
        
    def _init_render_containers(self):
        pos, size = Vector(0,0).norm_box(Vector(23,26).rotate(self.orientation.angle))
        RenderContainer.create_rectangle(self, pos=pos, size=size)
        AABB_Collider(self, pos=pos, size=size)
        
        self._conveyer = Conveyer(self, pos=Vector(3,3).rotate(self.orientation.angle), length=20, orientation=self.orientation, animated=False)
        self._conveyer.ignored_colliders.append(self)
        self._conveyer.triggers[0].check_group = self.spawned
        self._conveyer.triggers[0].register(type=TriggerTypes.EXIT, func=self._trigger_exit_transfer_stack_to_parent)
        
        self._stack = Stack(self, pos=Vector(13,13).rotate(self.orientation.angle), layer=1, stack=self.stack)
    
    def _trigger_exit_transfer_stack_to_parent(self, entity:Stack):
        entity.change_parent(self.parent)
        self.spawned.remove(entity)
        """
        entity.pos = self.pos + entity.pos
        entity.parent = self.parent
        self.children.remove(entity)
        self.parent.children.append(entity)
        entity.update()
        """
            
    def spawn_stack(self) -> bool:
        if self.spawned:
            return False
        self.spawned.append(Stack(self, pos=Vector(13,13).rotate(self.orientation.angle), stack=self.stack))
        self._stack.renders[0].raise_to_top()
        return True


@register_entity
class Picker(Entity):
    add_to_layers = False
    
    class Head(Entity):
        def __init__(self, parent:"Picker", pos:Vector, render_head:bool=True):
            Entity.__init__(self, parent=parent, pos=pos)
            self.orientation:Vector = self.parent.orientation
            self.render_head:bool = render_head
            
            self._trigger:Trigger = None
            self._picked_stack:Stack = None
            
            self._init_render_containers()
        
        def _init_render_containers(self):
            pos, size = Vector(0,0).norm_box(Vector(6, 14).rotate(self.orientation.angle))
            if self.render_head:
                RenderContainer.create_rectangle(self, pos=pos, size=size, fill="blue")
            self._trigger = Trigger(self, collider=AABB_Collider(self, pos=pos, size=size), check_group=World.layers[0], check_types=(Stack,))
        
        def pick_up(self):
            if self._picked_stack:
                return
            if self._trigger.is_occupied():  #TODO: Check if stack has multiple elements
                self._picked_stack:Stack = list(self._trigger._present_entities)[0].unstack()
                self._picked_stack.change_parent(new_parent=self)
                self._picked_stack.change_layer(new_layer=1)  #TODO: Make layers dynamic
                
        def put_down(self):
            if not self._picked_stack:
                return
            if self._trigger.is_occupied():  #TODO: Check if stack has multiple elements
                self._picked_stack.stack_on(list(self._trigger._present_entities)[0])
            else:
                self._picked_stack.change_parent(new_parent=self.parent.parent)
                self._picked_stack.change_layer(new_layer=0)  #TODO: Make layer dynamic                
            self._picked_stack = None
                
            
    def __init__(self, parent:Entity, pos:Vector, length:int, orientation:Orientation=Orientation.EAST, render:bool=True, render_head:bool=True, confine_sled_target_pos:bool=True):
        Entity.__init__(self, parent=parent, pos=pos)
        self.length:int = length
        self.render:bool = render
        self.render_head:bool = render_head
        self.confine_sled_target_pos:bool = confine_sled_target_pos
        self.orientation:Vector = orientation.value if isinstance(orientation, (Orientation, Vector)) else Vector(*orientation)
        
        self.sled_actual_pos:int = 0
        self.sled_target_pos:int = 0
        self.sled_max_pos:int = self.length - 20
        self.sled_min_pos:int = 0
        self.sled_in_pos:bool = False
        
        self._animation_obj:Picker.Head = None
        self._animation_speed = 1
        self._animation_pos:Vector = None
        
        self._init_render_containers()
        World.animations.append(self._sled_animation)
        
        self.update()
    
    @property
    def sled_occupied(self):
        return bool(self._animation_obj._picked_stack)
    
    def pick_up(self):
        self._animation_obj.pick_up()
    
    def put_down(self):
        self._animation_obj.put_down()
        
    def _init_render_containers(self):
        pos, size = Vector(0,0).norm_box(Vector(self.length, 10).rotate(self.orientation.angle))
        if self.render:
            RenderContainer.create_rectangle(self, pos=pos, size=size, fill="lightgrey")
        
        pos = Vector(7,10).rotate(self.orientation.angle)
        self._animation_obj = Picker.Head(parent=self, pos=pos, render_head=self.render_head)
        self._animation_pos = pos
        
    def _sled_animation(self):
        self.raise_to_top()
        if self.confine_sled_target_pos:
            if self.sled_target_pos > self.sled_max_pos:
                self.sled_target_pos = self.sled_max_pos
            elif self.sled_target_pos < self.sled_min_pos:
                self.sled_target_pos = self.sled_min_pos
        
        self.sled_in_pos = False
        if self.sled_actual_pos < self.sled_target_pos:
            self.sled_actual_pos += self._animation_speed
        elif self.sled_actual_pos > self.sled_target_pos:
            self.sled_actual_pos -= self._animation_speed
        else:
            self.sled_in_pos = True
            return

        self._animation_obj.pos = self._animation_pos + self.orientation.value * self.sled_actual_pos
        self._animation_obj.update()


@register_entity
class Remover(Entity):
    add_to_layers = False
    
    def __init__(self, parent:Entity, pos:Vector, size:Vector):
        Entity.__init__(self, parent=parent, pos=pos)
        self.size = size
        
        RenderContainer.create_rectangle(self, pos=Vector(0,0), size=size, fill="red")
        Trigger(self, collider=AABB_Collider(self, pos=Vector(0,0), size=size), check_group=World.layers[0], check_types=(Stack,)).register(type=TriggerTypes.ENTER, func=lambda e: e.remove())
        self.update()


@register_entity
class PLC_Status(Entity, PLC_OPCua):
    add_to_layers = False
    
    def __init__(self, parent, pos:Vector, endpoint:str, name:str):
        Entity.__init__(self, parent=parent, pos=pos)
        PLC_OPCua.__init__(self, name=name, endpoint=endpoint)
        
        self.name:str = name
        self.endpoint = endpoint
        
        self.start:bool = False
        self.ack:bool = False
        self.busy:bool = False
        self.ready:bool = False
        
        self._init_render_containers()
    
    def _init_render_containers(self):
        RenderContainer.create_text(self, pos=Vector(25, 5), text=f"Start {self.name}", anchor="w")
        self.start_module_indicator = RenderContainer.create_oval(self, pos=Vector(0,0), size=Vector(20,20), fill="lightgrey")
        
        RenderContainer.create_text(self, pos=Vector(25, 30), text="Ack", anchor="w")
        self.ack_indicator = RenderContainer.create_oval(self, pos=Vector(0,25), size=Vector(20,20), fill="lightgrey")
        
        RenderContainer.create_text(self, pos=Vector(25, 55), text="Busy", anchor="w")
        self.busy_indicator = RenderContainer.create_oval(self, pos=Vector(0,50), size=Vector(20,20), fill="lightgrey")
        
        RenderContainer.create_text(self, pos=Vector(25, 80), text="Ready", anchor="w")
        self.ready_indicator = RenderContainer.create_oval(self, pos=Vector(0,75), size=Vector(20,20), fill="lightgrey")
        
        RenderContainer.create_window(self, pos=Vector(0, 100), tk_element=tk.Scale(World.instance.canvas, 
                                                                                    orient=tk.HORIZONTAL,
                                                                                    length=50, to=1,
                                                                                    showvalue=False,
                                                                                    sliderlength=25,
                                                                                    command=self._func_switch_main))
        self.update()
        
    def _func_switch_main(self, value):
        self.ready = bool(int(value))
        self.update()
    
    def _update(self):
        self.start_module_indicator.set_color("green" if self.start else "lightgrey")
        self.ack_indicator.set_color("green" if self.ack else "lightgrey")
        self.busy_indicator.set_color("red" if self.busy else "lightgrey")
        self.ready_indicator.set_color("green" if self.ready else "red")
        
        Entity._update(self)
    
    def remove(self):
        Entity.remove(self)
        PLC_OPCua.remove(self)


@register_entity
class PLC(Entity):
    add_to_layers = False
    instances = []
    
    def __init__(self, parent:Entity, pos:Vector, endpoint:str, name:str):
        Entity.__init__(self, parent=parent, pos=pos)
        self.name = name
        
        self.status = PLC_Status(self, pos=Vector(5,5), endpoint=endpoint, name=self.name)
        
        self._init_sim()
        self._init_plc()
        self.instances.append(self)
    
    def _init_sim(self):
        pass
    
    def update_logic(self):
        pass
    
    def _init_plc(self):
        pass
    
    def remove(self):
        '''Remove PLC_Entity from World'''
        self.instances.remove(self)
        self.status.remove()
        Entity.remove(self)
