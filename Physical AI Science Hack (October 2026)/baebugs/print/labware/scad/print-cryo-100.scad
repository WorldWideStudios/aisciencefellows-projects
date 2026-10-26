// 10x10 cryo grid insert, 133 mm
// part id: print-cryo-100  license: MIT
// labware.scad sha256: 025cbfe59bfb2d32557e6a9d5cc7a1fbf1fc54a5ea617dbfabe5a0ebfc3ffba2
// derived from: obs-cryobox-100
// Edit the parameters to remix. Catalog dimensions marked est. need calipers before a production run.
use <labware.scad>

grid_insert(rows = 10, cols = 10, pitch = 13.0, hole_d = 12.6, height = 12.0, a1_x = 8.0, a1_y = 8.0, footprint_x = 133.0, footprint_y = 133.0);
