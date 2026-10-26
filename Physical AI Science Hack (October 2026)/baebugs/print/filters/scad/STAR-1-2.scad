// STAR-1/2: 1/2 in star (shape punch, realisation punched) NOMINAL size, measure before use
// hole: star {"outer_d": 12.7}; inscribed 5.703 mm; 8 holes; open area 0.22; spec hash ccf0825ecd47c79e
plate = 50.0; thickness = 1.6;
hole = [[0.0000, 6.3500], [-1.6796, 2.3118], [-6.0392, 1.9623], [-2.7176, -0.8830], [-3.7324, -5.1373], [-0.0000, -2.8575], [3.7324, -5.1373], [2.7176, -0.8830], [6.0392, 1.9623], [1.6796, 2.3118]];
centres = [[9.0392, 8.7436], [22.1176, 8.7436], [35.196, 8.7436], [15.5784, 21.2309], [28.6568, 21.2309], [9.0392, 33.7181], [22.1176, 33.7181], [35.196, 33.7181]];
difference() {
  cube([plate, plate, thickness]);
  for (c = centres) translate([c[0], c[1], -1]) linear_extrude(thickness + 2) polygon(hole);
}
