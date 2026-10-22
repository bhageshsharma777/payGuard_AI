# Dataset instructions

For the initial runnable demo, `python model/train.py` creates synthetic data if no dataset is present. This lets you verify the application end-to-end, but synthetic-data metrics are not real-world performance.

For a more meaningful experiment, obtain a permitted copy of the Kaggle Credit Card Fraud Detection dataset and place it at:

`data/creditcard.csv`

Expected columns include `Time`, `Amount`, and `Class` where `Class` is 1 for fraud and 0 otherwise. The training script uses only `Time` and `Amount` as an intentionally simple baseline; this is not a production-quality feature set.

Respect the dataset's license and terms. Do not commit sensitive or restricted data to the public repository.
