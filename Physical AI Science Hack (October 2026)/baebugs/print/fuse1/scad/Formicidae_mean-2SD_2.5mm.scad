// Formicidae mean-2SD | CA museum specimens n=26: L 6.9±2.2 mm | size_flag: database-derived, unverified | STL: california/Formicidae_mean-2SD_2.5mm.stl
// plan=ant length=2.5 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-0.9375, 0.0000, 0.0000], [0.3594, 0.3600, 0.3520]);  // head_body
  ellipsoid([-0.1875, 0.0000, 0.0000], [0.4813, 0.3150, 0.3024]);  // thorax_body
  ellipsoid([0.7500, 0.0000, 0.0000], [0.5250, 0.3500, 0.3150]);  // abdomen_body
}
