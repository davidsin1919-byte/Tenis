import pandas as pd
import requests
import io
import os
from datetime import datetime
import numpy as np

class SackmannParser:
    def __init__(self, start_year=2015, data_dir="data"):
        self.base_url = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{}.csv"
        self.start_year = start_year
        self.current_year = datetime.now().year
        self.data_dir = data_dir
        
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def download_data(self):
        dfs = []
        for year in range(self.start_year, self.current_year + 1):
            file_path = os.path.join(self.data_dir, f"atp_matches_{year}.csv")
            
            if year != self.current_year and os.path.exists(file_path):
                print(f"Cargando {year} desde caché local...")
                df = pd.read_csv(file_path)
            else:
                print(f"Descargando datos del año {year}...")
                url = self.base_url.format(year)
                response = requests.get(url)
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    df = pd.read_csv(io.StringIO(response.text))
                else:
                    print(f"Datos de {year} no encontrados en GitHub (posiblemente aún no existen).")
                    continue
            dfs.append(df)
            
        if not dfs:
            raise Exception("No se pudieron cargar datos históricos.")
            
        combined_df = pd.concat(dfs, ignore_index=True)
        # Limpieza básica de fechas
        combined_df['tourney_date'] = pd.to_datetime(combined_df['tourney_date'], format='%Y%m%d', errors='coerce')
        combined_df = combined_df.dropna(subset=['tourney_date']).sort_values('tourney_date').reset_index(drop=True)
        return combined_df

if __name__ == "__main__":
    parser = SackmannParser(start_year=2015)
    df = parser.download_data()
    print(f"Total de partidos cargados: {len(df)}")
