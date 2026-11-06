# hsafm-eventaudit — environment setup

The Python dependencies for this repository are listed in [`requirements.txt`](../requirements.txt) and [`pyproject.toml`](../pyproject.toml).

## Windows / Miniconda

From the repository root, create a Python environment and install the dependencies:

```powershell
conda create -n eventaudit-paper1 python=3.11.16 -y
conda activate eventaudit-paper1
python -m pip install -r requirements.txt
python -m pip install "threadpoolctl==3.6.0"
```

The reference setup uses Python `3.11.16`, NumPy `2.4.4`, SciPy `1.17.1`, scikit-image `0.26.0`, scikit-learn `1.8.0`, AFMReader `0.0.7` and threadpoolctl `3.6.0`.

Native third-party HS-AFM `.asd` recordings and sealed evaluation truth are not included in this repository; workflows requiring them need separately authorized inputs.
