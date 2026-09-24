import pandas as pd
import requests
from bs4 import BeautifulSoup
import io

class TennisAbstractScraper:
    def __init__(self):
        self.url = "https://raw.githubusercontent.com/fivethirtyeight/data/master/tennis-elo-2/tennis_elo.csv" # wait, 538 is outdated.
        self.url = "https://www.tennisabstract.com/reports/atp_elo_ratings.html"
        
    def get_elo_ratings(self):
        print("Obteniendo ELO ratings reales de Tennis Abstract...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(self.url, headers=headers)
        
        if response.status_code != 200:
            print("Error al descargar Tennis Abstract")
            return None
            
        try:
            # Using BeautifulSoup to extract the table data if Pandas fails
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'id': 'reportable'})
            
            if not table:
                print("No se encontró la tabla de ELO")
                return None
                
            df = pd.read_html(io.StringIO(str(table)))[0]
            
            # Limpiar nombres de columnas
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(0)
                
            df.columns = [str(c).lower().replace(' ', '_') for c in df.columns]
            
            return df
        except Exception as e:
            print("Error parseando Tennis Abstract:", e)
            return None

if __name__ == "__main__":
    scraper = TennisAbstractScraper()
    df = scraper.get_elo_ratings()
    if df is not None:
        print(df.head())
        print(df.columns)
