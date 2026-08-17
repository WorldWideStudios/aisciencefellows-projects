"""DMD capsid world model — wraps v1_release AMDCapsidWorldModel.

Only change from AMD: output names are muscle_transduction, nab_escape,
hepatotoxicity_score instead of rpe_transduction, neut_escape, inflammation_score.
The GP logic, PCA, and featurization are identical.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from botorch.fit import fit_gpytorch_mll
from botorch.models import SingleTaskGP
from botorch.models.transforms import Normalize, Standardize
from gpytorch.mlls import ExactMarginalLogLikelihood
from sklearn.decomposition import PCA
import h5py

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dmd_config as config

OUTPUTS = ["muscle_transduction", "nab_escape", "hepatotoxicity_score"]


def load_embedding(sequence_hash: str) -> np.ndarray:
    with h5py.File(config.EMBEDDINGS_DIR / f"{sequence_hash}.h5", "r") as f:
        return np.array(f["embedding"])


class DMDCapsidWorldModel:
    """GP world model: PCA(2560-d embedding) + 4 engineered features.

    Three independent SingleTaskGPs, one per output.
    Structurally identical to AMDCapsidWorldModel in v1_release.
    """

    def __init__(self, pca_dim: int = 16):
        self.pca_dim = pca_dim
        self.feature_dim = pca_dim + 4
        self.pca: PCA | None = None
        self.models: dict[str, SingleTaskGP] = {}

    def fit_pca(self, embeddings: np.ndarray) -> None:
        self.pca = PCA(n_components=self.pca_dim)
        self.pca.fit(embeddings)

    def featurize(self, embeddings: np.ndarray, engineered: np.ndarray) -> np.ndarray:
        if self.pca is None:
            raise RuntimeError("PCA not fit; call fit_pca() first.")
        reduced = self.pca.transform(embeddings)
        return np.concatenate([reduced, engineered], axis=1)

    def fit(
        self,
        embeddings: np.ndarray,
        engineered: np.ndarray,
        Y: pd.DataFrame,
        fit_hyperparameters: bool = True,
    ) -> None:
        if self.pca is None:
            self.fit_pca(embeddings)
        X_full = self.featurize(embeddings, engineered)
        self.models = {}
        for out in OUTPUTS:
            y = Y[out].to_numpy(dtype=np.float64)
            mask = ~np.isnan(y)
            if mask.sum() < 3:
                continue
            X_t = torch.tensor(X_full[mask], dtype=torch.float64)
            y_t = torch.tensor(y[mask], dtype=torch.float64).unsqueeze(-1)
            model = SingleTaskGP(
                X_t, y_t,
                input_transform=Normalize(d=X_t.shape[1]),
                outcome_transform=Standardize(m=1),
            )
            if fit_hyperparameters:
                mll = ExactMarginalLogLikelihood(model.likelihood, model)
                fit_gpytorch_mll(mll)
            self.models[out] = model

    def predict(
        self, embeddings: np.ndarray, engineered: np.ndarray
    ) -> dict[str, tuple[np.ndarray, np.ndarray]]:
        X_full = self.featurize(embeddings, engineered)
        X_t = torch.tensor(X_full, dtype=torch.float64)
        out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for name, model in self.models.items():
            model.eval()
            with torch.no_grad():
                posterior = model.posterior(X_t)
                mean = posterior.mean.squeeze(-1).cpu().numpy()
                var  = posterior.variance.squeeze(-1).cpu().numpy()
            out[name] = (mean, var)
        return out
