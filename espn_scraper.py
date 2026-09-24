import requests
import random
import time

class ESPNScraper:
    def __init__(self):
        self.url = "http://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard"
        
    def get_real_matches(self):
        """Obtiene la cartelera real desde ESPN API."""
        try:
            r = requests.get(self.url)
            data = r.json()
        except Exception as e:
            print("Error conectando a ESPN:", e)
            return []
            
        matches = []
        match_id = 1
        
        for event in data.get('events', []):
            tournament_name = event.get('name', 'ATP Tournament')
            # Extraer superficie y categoría real no viene tan fácil en ESPN, usamos Hard por defecto
            surface = "Hard" 
            
            for grouping in event.get('groupings', []):
                if grouping.get('grouping', {}).get('slug') != 'mens-singles':
                    continue
                    
                for comp in grouping.get('competitions', []):
                    # Solo nos interesan los partidos que aún no terminan
                    status_name = comp.get('status', {}).get('type', {}).get('name', '')
                    if status_name == 'STATUS_FINAL':
                        continue
                        
                    competitors = comp.get('competitors', [])
                    if len(competitors) < 2:
                        continue
                        
                    # Validar que tengan nombre real (no "TBD")
                    p1_name = competitors[0].get('athlete', {}).get('displayName', 'TBD')
                    p2_name = competitors[1].get('athlete', {}).get('displayName', 'TBD')
                    
                    if p1_name == 'TBD' or p2_name == 'TBD':
                        continue
                        
                    time_str = comp.get('date', '') # ej. 2026-09-22T05:00Z
                    if time_str:
                        time_str = time_str.split('T')[1][:5]
                    else:
                        time_str = "TBA"
                        
                    # SIMULAR ODD Y ELO PROBABILIDADES
                    # En la versión final esto se conecta al modelo entrenado y al The-Odds-API
                    prob_a = random.uniform(0.35, 0.85)
                    prob_b = 1 - prob_a
                    
                    odds_a = (1 / prob_a) * random.uniform(0.9, 1.05)
                    odds_b = (1 / prob_b) * random.uniform(0.9, 1.05)
                    
                    # Forzar algunos con EV positivo para que se vean en el filtro
                    if random.random() > 0.7:
                        odds_a = odds_a * 1.2
                        
                    matches.append({
                        "id": str(match_id),
                        "tournament": tournament_name,
                        "surface": surface,
                        "time": time_str,
                        "player_a": p1_name,
                        "player_b": p2_name,
                        "odds_a": round(odds_a, 2),
                        "odds_b": round(odds_b, 2),
                        "model_prob_a": round(prob_a, 4),
                        "model_prob_b": round(prob_b, 4)
                    })
                    match_id += 1
                    
        return matches

if __name__ == "__main__":
    scraper = ESPNScraper()
    matches = scraper.get_real_matches()
    print(f"Encontrados {len(matches)} partidos reales de la ATP.")
    if matches:
        print(matches[0])
