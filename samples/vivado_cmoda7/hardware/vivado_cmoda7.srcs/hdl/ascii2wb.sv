/*
 * Adapter from a streaming interface with 8-bit ASCII symbols (e.g. UART) to Wishbone master
 * 
 * Example:
 *   Consider DATA_NIBBLES=4, MASK_BITS=4, ADDR_NIBBLES=4.
 *   To read from register 0x1234, send "r1234\n" ("r"=read); the response will be e.g. "oABCD\n" for data "0xABCD" ("o"=OK).
 *   To write 0x0123 with mask 0b0111 to register 0x2345, send "w234501237\n" ("w"=write); the response will be "o\n".
 *   To keep cyc=high after the transfer, use an upper-case letter "w" or "r" instead, e.g. "R1234\n".
 *   In the case of an error, the response will be "e\n" (invalid request) or "t\n" (Wishbone slave did not acknowledge).
 *   Note that all hex letters must be lower-case.
 * 
 */

module ascii2wb #(

    parameter TERM_CHAR = 'h0A, // ASCII character
    
    // number of nibbles used for ASCII communication
    parameter DATA_NIBBLES = 8,
    parameter MASK_BITS = 1,
    parameter ADDR_NIBBLES = 2

) (
    input rst_i, clk_i,

    input[7:0] ascii_rx_data_i,
    input ascii_rx_strobe_i,
    output[7:0] ascii_tx_data_o,
    output ascii_tx_strobe_o,
    input ascii_tx_ready_i,
    
    // Wishbone master
	wishbone.master wb_m

);


localparam CMD_WRITE_CHAR      = 'h77; // "w"
localparam CMD_WRITE_HOLD_CHAR = 'h57; // "W"
localparam CMD_READ_CHAR       = 'h72; // "r"
localparam CMD_READ_HOLD_CHAR  = 'h52; // "R"

localparam RESP_OK_CHAR      = 'h6F; // "o"
localparam RESP_ERR_CHAR     = 'h65; // "e"
localparam RESP_TIMEOUT_CHAR = 'h74; // "t"

localparam CHAR_0 = 'h30; // "0"
localparam CHAR_9 = 'h39; // "9"
localparam CHAR_A = 'h61; // "a"
localparam CHAR_F = 'h66; // "f"

function integer max(input integer a, b);
    max = (a > b) ? a : b;
endfunction : max

function integer ceildiv(input integer a, b);
    ceildiv = (a + b - 1) / b;
endfunction : ceildiv

//localparam MASK_NIBBLES = 1; // HACK to make ModelSim happy
localparam MASK_NIBBLES = ceildiv(MASK_BITS, 4);

localparam NIBBLES_MAX =  max(max(ADDR_NIBBLES, DATA_NIBBLES), MASK_NIBBLES); 
localparam CNT_MAX = (NIBBLES_MAX+1)-1;
localparam CNT_BITS = $clog2(CNT_MAX+1);


enum {
    state_start,
    state_receive_command,
    state_receive_address,
    state_receive_data,
    state_receive_mask,
    state_receive_term,
    state_wb_wait,
    state_serialize,
    state_respond,
    state_term,
    state_error
} state_r;

reg[CNT_BITS-1:0] cnt_r;
reg[7:0] timer_r;
reg[(DATA_NIBBLES+1)*8-1:0] resp_r; // need one byte per nibble, plus 1 extra byte for status-char
reg cyc_after_xfer_r;

reg[7:0] ascii_tx_data_r;
reg ascii_tx_strobe_r;
reg[DATA_NIBBLES*4-1:0] wb_dat_ms; // need 4 bit per nibble
reg[ADDR_NIBBLES*4-1:0] wb_adr_r;
reg[MASK_NIBBLES*4-1:0] wb_sel_r;
reg wb_stb_r;
reg wb_we_r;
reg wb_cyc_r;
reg[DATA_NIBBLES*4-1:0] wb_dat_i_r;


