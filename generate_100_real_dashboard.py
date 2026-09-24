import json
import re
import math
from data_pipeline.espn_scraper import ESPNScraper
from data_pipeline.tennis_abstract_scraper import TennisAbstractScraper
from thefuzz import process

def get_elo_probability(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def main():
    print("1. Descargando ELO...")
    ta_scraper = TennisAbstractScraper()
    df_elo = ta_scraper.get_elo_ratings()
    
    elo_dict = {}
    if df_elo is not None:
        for _, row in df_elo.iterrows():
            player = str(row.get('player', '')).replace('\xa0', ' ').strip()
            elo_dict[player] = {
                'general': float(row.get('elo', 1500)),
                'hard': float(row.get('helo', 1500)),
                'clay': float(row.get('celo', 1500)),
                'grass': float(row.get('gelo', 1500))
            }
        
    print("2. Obteniendo ESPN...")
    espn_scraper = ESPNScraper()
    matches = espn_scraper.get_real_matches()

    print("3. Ejecutando Motor Estadístico...")
    processed_matches = []
    DEFAULT_ELO = 1450

    def find_stats_fuzzy(name):
        if name in elo_dict: return elo_dict[name]
        choices = list(elo_dict.keys())
        best_match, score = process.extractOne(name, choices)
        if score > 75: return elo_dict[best_match]
        return None

    for m in matches:
        p1_stats = find_stats_fuzzy(m['player_a'])
        p2_stats = find_stats_fuzzy(m['player_b'])
        
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

    processed_matches.sort(key=lambda x: max(x['model_prob_a'], x['model_prob_b']), reverse=True)

    print("4. Actualizando el Dashboard estático...")
    json_data = json.dumps(processed_matches)
    
    html_template = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
      tailwind.config = {
          theme: { extend: { colors: { background: '#ffffff', foreground: '#000000', card: '#ffffff', border: '#e5e7eb', mutedForeground: '#6b7280', secondary: '#f3f4f6', secondaryForeground: '#111827' } } }
      }
  </script>
</head>
<body class="bg-gray-50 text-gray-900 antialiased p-5">
  <div class="bg-white text-gray-900 border border-gray-200 rounded-xl p-5 shadow-sm max-w-5xl mx-auto">
    <div class="flex justify-between items-center mb-6 border-b border-gray-200 pb-4">
        <div>
            <h2 class="text-gray-900 font-bold text-2xl flex items-center gap-2">🏆 ATP Predictor - Winner Engine</h2>
            <p class="text-gray-500 text-sm mt-1">Predicciones 100% reales. Actualización vía GitHub Actions.</p>
        </div>
        <div class="flex gap-2">
            <button class="px-4 py-2 bg-gray-200 text-gray-900 rounded hover:bg-gray-300 text-sm font-medium" onclick="filterMatches('all')">Cartelera Completa</button>
            <button class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium shadow-sm" onclick="filterMatches('high-prob')">Favoritos Claros (>65%)</button>
        </div>
    </div>
    <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-sm">
            <thead>
                <tr class="border-b border-gray-200 text-gray-500 uppercase tracking-wider text-xs">
                    <th class="p-3">Torneo / Pista</th>
                    <th class="p-3">Partido</th>
                    <th class="p-3">Estadística (Elo)</th>
                    <th class="p-3">Probabilidad</th>
                    <th class="p-3">Pronóstico</th>
                </tr>
            </thead>
            <tbody id="matches-body" class="divide-y divide-gray-200"></tbody>
        </table>
    </div>
  </div>
  <script>
    let allMatches = REPLACE_JSON_DATA; 

    function renderMatches(matches) {
        const tbody = document.getElementById('matches-body');
        tbody.innerHTML = '';
        if(matches.length === 0){
            tbody.innerHTML = '<tr><td colspan="5" class="text-center p-8 text-gray-500">No hay partidos hoy.</td></tr>';
            return;
        }
        matches.forEach(m => {
            let isFavA = m.model_prob_a > m.model_prob_b;
            let colorA = isFavA ? 'text-blue-600 font-bold' : 'text-gray-500';
            let colorB = !isFavA ? 'text-blue-600 font-bold' : 'text-gray-500';
            let winnerName = isFavA ? m.player_a : m.player_b;
            let winnerProb = isFavA ? m.model_prob_a : m.model_prob_b;
            let winnerBadge = `<span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-blue-100 text-blue-800">👑 ${winnerName} (${(winnerProb*100).toFixed(1)}%)</span>`;
            let row = `
                <tr class="hover:bg-gray-50 transition-colors">
                    <td class="p-3"><div class="font-semibold">${m.tournament}</div><div class="text-xs text-gray-500">${m.surface} | ${m.time}</div></td>
                    <td class="p-3">
                        <div><span class="${isFavA ? 'font-bold' : 'font-medium'}">${m.player_a}</span></div>
                        <div class="mt-1"><span class="${!isFavA ? 'font-bold' : 'font-medium'}">${m.player_b}</span></div>
                    </td>
                    <td class="p-3 font-mono text-xs">
                        <div class="text-gray-500">Gen: ${m.elo_a_gen} | Surf: ${m.elo_a_surf}</div>
                        <div class="mt-1 text-gray-500">Gen: ${m.elo_b_gen} | Surf: ${m.elo_b_surf}</div>
                    </td>
                    <td class="p-3 font-mono">
                        <div class="${colorA} text-lg">${(m.model_prob_a * 100).toFixed(1)}%</div>
                        <div class="mt-1 ${colorB} text-lg">${(m.model_prob_b * 100).toFixed(1)}%</div>
                    </td>
                    <td class="p-3">${winnerBadge}</td>
                </tr>`;
            tbody.insertAdjacentHTML('beforeend', row);
        });
    }

    function filterMatches(type) {
        if (type === 'high-prob') {
            const clearFavorites = allMatches.filter(m => m.model_prob_a > 0.65 || m.model_prob_b > 0.65);
            renderMatches(clearFavorites.sort((a,b) => Math.max(b.model_prob_a, b.model_prob_b) - Math.max(a.model_prob_a, a.model_prob_b)));
        } else {
            renderMatches(allMatches);
        }
    }
    
    renderMatches(allMatches);
  </script>
</body>
</html>"""
    
    final_html = html_template.replace("REPLACE_JSON_DATA", json_data)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    print("COMPLETADO! Archivo index.html regenerado de cero.")

if __name__ == "__main__":
    main()
