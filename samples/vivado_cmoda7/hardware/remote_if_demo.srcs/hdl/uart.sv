module uart #(

	// frequency of the refence clock
	parameter CLOCKFREQ = 100.0e6,
	
	// baud rate
	parameter BAUDRATE = 9600.0,
	
	// data bits
	parameter REGSIZE = 8,
	
	// stop bits (1.5 is not supported)
	parameter STOPBITS = 1,
	
	// invert signals
	parameter INVERT_RXD = 0,
	parameter INVERT_TXD = 0

) (

		// reset (active high), clock (rising edge)
		input rst_i, clk_i,
		
		// asynchronous rxd_i and txd_o signals
		output txd_o,
		input rxd_i,
		
		// transmit data
		input[REGSIZE-1:0] tx_data_i,
		input tx_strobe_i,
		output tx_ready_o,
		
		// receive data
		output[REGSIZE-1:0] rx_data_o,
		output rx_strobe_o
		
);

localparam TIMER_INTERVAL = int'(CLOCKFREQ / BAUDRATE + 0.5);
localparam TIMER_HALF_INTERVAL = int'(0.5 * CLOCKFREQ / BAUDRATE + 0.5);
localparam BAUDRATE_ACTUAL = CLOCKFREQ / TIMER_INTERVAL;
localparam BAUDRATE_DEVIATION_PCT = (BAUDRATE_ACTUAL / BAUDRATE - 1.0) * 100.0;
localparam TIMER_BITS = $clog2(TIMER_INTERVAL+1);


reg[TIMER_BITS-1:0] tx_timer_r;
reg[TIMER_BITS-1:0] rx_timer_r;
reg tx_timer_strobe_r;
reg rxd_sync1_r, rxd_sync2_r, rxd_delay1_r;
enum {rxstate_idle, rxstate_receive, rxstate_complete} rx_state_r;
enum {txstate_idle, txstate_start_bit, txstate_data_bits, txstate_stop_bit} tx_state_r;
reg tx_busy_r;
reg[REGSIZE-1:0] tx_data_shiftreg_r, rx_data_shiftreg_r;
reg[4:0] tx_bit_counter_r, rx_bit_counter_r;

reg txd_r;
reg [REGSIZE-1:0] rx_data_r;
reg rx_strobe_r;


// verify parameters
initial begin
    assert(BAUDRATE < 0.5 * CLOCKFREQ) else
        $error("UART reference clock frequency must be at least 2x faster than baud rate");
    assert((BAUDRATE_DEVIATION_PCT >= -1.0) && (BAUDRATE_DEVIATION_PCT <= +1.0)) else
        $error("UART baud rate deviates by %d%% (target: 1%% or better)", BAUDRATE_DEVIATION_PCT);
end


// generate tx timer
always_ff @ (posedge rst_i or posedge clk_i) begin
    if (rst_i) begin
        tx_timer_r <= '0;
        tx_timer_strobe_r <= 0;
    end else begin	
        if (tx_timer_r == 0) begin
            tx_timer_r <= TIMER_INTERVAL - 1;
            tx_timer_strobe_r <= '1;
        end else begin
            tx_timer_r <= tx_timer_r - 1;
            tx_timer_strobe_r <= '0;
        end
    end
end


