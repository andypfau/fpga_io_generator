from context import src, demo_output_folder, prepare_output_folder

from src.bus.structure import WbMaster, WbSlave, WbBus, WbBusTopology
from src.bus.codegen import BusGraphGenerator, BusSvGenerator, BusMdGenerator



if __name__ == '__main__':

    NAME = demo_output_folder() + '/02-03_multi_slave'
    prepare_output_folder()

    m = WbMaster('MCU',            32,  8, 16)
    s1 = WbSlave('User Interface',  8,  8,  5, 0x0000)
    s2 = WbSlave('Io Expander',    32, 16,  3, 0x1000)
    s3 = WbSlave('PWM Generator',  16, 16,  3, 0x2000)
    b = WbBus('MyBus', [m], [s1, s2, s3])

    BusSvGenerator(b, 'my_bus').save(filename_code=f'{NAME}.sv')
    BusGraphGenerator(b).save(f'{NAME}.png')
    BusMdGenerator(b).save(f'{NAME}.md')
