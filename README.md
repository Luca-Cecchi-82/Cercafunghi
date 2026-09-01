# Cercafunghi Toscana

App web che individua le zone in cui, in un dato giorno, le condizioni di
pioggia, temperatura e umidità del suolo sono compatibili con la fruttificazione
di sette specie di funghi, su 376 stazioni meteorologiche toscane.

**→ [Apri l'app](https://luca-cecchi-82.github.io/Cercafunghi/)**

Non dice dove ci sono i funghi: dice dove il bosco giusto avrebbe le condizioni
giuste. Il metodo, le soglie e i pesi sono spiegati per esteso in fondo alla
pagina dell'app.

## Organizzazione a rami

Ogni versione dell'app sta in una **sottocartella**. La lettera indica
l'impianto, il numero è progressivo:

- `A` — impianto a stazioni puntuali
- `B` — impianto a griglia

Una modifica che cambia le uscite crea un ramo nuovo: non sovrascrive quello
precedente, che resta raggiungibile al suo indirizzo. La stringa di versione sta
in `<ramo>/config.json` e viene scritta dentro `<ramo>/dati.json`, quindi compare
in ogni uscita — pagina, CSV e Excel.

| Ramo | Versione | Indirizzo |
|---|---|---|
| A1 | A1.0 | [/A1/](https://luca-cecchi-82.github.io/Cercafunghi/A1/) |

La pagina alla radice elenca i rami e rimanda al corrente.

## Struttura dei file

```
index.html                       pagina di rimando alla versione corrente
stazioni.csv                     anagrafica delle 376 stazioni, condivisa
A1/index.html                    l'app
A1/config.json                   versione e parametri del ramo
A1/dati.json                     dati, ricostruiti automaticamente
scripts/aggiorna_dati.py         scarica le sorgenti e monta i dati.json
.github/workflows/aggiorna.yml   esegue lo script ogni notte
```

## Aggiornamento

I `dati.json` si aggiornano da soli ogni notte alle 5:10 tramite GitHub Actions.
Si può anche lanciare a mano da **Actions → Aggiorna i dati → Run workflow**.

Per rifarlo sul proprio computer serve solo Python 3, senza installare niente:

```
python scripts/aggiorna_dati.py A1
```

Senza argomenti usa il ramo `A1`. Indicandone più di uno, le sorgenti vengono
scaricate una volta sola e cambia solo il montaggio, secondo la configurazione
di ciascun ramo.

Se il SIR non risponde, lo script riusa la pioggia già pubblicata invece di
perderla, e aggiorna solo la parte modellata. Se Open-Meteo rifiuta una
chiamata, riprova tre volte prima di rinunciare, e le stazioni rimaste senza
dati del suolo restano comunque in mappa con la sola pioggia.

## Aggiungere un ramo

1. Copia la cartella del ramo di partenza, per esempio `A1` in `A2`
2. In `A2/config.json` cambia `versione` e `ramo`
3. In `.github/workflows/aggiorna.yml` scrivi `RAMI: "A1 A2"`
4. Aggiungi la voce nella pagina `index.html` alla radice

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
