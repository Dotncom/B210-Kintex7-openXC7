create_clock -period 25.000 [get_ports codec_main_clk_p]
create_clock -period 16.276 [get_ports codec_data_clk_p]
create_clock -period 10.000 [get_nets gpif_clk]
create_clock -period 16.276 [get_nets radio_clk]
