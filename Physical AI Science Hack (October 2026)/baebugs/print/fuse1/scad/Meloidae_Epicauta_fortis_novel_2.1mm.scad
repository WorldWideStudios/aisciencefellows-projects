// Meloidae (Epicauta fortis) novel | outside CA (AZ) | size_flag: suspect: 2.1 mm far smaller than typical for a blister beetle | STL: novel_outside_ca/Meloidae_Epicauta_fortis_novel_2.1mm.stl
// plan=beetle_long length=2.1 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-0.8925, 0.0000, 0.0000], [0.1811, 0.4020, 0.3400]);  // head_body
  ellipsoid([-0.4725, 0.0000, 0.0000], [0.2888, 0.3780, 0.2880]);  // thorax_body
  ellipsoid([0.4200, 0.0000, 0.0000], [0.6615, 0.4200, 0.3000]);  // abdomen_body
}
