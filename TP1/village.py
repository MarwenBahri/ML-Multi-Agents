import math
import random
import numpy as np
from collections import defaultdict

import uuid
import mesa
import numpy
import pandas
from mesa import space
from mesa.batchrunner import BatchRunner
from mesa.datacollection import DataCollector
from mesa.time import RandomActivation
from mesa.visualization.ModularVisualization import ModularServer, VisualizationElement, UserSettableParameter
from mesa.visualization.modules import ChartModule

class ContinuousCanvas(VisualizationElement):
    local_includes = [
        "./js/simple_continuous_canvas.js",
    ]

    def __init__(self, canvas_height=500,
                 canvas_width=500, instantiate=True):
        self.canvas_height = canvas_height
        self.canvas_width = canvas_width
        self.identifier = "space-canvas"
        if (instantiate):
            new_element = ("new Simple_Continuous_Module({}, {},'{}')".
                           format(self.canvas_width, self.canvas_height, self.identifier))
            self.js_code = "elements.push(" + new_element + ");"

    def portrayal_method(self, obj):
        return obj.portrayal_method()

    def render(self, model):
        representation = defaultdict(list)
        for obj in model.schedule.agents:
            portrayal = self.portrayal_method(obj)
            if portrayal:
                portrayal["x"] = ((obj.pos[0] - model.space.x_min) /
                                  (model.space.x_max - model.space.x_min))
                portrayal["y"] = ((obj.pos[1] - model.space.y_min) /
                                  (model.space.y_max - model.space.y_min))
            representation[portrayal["Layer"]].append(portrayal)
        return representation

class ChartModule(VisualizationElement):

    local_includes = [
        "./js/ChartModule.js",
        "./js/chart.min.js"
    ]

    def __init__(
        self,
        series,
        canvas_height=400,
        canvas_width=800,
        data_collector_name="data_collector",
    ):

        self.series = series
        self.canvas_height = canvas_height
        self.canvas_width = canvas_width
        self.data_collector_name = data_collector_name
        #series_json = json.dumps(self.series)
        new_element = ("new ChartModule({}, {},'{}')".
                           format(self.series, self.canvas_width, self.canvas_height))
        self.js_code = "elements.push(" + new_element + ");"
        
        #new_element = "new ChartModule({}, {},  {})"
        #new_element = new_element.format(series_json, canvas_width, canvas_height)
        #self.js_code = "elements.push(" + new_element + ");"

    
    def render(self, model):
        current_values = []
        data_collector = getattr(model, self.data_collector_name)
        data_collector.collect(model)
        
        for s in self.series:
            name = s["Label"]
            try:
                val = data_collector.model_vars[name][-1]  # Latest value

            except (IndexError, KeyError):
                val = 0
            current_values.append(val)
        return current_values

def wander(x, y, speed, model):
    r = random.random() * math.pi * 2
    new_x = max(min(x + math.cos(r) * speed, model.space.x_max), model.space.x_min)
    new_y = max(min(y + math.sin(r) * speed, model.space.y_max), model.space.y_min)

    return new_x, new_y

class  Village(mesa.Model):
    def  __init__(self,  n_villagers, n_lycanthropes, n_clerics, n_hunters):
        mesa.Model.__init__(self)
        self.space = mesa.space.ContinuousSpace(600, 600, False)
        self.schedule = RandomActivation(self)
        self.villagers = []
        self.wolfs = []
        self.clerics = []
        self.hunters = []
        
        self.data_collector =  DataCollector({"Werewolves": lambda m: len([i for i in m.wolfs if not i.transformed]),
                                "Transformed": lambda m: len([i for i in m.wolfs if i.transformed]),
                                "Total": lambda m: m.schedule.get_agent_count(),
                                "Population": lambda m: m.schedule.get_agent_count()-len(m.wolfs)})
        
        for  _  in  range(n_villagers+n_lycanthropes+n_clerics+n_hunters):
            if _ < n_villagers:
                self.villagers.append(Villager(random.random()  *  600,  random.random()  *  600,  10, _, self))
                self.schedule.add(self.villagers[-1])
                
            elif _ < n_villagers + n_lycanthropes:
                self.wolfs.append(Villager(random.random()  *  600,  random.random()  *  600,  10, _, self, wolf=True))
                self.schedule.add(self.wolfs[-1])

            elif _ < n_villagers + n_lycanthropes + n_clerics:

                self.clerics.append(Cleric(random.random()  *  600,  random.random()  *  600,  10, _, self))
                self.schedule.add(self.clerics[-1])
            else:
                self.hunters.append(Hunter(random.random()  *  600,  random.random()  *  600,  10, _, self))
                self.schedule.add(self.hunters[-1])
  
    def step(self):
        self.schedule.step()
        if self.schedule.steps >= 1000:
            self.running = False

