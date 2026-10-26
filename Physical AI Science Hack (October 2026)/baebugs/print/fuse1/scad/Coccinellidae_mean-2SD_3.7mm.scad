// Coccinellidae mean-2SD | CA museum specimens n=54: L 6.3±1.3 mm | size_flag: database-derived, unverified | STL: california/Coccinellidae_mean-2SD_3.7mm.stl
// plan=beetle_dome length=3.7 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-1.5725, 0.0000, 0.0000], [0.3191, 0.9825, 0.8215]);  // head_body
  ellipsoid([-0.8325, 0.0000, 0.0000], [0.5088, 1.2488, 0.8658]);  // thorax_body
  ellipsoid([0.7400, 0.0000, 0.0000], [1.1655, 1.3875, 0.9019]);  // abdomen_body
}
