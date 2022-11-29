module sweep (

	input rst_i,
	input clk_i,

	// Wishbone master/slave
	wishbone.slave wb_s,
	wishbone.master wb_m

);


// target addresses for LED PWM control
localparam LED_BASE_ADDRESS = 'h00;
localparam LED_REG_RED   = 'h0;
localparam LED_REG_GREEN = 'h2;
localparam LED_REG_BLUE  = 'h4;
// no shift is needed: the master has range [:1], which swallows 1 bit, but since the common master
//   bus is 32 bit, we need 1 extra address bit, so the net shift is zero
localparam FINAL_ADDRESS_RED   = LED_BASE_ADDRESS | LED_REG_RED;
localparam FINAL_ADDRESS_GREEN = LED_BASE_ADDRESS | LED_REG_GREEN;
localparam FINAL_ADDRESS_BLUE  = LED_BASE_ADDRESS | LED_REG_BLUE;


wire sweep_en_w;
wire[9:0] delay_w;
wire[9:0] incr_w;
wire[9:0] max_w;
wire range_access_strobe_w;


sweep_reg reg_inst (
	.rst_i(rst_i),
	.clk_i(clk_i),
	.ctrl2_access_strobe_o(range_access_strobe_w),
	.ctrl1_en_flag_o(sweep_en_w),
	.ctrl1_delay_field_o(delay_w),
	.ctrl2_incr_field_o(incr_w),
	.ctrl2_max_field_o(max_w),
	.wb_s(wb_s)
);


enum { idle_sst, start_sst, red_sst, green_sst, blue_sst } sweep_state_r;
reg[9:0] red_r, green_r, blue_r;
reg red_update_r, green_update_r, blue_update_r;
reg[19:0] counter_r;
reg step_r;


always_ff @(posedge clk_i or posedge rst_i) begin
	if (rst_i) begin
		counter_r <= '0;
		step_r <= '0;
		red_r <= '0;
		green_r <= '0;
		blue_r <= '0;
		red_update_r <= '0;
		green_update_r <= '0;
		blue_update_r <= '0;
		sweep_state_r <= idle_sst;
	end else begin
		
		red_update_r <= '0;
		green_update_r <= '0;
		blue_update_r <= '0;
		
		if (sweep_en_w) begin
			if (counter_r == 0) begin
				counter_r <= { delay_w, 10'b0 };
				step_r <= '1;
			end else begin
				counter_r--;
				step_r <= '0;
			end
		end else begin
			counter_r <= '0;
			step_r <= '0;
		end
		
		case (sweep_state_r)
			
			idle_sst: begin
				if (sweep_en_w == 1)
					sweep_state_r <= start_sst;
			end

			start_sst: begin
				red_r   <= '0;
				green_r <= '0;
				blue_r  <= max_w;
				red_update_r   <= '1;
				green_update_r <= '1;
				blue_update_r  <= '1;
				sweep_state_r <= red_sst;
			end
			
			red_sst: begin
				if (sweep_en_w == 0) begin
					sweep_state_r <= idle_sst;
				end else if (range_access_strobe_w) begin
					sweep_state_r <= start_sst;
				end else if (red_r == max_w) begin
					red_r   <= max_w;
					green_r <= '0;
					blue_r  <= '0;
                    red_update_r   <= '1;
                    green_update_r <= '1;
                    blue_update_r  <= '1;
                    sweep_state_r <= green_sst;
                end else if (step_r) begin
                    red_r   <= red_r + incr_w;
                    green_r <= green_r;
                    blue_r  <= blue_r - incr_w;
                    red_update_r   <= '1;
                    green_update_r <= '0;
                    blue_update_r  <= '1;
                end
			end

			green_sst: begin
				if (sweep_en_w == 0) begin
					sweep_state_r <= idle_sst;
				end else if (range_access_strobe_w) begin
					sweep_state_r <= start_sst;
				end else if (green_r == max_w) begin
					red_r   <= '0;
					green_r <= max_w;
					blue_r  <= '0;
                    red_update_r   <= '1;
                    green_update_r <= '1;
                    blue_update_r  <= '1;
                    sweep_state_r <= blue_sst;
                end else if (step_r) begin
                    red_r   <= red_r   - incr_w;
                    green_r <= green_r + incr_w;
                    blue_r  <= blue_r;
                    red_update_r   <= '1;
                    green_update_r <= '1;
                    blue_update_r  <= '0;
                end
			end

			blue_sst: begin
				if (sweep_en_w == 0) begin
					sweep_state_r <= idle_sst;
				end else if (range_access_strobe_w) begin
					sweep_state_r <= start_sst;
				end else if (blue_r == max_w) begin
					red_r   <= '0;
					green_r <= '0;
					blue_r  <= max_w;
                    red_update_r   <= '1;
                    green_update_r <= '1;
                    blue_update_r  <= '1;
                    sweep_state_r <= red_sst;
                end else if (step_r) begin
                    red_r   <= red_r;
                    green_r <= green_r - incr_w;
                    blue_r  <= blue_r  + incr_w;
                    red_update_r   <= '0;
                    green_update_r <= '1;
                    blue_update_r  <= '1;
                end
			end

			default: begin
				sweep_state_r <= idle_sst;
			end
			
		endcase
	end
end


enum { check_mst, wait_mst } master_state_r;
reg red_pending_r, green_pending_r, blue_pending_r;


always_ff @(posedge clk_i or posedge rst_i) begin
	if (rst_i) begin
		master_state_r <= check_mst;
		red_pending_r <= '0;
		green_pending_r <= '0;
		blue_pending_r <= '0;
		wb_m.adr <= '0;
		wb_m.dat_ms <= '0;
		wb_m.stb <= '0;
		wb_m.cyc <= '0;
	end else begin
			
		case (master_state_r)
			
			check_mst: begin
				if (sweep_en_w == 1) begin
					if (red_pending_r) begin
						red_pending_r <= '0;
						wb_m.adr <= FINAL_ADDRESS_RED;
						wb_m.dat_ms <= red_r;
						wb_m.stb <= '1;
						wb_m.cyc <= '1;
						master_state_r <= wait_mst;
					end else if (green_pending_r) begin
						green_pending_r <= '0;
						wb_m.adr <= FINAL_ADDRESS_GREEN;
						wb_m.dat_ms <= green_r;
						wb_m.stb <= '1;
						wb_m.cyc <= '1;
						master_state_r <= wait_mst;
					end else if (blue_pending_r) begin
						blue_pending_r <= '0;
						wb_m.adr <= FINAL_ADDRESS_BLUE;
						wb_m.dat_ms <= blue_r;
						wb_m.stb <= '1;
						wb_m.cyc <= '1;
						master_state_r <= wait_mst;
					end
				end
			end

			wait_mst: begin
				if (wb_m.ack) begin
					wb_m.stb <= '0;
					wb_m.cyc <= '0;
					master_state_r <= check_mst;
				end
			end

			default: begin
				master_state_r <= check_mst;
			end
			
		endcase
		
		if (red_update_r)
			red_pending_r <= '1;
		if (green_update_r)
			green_pending_r <= '1;
		if (blue_update_r)
			blue_pending_r <= '1;
	end
end


assign wb_m.sel = '1;
assign wb_m.we = '1;


endmodule
