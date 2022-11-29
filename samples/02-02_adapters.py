from context import src, demo_output_folder, prepare_output_folder

from src.bus.structure import WbMaster, WbSlave, WbBus, WbBusTopology
from src.bus.codegen import BusGraphGenerator, BusSvGenerator, BusMdGenerator



if __name__ == '__main__':

    NAME = demo_output_folder() + '/02-02_adapters'
    prepare_output_folder()

    for mw,sw in [(32,16), (16,32)]:
        
        m = WbMaster('MCU', mw, 8, 16)
        s = WbSlave('Registers', sw, 8, 2, 0)
        b = WbBus('My Bus', [m], [s])

        BusSvGenerator(b).save(filename_code=f'{NAME}_{mw}-{sw}.sv')
        BusGraphGenerator(b).save(f'{NAME}_{mw}-{sw}.png')
        BusMdGenerator(b).save(f'{NAME}_{mw}-{sw}.md')