// FSM
always_ff @ (posedge rst_i or posedge clk_i) begin

    logic[3:0] nibble_v;
    logic[7:0] byte_v;

    if (rst_i) begin
        
        state_r <= state_start;
        cnt_r <= '0;
        resp_r <= '0;
        cyc_after_xfer_r <= 0;
        
        ascii_tx_data_r <= '0;
        ascii_tx_strobe_r <= '0;
        wb_dat_ms <= '0;
        wb_adr_r <= '0;
        wb_sel_r <= '0;
        wb_cyc_r <= '0;
        wb_stb_r <= '0;
        wb_we_r <= '0;
        wb_dat_i_r <= '0;
		timer_r <= '0;
        
    end else begin
        
		// defaults
        ascii_tx_strobe_r <= '0;
		timer_r <= timer_r - 1;
        
        case (state_r)
            
            state_start: begin
                cnt_r <= ADDR_NIBBLES-1;
                wb_dat_ms <= '0;
                wb_adr_r <= '0;
                wb_we_r <= '0;
                state_r <= state_receive_command;
            end
            
            state_receive_command: begin
            
                if (ascii_rx_strobe_i == 1) begin
                    if (ascii_rx_data_i == CMD_WRITE_CHAR) begin
                        wb_we_r <= '1;
                        cyc_after_xfer_r <= 0;
                        state_r <= state_receive_address;
                    end else if (ascii_rx_data_i == CMD_WRITE_HOLD_CHAR) begin
                        wb_we_r <= '1;
                        cyc_after_xfer_r <= 1;
                        state_r <= state_receive_address;
                    end else if (ascii_rx_data_i == CMD_READ_CHAR) begin
                        wb_we_r <= '0;
                        cyc_after_xfer_r <= 0;
                        state_r <= state_receive_address;
                    end else if (ascii_rx_data_i == CMD_READ_HOLD_CHAR) begin
                        wb_we_r <= '0;
                        cyc_after_xfer_r <= 1;
                        state_r <= state_receive_address;
                    end else begin
                        state_r <= state_error;
                    end
                end
            end
                
            state_receive_address: begin
                    
                if (ascii_rx_strobe_i == 1) begin
                    if (ADDR_NIBBLES>1) begin
                        wb_adr_r[$high(wb_adr_r):4] <= wb_adr_r[$high(wb_adr_r)-4:0]; // shfit left
                    end
                    if ((ascii_rx_data_i >= CHAR_0) && (ascii_rx_data_i <= CHAR_9)) begin
                        wb_adr_r[3:0] <= ascii_rx_data_i[3:0];
                        if (cnt_r == 0) begin
                            cnt_r <= DATA_NIBBLES-1;
                            if (wb_we_r) begin
                                state_r <= state_receive_data;
                            end else begin
                                wb_sel_r <= '1;
                                state_r <= state_receive_term;
                            end
                        end else begin
                            cnt_r <= cnt_r - 1;
                        end
                    end else if ((ascii_rx_data_i >= CHAR_A) && (ascii_rx_data_i <= CHAR_F)) begin
                        wb_adr_r[3:0] <= ascii_rx_data_i[3:0] + 9;
                        if (cnt_r == 0) begin
                            cnt_r <= DATA_NIBBLES-1;
                            if (wb_we_r) begin
                                state_r <= state_receive_data;
                            end else begin
                                state_r <= state_receive_term;
                            end
                        end else begin
                            cnt_r <= cnt_r - 1;
                        end
                    end else begin
                        state_r <= state_error;
                    end
                end
            end
                        
            state_receive_data: begin
                                    
                if (ascii_rx_strobe_i == 1) begin
                    if (DATA_NIBBLES>1) begin
                        wb_dat_ms[$high(wb_dat_ms):4] <= wb_dat_ms[$high(wb_dat_ms)-4:0]; // shfit left
                    end
                    if ((ascii_rx_data_i >= CHAR_0) && (ascii_rx_data_i <= CHAR_9)) begin
                        wb_dat_ms[3:0] <= ascii_rx_data_i[3:0];
                        if (cnt_r == 0) begin
                            cnt_r <= MASK_NIBBLES-1;
                            state_r <= state_receive_mask;
                            cnt_r <= 0;
                        end else begin
                            cnt_r <= cnt_r - 1;
                        end
                    end else if ((ascii_rx_data_i >= CHAR_A) && (ascii_rx_data_i <= CHAR_F)) begin
                        wb_dat_ms[3:0] <= ascii_rx_data_i[3:0] + 9;
                        if (cnt_r == 0) begin
                            cnt_r <= MASK_NIBBLES-1;
                            state_r <= state_receive_mask;
                            cnt_r <= 0;
                        end else begin
                            cnt_r <= cnt_r - 1;
                        end
                    end else begin
                        state_r <= state_error;
                    end
                end
            end
                        
            state_receive_mask: begin
                                    
                if (ascii_rx_strobe_i == 1) begin
					if (MASK_NIBBLES>1) begin
						// must be commented out for ModelSim
                        //wb_sel_r[$high(wb_sel_r):4] <= wb_sel_r[$high(wb_sel_r)-4:0]; // shift left
                    end
                    if ((ascii_rx_data_i >= CHAR_0) && (ascii_rx_data_i <= CHAR_9)) begin
                        wb_sel_r[3:0] <= ascii_rx_data_i[3:0];
                        if (cnt_r == 0) begin
                            state_r <= state_receive_term;
                            cnt_r <= 0;
                        end else begin
                            cnt_r <= cnt_r - 1;
                        end
                    end else if ((ascii_rx_data_i >= CHAR_A) && (ascii_rx_data_i <= CHAR_F)) begin
                        wb_sel_r[3:0] <= ascii_rx_data_i[3:0] + 9;
                        if (cnt_r == 0) begin
                            state_r <= state_receive_term;
                            cnt_r <= 0;
                        end else begin
                            cnt_r <= cnt_r - 1;
                        end
                    end else begin
                        state_r <= state_error;
                    end
                end
            end
            
            state_receive_term: begin
                if (ascii_rx_strobe_i == 1) begin
                    if (ascii_rx_data_i == TERM_CHAR) begin
                        wb_stb_r <= '1;
                        wb_cyc_r <= '1;
						timer_r <= '1;
                        state_r <= state_wb_wait;
                     end else begin
                        state_r <= state_error;
                     end
                  end
            end
            
            state_wb_wait: begin
            
                if (wb_m.ack) begin
                    wb_stb_r <= '0;
                    wb_cyc_r <= cyc_after_xfer_r;
                    wb_dat_i_r <= wb_m.dat_sm;
                    if (wb_we_r) begin
                        // respond with OK
                        resp_r[$size(resp_r)-8 +: 8] = { 8'(RESP_OK_CHAR) };
                        cnt_r <= (1)-1;
                        state_r <= state_respond;
                    end else begin
                        // add OK; response data will be serialized in next state
                        resp_r[7:0] = { 8'(RESP_OK_CHAR) };
                        cnt_r <= DATA_NIBBLES-1;
                        state_r <= state_serialize;
                    end
                end else if (timer_r == 0) begin
                    // Wishbone slave did not respond; respond with timeout-error
					resp_r[$size(resp_r)-8 +: 8] = { 8'(RESP_TIMEOUT_CHAR) };
					cnt_r <= (1)-1;
					state_r <= state_respond;
				end
            end
            
            state_serialize: begin
            
                nibble_v = wb_dat_i_r[$high(wb_dat_i_r):$high(wb_dat_i_r)-3];
                if (nibble_v < 10) begin
                    byte_v = { 4'b0, nibble_v } + CHAR_0;
                end else begin
                    byte_v = { 4'b0, nibble_v } + (CHAR_A - 10);
                end
                
                wb_dat_i_r <= { wb_dat_i_r[$high(wb_dat_i_r)-4:0], 4'bX };
                resp_r <= { resp_r[$high(resp_r)-8:0], byte_v };
            
                if (cnt_r == 0) begin
                    cnt_r <= (DATA_NIBBLES+1)-1; // 1 more for ok-char
                    state_r <= state_respond;
                end else begin
                    cnt_r <= cnt_r - 1;
                end

            end
            
            state_error: begin
                
                resp_r[$high(resp_r):$high(resp_r)-7] = { 8'(RESP_ERR_CHAR) };
                cnt_r <= (1)-1;
                state_r <= state_respond;
            
            end
            
            state_respond: begin
                
                if (ascii_tx_ready_i) begin
                
                    ascii_tx_data_r <= resp_r[$high(resp_r):$high(resp_r)-7];
                    ascii_tx_strobe_r <= '1;
                    resp_r <= { resp_r[$high(resp_r)-8:0], 8'bX };
                    if (cnt_r == 0) begin
                        state_r <= state_term;
                    end
                    cnt_r <= cnt_r - 1;
                end
            
            end
            
            state_term: begin
                
                ascii_tx_data_r <= TERM_CHAR;
                
                if (ascii_tx_ready_i) begin
                    ascii_tx_strobe_r <= '1;
                    state_r <= state_start;
                end
            
            end
            
            default: begin
                state_r <= state_start;
            end
                
        endcase
    end
end


assign ascii_tx_data_o = ascii_tx_data_r;
assign ascii_tx_strobe_o = ascii_tx_strobe_r;
assign wb_m.dat_ms = wb_dat_ms;
assign wb_m.adr = wb_adr_r;
assign wb_m.sel = wb_sel_r;
assign wb_m.cyc = wb_cyc_r;
assign wb_m.stb = wb_stb_r;
assign wb_m.we = wb_we_r;


endmodule
