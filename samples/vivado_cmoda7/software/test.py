from buttons import Buttons
from pwm_gen import PwmGen
from sweep_gen import SweepGen
from leds import Leds
from serialcomm import SerialComm
import time


#PORTNAME = '/dev/ttyUSBartix7'
PORTNAME = 'COM11'


com = SerialComm(PORTNAME, verbose=False)
buttons = Buttons(com)
sweep = SweepGen(com)
leds = Leds(com)
pwm = PwmGen(com)


# for i in range(9999999):
#     leds.set_control_led_1_masked(True if i % 2 == 0 else False)
#     leds.set_control_led_2_masked(True if i % 2 != 0 else False)
#     print(f'Buttons: {buttons.get_buttons_btn1()}, {buttons.get_buttons_btn2()}')
#     time.sleep(0.2)

leds.set_control_led_1_masked(True)
leds.set_control_led_2_masked(False)

print(buttons.get_buttons_btn1())
print(buttons.get_buttons_btn2())

# sweep.set_control_1_en_shadow(False, flush=True)
# pwm.set_red_value_overwrite(200)
# pwm.set_green_value_overwrite(0)
# pwm.set_blue_value_overwrite(0)

sweep.set_control_1_delay_shadow(1500)
sweep.set_control_2_incr_shadow(5)
sweep.set_control_2_max_shadow(200)
sweep.set_control_1_en_shadow(True)
sweep.flush_shadow()
