module bus_tb();

logic rst, clk;

////////////////////////////////////////////////////////////
// Faux UART

logic[7:0] uart_rx_data_w;
logic uart_rx_strobe_w;
logic[7:0] uart_tx_data_w;
logic uart_tx_strobe_w;
logic uart_tx_ready_w;


////////////////////////////////////////////////////////////
// Wishbone

wishbone #(.ADR_BITS(16), .PORT_SIZE(32), .GRANULARITY(8)) ctrl_wbm();
wishbone #(.ADR_BITS(16), .PORT_SIZE(16), .GRANULARITY(8)) sweep_wbm();

wishbone #(.ADR_BITS(1), .PORT_SIZE(8), .GRANULARITY(8)) btns_wbs();
wishbone #(.ADR_BITS(1), .PORT_SIZE(16), .GRANULARITY(8)) leds_wbs();
wishbone #(.ADR_BITS(2), .PORT_SIZE(16), .GRANULARITY(8)) pwm_wbs();
wishbone #(.ADR_BITS(1), .PORT_SIZE(32), .GRANULARITY(8)) sweep_wbs();

wb_bus wb_bus_inst (
	.rst_i(rst),
	.clk_i(clk),
	.Control_mi(ctrl_wbm),
	.Sweep_mi(sweep_wbm),
	.Buttons_so(btns_wbs),
	.LEDs_so(leds_wbs),
	.PWM_Reg_so(pwm_wbs),
	.Sweep_Reg_so(sweep_wbs)
);



////////////////////////////////////////////////////////////
// interface translator

ascii2wb #(
    .TERM_CHAR('h0A), // 10 = \n; PuTTY: CTRl+J
    .DATA_NIBBLES(8),
    .MASK_BITS(4),
    .ADDR_NIBBLES(4)
) ascii2wb_inst (
    .rst_i(rst),
    .clk_i(clk),
    .ascii_rx_data_i(uart_rx_data_w),
    .ascii_rx_strobe_i(uart_rx_strobe_w),
    .ascii_tx_data_o(uart_tx_data_w),
    .ascii_tx_strobe_o(uart_tx_strobe_w),
    .ascii_tx_ready_i(uart_tx_ready_w),
    .wb_m(ctrl_wbm)
);


////////////////////////////////////////////////////////////
// Static LED control

logic led1_w, led2_w;

leds leds_inst (
	.rst_i(rst),
	.clk_i(clk),
	.ctrl_led1_flag_o(led1_w),
	.ctrl_led2_flag_o(led2_w),
	.wb_s(leds_wbs)
);


////////////////////////////////////////////////////////////
// PWM LED control

logic led0r_w, led0g_w, led0b_w;

pwm pwm_inst (
	.rst_i(rst),
	.clk_i(clk),
	.red_o(led0r_w),
	.green_o(led0g_w),
	.blue_o(led0b_w),
	.wb_s(pwm_wbs)
);


////////////////////////////////////////////////////////////
// PWM Sweep

sweep sweep_inst (
	.rst_i(rst),
	.clk_i(clk),
	.wb_s(sweep_wbs),
	.wb_m(sweep_wbm)
);


////////////////////////////////////////////////////////////
// Buttons

logic btn1_w, btn2_w;

buttons buttons_inst (
	.rst_i(rst),
	.clk_i(clk),
	.buttons_btn1_flag_i(btn1_w),
	.buttons_btn2_flag_i(btn2_w),
	.button_events_btn1_flag_i(btn1_w),
	.button_events_btn2_flag_i(btn2_w),
	.wb_s(btns_wbs)
);

assign btn1_w = 0;
assign btn2_w = 1;


////////////////////////////////////////////////////////////
// Stimulus

