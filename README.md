# Cercafunghi Toscana

App web che individua le zone in cui, in un dato giorno, le condizioni di
pioggia, temperatura e umidità del suolo sono compatibili con la fruttificazione
di sette specie di funghi, su 376 stazioni meteorologiche toscane.

**→ [Apri l'app](https://luca-cecchi-82.github.io/Cercafunghi/)**

Non dice dove ci sono i funghi: dice dove il bosco giusto avrebbe le condizioni
giuste. Il metodo, le soglie e i pesi sono spiegati per esteso in fondo alla
pagina dell'app.

## Come è fatto

| File | Cosa fa |
|---|---|
| `index.html` | L'app. Carica `dati.json` all'apertura |
| `dati.json` | I dati delle stazioni, ricostruiti automaticamente |
| `stazioni.csv` | Anagrafica delle 376 stazioni con coordinate |
| `scripts/aggiorna_dati.py` | Scarica pioggia e suolo e ricostruisce `dati.json` |
| `.github/workflows/aggiorna.yml` | Esegue lo script ogni notte |

## Aggiornamento

`dati.json` si aggiorna da solo ogni notte alle 5:10 tramite GitHub Actions.
Si può anche lanciare a mano dalla scheda **Actions → Aggiorna i dati → Run workflow**.

Per rifarlo sul proprio computer serve solo Python 3, senza installare niente:

```
python scripts/aggiorna_dati.py
```

Se il SIR non risponde, lo script riusa la pioggia già presente in `dati.json`
invece di perderla, e aggiorna solo la parte modellata.

## Fonti

- **Pioggia misurata**: SIR — Servizio Idrologico Regionale, Regione Toscana
- **Temperatura e umidità del suolo, aria**: Open-Meteo (ERA5-Land, ICON), uso non commerciale
- **Coordinate stazioni**: Open Data Regione Toscana, CC BY-SA
- **Boschi**: Inventario Forestale della Toscana 1978 e Uso e Copertura del Suolo 2019, WMS Geoscopio
- **Sfondi**: OpenTopoMap (CC-BY-SA), OpenStreetMap (ODbL), Esri World Imagery

## Avvertenza

Modello sperimentale, nessuna garanzia sui risultati. Raccogli solo quello che
riconosci con certezza: in caso di dubbio rivolgiti a un ispettorato micologico
ASL, il servizio è gratuito. Rispetta i regolamenti regionali su tesserino,
limiti di quantità e aree protette.
