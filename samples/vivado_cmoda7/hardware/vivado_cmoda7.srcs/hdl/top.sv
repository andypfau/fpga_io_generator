
module top (

    input clk_i,
    
    output led1_o, led2_o,
    output led0r_o, led0g_o, led0b_o,
    
    input btn1_i, btn2_i,
    
    output uart_tx_o,
    input uart_rx_i

);


localparam CLK_FREQ = 12.0e6;
localparam BAUD_RATE = 115384;


////////////////////////////////////////////////////////////
// reset generator

reg[3:0] rst_shiftreg_r;

initial
    rst_shiftreg_r <= '1;

always_ff @(posedge clk_i)
    rst_shiftreg_r <= { 1'b0, rst_shiftreg_r[$high(rst_shiftreg_r):1] };


wire rst_w;

assign rst_w = rst_shiftreg_r[0];


////////////////////////////////////////////////////////////
// UART

wire[7:0] uart_rx_data_w;
wire uart_rx_strobe_w;
wire[7:0] uart_tx_data_w;
wire uart_tx_strobe_w;
wire uart_tx_ready_w;


uart #(
    .CLOCKFREQ(CLK_FREQ),
    .BAUDRATE(BAUD_RATE),
    .REGSIZE(8)
) uart_inst (
	.rst_i(rst_w),
	.clk_i(clk_i),
	.txd_o(uart_tx_o),
	.rxd_i(uart_rx_i),
	
	.rx_data_o(uart_rx_data_w),
    .rx_strobe_o(uart_rx_strobe_w),
    
	.tx_data_i(uart_tx_data_w),
	.tx_strobe_i(uart_tx_strobe_w),
	.tx_ready_o(uart_tx_ready_w)
	
);


////////////////////////////////////////////////////////////
// Wishbone

wishbone #(.ADR_BITS(16), .PORT_SIZE(32), .GRANULARITY(8)) ctrl_wbm();
wishbone #(.ADR_BITS(16), .PORT_SIZE(16), .GRANULARITY(8)) sweep_wbm();

/*wishbone #(.ADR_BITS(1), .PORT_SIZE(8), .GRANULARITY(8)) btns_wbs();
wishbone #(.ADR_BITS(1), .PORT_SIZE(16), .GRANULARITY(8)) leds_wbs();
wishbone #(.ADR_BITS(2), .PORT_SIZE(16), .GRANULARITY(8)) pwm_wbs();
wishbone #(.ADR_BITS(1), .PORT_SIZE(32), .GRANULARITY(8)) sweep_wbs();*/
wishbone #(.ADR_BITS(16), .PORT_SIZE(8), .GRANULARITY(8)) btns_wbs();
wishbone #(.ADR_BITS(16), .PORT_SIZE(16), .GRANULARITY(8)) leds_wbs();
wishbone #(.ADR_BITS(16), .PORT_SIZE(16), .GRANULARITY(8)) pwm_wbs();
wishbone #(.ADR_BITS(16), .PORT_SIZE(32), .GRANULARITY(8)) sweep_wbs();


my_bus wb_bus_inst (
	.rst_i(rst_w),
	.clk_i(clk_i),
	.external_io_mi(ctrl_wbm),
	.sweep_master_mi(sweep_wbm),
	.buttons_so(btns_wbs),
	.leds_so(leds_wbs),
	.pwm_reg_so(pwm_wbs),
	.sweep_reg_so(sweep_wbs)
);


////////////////////////////////////////////////////////////
// interface translator

ascii2wb #(
    .TERM_CHAR('h0A), // 10 = \n; PuTTY: CTRl+J
    .DATA_NIBBLES(8),
    .MASK_BITS(4),
    .ADDR_NIBBLES(4)
) ascii2wb_inst (
    .rst_i(rst_w),
    .clk_i(clk_i),
    .ascii_rx_data_i(uart_rx_data_w),
    .ascii_rx_strobe_i(uart_rx_strobe_w),
    .ascii_tx_data_o(uart_tx_data_w),
    .ascii_tx_strobe_o(uart_tx_strobe_w),
    .ascii_tx_ready_i(uart_tx_ready_w),
    .wb_m(ctrl_wbm)
);


////////////////////////////////////////////////////////////
// Static LED control

leds leds_inst (
	.rst_i(rst_w),
	.clk_i(clk_i),
	.control_led_1_flag_o(led1_o),
	.control_led_2_flag_o(led2_o),
	.wb_s(leds_wbs)
);


////////////////////////////////////////////////////////////
// PWM LED control

pwm pwm_inst (
	.rst_i(rst_w),
	.clk_i(clk_i),
	.red_o(led0r_w),
	.green_o(led0g_w),
	.blue_o(led0b_w),
	.wb_s(pwm_wbs)
);


////////////////////////////////////////////////////////////
// PWM Sweep

sweep sweep_inst (
	.rst_i(rst_w),
	.clk_i(clk_i),
	.wb_s(sweep_wbs),
	.wb_m(sweep_wbm)
);


////////////////////////////////////////////////////////////
// Buttons

buttons buttons_inst (
	.rst_i(rst_w),
	.clk_i(clk_i),
	.buttons_btn1_flag_i(btn1_i),
	.buttons_btn2_flag_i(btn2_i),
	.button_events_btn1_flag_i(btn1_i),
	.button_events_btn2_flag_i(btn2_i),
	.wb_s(btns_wbs)
);


////////////////////////////////////////////////////////////
// I/O

assign led0r_o = ~led0r_w;
assign led0g_o = ~led0g_w;
assign led0b_o = ~led0b_w;


endmodule
