#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aggiorna_dati.py

Ricostruisce "dati.json", il file che alimenta l'app Cercafunghi.

Fa tre cose:
  1. scarica dal SIR Toscana la pioggia giornaliera misurata
  2. scarica da Open-Meteo temperatura e umidita' del suolo, e l'aria
  3. calcola le cumulate e scrive dati.json

Usa SOLO la libreria standard di Python 3: nessuna installazione.

Uso:
    python scripts/aggiorna_dati.py

Se il SIR non risponde, riusa la pioggia gia' presente nel dati.json
precedente invece di buttare via tutto.

Fonti:
  SIR - Servizio Idrologico Regionale, Regione Toscana (pioggia misurata)
  Open-Meteo, modelli ERA5-Land e ICON (suolo e aria, modellati)
"""

import csv
import http.cookiejar
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, timedelta

# ===========================================================================
# IMPOSTAZIONI
# ===========================================================================

GIORNI_INDIETRO = 45      # quanti giorni di storia mostrare nell'app
GIORNI_AVANTI   = 7       # giorni di previsione del suolo
GIORNI_PIOGGIA  = 80      # quanta pioggia scaricare, per le cumulate a 30 gg

PAUSA_SIR = 0.6
PAUSA_METEO = 1.5
STAZIONI_PER_CHIAMATA = 25

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_STAZIONI = os.path.join(RADICE, "stazioni.csv")
FILE_USCITA   = os.path.join(RADICE, "dati.json")

# ===========================================================================

SIR_BASE = "http://www.sir.toscana.it/archivio/dati.php"
SIR_SESSIONE = "http://www.sir.toscana.it/consistenza-rete"
METEO_BASE = "https://api.open-meteo.com/v1/forecast"
VARIABILI = ["temperature_2m", "soil_temperature_0_to_7cm",
             "soil_temperature_7_to_28cm", "soil_moisture_7_to_28cm"]

INTESTAZIONI = {
    "Accept": "*/*",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/151.0.0.0 Safari/537.36"),
    "X-Requested-With": "XMLHttpRequest",
    "Referer": SIR_SESSIONE,
}


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- stazioni
def leggi_stazioni():
    if not os.path.exists(FILE_STAZIONI):
        log("ERRORE: manca %s" % FILE_STAZIONI)
        sys.exit(1)
    elenco = []
    with open(FILE_STAZIONI, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            try:
                elenco.append({
                    "c": r["codice"].strip(), "n": r["nome"].strip(),
                    "m": r.get("comune", "").strip(), "p": r.get("prov", "").strip(),
                    "a": r.get("area", "").strip(), "q": int(float(r["quota_m"])),
                    "lat": float(r["lat"]), "lon": float(r["lon"]),
                    "ap": 1 if r.get("pos_approssimata", "").strip().lower() == "si" else 0,
                })
            except (KeyError, ValueError):
                pass
    return elenco


# -------------------------------------------------------------------- SIR
def sessione_sir():
    barattolo = http.cookiejar.CookieJar()
    ap = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(barattolo))
    try:
        req = urllib.request.Request(SIR_SESSIONE,
                                     headers={"User-Agent": INTESTAZIONI["User-Agent"]})
        with ap.open(req, timeout=45) as r:
            r.read()
    except Exception as e:
        log("  avviso apertura sessione SIR: %s" % e)
    return ap


def scarica_pioggia(stazioni, da):
    """Restituisce {codice: {data: mm}}. Solleva eccezione se fallisce tutto."""
    ap = sessione_sir()
    anno = str(date.today().year)
    fuori = {}
    ok = falliti = vuote = 0
    for i, s in enumerate(stazioni, 1):
        serie = None
        for sensore in ("pluvio0_24", "pluvio"):
            try:
                par = {"A": anno, "IDS": s["c"], "IDST": sensore, "D": "json"}
                req = urllib.request.Request(SIR_BASE + "?" + urllib.parse.urlencode(par),
                                             headers=INTESTAZIONI)
                with ap.open(req, timeout=120) as r:
                    dati = json.loads(r.read().decode("utf-8"))
                voci = (dati.get("properties") or {}).get("SerieDati") or []
            except Exception:
                voci = []
            tenute = {}
            for v in voci:
                g = (v.get("Data") or "")[:10]
                if not g or g < da:
                    continue
                if v.get("Valore") is None or v.get("TipoValore") == "@":
                    continue
                try:
                    tenute[g] = float(v["Valore"])
                except (TypeError, ValueError):
                    pass
            if tenute:
                serie = tenute
                break
            time.sleep(0.2)
        if serie:
            fuori[s["c"]] = serie
            ok += 1
        else:
            vuote += 1
        if i % 40 == 0:
            log("    SIR %d/%d  (con dati %d, senza %d)" % (i, len(stazioni), ok, vuote))
        time.sleep(PAUSA_SIR)
    log("  SIR: %d stazioni con dati, %d senza" % (ok, vuote))
    if ok == 0:
        raise RuntimeError("il SIR non ha restituito nessun dato")
    return fuori


# ------------------------------------------------------------- Open-Meteo
def scarica_suolo(stazioni):
    fuori = defaultdict(dict)
    gruppi = [stazioni[i:i + STAZIONI_PER_CHIAMATA]
              for i in range(0, len(stazioni), STAZIONI_PER_CHIAMATA)]
    for n, g in enumerate(gruppi, 1):
        par = {
            "latitude": ",".join("%.5f" % s["lat"] for s in g),
            "longitude": ",".join("%.5f" % s["lon"] for s in g),
            "hourly": ",".join(VARIABILI),
            "past_days": str(min(92, GIORNI_INDIETRO + 5)),
            "forecast_days": str(GIORNI_AVANTI),
            "timezone": "Europe/Rome",
        }
        url = METEO_BASE + "?" + urllib.parse.urlencode(par)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cercafunghi/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                risp = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            log("    gruppo %d/%d FALLITO: %s" % (n, len(gruppi), e))
            time.sleep(PAUSA_METEO * 3)
            continue
        if isinstance(risp, dict):
            risp = [risp]
        for s, d in zip(g, risp):
            orario = d.get("hourly") or {}
            per_g = defaultdict(lambda: defaultdict(list))
            for k, istante in enumerate(orario.get("time", [])):
                gg = istante[:10]
                for var in VARIABILI:
                    serie = orario.get(var) or []
                    if k < len(serie) and serie[k] is not None:
                        per_g[gg][var].append(serie[k])
            for gg, vv in per_g.items():
                voce = {var: (round(sum(v) / len(v), 2) if v else None)
                        for var, v in vv.items()}
                aria = vv.get("temperature_2m") or []
                voce["t_min"] = round(min(aria), 1) if aria else None
                voce["t_max"] = round(max(aria), 1) if aria else None
                fuori[s["c"]][gg] = voce
        log("    meteo %d/%d" % (n, len(gruppi)))
        time.sleep(PAUSA_METEO)
    return fuori


# ---------------------------------------------------------------- montaggio
def costruisci(stazioni, pioggia, suolo):
    oggi = date.today()
    d0 = oggi - timedelta(GIORNI_INDIETRO)
    d1 = oggi + timedelta(GIORNI_AVANTI)
    date_app = [(d0 + timedelta(k)).isoformat() for k in range((d1 - d0).days + 1)]

    def somma(cod, giorno, n):
        d = date.fromisoformat(giorno)
        tot = 0.0
        trovati = 0
        for k in range(n):
            v = pioggia.get(cod, {}).get((d - timedelta(k)).isoformat())
            if v is not None:
                tot += v
                trovati += 1
        return round(tot, 1) if trovati else None

    def q(v, n=1):
        return None if v is None else round(v, n)

    fuori = []
    ultima = ""
    for s in stazioni:
        S = suolo.get(s["c"], {})
        P = pioggia.get(s["c"], {})
        if not S:
            continue
        for g, v in P.items():
            if v is not None and g <= oggi.isoformat() and g > ultima:
                ultima = g
        voce = dict(s)
        voce["pio"] = [P.get(g) for g in date_app]
        voce["p7"] = [somma(s["c"], g, 7) for g in date_app]
        voce["p15"] = [somma(s["c"], g, 15) for g in date_app]
        voce["p30"] = [somma(s["c"], g, 30) for g in date_app]
        for chiave, var, dec in (("ts", "soil_temperature_7_to_28cm", 1),
                                 ("ts0", "soil_temperature_0_to_7cm", 1),
                                 ("sm", "soil_moisture_7_to_28cm", 3),
                                 ("ta", "temperature_2m", 1)):
            voce[chiave] = [q((S.get(g) or {}).get(var), dec) for g in date_app]
        voce["tmn"] = [q((S.get(g) or {}).get("t_min"), 1) for g in date_app]
        voce["tmx"] = [q((S.get(g) or {}).get("t_max"), 1) for g in date_app]
        fuori.append(voce)

    return {"date": date_app, "ultima_pioggia": ultima or date_app[0],
            "aggiornato": oggi.isoformat(), "stazioni": fuori}


def main():
    stazioni = leggi_stazioni()
    log("Stazioni: %d" % len(stazioni))

    da_pioggia = (date.today() - timedelta(GIORNI_PIOGGIA)).isoformat()

    log("\n[1/3] Pioggia misurata dal SIR (ci vuole un po')...")
    try:
        pioggia = scarica_pioggia(stazioni, da_pioggia)
    except Exception as e:
        log("  SIR non disponibile: %s" % e)
        pioggia = {}
        if os.path.exists(FILE_USCITA):
            log("  riuso la pioggia del dati.json precedente")
            vecchio = json.load(open(FILE_USCITA, encoding="utf-8"))
            date_v = vecchio.get("date", [])
            for st in vecchio.get("stazioni", []):
                serie = {g: v for g, v in zip(date_v, st.get("pio", [])) if v is not None}
                if serie:
                    pioggia[st["c"]] = serie
        if not pioggia:
            log("  nessuna pioggia disponibile: mi fermo senza toccare dati.json")
            sys.exit(1)

    log("\n[2/3] Suolo e aria da Open-Meteo...")
    suolo = scarica_suolo(stazioni)
    if not suolo:
        log("  Open-Meteo non ha risposto: mi fermo senza toccare dati.json")
        sys.exit(1)

    log("\n[3/3] Monto dati.json...")
    dati = costruisci(stazioni, pioggia, suolo)
    with open(FILE_USCITA, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, separators=(",", ":"))

    log("\n" + "-" * 56)
    log("  stazioni scritte : %d" % len(dati["stazioni"]))
    log("  giorni           : %d  (%s -> %s)"
        % (len(dati["date"]), dati["date"][0], dati["date"][-1]))
    log("  ultima pioggia   : %s" % dati["ultima_pioggia"])
    log("  file             : %s  (%.0f KB)"
        % (FILE_USCITA, os.path.getsize(FILE_USCITA) / 1024))
    log("-" * 56)


if __name__ == "__main__":
    main()
