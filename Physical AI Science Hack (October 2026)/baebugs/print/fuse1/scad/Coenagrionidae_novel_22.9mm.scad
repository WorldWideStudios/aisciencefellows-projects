// Coenagrionidae novel | outside CA (AZ, NV) | size_flag: database-derived, unverified | STL: novel_outside_ca/Coenagrionidae_novel_22.9mm.stl
// plan=damselfly length=22.9 mm features: folded wings 0.8 mm
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-10.5340, 0.0000, 0.0000], [1.0534, 0.6996, 0.8328]);  // head_body
  ellipsoid([-7.6715, 0.0000, 0.0000], [2.1412, 0.8244, 0.8794]);  // thorax_body
  ellipsoid([2.8625, 0.0000, 0.0000], [9.0169, 0.9160, 0.9160]);  // abdomen_body
  plate([-0.8015, -0.4200, 0.9526], [17.1750, 1.2000, 0.8000]);  // wing_L
  plate([-0.8015, 0.4200, 0.9526], [17.1750, 1.2000, 0.8000]);  // wing_R
}
