// small beetle fill | fill-in: below database minimum (2.8 mm); not measured | size_flag: fill-in size, not measured | STL: fill_in_1-3mm/small_beetle_fill_3.0mm.stl
// plan=beetle_dome length=3.0 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-1.2750, 0.0000, 0.0000], [0.2587, 0.8250, 0.6850]);  // head_body
  ellipsoid([-0.6750, 0.0000, 0.0000], [0.4125, 1.0125, 0.7020]);  // thorax_body
  ellipsoid([0.6000, 0.0000, 0.0000], [0.9450, 1.1250, 0.7313]);  // abdomen_body
}
