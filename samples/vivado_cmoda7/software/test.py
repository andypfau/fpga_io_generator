from buttons import Buttons
from pwm_reg import PWM_Reg
from sweep_reg import Sweep_Reg
from leds import LEDs
from serialcomm import SerialComm
import time


#PORTNAME = '/dev/ttyUSBartix7'
PORTNAME = 'COM11'


com = SerialComm(PORTNAME, verbose=False)
buttons = Buttons(com)
sweep = Sweep_Reg(com)
leds = LEDs(com)
pwm = PWM_Reg(com)


# for i in range(9999999):
#     leds.set_ctrl_led1_masked(True if i % 2 == 0 else False)
#     leds.set_ctrl_led2_masked(True if i % 2 != 0 else False)
#     print(f'Buttons: {buttons.get_buttons_btn1()}, {buttons.get_buttons_btn2()}')
#     time.sleep(0.2)

leds.set_ctrl_led1_masked(True)
leds.set_ctrl_led2_masked(False)

print(buttons.get_buttons_btn1())
print(buttons.get_buttons_btn2())

# sweep.set_ctrl1_en_shadow(False, flush=True)
# pwm.set_red_value_overwrite(200)
# pwm.set_green_value_overwrite(0)
# pwm.set_blue_value_overwrite(0)

sweep.set_ctrl1_delay_shadow(1500)
sweep.set_ctrl2_incr_shadow(5)
sweep.set_ctrl2_max_shadow(200)
sweep.set_ctrl1_en_shadow(True)
sweep.flush_shadow()

# com.write_reg(0x20, (1<<0) | (1000<<1))
# com.write_reg(0x24, (2<<0) | (100<<16))
