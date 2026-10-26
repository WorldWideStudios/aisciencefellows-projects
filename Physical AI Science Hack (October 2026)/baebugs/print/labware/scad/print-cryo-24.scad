// SBS 4x6 rack, 2 mL cryotubes
// part id: print-cryo-24  license: MIT
// labware.scad sha256: 025cbfe59bfb2d32557e6a9d5cc7a1fbf1fc54a5ea617dbfabe5a0ebfc3ffba2
// derived from: obs-cryotube-2ml, obs-microtube-50-purple
// Edit the parameters to remix. Catalog dimensions marked est. need calipers before a production run.
use <labware.scad>

sbs_plate(rows = 4, cols = 6, pitch = 19.3, hole_d = 13.2, height = 30.0, a1_x = 15.63, a1_y = 13.79, footprint_x = 127.76, footprint_y = 85.48);
