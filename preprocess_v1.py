import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# EDA

# Graficas

def histogram(df):
    
    var_num = df.select_dtypes(include=['int64', 'float64'])
    num_cols = len(var_num.columns)
    
    fig = plt.figure(figsize=(15, 5 *((num_cols + 2)//3 )))
    
    for idx, col in enumerate(var_num.columns, 1):
        ax = fig.add_subplot((num_cols + 2) // 3, 3, idx)
        ax.hist(var_num[col], bins=30, edgecolor='black', alpha=0.7)
        ax.set_title(f'Histograma: {col}', fontweight='bold')
        ax.set_xlabel(col)
        ax.set_ylabel('Frecuencia')
        ax.grid(alpha=0.3)
        
    plt.tight_layout()

def boxplot_simple(df):
    data = df.select_dtypes(['int64', 'float64'])
    for i in data.columns:   
        ax = data.boxplot(column=i, figsize=(8, 5))
        plt.xticks()
        plt.tight_layout()
        plt.show()


def boxplot_colors(df, var1, var2, var3):
    sns.boxplot(x=var1, y=var2, hue=var3, palette=['m', 'g'], data=df)



    

# imputaciones

def categorical_imputation(df):
    
    # Identificar columnas categóricas
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    # calcular la moda para cada columna categorica
    modas = {}
    for col in cat_cols:
        moda = df[col].mode()
        if not moda.empty:
            modas[col] = moda[0]
            print(f"{col}: Moda = '{modas[col]}' ({df[col].isna().sum()} nulos a reemplazar)")
        else:
            modas[col] = None
            print(f"{col}: No hay moda, todos los valores son NAN's")

    # imputar valores nulos
    df = df.copy()
    for col, moda_valor in modas.items():
        if moda_valor is not None:
            # contal nulos antes y despues
            nulos_antes = df[col].isna().sum()
            df[col] = df[col].fillna(moda_valor)
            nulos_despues = df[col].isna().sum()

            print(f"{col}: {nulos_antes}→ {nulos_despues} nulos ")

    return df


    

def numeric_imputation(df, var):

     median = df[var].median()

     imputation = df[var].fillna(median)
     return imputation





    