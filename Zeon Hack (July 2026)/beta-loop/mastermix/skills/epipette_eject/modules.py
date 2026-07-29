"""
Supporting modules for generic epipette tip-eject operations.
"""


from execution.execution_functions import *

# EPIPETTE_10UL ("epipette_10ul") comes from the star import above and matches
# main.py's boot init_epipette call. Used as the fallback when the device name
# can't be derived from the passed pipette object.
