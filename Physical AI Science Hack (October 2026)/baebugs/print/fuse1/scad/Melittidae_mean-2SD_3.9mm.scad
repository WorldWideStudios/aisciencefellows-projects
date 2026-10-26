// Melittidae mean-2SD | CA museum specimens n=23: L 7.7±1.9 mm | size_flag: database-derived, unverified | STL: california/Melittidae_mean-2SD_3.9mm.stl
// plan=bee length=3.9 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-1.5990, 0.0000, 0.0000], [0.4036, 0.6414, 0.6897]);  // head_body
  ellipsoid([-0.6240, 0.0000, 0.0000], [0.6864, 0.7371, 0.7076]);  // thorax_body
  ellipsoid([0.9750, 0.0000, 0.0000], [1.0237, 0.8190, 0.7371]);  // abdomen_body
}
