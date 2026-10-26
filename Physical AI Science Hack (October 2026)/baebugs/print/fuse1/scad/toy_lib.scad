// baebugs toy insect primitives (TOY models, not replicas)
$fn = 40;
module ellipsoid(c, r) { translate(c) scale(r) sphere(1); }
module rod(a, b, d)    { hull() { translate(a) sphere(d / 2); translate(b) sphere(d / 2); } }
module plate(c, e)     { translate(c) cube(e, center = true); }
