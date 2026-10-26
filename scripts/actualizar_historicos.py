"""Descarga precios históricos reales (Financial Times, markets.ft.com) de los
fondos de la cartera y de los activos de comparación, y los guarda en
historicos.json (cierre de cada mes, en la divisa del fondo).

Uso:  python scripts/actualizar_historicos.py

Solo usa datos publicados por FT para cada ISIN: no rellena huecos ni inventa
valores. Si un fondo no existía en una fecha, simplemente no tiene datos ahí.
"""
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
OUT = Path(__file__).resolve().parent.parent / 'historicos.json'

# id = el mismo que usa el dashboard para el activo (o uno propio para comparativas)
SERIES = [
    # --- Cartera ---
    {'id': 'ishares_dev', 'isin': 'IE000ZYRH0Q7', 'name': 'iShares Developed World Index (IE)'},
    {'id': 'horos_val', 'isin': 'ES0146309002', 'name': 'Horos Value Internacional FI'},
    {'id': 'cobas_intl', 'isin': 'ES0119199000', 'name': 'Cobas International FI'},
    {'id': 'vanguard_emerg', 'isin': 'IE0031786696', 'name': 'Vanguard Emerging Markets Stock Index'},
    {'id': 'gold_etc', 'isin': 'IE00B4ND3602', 'name': 'iShares Physical Gold ETC', 'kinds': ['etfs', 'funds']},
    {'id': 'vanguard_small', 'isin': 'IE00BLP5S460', 'name': 'Jupiter Merian Global Equity Absolute Return'},
    {'id': 'axa_cash', 'isin': 'FR0000447823', 'name': 'AXA Trésor Court Terme'},
    {'id': 'asset_1792426198360', 'isin': 'LU3038481936', 'name': 'Hamco SICAV Global Value'},
    {'id': 'vanguard_dev', 'isin': 'IE00B0476091', 'name': 'Vanguard Global Stock Index'},
    # --- Comparativas (fondos indexados reales con histórico largo, en EUR) ---
    {'id': 'bm_msci_world', 'isin': 'IE00B03HD191', 'name': 'MSCI World (Vanguard Global Stock Index EUR)', 'bench': True},
    {'id': 'bm_sp500', 'isin': 'IE0032126645', 'name': 'S&P 500 (Vanguard U.S. 500 Stock Index EUR)', 'bench': True},
    {'id': 'bm_emerg', 'isin': 'IE0031786696', 'name': 'Emergentes (Vanguard Emerging Markets EUR)', 'bench': True},
    {'id': 'bm_bonds', 'isin': 'IE00B18GC888', 'name': 'Bonos globales (Vanguard Global Bond Index EUR Hedged)', 'bench': True},
    {'id': 'bm_cash', 'isin': 'FR0000447823', 'name': 'Monetario (AXA Trésor Court Terme)', 'bench': True},
    {'id': 'bm_gold', 'isin': 'IE00B4ND3602', 'name': 'Oro (iShares Physical Gold ETC)', 'bench': True, 'kinds': ['etfs', 'funds']},
]


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 + i * 2)


def find_symbol(isin, kinds):
    """Devuelve (xid, símbolo, divisa) de FT para el ISIN."""
    for kind in kinds:
        for cur in ('EUR', 'USD', 'GBX', 'GBP', None):
            sym = f'{isin}:{cur}' if cur else isin
            try:
                page = get(f'https://markets.ft.com/data/{kind}/tearsheet/historical?s={urllib.parse.quote(sym)}')
            except Exception:  # noqa: BLE001
                continue
            m = re.search(r'data-mod-config="([^"]*xid[^"]*)"', page)
            if not m:
                continue
            cfg = json.loads(html.unescape(m.group(1)))
            if cfg.get('xid'):
                return cfg['xid'], cfg.get('symbol', sym), cfg.get('currency') or cur
    return None, None, None


# Una fila por día: fecha (versión larga) y apertura, máximo, mínimo, cierre
ROW = re.compile(
    r'<tr><td class="mod-ui-table__cell--text"><span class="mod-ui-hide-small-below">([^<]+)</span>.*?</td>'
    r'<td>([\d.,]+)</td><td>([\d.,]+)</td><td>([\d.,]+)</td><td>([\d.,]+)</td>',
    re.S)


