// aphid-like fill | fill-in: below database minimum (2.8 mm); not measured | size_flag: fill-in size, not measured | STL: fill_in_1-3mm/aphid_like_fill_3.0mm.stl
// plan=aphid length=3.0 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-1.2750, 0.0000, 0.0000], [0.2587, 0.6450, 0.5950]);  // head_body
  ellipsoid([-0.7500, 0.0000, 0.0000], [0.3300, 0.7425, 0.5940]);  // thorax_body
  ellipsoid([0.5250, 0.0000, 0.0000], [1.0238, 0.8250, 0.6188]);  // abdomen_body
}
