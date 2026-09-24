import json
import re
import math
from data_pipeline.espn_scraper import ESPNScraper
from data_pipeline.tennis_abstract_scraper import TennisAbstractScraper

NAME_MAPPINGS = {
    "Carlos Alcaraz Garfia": "Carlos Alcaraz",
    "Stanislas Wawrinka": "Stan Wawrinka",
    "Alex De Minaur": "Alex de Minaur",
    "J.J. Wolf": "Jeffrey John Wolf",
    "Alexander Zverev": "Alexander Zverev",
}

def normalize_name(name):
    if name in NAME_MAPPINGS:
        return NAME_MAPPINGS[name]
    return name

def get_elo_probability(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def main():
    print("1. Descargando ELO...")
    ta_scraper = TennisAbstractScraper()
    df_elo = ta_scraper.get_elo_ratings()
    
    elo_dict = {}
    if df_elo is not None:
        for _, row in df_elo.iterrows():
            player = str(row.get('player', '')).strip()
            elo_dict[player] = {
                'general': float(row.get('elo', 1500)),
                'hard': float(row.get('hardraw', 1500)),
                'clay': float(row.get('clayraw', 1500)),
                'grass': float(row.get('grassraw', 1500))
            }
        
    print("2. Obteniendo ESPN...")
    espn_scraper = ESPNScraper()
    matches = espn_scraper.get_real_matches()

    print("3. Ejecutando Motor Estadístico...")
    processed_matches = []
    DEFAULT_ELO = 1450

    for m in matches:
        p1_name = normalize_name(m['player_a'])
        p2_name = normalize_name(m['player_b'])
        
        p1_stats = elo_dict.get(p1_name)
        p2_stats = elo_dict.get(p2_name)
        
        if not p1_stats:
            for ta_name in elo_dict.keys():
                if p1_name.split()[-1] in ta_name and p1_name[0] == ta_name[0]:
                    p1_stats = elo_dict[ta_name]
                    break
        if not p2_stats:
            for ta_name in elo_dict.keys():
                if p2_name.split()[-1] in ta_name and p2_name[0] == ta_name[0]:
                    p2_stats = elo_dict[ta_name]
                    break
                    
        p1_stats = p1_stats or {'general': DEFAULT_ELO, 'hard': DEFAULT_ELO, 'clay': DEFAULT_ELO, 'grass': DEFAULT_ELO}
        p2_stats = p2_stats or {'general': DEFAULT_ELO, 'hard': DEFAULT_ELO, 'clay': DEFAULT_ELO, 'grass': DEFAULT_ELO}
        
        surface = m['surface'].lower()
        if 'clay' in surface: surf_key = 'clay'
        elif 'grass' in surface: surf_key = 'grass'
        else: surf_key = 'hard'
        
        m['elo_a_gen'] = int(p1_stats['general'])
        m['elo_b_gen'] = int(p2_stats['general'])
        m['elo_a_surf'] = int(p1_stats[surf_key])
        m['elo_b_surf'] = int(p2_stats[surf_key])
        
        blended_elo_a = (0.6 * p1_stats[surf_key]) + (0.4 * p1_stats['general'])
        blended_elo_b = (0.6 * p2_stats[surf_key]) + (0.4 * p2_stats['general'])
        
        prob_a = get_elo_probability(blended_elo_a, blended_elo_b)
        
        m['model_prob_a'] = round(prob_a, 4)
        m['model_prob_b'] = round(1 - prob_a, 4)
        
        processed_matches.append(m)

    # Sort matches by the most clear favorites first
    processed_matches.sort(key=lambda x: max(x['model_prob_a'], x['model_prob_b']), reverse=True)

    print("4. Actualizando el Dashboard...")
    json_data = json.dumps(processed_matches)
    widget_path = r'index.html'
    
    with open(widget_path, 'r', encoding='utf-8') as f:
        html = f.read()
        
    html = re.sub(r'let allMatches = \[\];', f'let allMatches = {json_data};\n    renderMatches(allMatches);', html, flags=re.DOTALL)
    
    with open(widget_path, 'w', encoding='utf-8') as f:
        f.write(html)
        
    print("COMPLETADO!")

if __name__ == "__main__":
    main()
