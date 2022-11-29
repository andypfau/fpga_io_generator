from context import src, demo_output_folder, prepare_output_folder

from src.bus.structure import WbMaster, WbSlave, WbBus, WbBusTopology
from src.bus.codegen import BusGraphGenerator, BusSvGenerator, BusMdGenerator
from src.registers.structure import RegisterSet, Register, Field, FieldType, FieldFunction, RegType, WriteEventType, FieldChangeType
from src.registers.codegen import RegisterSvGenerator, RegisterPyGenerator, RegisterCGenerator, RegisterMdGenerator




if __name__ == '__main__':

    NAME = demo_output_folder() + '/03-01_registers+bus'
    prepare_output_folder()


    # In this example we will combine bus generation and register generation.

    
    # Some bus masters
    m_ctr = WbMaster('Control', 32, 8, 16)
    m_swp = WbMaster('Sweep', 16, 8, 16)


    # register to control the RGB-LEDs via PWM
    r_pwm = RegisterSet('PWM_Reg', 0x00, 16, [
        Register('red', 'PWM config for red', ..., RegType.Write, [
            Field('value', 'PWM value', [9,0], FieldType.Unsigned16Bit, FieldFunction.Overwrite)
        ]),
        Register('green', 'PWM config for green', ..., RegType.Write, [
            Field('value', 'PWM value', [9,0], FieldType.Unsigned16Bit, FieldFunction.Overwrite),
        ]),
        Register('blue', 'PWM config for blue', ..., RegType.Write, [
            Field('value', 'PWM value', [9,0], FieldType.Unsigned16Bit, FieldFunction.Overwrite),
        ]),
    ])
    
    # register to control the monochrome LEDs
    r_led = RegisterSet('LEDs', 0x10, 16, [
        Register('ctrl', 'LED Driver', ..., RegType.Write, [
            Field('led1', 'Enable LED 1', [0], FieldType.Boolean, FieldFunction.WriteMasked),
            Field('led2', 'Enable LED 2', [8], FieldType.Boolean, FieldFunction.WriteMasked),
        ])
    ])
    
    # register to configure the automatic sweep controller
    r_swp = RegisterSet('Sweep_Reg', 0x20, 32, [
        Register('ctrl1', 'Sweep config 1 (enable and delay)', ..., RegType.Write, write_event=WriteEventType.StrobeAfterWriteOnCycleEnd, fields=[
            Field('en', 'Enable PWM sweep', [0], FieldType.Boolean, FieldFunction.WriteShadow, default=0,
                comment='If sweeping is disabled, you can still control the PWM by configuring it directly'),
            Field('delay', 'Sweep delay', [10,1], FieldType.Unsigned16Bit, FieldFunction.WriteShadow, default=100)
        ]),
        Register('ctrl2', 'Sweep config 2 (sweep range)', ..., RegType.Write, [
            Field('incr', 'Sweep increment', [9,0], FieldType.Unsigned16Bit, FieldFunction.WriteShadow, default=5,
                comment='If sweeping is disabled, you can still control the PWM by configuring it directly'),
            Field('max', 'Sweep max value', [25,16], FieldType.Signed16Bit, FieldFunction.WriteShadow, default=500),
        ]),
    ])
    
    # register to query the push-buttons
    r_btn = RegisterSet('Buttons', 0x30, 8, [
        Register( 'buttons', 'Button status', ..., RegType.Read, [
            Field('btn1', 'Button 1 status', [0], FieldType.Boolean, FieldFunction.Read),
            Field('btn2', 'Button 2 status', [1], FieldType.Boolean, FieldFunction.Read),
        ]),
        Register('button_events', 'Button events', ..., RegType.ReadEvent, [
            Field('btn1', 'Button 1 was pressed', [0], FieldType.Boolean, FieldFunction.ReadShadow,
                trigger_on=FieldChangeType.High),
            Field( 'btn2', 'Button 2 status was pressed', [1], FieldType.Boolean, FieldFunction.ReadShadow,
                trigger_on=FieldChangeType.High),
        ]),
    ])
    
    # debug-register just for fun
    r_dbg = RegisterSet('Debug', 0x40, 16, [
        Register('debug1', 'Debug Register  #1', ..., RegType.Strobe, write_event=WriteEventType.StrobeAfterWriteOnCycleEnd, fields=[
            Field('test', 'Test', [0], FieldType.Boolean, FieldFunction.Strobe),
        ]),
        Register('debug2', 'Debug Register #2', ..., RegType.Handshake, [
            Field('test', 'Test', [0], FieldType.Boolean, FieldFunction.Strobe),
        ]),
        Register( 'debug3', 'Debug Register  #3', ..., RegType.WriteRead, [
            Field('test', 'Test', [15,0], FieldType.Signed16Bit,
                FieldFunction.Overwrite|FieldFunction.WriteShadow|FieldFunction.WriteMasked|FieldFunction.ReadShadow|FieldFunction.Read|FieldFunction.ReadModifyWrite),
        ]),
        Register('debug4', 'Debug Register  #4', ..., RegType.ReadEvent, [
            Field('toggle', 'Indicates that something toggled', [0], FieldType.Boolean, FieldFunction.Read,
                trigger_on=FieldChangeType.Rising|FieldChangeType.Falling),
            Field('high', 'Indicates that something else was high', [8], FieldType.Boolean, FieldFunction.ReadShadow,
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
    b = WbBus('MyBus', [m_ctr, m_swp], [s_rpm, s_led, s_swp, s_btn, s_dbg])

    
    for regset in [r_pwm, r_led, r_swp, r_btn, r_dbg]:
        code_name = regset.name.lower()
        RegisterSvGenerator(regset, modulename='my_registers').save(
            filename_instance_template=f'{NAME}_{code_name}_instance_template.sv',
            filename_code=f'{NAME}_{code_name}.sv')
        RegisterCGenerator(regset, NAME).save(
            filename_header=f'{NAME}_{code_name}.h',
            filename_code=f'{NAME}_{code_name}.c')
        RegisterPyGenerator(regset, regset.name).save(f'{NAME}_{code_name}.py')
        RegisterMdGenerator(regset, regset.name).save(f'{NAME}_{code_name}.md')
    BusSvGenerator(b, 'my_bus').save(filename_code=f'{NAME}.sv')
    BusGraphGenerator(b).save(f'{NAME}.png')
    BusMdGenerator(b).save(f'{NAME}.md')
