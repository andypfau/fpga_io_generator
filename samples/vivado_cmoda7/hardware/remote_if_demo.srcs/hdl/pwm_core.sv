module pwm_core #(

	parameter BITS = 8,
	parameter CHANNELS = 4

) (

	input rst_i,
	input clk_i,

	input[BITS-1:0] levels_i[CHANNELS-1:0],
	output[CHANNELS-1:0] channels_o
		
);


reg[BITS-1:0] counter_r;
logic[CHANNELS-1:0] channels_r;


always_ff @(posedge rst_i or posedge clk_i) begin
	if (rst_i) begin
		counter_r <= '0;
		channels_r <= '0;
	end else begin

		if (counter_r == (1 << BITS)-2)
			counter_r <= '0;
		else
			counter_r <= counter_r + 1;

		if (counter_r == 0)
			channels_r <= '1;

		for (int i = 0; i < CHANNELS; i++)
			if (counter_r == levels_i[i])
				channels_r[i] <= 0;

	end
end


assign channels_o = channels_r;


endmodule
