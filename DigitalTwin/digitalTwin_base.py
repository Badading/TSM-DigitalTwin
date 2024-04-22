from dataclasses import dataclass
import typing
import inspect
from enum import Enum
import tkinter as tk
import math
import time


TIMINGS = dict()


ENTITY_REGISTER = {}
def register_entity(cls):
    ENTITY_REGISTER[cls.__name__] = cls
    return cls


@dataclass
class Vector:
    x:float
    y:float
    
    _length = None
    
    def __post_init__(self):
        #self.x = round(self.x, 5)
        #self.y = round(self.y, 5)
        pass
    
    def __add__(self, other) -> "Vector":
        return Vector(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other) -> "Vector":
        return Vector(self.x - other.x, self.y - other.y)
    
    def __repr__(self) -> str:
        return str((self.x, self.y))
    
    def __str__(self) -> str:
        return str((self.x, self.y))
    
    def __iter__(self):
        yield self.x
        return self.y
    
    @property
    def value(self) -> "Vector":
        return self
    
    @property
    def length(self) -> float:
        if self._length is None:
            self._length = math.sqrt(self.x**2 + self.y**2)
        return self._length
    
    @property
    def angle(self) -> float:  
        # PERF: We could cache the angle, but it's not called that often
        #       and would slow obj creation
        if self.x > 0:
            return math.atan(self.y / self.x)
        if self.x < 0:
            deg = math.atan(self.y / -self.x)
            if deg == 0:
                return math.pi
            elif deg < 0:
                return deg - math.pi/2
            else:
                return deg + math.pi/2
        if self.y < 0:
            return -math.pi/2
        else:
            return math.pi/2
        
    @property
    def norm(self) -> "Vector":
        length = self.length
        return Vector(self.x/length, self.y/length)
    
    def __truediv__(self, other) -> "Vector":
        if type(other) in [int, float]:
            return Vector(self.x/other, self.y/other)
        
    def rotate(self, deg) -> "Vector":
        # deg = deg/180*math.pi
        x = self.x * math.cos(deg) - math.sin(deg) * self.y
        y = self.x * math.sin(deg) + math.cos(deg) * self.y
        return Vector(x, y)
    
    def __floordiv__(self, other):
        pass
    
    def __mul__(self, other):
        '''
        other [int/float] -> Vector
        other [Vector] -> float/int
        '''
        if type(other) in [int, float]:
            return Vector(self.x * other, self.y * other)
        if isinstance(other, Vector):
            return self.x * other.x + self.y * other.y
    
    def __rmul__(self, other):
        return self.__mul__(other=other)
    
    def __lt__(self, other) -> bool:
        if isinstance(other, Vector):
            return self.length < other.length
        else:
            return self.length < other
        
    def __gt__(self, other) -> bool:
        if isinstance(other, Vector):
            return self.length > other.length
        else:
            return self.length > other
        
    def __le__(self, other) -> bool:
        if isinstance(other, Vector):
            return self.length <= other.length
        else:
            return self.length <= other
        
    def __ge__(self, other) -> bool:
        if isinstance(other, Vector):
            return self.length >= other.length
        else:
            return self.length >= other
        
    def norm_box(self, size:"Vector") -> tuple["Vector", "Vector"]:
        """pos.norm_box(size) -> (pos:Vector, size:Vector)"""
        size = self + size
        pos1 = Vector(x=min(self.x, size.x), y=min(self.y, size.y))
        pos2 = Vector(x=max(self.x, size.x), y=max(self.y, size.y))
        return pos1, pos2-pos1


class Orientation(Enum):
    NORTH = Vector(0, -1)
    SOUTH = Vector(0, 1)
    EAST = Vector(1, 0)
    WEST = Vector(-1, 0)


