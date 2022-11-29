# prepare working library
transcript on
if {[file exists rtl_work]} {
	vdel -lib rtl_work -all
}
vlib rtl_work
vmap work rtl_work

# compile source files
vlog -work work {bus_tb.sv}
vlog -work work {../remote_if_demo.srcs/hdl/wb_interface.sv}
vlog -work work {../remote_if_demo.srcs/hdl/wb_bus.sv}
vlog -work work {../remote_if_demo.srcs/hdl/wb_bus_arbiter.sv}
vlog -work work {../remote_if_demo.srcs/hdl/wb_adapter.sv}
vlog -work work {../remote_if_demo.srcs/hdl/ascii2wb.sv}
vlog -work work {../remote_if_demo.srcs/hdl/buttons.sv}
vlog -work work {../remote_if_demo.srcs/hdl/leds.sv}
vlog -work work {../remote_if_demo.srcs/hdl/pwm.sv}
vlog -work work {../remote_if_demo.srcs/hdl/pwm_core.sv}
vlog -work work {../remote_if_demo.srcs/hdl/pwm_reg.sv}
vlog -work work {../remote_if_demo.srcs/hdl/sweep.sv}
vlog -work work {../remote_if_demo.srcs/hdl/sweep_reg.sv}

# simulate testbench
vsim \
	-t 1ns \
	-L altera \
	-L altera_mf \
	-L lpm \
	-L sgate \
	-L cyclonev \
	-L rtl_work \
	-L work \
	-voptargs="+acc" \
	-msgmode both \
	-displaymsgmode both \
	bus_tb

# add memories and unpacked arrays to waveform when using wildcards
set WildcardFilter [lsearch -not -all -inline $WildcardFilter Memory]

# add signals to waveform viewer
add wave -group TB        sim:bus_tb/*
add wave -group TB -group ControlM    -r sim:bus_tb/ctrl_wbm/*
add wave -group TB -group SweepM      -r sim:bus_tb/sweep_wbm/*
add wave -group TB -group BtnsS       -r sim:bus_tb/btns_wbs/*
add wave -group TB -group LedsS       -r sim:bus_tb/leds_wbs/*
add wave -group TB -group PwmS        -r sim:bus_tb/pwm_wbs/*
add wave -group TB -group SweepS      -r sim:bus_tb/sweep_wbs/*
add wave -group ASCII2WB  sim:bus_tb/ascii2wb_inst/*
add wave -group Sweep     sim:bus_tb/sweep_inst/*
add wave -group PWM       sim:bus_tb/pwm_inst/*
add wave -group PWM -group PWM      sim:bus_tb/pwm_inst/pwm_core_inst/*
add wave -group Bus       sim:bus_tb/wb_bus_inst/*
add wave -group Bus -group SweepMAdapted  -r sim:bus_tb/wb_bus_inst/Sweep_adapted_w/*
add wave -group Bus -group BtnsSAdapted   -r sim:bus_tb/wb_bus_inst/Buttons_adapted_w/*
add wave -group Bus -group LedsSAdapted   -r sim:bus_tb/wb_bus_inst/LEDs_adapted_w/*
add wave -group Bus -group PwmSAdapted    -r sim:bus_tb/wb_bus_inst/PWM_Reg_adapted_w/*

# run simulation
run -all
