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

| Ramo | Versione | Indirizzo | Cosa cambia |
|---|---|---|---|
| A1 | A1.1 | [/A1/](https://luca-cecchi-82.github.io/Cercafunghi/A1/) | indice a somma pesata |
| A2 | A2.2 | [/A2/](https://luca-cecchi-82.github.io/Cercafunghi/A2/) | condizioni necessarie che azzerano l'indice |
| A3 | A3.1 | [/A3/](https://luca-cecchi-82.github.io/Cercafunghi/A3/) | ondate di fruttificazione seguite nel tempo |

La pagina alla radice elenca i rami e rimanda al corrente.

Dalla versione A3 ogni cambio di versione ha una **release** su GitHub, che congela lo
stato completo del progetto in quel momento, e una voce in [`CHANGELOG.md`](CHANGELOG.md)
che spiega cosa è cambiato e perché.

### Che cosa cambia da un ramo all'altro

**A3 pone una domanda diversa dagli altri due.** A1 e A2 rispondono a *«oggi le
condizioni sono favorevoli?»*: una fotografia del giorno scelto, senza memoria. A3
risponde a *«oggi ci sono funghi maturi da raccogliere?»*, che è lo stato di un processo
lungo settimane.

A3 risale alle piogge dei 45 giorni precedenti, individua le ondate di fruttificazione e
segue ciascuna nel suo ciclo: quanti giorni sono passati, quanto era grosso l'evento, e
soprattutto **cosa è successo nel frattempo**. Se fra la pioggia e oggi ci sono stati
giorni di caldo secco o di suolo asciutto, l'ondata è compromessa e resta compromessa
anche se poi rinfresca.

Oltre al punteggio, A3 dice **a che punto è**: attesa fra tot giorni, in corso da tot,
in esaurimento, passata, con i giorni dall'evento sempre dichiarati.

Il dettaglio è in [`CHANGELOG.md`](CHANGELOG.md) e nella pagina del ramo.

### Differenza fra A1 e A2

In **A1** l'indice è una somma pesata: un fattore alto compensa un fattore
basso. Con temperatura perfetta e terreno arido da un mese, il solo termine
termico porta comunque quarantacinque punti su cento.

In **A2** alcune condizioni sono *necessarie*: se non sono rispettate l'indice
va a zero, per quanto tutto il resto sia favorevole.

| Condizione | Soglia | Provenienza |
|---|---|---|
| aria fuori dalla finestra utile | fuori da 5–21 °C, media 5 giorni | osservazione, allargata di 2 °C per lato |
| caldo senza pioggia | sopra 17,5 °C con meno di 1 mm/giorno | osservazione |
| siccità prolungata | meno di 15 mm in 30 giorni | **stima**, non letteratura |

Le prime due vengono da uno studio decennale su 1905 carpofori di *Boletus
edulis* in faggete tedesche: nessun carpoforo osservato fuori dalla finestra
7–19 °C di temperatura dell'aria, nessuno sopra 17,5 °C in assenza di pioggia.
Le soglie qui sono volutamente più larghe del dato osservato, perché quel dato
viene dal nord Europa.

Un veto sbagliato è più pericoloso di un peso sbagliato: azzera una zona, non
ci vai, e non scopri mai di esserti perso una fruttata. Per questo le soglie
sono larghe e tutte modificabili da `config.json`, dove `"attivi": false` le
disattiva in blocco. Quando un punteggio è azzerato, la scheda della stazione
ne indica il motivo.

A2 rimuove anche la penalità sull'umidità superficiale presente in A1. Misurata
sui dati reali, la situazione che quella penalità voleva cogliere — superficie
secca con profondità umida — si verifica nello 0,1% dei casi: nel resto contava
due volte lo stesso fatto.

## Struttura dei file

```
index.html                       pagina di rimando alla versione corrente
segnala.html                     modulo per registrare le uscite sul campo
stazioni.csv                     anagrafica delle 376 stazioni, condivisa
A1/index.html                    l'app
A1/config.json                   versione e parametri del ramo
A1/dati.json                     dati, ricostruiti automaticamente
A2/…                             stesso schema
A3/…                             stesso schema
CHANGELOG.md                     registro delle versioni, dalla A3 in poi
scripts/aggiorna_dati.py         scarica le sorgenti e monta i dati.json
.github/workflows/aggiorna.yml   esegue lo script ogni notte
```

## Archivio delle osservazioni

`segnala.html` raccoglie le uscite sul campo — data, zona indicata sulla mappa,
tempo di ricerca, tipo di bosco, esito, ed eventuale tracciato GPX — e le scrive
in un foglio Google privato tramite Apps Script.

**Le uscite a vuoto sono record validi quanto i ritrovamenti.** Senza sapere
dove e quando i funghi *non* c'erano, nessuna calibrazione è possibile: un
modello verificato e uno non verificato sono indistinguibili dall'esterno.

Le posizioni sono approssimative per costruzione, perché si compila a fine
uscita: utilizzabili per il segnale temporale, non per quello spaziale. Solo i
GPX danno una posizione affidabile.

## Aggiornamento

I `dati.json` si aggiornano da soli ogni notte alle 5:10 tramite GitHub Actions.
Si può anche lanciare a mano da **Actions → Aggiorna i dati → Run workflow**.

Per rifarlo sul proprio computer serve solo Python 3, senza installare niente:

```
python scripts/aggiorna_dati.py A1 A2 A3
```

Senza argomenti usa il ramo `A1`. Indicandone più di uno, le sorgenti vengono
scaricate una volta sola e cambia solo il montaggio, secondo la configurazione
di ciascun ramo.

Se il SIR non risponde, lo script riusa la pioggia già pubblicata invece di
perderla, e aggiorna solo la parte modellata. Se Open-Meteo rifiuta una
chiamata, riprova tre volte prima di rinunciare, e le stazioni rimaste senza
dati del suolo restano comunque in mappa con la sola pioggia.

Le cumulate di pioggia restituiscono un valore solo se almeno l'80% dei giorni
della finestra ha un dato vero. Senza questo controllo i giorni previsti, dove
la pioggia misurata non esiste ancora, restituivano somme parziali che l'app
leggeva come scarsità di pioggia invece che come assenza di dato.

## Aggiungere un ramo

1. Copia la cartella del ramo di partenza, per esempio `A3` in `A4`
2. In `A4/config.json` cambia `versione` e `ramo`
3. In `.github/workflows/aggiorna.yml` aggiungi il ramo a `RAMI`
4. Aggiungi la voce nella pagina `index.html` alla radice, e sposta lì il
   rimando automatico se il nuovo ramo diventa il corrente
5. Aggiungi la voce in `CHANGELOG.md`
6. Crea la release su GitHub con il tag della versione

## Fonti

- **Pioggia misurata**: SIR — Servizio Idrologico Regionale, Regione Toscana.
  Unico dato realmente misurato della catena. Stazioni a 7–8 km l'una
  dall'altra: fra una e l'altra qualunque valore è interpolato.
- **Temperatura e umidità del suolo, aria**: Open-Meteo, endpoint `/v1/forecast`,
  uso non commerciale, CC BY 4.0. Anche i giorni passati arrivano da lì, cioè da
  run precedenti dello stesso modello di previsione ricucite fra loro: **non è
  rianalisi**, e l'umidità del suolo mostra scalini nei punti di giunzione. In
  Toscana non esiste nessuna rete di misura del suolo forestale: ogni valore di
  suolo di questo progetto è, e resterà, modellato.
- **Coordinate stazioni**: Open Data Regione Toscana, CC BY-SA
- **Boschi**: Inventario Forestale della Toscana (fotointerpretazione volo 1978
  integrata con rilievi a terra nei primi anni '90, griglia 400 m) e Uso e
  Copertura del Suolo 2019, WMS Geoscopio. Il primo dice *che* bosco è, il
  secondo *dove* c'è bosco oggi.
- **Sfondi**: OpenTopoMap (CC-BY-SA), OpenStreetMap (ODbL), Esri World Imagery

Il dettaglio delle fonti, con limiti e provenienza di ogni assunzione, sta in
`Fonti.txt`.

## Avvertenza

Modello sperimentale, nessuna garanzia sui risultati. I pesi e le soglie sono
scelti a mano e non calibrati su osservazioni di campo. Solo *Boletus edulis*
s.l. ha modelli quantitativi pubblicati in letteratura: ovolo, finferlo e
chiodino sono indicazioni grezze.

Raccogli solo quello che riconosci con certezza: in caso di dubbio rivolgiti a
un ispettorato micologico ASL, il servizio è gratuito. Rispetta i regolamenti
regionali su tesserino, limiti di quantità e aree protette.
