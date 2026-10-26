// Melittidae mean-1SD | CA museum specimens n=23: L 7.7±1.9 mm | size_flag: database-derived, unverified | STL: california/Melittidae_mean-1SD_5.8mm.stl
// plan=bee length=5.8 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-2.3780, 0.0000, 0.0000], [0.6003, 0.8808, 0.9770]);  // head_body
  ellipsoid([-0.9280, 0.0000, 0.0000], [1.0208, 1.0962, 1.0524]);  // thorax_body
  ellipsoid([1.4500, 0.0000, 0.0000], [1.5225, 1.2180, 1.0962]);  // abdomen_body
}
