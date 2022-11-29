module pwm (

	input rst_i,
	input clk_i,

	output red_o,
	output green_o,
	output blue_o,
	
	wishbone.slave wb_s
		
);


wire[9:0] red_value_field_w;
wire[9:0] green_value_field_w;
wire[9:0] blue_value_field_w;


pwm_reg pwm_reg_inst (
	.rst_i(rst_i),
	.clk_i(clk_i),
	.red_value_field_o(red_value_field_w),
	.green_value_field_o(green_value_field_w),
	.blue_value_field_o(blue_value_field_w),
	.wb_s(wb_s)
);


pwm_core #(
	.BITS(10),
	.CHANNELS(3)
) pwm_core_inst (
	.rst_i(rst_i),
	.clk_i(clk_i),
	.levels_i({ red_value_field_w, green_value_field_w, blue_value_field_w }),
	.channels_o({ red_o, green_o, blue_o })
);


endmodule
