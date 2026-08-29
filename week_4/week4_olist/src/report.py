import pandas as pd
import matplotlib.pyplot as plt

def save_csv(df:pd.DataFrame, filepath:str)-> None:
    df.to_csv(filepath)
def plot_chart(data: pd.Series, title: str, filepath: str, kind: str = 'bar') -> None:
    kwargs = {'kind': kind, 'title': title}
    if kind == 'line':
        kwargs['marker'] = 'o'
    data.plot(**kwargs)
    plt.ylabel('Revenue (BRL)')
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()