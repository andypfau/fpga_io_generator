from context import src, demo_output_folder, prepare_output_folder

from src.bus.structure import WbMaster, WbSlave, WbBus, WbBusTopology
from src.bus.codegen import BusGraphGenerator, BusSvGenerator, BusMdGenerator



if __name__ == '__main__':

    NAME = demo_output_folder() + '/02-01_simple_bus'
    prepare_output_folder()

    # We define a master and a slave; they both are compatible in this case (32 bit wide, 8 bit granularity)
    m = WbMaster('MCU', 32, 8, 16)
    s = WbSlave('Registers', 32, 8, 2, 0)

    # Now we define a simple bus, which only has that master and that slave
    b = WbBus('My Bus', [m], [s])


    # This class generates the SystemVerilog source code for that bus, plus a template for the instantiation.
    BusSvGenerator(b).save(
        filename_instance_template=f'{NAME}_instance_template.sv',
        filename_code=f'{NAME}.sv')


    # We can also generate a graph for that bus. The file format could also be e.g. PDF.
    BusGraphGenerator(b).save(f'{NAME}.png')


    # And finnaly we generate some documentation in Markdown-format
    BusMdGenerator(b).save(f'{NAME}.md')

    # Note that you will need some SystemVerilog files from the <include>-folder to synthesize the generated code.
