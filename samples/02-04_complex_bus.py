from context import src, demo_output_folder, prepare_output_folder

from src.bus.structure import WbMaster, WbSlave, WbBus, WbBusTopology
from src.bus.codegen import BusGraphGenerator, BusSvGenerator, BusMdGenerator



if __name__ == '__main__':

    NAME = demo_output_folder() + '/02-04_complex_bus'
    prepare_output_folder()

    m1 = WbMaster('MCU',           32, 8, 16)
    m2 = WbMaster('Debug',          8, 8, 24)
    
    # Note that we can use an ellipsis for any address, and the addresses will be assigned automatically
    s1 = WbSlave('User Interface',  8, 8,  5, 0x100)
    s2 = WbSlave('I/O Expander',   32, 8,  3, ...)
    s3 = WbSlave('PWM Generator',  16, 8,  3, ...)
    
    b = WbBus('My Bus', [m1, m2], [s1, s2, s3])

    BusSvGenerator(b).save(filename_code=f'{NAME}.sv')
    BusGraphGenerator(b).save(f'{NAME}.png')
    BusMdGenerator(b).save(f'{NAME}.md')
