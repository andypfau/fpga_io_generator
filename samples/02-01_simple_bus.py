from context import src, demo_output_folder, prepare_output_folder

from src.bus.structure import WbMaster, WbSlave, WbBus, WbBusTopology
from src.bus.codegen import BusGraphGenerator, BusSvGenerator



if __name__ == '__main__':

    NAME = demo_output_folder() + '/02-01_simple_bus'
    prepare_output_folder()


    m = WbMaster('MCU', 32, 8, 16)
    s = WbSlave('RegisterSet', 0, 32, 8, 2)
    b = WbBus('MyBus', [m], [s])

    
    BusGraphGenerator(b, 'test.gv').graph.render()
