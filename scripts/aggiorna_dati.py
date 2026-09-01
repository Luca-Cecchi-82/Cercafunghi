#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aggiorna_dati.py

Ricostruisce il dati.json di uno o piu' rami dell'app Cercafunghi.

Fa tre cose:
  1. scarica dal SIR Toscana la pioggia giornaliera misurata
  2. scarica da Open-Meteo temperatura e umidita' del suolo, e l'aria
  3. calcola le cumulate e scrive <ramo>/dati.json

Ogni ramo sta in una sua sottocartella e ha il suo <ramo>/config.json,
da cui vengono letti la stringa di versione e i parametri della finestra
temporale. La versione finisce dentro dati.json e da li' nell'app.

Lo scarico dalle sorgenti avviene UNA VOLTA SOLA anche con piu' rami:
cambia solo il montaggio, secondo la configurazione di ciascuno.

Usa SOLO la libreria standard di Python 3: nessuna installazione.

Uso:
    python scripts/aggiorna_dati.py            (usa il ramo A1)
    python scripts/aggiorna_dati.py A1 A2      (rami indicati)

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

RAMI_PREDEFINITI = ["A1"]

# valori usati se il config.json del ramo non li specifica
GIORNI_INDIETRO = 45      # quanti giorni di storia mostrare nell'app
GIORNI_AVANTI   = 7       # giorni di previsione del suolo
GIORNI_PIOGGIA  = 80      # quanta pioggia scaricare, per le cumulate a 30 gg
# Frazione minima di giorni con dato vero perche' una cumulata sia valida.
# Senza questo controllo una finestra mezza vuota - i giorni futuri, dove
# la pioggia misurata non esiste, o un buco nella serie SIR - restituisce
# una somma parziale che l'app legge come "e' piovuto poco" invece che
# come "il dato non c'e'".
COPERTURA_CUMULATE = 0.8

PAUSA_SIR = 0.6
PAUSA_METEO = 3.0          # Open-Meteo limita la frequenza: meglio non correre
STAZIONI_PER_CHIAMATA = 25
TENTATIVI_METEO = 3        # quante volte riprovare un gruppo che fallisce
TIMEOUT_METEO = 45         # secondi: se non risponde entro, e' inutile aspettare

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_STAZIONI = os.path.join(RADICE, "stazioni.csv")


def cartella(ramo):
    return os.path.join(RADICE, ramo)


def file_config(ramo):
    return os.path.join(cartella(ramo), "config.json")


def file_dati(ramo):
    return os.path.join(cartella(ramo), "dati.json")


def leggi_config(ramo):
    """Legge <ramo>/config.json. Se manca qualcosa usa i valori predefiniti."""
    percorso = file_config(ramo)
    if not os.path.exists(percorso):
        log("ERRORE: manca %s" % percorso)
        sys.exit(1)
    with open(percorso, encoding="utf-8") as f:
        cfg = json.load(f)
    d = cfg.get("dati") or {}
    cfg["_indietro"] = int(d.get("giorni_indietro", GIORNI_INDIETRO))
    cfg["_avanti"] = int(d.get("giorni_avanti", GIORNI_AVANTI))
    cfg["_pioggia"] = int(d.get("giorni_pioggia", GIORNI_PIOGGIA))
    cfg["_copertura"] = float(d.get("copertura_minima_cumulate",
                                    COPERTURA_CUMULATE))
    if not cfg.get("versione"):
        log("ERRORE: %s non contiene la stringa di versione" % percorso)
        sys.exit(1)
    return cfg

# ===========================================================================

SIR_BASE = "http://www.sir.toscana.it/archivio/dati.php"
SIR_SESSIONE = "http://www.sir.toscana.it/consistenza-rete"
METEO_BASE = "https://api.open-meteo.com/v1/forecast"
VARIABILI = ["temperature_2m", "soil_temperature_0_to_7cm",
             "soil_temperature_7_to_28cm", "soil_moisture_7_to_28cm",
             "soil_moisture_0_to_7cm"]

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
FINESTRA = {"indietro": GIORNI_INDIETRO, "avanti": GIORNI_AVANTI}


