from context import src, workdir

from src.bus.structure import WbMaster, WbSlave, WbBus, WbBusTopology
from src.bus.codegen import BusGraphGenerator, BusSvGenerator, BusMdGenerator
from src.registers.structure import RegisterSet, Register, Field, FieldType, FieldFunction, RegType, WriteEventType, FieldChangeType
from src.registers.codegen import RegisterSvGenerator, RegisterPyGenerator, RegisterCGenerator, RegisterMdGenerator

import shutil



if __name__ == '__main__':

    DIR = f'{workdir()}/vivado_cmoda7/'


    # In this example we will combine bus generation and register generation.

    
    # Some bus masters
    m_ctr = WbMaster('External I/O', 32, 8, 16)
    m_swp = WbMaster('Sweep Master', 16, 8, 16)


    # register to control the RGB-LEDs via PWM
    r_pwm = RegisterSet('PWM Gen', 0x00, 16, [
        Register('Red', 'PWM config for red', ..., RegType.Write, [
            Field('Value', 'PWM value', [9,0], FieldType.Unsigned16Bit, FieldFunction.Overwrite)
        ]),
        Register('Green', 'PWM config for green', ..., RegType.Write, [
            Field('Value', 'PWM value', [9,0], FieldType.Unsigned16Bit, FieldFunction.Overwrite),
        ]),
        Register('Blue', 'PWM config for blue', ..., RegType.Write, [
            Field('Value', 'PWM value', [9,0], FieldType.Unsigned16Bit, FieldFunction.Overwrite),
        ]),
    ])
    
    # register to control the monochrome LEDs
    r_led = RegisterSet('LEDs', 0x10, 16, [
        Register('Control', 'LED Driver', ..., RegType.Write, [
            Field('LED 1', 'Enable LED 1', [0], FieldType.Boolean, FieldFunction.WriteMasked),
            Field('LED 2', 'Enable LED 2', [8], FieldType.Boolean, FieldFunction.WriteMasked),
        ])
    ])
    
    # register to configure the automatic sweep controller
    r_swp = RegisterSet('Sweep Gen', 0x20, 32, [
        Register('Control 1', 'Sweep config 1 (enable and delay)', ..., RegType.Write, write_event=WriteEventType.StrobeAfterWriteOnCycleEnd, fields=[
            Field('En', 'Enable PWM sweep', [0], FieldType.Boolean, FieldFunction.WriteShadow, default=0,
                comment='If sweeping is disabled, you can still control the PWM by configuring it directly'),
            Field('Delay', 'Sweep delay', [10,1], FieldType.Unsigned16Bit, FieldFunction.WriteShadow, default=100)
        ]),
        Register('Control 2', 'Sweep config 2 (sweep range)', ..., RegType.Write, [
            Field('Incr', 'Sweep increment', [9,0], FieldType.Unsigned16Bit, FieldFunction.WriteShadow, default=5,
                comment='If sweeping is disabled, you can still control the PWM by configuring it directly'),
            Field('Max', 'Sweep max value', [25,16], FieldType.Signed16Bit, FieldFunction.WriteShadow, default=500),
        ]),
    ])
    
    # register to query the push-buttons
    r_btn = RegisterSet('Buttons', 0x30, 8, [
        Register('Buttons', 'Button status', ..., RegType.Read, [
            Field('Btn1', 'Button 1 status', [0], FieldType.Boolean, FieldFunction.Read),
            Field('Btn2', 'Button 2 status', [1], FieldType.Boolean, FieldFunction.Read),
        ]),
        Register('Button Events', 'Button events', ..., RegType.ReadEvent, [
            Field('Btn1', 'Button 1 was pressed', [0], FieldType.Boolean, FieldFunction.ReadShadow,
                trigger_on=FieldChangeType.High),
            Field('Btn2', 'Button 2 status was pressed', [1], FieldType.Boolean, FieldFunction.ReadShadow,
                trigger_on=FieldChangeType.High),
        ]),
    ])
    
    # debug-register just for fun
    r_dbg = RegisterSet('Debug', 0x40, 16, [
        Register('Debug 1', 'Debug Register #1', ..., RegType.Strobe, write_event=WriteEventType.StrobeAfterWriteOnCycleEnd, fields=[
            Field('Test', 'Test', [0], FieldType.Boolean, FieldFunction.Strobe),
        ]),
        Register('Debug 2', 'Debug Register #2', ..., RegType.Handshake, [
            Field('Test', 'Test', [0], FieldType.Boolean, FieldFunction.Strobe),
        ]),
        Register('Debug 3 ', 'Debug Register #3', ..., RegType.WriteRead, [
            Field('Test', 'Test', [15,0], FieldType.Signed16Bit,
                FieldFunction.Overwrite|FieldFunction.WriteShadow|FieldFunction.WriteMasked|FieldFunction.ReadShadow|FieldFunction.Read|FieldFunction.ReadModifyWrite),
        ]),
        Register('Debug 4', 'Debug Register #4', ..., RegType.ReadEvent, [
            Field('Toggle', 'Indicates that something toggled', [0], FieldType.Boolean, FieldFunction.Read,
                trigger_on=FieldChangeType.Rising|FieldChangeType.Falling),
            Field('High', 'Indicates that something else was high', [8], FieldType.Boolean, FieldFunction.ReadShadow,
                trigger_on=FieldChangeType.High),
        ], comment='Register to test event functionality')
    ])
    
    
    # Now we turn the registers into bus slaves
    s_rpm = WbSlave.from_register_set(r_pwm)
    s_led = WbSlave.from_register_set(r_led)
    s_swp = WbSlave.from_register_set(r_swp)
    s_btn = WbSlave.from_register_set(r_btn)
    s_dbg = WbSlave.from_register_set(r_dbg)
    
    
    # And we create a bus from all of those components
    # Note that adding the slaves to the bus will assign base addresses to the slaves
    b = WbBus('My Bus', [m_ctr, m_swp], [s_rpm, s_led, s_swp, s_btn, s_dbg])

    
    py_fmt = RegisterPyGenerator.Format(
        read_func='read_reg',
        write_func='write_reg',
        write_masked_func='write_reg',
        accessor_obj=True,
        import_clauses=[])
    
    for regset in [r_pwm, r_led, r_swp, r_btn, r_dbg]:
        code_name = regset.name.lower().replace(' ', '_')
        RegisterSvGenerator(regset).save(filename_code=f'{DIR}/hardware/remote_if_demo.srcs/hdl/{code_name}.sv')
        RegisterPyGenerator(regset, format=py_fmt).save(f'{DIR}/software/{code_name}.py')
        RegisterMdGenerator(regset).save(f'{DIR}/docs/{code_name}.md')
    BusSvGenerator(b).save(filename_code=f'{DIR}/hardware/remote_if_demo.srcs/hdl/wb_bus.sv')
    BusGraphGenerator(b).save(f'{DIR}/docs/bus.png')
    BusMdGenerator(b, graph_filename=f'bus.png').save(f'{DIR}/docs/bus.md')

    # copy some include-files
    shutil.copy(f'{workdir()}/../include/wb_interface.sv', f'{DIR}/hardware/remote_if_demo.srcs/hdl')
    shutil.copy(f'{workdir()}/../include/wb_arbiter.sv', f'{DIR}/hardware/remote_if_demo.srcs/hdl')
    shutil.copy(f'{workdir()}/../include/wb_adapter.sv', f'{DIR}/hardware/remote_if_demo.srcs/hdl')
