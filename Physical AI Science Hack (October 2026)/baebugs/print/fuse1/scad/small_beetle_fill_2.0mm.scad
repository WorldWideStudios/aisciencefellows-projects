// small beetle fill | fill-in: below database minimum (2.8 mm); not measured | size_flag: fill-in size, not measured | STL: fill_in_1-3mm/small_beetle_fill_2.0mm.stl
// plan=beetle_dome length=2.0 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-0.8500, 0.0000, 0.0000], [0.1725, 0.6000, 0.4900]);  // head_body
  ellipsoid([-0.4500, 0.0000, 0.0000], [0.2750, 0.6750, 0.4680]);  // thorax_body
  ellipsoid([0.4000, 0.0000, 0.0000], [0.6300, 0.7500, 0.4875]);  // abdomen_body
}
