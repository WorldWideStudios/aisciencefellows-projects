// aphid-like fill | fill-in: below database minimum (2.8 mm); not measured | size_flag: fill-in size, not measured | STL: fill_in_1-3mm/aphid_like_fill_1.5mm.stl
// plan=aphid length=1.5 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-0.6375, 0.0000, 0.0000], [0.1294, 0.3975, 0.3475]);  // head_body
  ellipsoid([-0.3750, 0.0000, 0.0000], [0.1650, 0.3713, 0.2970]);  // thorax_body
  ellipsoid([0.2625, 0.0000, 0.0000], [0.5119, 0.4125, 0.3094]);  // abdomen_body
}