@register_entity
class Entity:
    dont_save = False
    add_to_layers = True
    
    def __init__(self, parent:"Entity", pos:Vector, layer:int=0, collisions_enabled:bool=False):
        self.parent:Entity = parent
        self._pos:Vector = Vector(*pos) if not isinstance(pos, Vector) else pos
        self.layer:int = layer
        self.collisions_enabled:bool = collisions_enabled
        
        self._hash = None
        
        self.__post_init__()
        self._update_abs_pos()
    
    def __post_init__(self):
        self.abs_pos = self.parent.abs_pos + self._pos
        
        self.children:list[Entity] = list()
        self.colliders:list[AABB_Collider | Sphere_Collider] = list()
        self.colliders_ignore:list[Entity] = list()
        self.renders:list[RenderContainer] = list()
        self.triggers:list[Trigger] = list()
        
        self.parent.children.append(self)
        if self.add_to_layers:
            World.layers[self.layer].append(self)
        
    @property
    def pos(self):
        return self._pos
    
    @pos.setter
    def pos(self, value:Vector):
        self._pos = value
        self._update_abs_pos()
    
    def _update_abs_pos(self):
        self.abs_pos = self.parent.abs_pos + self._pos
        [x._update_abs_pos() for x in self.children] # DEBUG
        for x in self.colliders:
            x.abs_pos = self.abs_pos + x._pos
        
    @property
    def _abs_pos(self) -> Vector:
        return self.parent.abs_pos + self.pos
        
    def change_layer(self, new_layer:int):
        if self.add_to_layers:
            World.layers[self.layer].remove(self)
            self.layer = new_layer
            World.layers[self.layer].append(self)
    
    def change_parent(self, new_parent:"Entity"):
        self._pos = self.abs_pos - new_parent.abs_pos
        self.parent.children.remove(self)
        self.parent = new_parent
        self.parent.children.append(self)
        self._update_abs_pos()
        self.update()
    
    def update(self):
        World.updates.add(self)
        
    def _update(self):
        [x._update() for x in self.children]
        [x.render() for x in self.renders]
        
    
    def collision_check(self, other:"Entity", ignore=tuple()):
        if not(self.collisions_enabled and other.collisions_enabled):
            return False
        if other in self.colliders_ignore or self in other.colliders or other in ignore:
            return False
        return self in other
    
    def remove(self):
        """
        Removes an Entity from the world
        Caution: Removing an Entity can activate EXIT triggers
        """
        # cleanup pointers, so to gc can delete the objects
        [x.remove() for x in list(self.renders)]  # remove from canvas
        [x.remove() for x in list(self.children)]
        [x.remove() for x in list(self.colliders)]
        [x.remove() for x in list(self.triggers)]
        if self in World.layers[self.layer]:
            World.layers[self.layer].remove(self)
        self.parent.children.remove(self)
        
    def raise_to_top(self):
        [x.raise_to_top() for x in self.renders]
        [x.raise_to_top() for x in self.children]
        
    def lower_to_bottom(self):
        [x.lower_to_bottom() for x in self.children]
        [x.lower_to_bottom() for x in self.renders]
    
    def __contains__(self, other):
        # TODO: Implement rough checks
        # Entity in Entity checking can be expensive, avoid if possible
        if isinstance(other, (AABB_Collider, Sphere_Collider, Entity)):
            for x in self.colliders:
                if x in other:
                    return True
            return False
            #return any([x in other for x in self.colliders])
    
    def __str__(self):
        return f"<{str(self.__class__).strip('<>')} object at {hex(id(self))}>"
    
    def __hash__(self):
        if not self._hash:
            self._hash = hash(str(self))
        return self._hash
    
    # the _to_json / _from_json functions recursively traverse the parent/child structure of the world/save-file
    # to save/load all Entities to exclude a type of Entity from being saved set the class variable "dont_save = True"
    def _to_json(self):
        # for this to work all arguments of __init__ have to be assigned to self under the same name
        # example __init__(self, name:str)  ==>  self.name = name
        # otherwise the the save function has no way of knowing how to fill name variable for loading
        # alternatively one can override the _to_json function and assign values by hand
        return {"type": self.__class__.__name__, 
                "kwargs": {k:self.__getattribute__(k) for k in inspect.signature(self.__class__.__init__).parameters.keys() if not k in ["self", "parent", "args", "kwargs"]},
                "children": [x._to_json() for x in self.children if not x.dont_save]
                }
        
    @classmethod
    def _from_json(cls, parent, save_data):
        self = cls(parent=parent, **save_data.get("kwargs", {}))
        [ENTITY_REGISTER.get(x.get("type"))._from_json(parent=self, save_data=x) for x in save_data.get("children", {})]
        return self
    
    def __del__(self):
        print(f"GC: Removed {str(self)}")