`define send_char(char) \
	uart_rx_data_w <= char; \
	uart_rx_strobe_w <= '1; \
	@(posedge clk); \
	uart_rx_strobe_w <= '0; \
	@(posedge clk); \
	@(posedge clk);

`define send_str(str) \
	foreach(str[i]) begin \
		`send_char(str[i]); \
	end

`define read_str(buf) \
	buf = ""; \
	for (int i = 0; ; i++) begin \
		@(posedge clk); \
		if (uart_tx_strobe_w==1) begin \
			if (uart_tx_data_w=='h0A) \
				break; \
			buf={$sformatf("%s%s",buf,uart_tx_data_w)}; \
		end \
		if (i>=100) begin\
			$error("Timeout during read"); \
			break; \
		end \
	end

`define write_and_read(buf) \
	`send_str(buf); \
	`read_str(buf);

initial begin
	
	string cmd;
	
	uart_rx_data_w <= '0;
	uart_rx_strobe_w <= '0;
	uart_tx_ready_w <= '1;
	
	clk = 0;
	rst = 1;
	@(posedge clk);
	@(posedge clk);
	rst = 0;
	
	for (int i = 0; i < 100; i++) @(posedge clk);

	$info("Read button status (address 0x30)");
	cmd = "r000c\n";
	`write_and_read(cmd);
	$info("Button status query: '%s'",cmd);
	@(posedge clk);

	$info("Set all LEDs to on (address 0x10)");
	cmd = "w0004fffffffff\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	$info("Set all LEDs to off (address 0x10)");
	cmd = "w000400000000f\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);
	

	for (int i = 0; i < 4000; i++) @(posedge clk);


	$info("Programming red PWM to 0 (address 0x04)");
	cmd = "w000000000000f\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	$info("Programming green PWM to 1 (address 0x04)");
	cmd = "w000100000001f\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	$info("Programming blue PWM to 2 (address 0x04)");
	cmd = "w000200000002f\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);
	
	for (int i = 0; i < 4000; i++) @(posedge clk);

	$info("Programming red PWM to 3 (address 0x04)");
	cmd = "w000000000003f\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	$info("Programming green PWM to 4 (address 0x04)");
	cmd = "w000100000004f\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	$info("Programming blue PWM to 5 (address 0x04)");
	cmd = "w000200000005f\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);
	
	for (int i = 0; i < 4000; i++) @(posedge clk);

	$info("Programming red PWM to 256 (address 0x04)");
	cmd = "w000000000100f\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	$info("Programming green PWM to 512 (address 0x04)");
	cmd = "w000100000200f\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	$info("Programming blue PWM to 768 (address 0x04)");
	cmd = "w000200000300f\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);
	
	for (int i = 0; i < 4000; i++) @(posedge clk);

	$info("Programming red PWM to 1018 (address 0x04)");
	cmd = "w000000000ffaf\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	$info("Programming green PWM to 1019 (address 0x04)");
	cmd = "w000100000ffbf\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	$info("Programming blue PWM to 1020 (address 0x04)");
	cmd = "w000200000ffcf\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);
	
	for (int i = 0; i < 4000; i++) @(posedge clk);

	$info("Programming red PWM to 1021 (address 0x04)");
	cmd = "w000000000ffdf\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	$info("Programming green PWM to 1022 (address 0x04)");
	cmd = "w000100000ffef\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	$info("Programming blue PWM to 1023 (address 0x04)");
	cmd = "w000200000ffff\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	
	for (int i = 0; i < 4000; i++) @(posedge clk);
	
	
	$info("Configuring Sweep (address 0x21)");
	cmd = "w000902000040f\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);

	$info("Configuring Sweep (address 0x20)");
	cmd = "w000800000007f\n";
	`write_and_read(cmd);
	$info("Response: '%s'",cmd);
	@(posedge clk);
	
	for (int i = 0; i < 100000; i++) @(posedge clk);
	
	//for (int i = 0; i < 100000; i++) @(posedge clk);
	
	$stop;
end


always
	#10 clk = ~clk;


endmodule

