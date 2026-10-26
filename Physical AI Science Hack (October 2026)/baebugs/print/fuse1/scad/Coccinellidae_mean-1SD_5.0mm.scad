// Coccinellidae mean-1SD | CA museum specimens n=54: L 6.3±1.3 mm | size_flag: database-derived, unverified | STL: california/Coccinellidae_mean-1SD_5.0mm.stl
// plan=beetle_dome length=5.0 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-2.1250, 0.0000, 0.0000], [0.4312, 1.2750, 1.0750]);  // head_body
  ellipsoid([-1.1250, 0.0000, 0.0000], [0.6875, 1.6875, 1.1700]);  // thorax_body
  ellipsoid([1.0000, 0.0000, 0.0000], [1.5750, 1.8750, 1.2188]);  // abdomen_body
}
