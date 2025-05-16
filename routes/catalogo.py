import pandas as pd
import os

def cargar_catalogo():
    catalogo_path = os.path.join("data", "catalogo.csv")
    return pd.read_csv(catalogo_path, sep=";", encoding="latin1")