# Caution: RenderContainers create functions normalize the pos and size vectors
#           pos vectors have to always point to the top left corner of the element
#           else the update function will move the element unexpectedly
@dataclass
class RenderContainer:    
    parent:Entity
    pos:Vector
    canvas_id:int | tk.Frame
    
    def __post_init__(self):
        self.parent.renders.append(self)
        
    @classmethod
    def create_text(cls, parent:Entity, pos:Vector, text:str, *args, **kwargs):
        pos1 = parent.abs_pos + pos
        return cls(parent=parent, 
                   pos=pos,
                   canvas_id=World.instance.canvas.create_text(pos1.x, pos1.y, text=text, *args, **kwargs))
    
    @classmethod
    def create_rectangle(cls, parent:Entity, pos:Vector, size:Vector, *args, **kwargs):
        pos, size = pos.norm_box(size=size)        
        pos1 = parent.abs_pos + pos
        pos2 = pos1 + size
        return cls(parent=parent, 
                   pos=pos,
                   canvas_id=World.instance.canvas.create_rectangle(pos1.x, pos1.y, pos2.x, pos2.y, *args, **kwargs))

    @classmethod
    def create_line(cls, parent:Entity, pos:Vector, size:Vector, *args, **kwargs):
        pos, size = pos.norm_box(size=size)
        pos1 = parent.abs_pos + pos
        pos2 = pos1 + size
        return cls(parent=parent, 
                   pos=pos,
                   canvas_id=World.instance.canvas.create_line(pos1.x, pos1.y, pos2.x, pos2.y, *args, **kwargs))
        
    @classmethod
    def create_oval(cls, parent:Entity, pos:Vector, size:Vector, *args, **kwargs):
        pos, size = pos.norm_box(size=size)
        pos1 = parent.abs_pos + pos
        pos2 = pos1 + size
        return cls(parent=parent, 
                   pos=pos,
                   canvas_id=World.instance.canvas.create_oval(pos1.x, pos1.y, pos2.x, pos2.y, *args, **kwargs))
    
    @classmethod
    def create_window(cls, parent:Entity, pos:Vector, tk_element, *args, **kwargs):
        pos1 = parent.abs_pos + pos
        kwargs.setdefault("anchor", "nw")
        return cls(parent=parent,
                   pos=pos,
                   canvas_id=World.instance.canvas.create_window(pos1.x, pos1.y, window=tk_element, *args, **kwargs))
    
    @property
    def abs_pos(self) -> Vector:
        return self.parent.abs_pos + self.pos
    
    def __str__(self):
        return f"<{str(self.__class__).strip('<>')} object at {hex(id(self))}>"
    
    def __hash__(self):
        return(hash(str(self)))
    
    def update(self):
        self.render()
    
    def _update(self):
        self.render()
    
    def render(self):
        World.renders.add(self)
        
    def raise_to_top(self):
        if isinstance(self.canvas_id, int):
            World.instance.canvas.tag_raise(self.canvas_id)
        else:
            pass
        
    def lower_to_bottom(self):
        if isinstance(self.canvas_id, int):
            World.instance.canvas.tag_lower(self.canvas_id)
        
    def _render(self):
        pos = self.abs_pos
        if isinstance(self.canvas_id, int):
            World.instance.canvas.moveto(self.canvas_id, pos.x, pos.y)
        else:
            self.canvas_id.place(x=pos.x, y=pos.y)
        
    def remove(self):
        if isinstance(self.canvas_id, int):
            World.instance.canvas.delete(self.canvas_id)
        else:
            self.canvas_id.destroy()
        self.parent.renders.remove(self)
        self.parent = None
        
    def set_color(self, color:str):
        if isinstance(self.canvas_id, int):
            World.instance.canvas.itemconfig(self.canvas_id, fill=color)
        else:
            self.canvas_id.config(bg=color)


