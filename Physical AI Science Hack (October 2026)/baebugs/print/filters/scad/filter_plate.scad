// baebugs parametric filter plate (nominal sizes: measure the real punch / sheet)
// shape: "circle" | "square" | "hexagon" | "slot" | "star"
shape = "slot";
size = 3.2;          // circle/hex: diameter / across-flats; square: side; slot: width; star: outer diameter
slot_length = 19.05; // slot only
plate = 50;          // plate side (mm)
thickness = 1.6;     // Fuse 1+ PA12 >= 0.8; metal sheet ~0.5-1.0
border = 3;
web = 1.0;           // material between holes (Fuse >= 0.8)
hex_grid = true;     // stagger alternate rows
$fn = 48;

module hole2d() {
  if (shape == "circle") circle(d = size);
  else if (shape == "square") square(size, center = true);
  else if (shape == "hexagon") circle(d = size / cos(30), $fn = 6);
  else if (shape == "slot") hull() { translate([-(slot_length - size) / 2, 0]) circle(d = size);
                                     translate([(slot_length - size) / 2, 0]) circle(d = size); }
  else if (shape == "star") polygon([for (i = [0:9]) let(r = i % 2 ? size * 0.225 : size / 2, a = 90 + 36 * i)
                                     [r * cos(a), r * sin(a)]]);
}
hw = shape == "slot" ? slot_length : size;
px = hw + web; py = size + web;
difference() {
  cube([plate, plate, thickness]);
  for (j = [0 : floor((plate - 2 * border - size) / py)])
    for (i = [0 : floor((plate - 2 * border - hw) / px)])
      let(off = (hex_grid && j % 2 == 1) ? px / 2 : 0,
          x = border + hw / 2 + off + i * px, y = border + size / 2 + j * py)
      if (x + hw / 2 <= plate - border)
        translate([x, y, -1]) linear_extrude(thickness + 2) hole2d();
}