// tx fsm
always_ff @ (posedge rst_i or posedge clk_i) begin
    if (rst_i) begin
    
        txd_r <= '1;
        tx_state_r <= txstate_idle;
        tx_busy_r <= '1;
        tx_data_shiftreg_r <= '0;
        tx_bit_counter_r <= '0;
        
    end else begin		
    	
        case (tx_state_r)
        
            txstate_idle: begin
                // idle, wait for tx data
                
                // indicate idle
                tx_busy_r <= '0;
                
                if (tx_strobe_i) begin
                    // tx request received
                    
                    // register tx data
                    tx_data_shiftreg_r <= tx_data_i;
                    
                    // indicate busy
                    tx_busy_r <= '1;
                    
                    // advance to next state
                    tx_state_r <= txstate_start_bit;
                    
                end
            end
            
            txstate_start_bit: begin
                // transmit start bit on next clock
                
                if (tx_timer_strobe_r) begin
                    // clock strobe received, send start bit
                    
                    // start bit., must be 0
                    txd_r <= '0;
                    
                    // reset bit counter
                    tx_bit_counter_r <= REGSIZE-1;
                    
                    // advance to next state
                    tx_state_r <= txstate_data_bits;
                end
            end
            
            txstate_data_bits: begin
                // transmit one data bit per clock
                
                if (tx_timer_strobe_r) begin
                    // clock strobe received, send data bit
                    
                    // data bit
                    txd_r <= tx_data_shiftreg_r[0]; // must be transmitted LSB-first
                    
                    // shift data register
                    tx_data_shiftreg_r <= { 1'bX, tx_data_shiftreg_r[REGSIZE-1:1] };
                    
                    // count bits
                    tx_bit_counter_r <= tx_bit_counter_r - 1;
                    
                    if (tx_bit_counter_r == 0) begin
                        // all bit sent
                        
                        tx_bit_counter_r <= STOPBITS - 1;
                        
                        // advance to next state
                        tx_state_r <= txstate_stop_bit;
                    
                    end
                end
            end
            
            txstate_stop_bit: begin
                // transmit stop bit on next clock
                
                if (tx_timer_strobe_r) begin
                    // clock strobe received, send stop bit
                    
                    // stop bit, must be 1
                    txd_r <= '1;
                    
                    // advance to next state
                    if (tx_bit_counter_r == 0) begin
                        tx_state_r <= txstate_idle;
                    end
                    
                    tx_bit_counter_r <= tx_bit_counter_r - 1;
                end
            end
                                    
            default: begin
            
                // fallback state
                tx_state_r <= txstate_idle;
            
            end
        endcase
    end
end


// prepare rx data
always_ff @ (posedge rst_i or posedge clk_i) begin
    if (rst_i) begin
        rxd_sync1_r <= '0;
        rxd_sync2_r <= '0;
        rxd_delay1_r <= '0;
    end else begin			
        rxd_sync1_r <= rxd_i ^ INVERT_RXD;
        rxd_sync2_r <= rxd_sync1_r;
        rxd_delay1_r <= rxd_sync2_r;
    end
end
    

// rx fsm
always_ff @ (posedge rst_i or posedge clk_i) begin
    if (rst_i) begin
        rx_state_r <= rxstate_idle;
        rx_data_r <= '0;
        rx_bit_counter_r <= '0;
        rx_timer_r <= '0;
        rx_data_shiftreg_r <= '0;
        rx_strobe_r <= '0;
    end else begin			
                
        // default assignments
        rx_strobe_r <= '0;
    
        // fsm
        case (rx_state_r)
        
            rxstate_idle: begin
                // idle, wait for rx data
                
                if (rxd_delay1_r && !rxd_sync2_r) begin
                    // start bit (must be 0) detected
                    
                    // reset timer
                    rx_timer_r <= TIMER_HALF_INTERVAL-1;
                    
                    // reset bit counter
                    rx_bit_counter_r <= REGSIZE;
                    
                    // advance to next state
                    rx_state_r <= rxstate_receive;
                
                end
            end
            
            rxstate_receive: begin
                // receive data bits
                
                if (rx_timer_r == 0) begin
                    // we're in the middle of a bit now
                    
                    // shift data in (this will eventually shift out the start-bit, as we're counting one bit too much)
                    // data comes in LSB-first
                    rx_data_shiftreg_r <= { rxd_sync2_r, rx_data_shiftreg_r[REGSIZE-1:1] };
                    
                    // reset timer
                    rx_timer_r <= TIMER_INTERVAL-1;
                    
                    if (rx_bit_counter_r == 0) begin
                        // all bits received
                        
                        // advance to the next state
                        rx_state_r <= rxstate_complete;
                        
                    end
                    
                    // count bits
                    rx_bit_counter_r <= rx_bit_counter_r - 1;
                
                end else begin
                    
                    // timer count down
                    rx_timer_r <= rx_timer_r - 1;
                                    
                end
            end
                
            rxstate_complete: begin
                
                // display rx data
                rx_data_r <= rx_data_shiftreg_r;
                rx_strobe_r <= '1;
                
                // go to idle state
                rx_state_r <= rxstate_idle;
              
            end  
                
            default: begin
            
                // fallback state
                rx_state_r <= rxstate_idle;
            
            end
        endcase
    end
end


// combinatoric ready signal
assign tx_ready_o = (!tx_busy_r) && (!tx_strobe_i);


// output register renaming
assign txd_o = txd_r ^ INVERT_TXD;
assign rx_data_o = rx_data_r;
assign rx_strobe_o = rx_strobe_r;


endmodule
