create_project mul1_proj . -part xc7a35ticsg324-1L -force

add_files top.sv
add_files control.sv
add_files datapath.sv
add_files -fileset sim_1 tb_top.sv

set_property top tb_top [get_filesets sim_1]

launch_simulation

quit
