from buttons import Buttons
from pwm_reg import PwmReg
from sweep_reg import SweepReg
from leds import Leds
from serialcomm import SerialComm
from serial_to_wb import SerialToWb
import time


#PORTNAME = '/dev/ttyUSBartix7'
PORTNAME = 'COM11'


com = SerialComm(PORTNAME, verbose=False)
wb = SerialToWb(com)
buttons = Buttons(wb)
sweep = SweepReg(wb)
leds = Leds(wb)
pwm = PwmReg(wb)


# sweep RGB-LED
sweep.set_control_1_delay_shadow(50)
sweep.set_control_2_incr_shadow(5)
sweep.set_control_2_max_shadow(200)
sweep.set_control_1_en_shadow(True)
sweep.flush_shadow()


# loop to toggle LEDs and check buttons
toggle = False
while True:
    
    leds.set_control_led_1_masked(toggle)
    leds.set_control_led_2_masked(not toggle)
    
    print(f'Buttons: {buttons.get_buttons_btn1()}, {buttons.get_buttons_btn2()}')
    
    time.sleep(0.2)
    toggle = not toggle
