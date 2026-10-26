// BaeBugs parametric labware library (labware twin), v0.1
// All parts are built as 2D profiles extruded in Z, so remixes render fast.
// Units: mm. SBS footprint per ANSI/SLAS 1-2004: 127.76 x 85.48.
// License: CERN-OHL-W-2.0 unless a part file says otherwise.

SBS_X = 127.76;
SBS_Y = 85.48;
$fn = 32;

// Rounded rectangle profile anchored at the origin.
module rrect(x, y, r = 3) {
    translate([r, r]) offset(r = r) square([x - 2 * r, y - 2 * r]);
}

// Grid of round holes. A1 is the back-left well, matching Opentrons/SBS naming,
// so row 0 sits at y = footprint_y - a1_y.
module hole_grid(rows, cols, pitch, hole_d, a1_x, a1_y, footprint_y) {
    for (r = [0 : rows - 1], c = [0 : cols - 1])
        translate([a1_x + c * pitch, footprint_y - a1_y - r * pitch]) circle(d = hole_d);
}

// Tube or tip rack plate: solid top deck with holes, plus a skirt so it sits in a deck slot.
module sbs_plate(rows = 8, cols = 12, pitch = 9, hole_d = 5.8, height = 20,
                 a1_x = 14.38, a1_y = 11.24, footprint_x = SBS_X, footprint_y = SBS_Y,
                 deck = 3, skirt = 2) {
    // top deck
    translate([0, 0, height - deck]) linear_extrude(deck)
        difference() {
            rrect(footprint_x, footprint_y);
            hole_grid(rows, cols, pitch, hole_d, a1_x, a1_y, footprint_y);
        }
    // skirt wall
    linear_extrude(height - deck)
        difference() {
            rrect(footprint_x, footprint_y);
            translate([skirt, skirt]) rrect(footprint_x - 2 * skirt, footprint_y - 2 * skirt, 2);
        }
    // bottom locator ring (keeps tubes from sliding, 1.5 mm floor with smaller holes)
    linear_extrude(1.5)
        difference() {
            translate([skirt, skirt]) rrect(footprint_x - 2 * skirt, footprint_y - 2 * skirt, 2);
            hole_grid(rows, cols, pitch, hole_d * 0.6, a1_x, a1_y, footprint_y);
        }
}

// Flat grid insert (e.g. 10x10 cryo box insert).
module grid_insert(rows = 10, cols = 10, pitch = 13, hole_d = 12.8, height = 12,
                   a1_x = 8, a1_y = 8, footprint_x = 133, footprint_y = 133) {
    linear_extrude(height)
        difference() {
            rrect(footprint_x, footprint_y, 2);
            hole_grid(rows, cols, pitch, hole_d, a1_x, a1_y, footprint_y);
        }
}

// Open lipped frame: the "folder" frame. Inserts rest on the inner lip.
module frame(footprint_x = SBS_X, footprint_y = SBS_Y, height = 12, wall = 5, lip = 2, lip_z = 2) {
    linear_extrude(height)
        difference() {
            rrect(footprint_x, footprint_y);
            translate([wall, wall]) square([footprint_x - 2 * wall, footprint_y - 2 * wall]);
        }
    linear_extrude(lip_z)
        difference() {
            translate([wall - 0.01, wall - 0.01]) square([footprint_x - 2 * wall + 0.02, footprint_y - 2 * wall + 0.02]);
            translate([wall + lip, wall + lip]) square([footprint_x - 2 * (wall + lip), footprint_y - 2 * (wall + lip)]);
        }
}

// Frame split into rows x cols windows, each with a perforated floor (printed mesh).
module grid_frame(footprint_x = SBS_X, footprint_y = SBS_Y, height = 8, wall = 4, rows = 2, cols = 3,
                  rib = 3, floor = 1.2, mesh_hole = 2, mesh_pitch = 3) {
    ix = footprint_x - 2 * wall;
    iy = footprint_y - 2 * wall;
    cw = (ix - (cols - 1) * rib) / cols;
    ch = (iy - (rows - 1) * rib) / rows;
    // walls and ribs
    linear_extrude(height)
        difference() {
            rrect(footprint_x, footprint_y);
            for (r = [0 : rows - 1], c = [0 : cols - 1])
                translate([wall + c * (cw + rib), wall + r * (ch + rib)]) square([cw, ch]);
        }
    // perforated floor (square holes print cleanly without supports)
    linear_extrude(floor)
        difference() {
            translate([wall, wall]) square([ix, iy]);
            for (r = [0 : rows - 1], c = [0 : cols - 1])
                translate([wall + c * (cw + rib), wall + r * (ch + rib)])
                    for (i = [0 : floor((cw - mesh_pitch) / mesh_pitch)], j = [0 : floor((ch - mesh_pitch) / mesh_pitch)])
                        translate([mesh_pitch * 0.75 + i * mesh_pitch, mesh_pitch * 0.75 + j * mesh_pitch])
                            square(mesh_hole, center = true);
        }
}

// Hexagonal lattice clipped to a rectangle with a solid rim.
module honeycomb(footprint_x = 117, footprint_y = 75, height = 6, cell = 14, wall = 1.6, rim = 2) {
    dx = cell;                 // across-flats pitch
    dy = cell * sqrt(3) / 2;   // row pitch
    linear_extrude(height)
        difference() {
            square([footprint_x, footprint_y]);
            intersection() {
                translate([rim, rim]) square([footprint_x - 2 * rim, footprint_y - 2 * rim]);
                for (j = [0 : ceil(footprint_y / dy)], i = [-1 : ceil(footprint_x / dx)])
                    translate([i * dx + (j % 2) * dx / 2, j * dy])
                        rotate(30) circle(d = (cell - wall) / cos(30), $fn = 6);
            }
        }
}
