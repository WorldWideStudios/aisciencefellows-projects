// thrips-like fill | fill-in: below database minimum (2.8 mm); not measured | size_flag: fill-in size, not measured | STL: fill_in_1-3mm/thrips_like_fill_1.5mm.stl
// plan=thrips length=1.5 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-0.6375, 0.0000, 0.0000], [0.1294, 0.3600, 0.3400]);  // head_body
  ellipsoid([-0.3375, 0.0000, 0.0000], [0.2063, 0.3150, 0.2880]);  // thorax_body
  ellipsoid([0.3000, 0.0000, 0.0000], [0.4725, 0.3500, 0.3000]);  // abdomen_body
}
