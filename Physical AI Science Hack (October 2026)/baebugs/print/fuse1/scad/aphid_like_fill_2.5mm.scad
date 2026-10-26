// aphid-like fill | fill-in: below database minimum (2.8 mm); not measured | size_flag: fill-in size, not measured | STL: fill_in_1-3mm/aphid_like_fill_2.5mm.stl
// plan=aphid length=2.5 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-1.0625, 0.0000, 0.0000], [0.2156, 0.5625, 0.5125]);  // head_body
  ellipsoid([-0.6250, 0.0000, 0.0000], [0.2750, 0.6188, 0.4950]);  // thorax_body
  ellipsoid([0.4375, 0.0000, 0.0000], [0.8531, 0.6875, 0.5156]);  // abdomen_body
}