def chiedi_meteo(gruppo, etichetta):
    """Una chiamata a Open-Meteo, con piu' tentativi.
    Open-Meteo limita la frequenza e quando siamo troppo veloci lascia
    cadere la connessione invece di rispondere: riprovare risolve."""
    par = {
        "latitude": ",".join("%.5f" % s["lat"] for s in gruppo),
        "longitude": ",".join("%.5f" % s["lon"] for s in gruppo),
        "hourly": ",".join(VARIABILI),
        "past_days": str(min(92, FINESTRA["indietro"] + 5)),
        "forecast_days": str(FINESTRA["avanti"]),
        "timezone": "Europe/Rome",
    }
    url = METEO_BASE + "?" + urllib.parse.urlencode(par)
    ultimo = None
    for tentativo in range(1, TENTATIVI_METEO + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cercafunghi/1.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_METEO) as r:
                risp = json.loads(r.read().decode("utf-8"))
            return [risp] if isinstance(risp, dict) else risp
        except Exception as e:
            ultimo = e
            if tentativo < TENTATIVI_METEO:
                attesa = 5 * (2 ** (tentativo - 1))     # 5, 10, 20 secondi
                log("    %s: tentativo %d fallito (%s), riprovo fra %d s"
                    % (etichetta, tentativo, e, attesa))
                time.sleep(attesa)
            else:
                log("    %s: tentativo %d fallito (%s)" % (etichetta, tentativo, e))
    raise ultimo


def scarica_suolo(stazioni):
    fuori = defaultdict(dict)
    gruppi = [stazioni[i:i + STAZIONI_PER_CHIAMATA]
              for i in range(0, len(stazioni), STAZIONI_PER_CHIAMATA)]
    persi = 0
    for n, g in enumerate(gruppi, 1):
        etichetta = "gruppo %d/%d" % (n, len(gruppi))
        try:
            risp = chiedi_meteo(g, etichetta)
        except Exception as e:
            log("    %s PERSO dopo %d tentativi: %s"
                % (etichetta, TENTATIVI_METEO, e))
            persi += len(g)
            continue
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
                voce = {var: (round(sum(v) / len(v), 3) if v else None)
                        for var, v in vv.items()}
                aria = vv.get("temperature_2m") or []
                voce["t_min"] = round(min(aria), 1) if aria else None
                voce["t_max"] = round(max(aria), 1) if aria else None
                fuori[s["c"]][gg] = voce
        log("    %s scaricato" % etichetta)
        time.sleep(PAUSA_METEO)
    if persi:
        log("  ATTENZIONE: %d stazioni senza dati del suolo" % persi)
    return fuori


# ---------------------------------------------------------------- montaggio
def costruisci(stazioni, pioggia, suolo, cfg):
    oggi = date.today()
    d0 = oggi - timedelta(cfg["_indietro"])
    d1 = oggi + timedelta(cfg["_avanti"])
    date_app = [(d0 + timedelta(k)).isoformat() for k in range((d1 - d0).days + 1)]

    copertura = cfg.get("_copertura", COPERTURA_CUMULATE)

    def somma(cod, giorno, n):
        """Cumulata sugli n giorni che finiscono in 'giorno'.

        Restituisce None se i giorni con dato vero sono meno della
        frazione richiesta. Serve soprattutto per i giorni previsti:
        li' la pioggia misurata non esiste ancora, la finestra si
        svuota man mano che ci si allontana da oggi, e senza questo
        controllo il punteggio idrico calerebbe da solo ogni giorno
        per pura aritmetica, non per il meteo."""
        d = date.fromisoformat(giorno)
        minimo = n * copertura
        tot = 0.0
        trovati = 0
        for k in range(n):
            v = pioggia.get(cod, {}).get((d - timedelta(k)).isoformat())
            if v is not None:
                tot += v
                trovati += 1
        return round(tot, 1) if trovati >= minimo else None

    def q(v, n=1):
        return None if v is None else round(v, n)

    fuori = []
    ultima = ""
    for s in stazioni:
        S = suolo.get(s["c"], {})
        P = pioggia.get(s["c"], {})
        if not S and not P:
            continue          # nessun dato di nessun tipo: inutile tenerla
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
                                 ("sm0", "soil_moisture_0_to_7cm", 3),
                                 ("ta", "temperature_2m", 1)):
            voce[chiave] = [q((S.get(g) or {}).get(var), dec) for g in date_app]
        voce["tmn"] = [q((S.get(g) or {}).get("t_min"), 1) for g in date_app]
        voce["tmx"] = [q((S.get(g) or {}).get("t_max"), 1) for g in date_app]
        fuori.append(voce)

    return {"versione": cfg["versione"], "ramo": cfg.get("ramo", ""),
            "date": date_app, "ultima_pioggia": ultima or date_app[0],
            "aggiornato": oggi.isoformat(), "stazioni": fuori}