def fetch_daily(xid, start=dt.date(1998, 1, 1)):
    """Cierres diarios {fecha: precio}. FT devuelve como mucho ~1 año por petición."""
    out = {}
    end = dt.date.today()
    cur_end = end
    empty_years = 0
    while cur_end > start:
        cur_start = max(start, cur_end - dt.timedelta(days=364))
        url = ('https://markets.ft.com/data/equities/ajax/get-historical-prices?'
               f'startDate={cur_start:%Y/%m/%d}&endDate={cur_end:%Y/%m/%d}&symbol={xid}')
        data = json.loads(get(url))
        rows = ROW.findall(data.get('html', ''))
        for d, _o, _h, _l, close in rows:
            day = dt.datetime.strptime(d.strip(), '%A, %B %d, %Y').date()
            out[day.isoformat()] = float(close.replace(',', ''))
        if rows:
            empty_years = 0
        else:
            empty_years += 1
            if empty_years >= 2:  # antes del lanzamiento del fondo
                break
        cur_end = cur_start - dt.timedelta(days=1)
        time.sleep(0.4)
    return dict(sorted(out.items()))


def month_end(daily):
    """Último cierre disponible de cada mes (fecha real de ese cierre)."""
    by_month = {}
    for day, px in daily.items():
        by_month[day[:7]] = (day, px)
    return [[d, round(p, 6)] for _m, (d, p) in sorted(by_month.items())]


def ecb_usd_per_eur():
    """Tipo oficial diario del BCE (dólares por euro): {fecha: tipo}."""
    url = ('https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A'
           '?format=csvdata&startPeriod=1999-01-01')
    rates = {}
    lines = get(url).splitlines()
    head = lines[0].split(',')
    i_t, i_v = head.index('TIME_PERIOD'), head.index('OBS_VALUE')
    for line in lines[1:]:
        cols = line.split(',')
        try:
            rates[cols[i_t]] = float(cols[i_v])
        except (ValueError, IndexError):
            pass
    return dict(sorted(rates.items()))


def to_eur(monthly, rates):
    """Convierte cierres en USD a EUR con el tipo BCE de ese día (o el último anterior)."""
    days = list(rates)
    out = []
    j = 0
    for d, px in monthly:
        while j + 1 < len(days) and days[j + 1] <= d:
            j += 1
        if days[j] > d:
            continue  # no hay tipo oficial anterior: no se inventa
        out.append([d, round(px / rates[days[j]], 6)])
    return out


def main():
    result = {
        'source': 'Financial Times (markets.ft.com), precio de cierre diario por ISIN',
        'generated': dt.date.today().isoformat(),
        'note': 'Cierre del último día con dato de cada mes. Sin datos inventados: '
                'si un fondo no existía, no tiene puntos en esas fechas.',
        'series': {}
    }
    cache = {}
    for s in SERIES:
        isin = s['isin']
        if isin not in cache:
            xid, sym, cur = find_symbol(isin, s.get('kinds', ['funds', 'etfs']))
            if not xid:
                print(f'!! {isin} ({s["name"]}): no encontrado en FT', file=sys.stderr)
                cache[isin] = None
                continue
            daily = fetch_daily(xid)
            if not cur and sym and ':' in sym:
                cur = sym.rsplit(':', 1)[1]
            monthly = month_end(daily)
            if cur == 'USD':
                monthly = to_eur(monthly, ecb_usd_per_eur())
                cur = 'EUR (convertido de USD con el tipo oficial del BCE de cada fecha)'
            cache[isin] = {'symbol': sym, 'currency': cur, 'monthly': monthly,
                           'first': next(iter(daily), None), 'last': next(reversed(daily), None)}
            print(f'ok {isin} {sym} {cur}: {len(daily)} días, {cache[isin]["first"]} -> {cache[isin]["last"]}')
        c = cache[isin]
        if not c:
            continue
        result['series'][s['id']] = {
            'isin': isin, 'name': s['name'], 'bench': bool(s.get('bench')),
            'ftSymbol': c['symbol'], 'currency': c['currency'],
            'first': c['first'], 'last': c['last'], 'monthly': c['monthly'],
        }
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('guardado', OUT)


if __name__ == '__main__':
    main()
