// small beetle fill | fill-in: below database minimum (2.8 mm); not measured | size_flag: fill-in size, not measured | STL: fill_in_1-3mm/small_beetle_fill_2.5mm.stl
// plan=beetle_dome length=2.5 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-1.0625, 0.0000, 0.0000], [0.2156, 0.7125, 0.5875]);  // head_body
  ellipsoid([-0.5625, 0.0000, 0.0000], [0.3438, 0.8438, 0.5850]);  // thorax_body
  ellipsoid([0.5000, 0.0000, 0.0000], [0.7875, 0.9375, 0.6094]);  // abdomen_body
}