def collider_helper(sc: "Sphere_Collider", aabb: "AABB_Collider") -> bool:
    def check(pn, b_min, b_max):
        out = 0
        if pn < b_min:
            out += (b_min - pn)**2
        if pn > b_max:
            out += (pn - b_max)**2
        return out
    
    sq = 0.0
    b_min, b_max = aabb.get_box()
    sc_abs_pos = sc.abs_pos
    sq += check(sc_abs_pos.x, b_min.x, b_max.x)
    sq += check(sc_abs_pos.y, b_min.y, b_max.y)

    return sq <= (sc.radius * sc.radius)


@dataclass
class AABB_Collider:  # Axes Aligned Boundary Box
    parent:Entity
    size:Vector
    pos:Vector
    
    def __post_init__(self):
        self.parent.colliders.append(self)
        self._abs_pos = self.parent.abs_pos + self._pos
        self._norm_box = None
        
    @property
    def pos(self):
        return self._pos
    
    @pos.setter
    def pos(self, value:Vector):
        self._pos = value
        self.abs_pos = self.parent.abs_pos + self._pos
        self._norm_box = None  # invalidate box cash on pos change
    
    @property
    def abs_pos(self):
        return self._abs_pos
    
    @abs_pos.setter
    def abs_pos(self, value):
        self._abs_pos = value
        self._norm_box = None  # invalidate box cash on abs_pos change
        
    def get_box(self):  # cashing this call dramatically improves performance
        if self._norm_box:
            return self._norm_box
        pos1, size = (self.parent.abs_pos + self._pos).norm_box(self.size)
        self._norm_box = (pos1, pos1+size)
        return self._norm_box
    
    def remove(self):
        self.parent.colliders.remove(self)
        self.parent = None
    
    def __contains__(self, other) -> bool:
        if isinstance(other, AABB_Collider):
            pos00, pos01 = self.get_box()
            pos10, pos11 = other.get_box()
            return (pos00.x > pos11.x or pos01.x < pos10.x or
                    pos00.y > pos11.y or pos01.y < pos10.y)
        elif isinstance(other, Sphere_Collider):
            return collider_helper(sc=other, aabb=self)
        elif isinstance(other, Entity):
            # hand over to Entity object to enable rough checks by overriding the Entity's __contains__ function
            return self in other
        
    def _update(self):
        pass
    
    def __str__(self):
        return f"<{str(self.__class__).strip('<>')} object at {hex(id(self))}>"
    
    def __hash__(self):
        return(hash(str(self)))
        

@dataclass
class Sphere_Collider:  # Sphere collider
    parent:Entity
    radius:float
    pos:Vector
    
    def __post_init__(self):
        self.parent.colliders.append(self)
        self.abs_pos = self.parent.abs_pos + self._pos
        
    @property
    def pos(self):
        return self._pos
    
    @pos.setter
    def pos(self, value:Vector):
        self._pos = value
        self.abs_pos = self.parent.abs_pos + self._pos
        
    def remove(self):
        self.parent.colliders.remove(self)
        self.parent = None
    
    def __contains__(self, other) -> bool:
        if isinstance(other, Sphere_Collider):
            return (self.abs_pos - other.abs_pos).length < self.radius + other.radius
        elif isinstance(other, AABB_Collider):
            return collider_helper(sc=self, aabb=other)
        elif isinstance(other, Entity):
            # hand over to Entity object to enable rough checks by overriding the Entity's __contains__ function
            return self in other
    
    
class TriggerTypes(Enum):
    PRESENT = 0
    ENTER = 1
    EXIT = 2  # Can get triggered by a removed Entity
    OCCUPANCY = 3


