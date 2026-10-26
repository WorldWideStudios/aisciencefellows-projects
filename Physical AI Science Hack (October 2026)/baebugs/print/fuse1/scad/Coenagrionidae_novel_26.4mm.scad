// Coenagrionidae novel | outside CA (AZ, NV) | size_flag: database-derived, unverified | STL: novel_outside_ca/Coenagrionidae_novel_26.4mm.stl
// plan=damselfly length=26.4 mm features: folded wings 0.8 mm
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-12.1440, 0.0000, 0.0000], [1.2144, 0.7836, 0.9448]);  // head_body
  ellipsoid([-8.8440, 0.0000, 0.0000], [2.4684, 0.9504, 1.0138]);  // thorax_body
  ellipsoid([3.3000, 0.0000, 0.0000], [10.3950, 1.0560, 1.0560]);  // abdomen_body
  plate([-0.9240, -0.4200, 1.0982], [19.8000, 1.2000, 0.8000]);  // wing_L
  plate([-0.9240, 0.4200, 1.0982], [19.8000, 1.2000, 0.8000]);  // wing_R
}