def main():
    rami = sys.argv[1:] or RAMI_PREDEFINITI
    config = {r: leggi_config(r) for r in rami}
    log("Rami da ricostruire: %s"
        % ", ".join("%s (versione %s)" % (r, config[r]["versione"]) for r in rami))

    # una sola finestra di scarico, la piu' ampia richiesta dai rami
    FINESTRA["indietro"] = max(c["_indietro"] for c in config.values())
    FINESTRA["avanti"] = max(c["_avanti"] for c in config.values())
    giorni_pioggia = max(c["_pioggia"] for c in config.values())

    stazioni = leggi_stazioni()
    log("Stazioni: %d" % len(stazioni))

    da_pioggia = (date.today() - timedelta(giorni_pioggia)).isoformat()

    log("\n[1/3] Pioggia misurata dal SIR (ci vuole un po')...")
    try:
        pioggia = scarica_pioggia(stazioni, da_pioggia)
    except Exception as e:
        log("  SIR non disponibile: %s" % e)
        pioggia = {}
        for r in rami:                       # riuso quella gia' pubblicata
            if not os.path.exists(file_dati(r)):
                continue
            log("  riuso la pioggia gia' presente in %s/dati.json" % r)
            vecchio = json.load(open(file_dati(r), encoding="utf-8"))
            date_v = vecchio.get("date", [])
            for st in vecchio.get("stazioni", []):
                serie = {g: v for g, v in zip(date_v, st.get("pio", []))
                         if v is not None}
                if serie:
                    pioggia.setdefault(st["c"], {}).update(serie)
            break
        if not pioggia:
            log("  nessuna pioggia disponibile: mi fermo senza toccare niente")
            sys.exit(1)

    log("\n[2/3] Suolo e aria da Open-Meteo...")
    suolo = scarica_suolo(stazioni)
    if not suolo:
        log("  Open-Meteo non ha risposto: mi fermo senza toccare niente")
        sys.exit(1)

    log("\n[3/3] Monto i file dei rami...")
    for r in rami:
        cfg = config[r]
        dati = costruisci(stazioni, pioggia, suolo, cfg)
        os.makedirs(cartella(r), exist_ok=True)
        with open(file_dati(r), "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, separators=(",", ":"))
        con_suolo = sum(1 for st in dati["stazioni"]
                        if any(v is not None for v in st["ts"]))
        log("")
        log("  ramo %s, versione %s" % (r, cfg["versione"]))
        log("    stazioni scritte : %d  (con dati del suolo: %d)"
            % (len(dati["stazioni"]), con_suolo))
        log("    giorni           : %d  (%s -> %s)"
            % (len(dati["date"]), dati["date"][0], dati["date"][-1]))
        log("    ultima pioggia   : %s" % dati["ultima_pioggia"])
        log("    file             : %s  (%.0f KB)"
            % (file_dati(r), os.path.getsize(file_dati(r)) / 1024))
    log("\n" + "-" * 56)


if __name__ == "__main__":
    main()