class Villager(mesa.Agent):
    def __init__(self, x, y, speed, unique_id: int, model: Village, distance_attack=40, p_attack=0.6, wolf=False):
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.speed = speed
        self.model = model
        self.distance_attack = distance_attack
        self.p_attack = p_attack
        self.wolf = wolf
        self.transformed = False
        
    def portrayal_method(self):
        color = "red" if self.wolf else "blue"
        r = 3 if not self.transformed else 6
        portrayal = {"Shape": "circle",
                     "Filled": "true",
                     "Layer": 1,
                     "Color": color,
                     "r": r}
        return portrayal

    def step(self):
        if self.wolf and random.random() <= 0.1:
            self.transformed = True

        if self.wolf:
            rem = []
            for agent in self.model.villagers:
                dist = math.sqrt((agent.pos[0] - self.pos[0])**2 + (agent.pos[1] - self.pos[1])**2)
                if dist <= self.distance_attack:
                    agent.wolf = True
                    self.model.wolfs.append(agent)
                    rem.append(agent)
                    
            for agent in rem:
                self.model.villagers.remove(agent)
                    
        self.pos = wander(self.pos[0], self.pos[1], self.speed, self.model)

class Cleric(mesa.Agent):
    def __init__(self, x, y, speed, unique_id: int, model: Village, distance_attack=30, p_attack=0.6):
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.speed = speed
        self.model = model
        self.distance_attack = distance_attack
        self.p_attack = p_attack
        
    def portrayal_method(self):
        color = "green"
        r = 3 
        portrayal = {"Shape": "circle",
                     "Filled": "true",
                     "Layer": 1,
                     "Color": color,
                     "r": r}
        return portrayal

    def step(self):
        rem = []
        for agent in self.model.wolfs:
            if agent.transformed:
                continue
            dist = math.sqrt((agent.pos[0] - self.pos[0])**2 + (agent.pos[1] - self.pos[1])**2)
            if dist <= self.distance_attack:
                agent.wolf = False
                self.model.villagers.append(agent)
                rem.append(agent)

        for agent in rem:
            self.model.wolfs.remove(agent)
            
            
        self.pos = wander(self.pos[0], self.pos[1], self.speed, self.model)

class Hunter(mesa.Agent):
    def __init__(self, x, y, speed, unique_id: int, model: Village, distance_attack=40, p_attack=0.6):
        super().__init__(unique_id, model)
        self.pos = (x, y)
        self.speed = speed
        self.model = model
        self.distance_attack = distance_attack
        self.p_attack = p_attack
        
    def portrayal_method(self):
        color = "black"
        r = 3 
        portrayal = {"Shape": "circle",
                     "Filled": "true",
                     "Layer": 1,
                     "Color": color,
                     "r": r}
        return portrayal

    def step(self):
        rem = []
        for agent in self.model.wolfs:
            if not agent.transformed:
                continue
            dist = math.sqrt((agent.pos[0] - self.pos[0])**2 + (agent.pos[1] - self.pos[1])**2)
            if dist <= self.distance_attack:
                rem.append(agent)

        for agent in rem:
            self.model.wolfs.remove(agent)
            self.model.schedule.remove(agent)
            
        self.pos = wander(self.pos[0], self.pos[1], self.speed, self.model)


def run_single_server():
    server  =  ModularServer(Village, [ContinuousCanvas(), ChartModule([{"Label": "Population", "Color": "Orange"},
                                                                        {"Label": "Werewolves", "Color": "Red"},
                                                                        {"Label": "Transformed", "Color": "Brown"},
                                                                        {"Label": "Total", "Color": "black"}])],
                                                                    "Village",{"n_villagers":  UserSettableParameter('slider', "Villagers", 20, 10, 100, 1),
                                                                      "n_lycanthropes": UserSettableParameter('slider', "Werwolves", 5, 3, 50, 1),
                                                                      "n_clerics": UserSettableParameter('slider', "Clerics", 1, 1, 50, 1),
                                                                      "n_hunters": UserSettableParameter('slider', "Hunters", 2, 1, 50, 1)})
    server.port = 8521
    server.launch()


def run_batch():
    params = {"n_villagers":  [50],
            "n_lycanthropes": [5],
            "n_clerics": range(0, 6, 1),
            "n_hunters": [1]}

    batchrunner = BatchRunner(Village, params, model_reporters={"n_villagers": lambda m: len(m.villagers),
                                "n_lycanthropes": lambda m: len(m.wolfs),
                                "n_clerics": lambda m: len(m.clerics),
                                "n_hunters": lambda m: len(m.hunters)})
    batchrunner.port = 8521
    batchrunner.run_all()
    df = batchrunner.get_model_vars_dataframe()
    df.to_csv('params.csv')
if  __name__  ==  "__main__":
    run_batch()
