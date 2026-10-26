// aphid-like fill | fill-in: below database minimum (2.8 mm); not measured | size_flag: fill-in size, not measured | STL: fill_in_1-3mm/aphid_like_fill_2.0mm.stl
// plan=aphid length=2.0 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-0.8500, 0.0000, 0.0000], [0.1725, 0.4800, 0.4300]);  // head_body
  ellipsoid([-0.5000, 0.0000, 0.0000], [0.2200, 0.4950, 0.3960]);  // thorax_body
  ellipsoid([0.3500, 0.0000, 0.0000], [0.6825, 0.5500, 0.4125]);  // abdomen_body
}
