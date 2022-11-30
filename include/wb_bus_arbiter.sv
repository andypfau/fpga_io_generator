// generic Wishbone multi-master arbiter


module wb_bus_arbiter #(
    
    parameter N = 2 // number of masters to arbitrate
    
)(

    input clk_i,
    input rst_i,

    input[N-1:0] cyc_i,
    output cyc_common_o,
    output[N-1:0] gnt_o

);


logic cyc_common_c;
reg[N-1:0] token_r;



always_ff @(posedge rst_i or posedge clk_i) begin

    logic[N-1:0] next_token_v;
    logic[N-1:0] new_requests_v;
    logic advance_v;
    logic cycle_in_progress_v;

    if (rst_i) begin
    
        token_r <= { {(N-1){1'b0}}, 1'b1 };
        
    end else begin
        
        cycle_in_progress_v = cyc_common_c;
        if (!cycle_in_progress_v) begin
            
            // advance token N times, except if it arrives at a new request
            // (this means that if there is no request, it arrives back where it was)
            
            next_token_v = token_r;
            new_requests_v = cyc_i & ~token_r; // only check new requests, i.e. not the current level
            
            for (int i = 0; i < N; i++) begin
            
                advance_v = 1'b1;
                for (int j = 0; j < N; j++) begin
                    if (next_token_v[j] & new_requests_v[j]) begin
                        advance_v = 1'b0;
                    end
                end
                
                if (advance_v) begin
                    next_token_v = { next_token_v[N-2:0], next_token_v[N-1] };
                end
                
            end
            
            token_r <= next_token_v;
        end
    end
end


always_comb begin
    cyc_common_c <= |(cyc_i & token_r);
end


assign cyc_common_o = cyc_common_c;
assign gnt_o = token_r;


endmodule
