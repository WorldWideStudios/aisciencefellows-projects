"""Run sorter.py with the optimizer's one-box seesaw patch, so a one-piece design (gated container, plinko) rocks
as a single level about its middle. Usage: python run_onebox.py <sim dir> <sorter.py args...>"""
import sys

sim = sys.argv[1]
sys.path.insert(0, sim)
import os  # noqa: E402

os.chdir(sim)
import optimize  # noqa: E402
import sorter  # noqa: E402

optimize.one_box_seesaw()
sys.argv = ["sorter.py", *sys.argv[2:]]
sorter.main()
