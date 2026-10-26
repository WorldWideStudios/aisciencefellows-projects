# DAISY-BB-004 amendment 1: compute platform (filed before any run)

- **What changed:** where the frozen kernel runs. Kaggle refused the push: the account's weekly GPU quota (30 h) is used up. The same kernel code now runs on magicstudio (Mac, CPU) through `kaggle/make_taxon_kernel.py local`, which executes the identical code cell with only the input and working directories set by environment variable.
- **What did not change:** the protocol file and its sha256 (`31b1b0a6…`), data root (`4d5f2831…`), init weights pin, runs, classes, epochs, imgsz, batch, seed, gates, decision rule and margin. Nothing has been trained yet, so no result informed this change.
- **Recorded in the run:** the environment gate now also logs platform, machine and torch thread count, so a reader can see the run was CPU on arm64.
- **Effect to expect:** CPU training is slower and numerically different from GPU; the tensor sha of the weights is the identity of the realization, as for every DAISY run.
- **Bonus for custody:** the weights are written straight onto the magicBLACKbox drive, so they resolve the moment they exist.
