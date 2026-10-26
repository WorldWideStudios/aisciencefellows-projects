// Syrphidae mean-2SD | CA museum specimens n=94: L 10.7±2.8 mm | size_flag: database-derived, unverified | STL: california/Syrphidae_mean-2SD_5.1mm.stl
// plan=fly length=5.1 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-2.0400, 0.0000, 0.0000], [0.5865, 0.7620, 0.7936]);  // head_body
  ellipsoid([-0.6375, 0.0000, 0.0000], [0.9817, 0.9180, 0.8323]);  // thorax_body
  ellipsoid([1.4025, 0.0000, 0.0000], [1.2049, 1.0200, 0.8670]);  // abdomen_body
}