@dataclass
class Trigger:
    instances:typing.ClassVar[list["Trigger"]] = list()
    
    parent:Entity
    collider:AABB_Collider | Sphere_Collider
    check_group:list[Entity]
    check_types:list[Entity] = None
    
    def __post_init__(self):
        self.pos = Vector(0,0)
        self.check_types = self.check_types if self.check_types else (Entity,)
        self._triggers = {x:list() for x in TriggerTypes}
        self._present_entities = set()  # Caution can contain a ref to a removed Entity that will trigger an EXIT event
                
        self.parent.triggers.append(self)
        self.instances.append(self)
        
    @property
    def abs_pos(self):
        return self.parent.abs_pos
            
    def register(self, type:TriggerTypes, func):
        self._triggers.get(type, []).append(func)
    
    def __str__(self):
        return f"<{str(self.__class__).strip('<>')} object at {hex(id(self))}>"
    
    def __hash__(self):
        return(hash(str(self)))
        
    def _update(self):
        pass
        
    def check(self):
        collider = self.collider
        present_entities = set()
        for entity in self.check_group:
            if not isinstance(entity, self.check_types):
                continue
            if entity in collider:
                present_entities.add(entity)
                
        exit_entities = self._present_entities.difference(present_entities)
        enter_entities = present_entities.difference(self._present_entities)
        
        occupancy_change = bool(self._present_entities) != bool(present_entities)
        self._present_entities = present_entities
        if occupancy_change:
            [list(World.enqueue_event(func=func, args=(bool(present_entities),)) for func in self._triggers.get(TriggerTypes.OCCUPANCY))]
        [list(map(lambda e: World.enqueue_event(func=func, args=(e,)), present_entities)) for func in self._triggers.get(TriggerTypes.PRESENT)]
        [list(map(lambda e: World.enqueue_event(func=func, args=(e,)), enter_entities)) for func in self._triggers.get(TriggerTypes.ENTER)]
        [list(map(lambda e: World.enqueue_event(func=func, args=(e,)), exit_entities)) for func in self._triggers.get(TriggerTypes.EXIT)]
    
    def is_occupied(self):
        return bool(self._present_entities)
    
    def remove(self):
        self.parent.triggers.remove(self)
        self.instances.remove(self)
        self._present_entities = None
        self.parent = None
        

class World:
    instance:"World" = None
    
    animations:list = list()
    layers:dict[int, list[Entity]] = [list(), list(), list()]  # [0 = No collisions, 1 = bottom layer, 1+ = picked layers]
    
    events:list = list()
    updates:set[Entity] = set()
    renders:set[RenderContainer] = set()
    
    def __init__(self, canvas):
        self.canvas:tk.Canvas = canvas
        self._canvas_layers = list() 
        self.parent:"Entity" = None
        self.pos:Vector = Vector(0,0)
        self.children:list[Entity] = list()        
        
        self.__class__.instance = self
    
    @staticmethod
    def update_world():
        [x.check() for x in Trigger.instances]  # check Triggers and queue trigger events
        TIMINGS["t_trigger"] = time.process_time()
        # [x._update() for x in self.children]
        [x[0](*x[1], **x[2]) for x in World.events]  # execute queued trigger events (entities move with collision checks) + get marked for update
        World.events = list()
        TIMINGS["t_events"] = time.process_time()
        [x._update() for x in World.updates]  # execute recursive updates for changed entities + queue render calls
        World.updates = set()
        TIMINGS["t_updates"] = time.process_time()
        [x() for x in World.animations]  # queue updates for animations
        [x._render() for x in World.renders]  # execute queued render calls
        TIMINGS["t_render"] = time.process_time()
        World.renders = set()
        # clear queues
    
    @property
    def abs_pos(self) -> Vector:
        return self.pos
    
    @staticmethod
    def enqueue_event(func, args=None, kwargs=None):
        args = args if args else tuple()
        kwargs = kwargs if kwargs else dict()
        World.events.append([func, args, kwargs])
        
    def save(self) -> dict:
        return {"type": self.__class__.__name__, 
                "children": [x._to_json() for x in self.children if not x.dont_save]
                }

    def load(self, save_data) -> None:
        def recursive_load(self, save_data):
            [recursive_load(ENTITY_REGISTER.get(x.get("type"))._from_json(parent=self, save_data=x), x) for x in save_data.get("children", {})]
        # recursive_load(self, save_data)
        
        [ENTITY_REGISTER.get(x.get("type"))._from_json(parent=self, save_data=x) for x in save_data.get("children", {})]
