// baebugs wood tower: post + cantilevered rail arms (generated from config/tower.yaml; MEASURE values)
post = [38, 89, 580.0]; tray = [90.0, 120.0]; strip = [12.0, 6.0];
cube(post);
translate([-90.0, -21.5, 84.0]) cube([128.0, strip[1], 6]);  // storage L0
translate([-90.0, 104.5, 84.0]) cube([128.0, strip[1], 6]);  // storage L0
translate([-90.0, -21.5, 184.0]) cube([128.0, strip[1], 6]);  // storage L1
translate([-90.0, 104.5, 184.0]) cube([128.0, strip[1], 6]);  // storage L1
translate([-90.0, -21.5, 284.0]) cube([128.0, strip[1], 6]);  // storage L2
translate([-90.0, 104.5, 284.0]) cube([128.0, strip[1], 6]);  // storage L2
translate([-90.0, -21.5, 384.0]) cube([128.0, strip[1], 6]);  // storage L3
translate([-90.0, 104.5, 384.0]) cube([128.0, strip[1], 6]);  // storage L3
translate([38.0, -21.5, 134.0]) cube([90.0, strip[1], 6]);  // filter L0
translate([38.0, 104.5, 134.0]) cube([90.0, strip[1], 6]);  // filter L0
translate([38.0, -21.5, 234.0]) cube([90.0, strip[1], 6]);  // filter L1
translate([38.0, 104.5, 234.0]) cube([90.0, strip[1], 6]);  // filter L1
translate([38.0, -21.5, 334.0]) cube([90.0, strip[1], 6]);  // filter L2
translate([38.0, 104.5, 334.0]) cube([90.0, strip[1], 6]);  // filter L2
translate([38.0, -21.5, 434.0]) cube([90.0, strip[1], 6]);  // filter L3
translate([38.0, 104.5, 434.0]) cube([90.0, strip[1], 6]);  // filter L3
