// baebugs variable-aperture slot pair (proof of concept; laser-cut 316L, deburr all edges)
// w0=6.0 mm, slot length=19.05 mm, pitch=9.0 mm, sheet=0.5 mm
offset = 0;   // 0 = fully open (6.0 mm); width = 6.0 - offset
module slot_plate(t) {
  difference() {
    cube([55.0, 77.15, t]);
    for (i = [0:4], j = [0:2])
      translate([5 + i*9.0, 4 + j*23.05, -1]) cube([6.0, 19.05, t + 2]);
    for (x = [2.5, 52.5], y = [2.5, 74.65]) translate([x, y, -1]) cylinder(d=2.2, h=t+2, $fn=24);
  }
}
slot_plate(0.5);                                        // fixed plate
color("silver") translate([offset, 0, 0.5]) slot_plate(0.5);   // sliding plate
// printed guide frame: rails either side of the sliding plate, lead-screw boss on +x
color("white") difference() {
  translate([-4, -4, -2]) cube([75.0, 85.15, 2 + 2*0.5 + 1.5]);
  translate([-0.2, -0.2, -0.1]) cube([55.0 + 0.4 + 6.0, 77.15 + 0.4, 10]);
  translate([4, 4, -3]) cube([47.0, 69.15, 5]);
}
translate([65.0, 38.575, 0.5]) rotate([0, 90, 0]) color("gray") cylinder(d=8, h=40, $fn=24); // M8 lead screw
