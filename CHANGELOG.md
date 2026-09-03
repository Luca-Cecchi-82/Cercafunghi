# Registro delle versioni

Ogni voce dice **cosa** è cambiato, **perché**, e cosa è stato deciso di **non** fare.
Le versioni precedenti ad A3 sono beta sperimentali e non sono documentate a ritroso.

Ogni versione ha una release su GitHub con lo stato completo del progetto in quel
momento: [Releases](https://github.com/luca-cecchi-82/Cercafunghi/releases).

---

## A3.1 — 3 settembre 2026

Nessun cambiamento al calcolo: l'indice di A3.0 e quello di A3.1 sono identici. Cambia
solo come viene spiegato.

### Perché

In A3.0 la scheda diceva *«compromessa: 2 giorni sfavorevoli, ne resta il 56%»*. È
un'informazione corretta ma opaca: non si capisce quando è arrivato il danno, in quale
fase del ciclo, né perché due specie sullo stesso punto abbiano punteggi molto diversi.

### La scheda dell'ondata

Ogni specie ha ora una scheda che si legge da sola, senza rimandi alle altre.

In cima una **barra del ciclo** in caratteri a larghezza fissa, un carattere per giorno:

```
22ago               1set                11set
●───────────────✗─✗─██▼█████████████████┤ ········
0         5         10        15        20
```

Sopra le date del calendario, sotto i giorni trascorsi dalla pioggia, ogni cinque. Il
tratto è il periodo in cui i funghi crescono sotto terra, il pieno quando sono
raccoglibili. Le ✗ mostrano **dove** è caduto il danno: nell'esempio al nono e decimo
giorno, cioè a ridosso della nascita, che è il momento peggiore.

Sotto i 500 pixel la barra passa da due colonne per giorno a una.

Segue un testo generato dai dati veri della stazione e dalle soglie della specie: quanta
pioggia è caduta e quando, quando sono usciti o usciranno i carpofori, quali giorni
hanno fatto danno e in quale fase, perché quel danno non si recupera, e quanto resta.

### Cosa cambia nella lettura

Due specie sulla stessa stazione possono avere punteggi molto diversi, e ora la ragione
è leggibile: soglie di sofferenza diverse, cicli di lunghezza diversa, e quindi giorni
di danno che cadono in fasi diverse. Prima sembrava che il modello facesse i capricci.

---

## A3.0 — 2 settembre 2026

Primo ramo che risponde a una domanda diversa: non *«oggi le condizioni sono
favorevoli?»* ma **«oggi ci sono funghi maturi da raccogliere?»**.

### Perché

Nei rami precedenti l'indice era una fotografia del giorno scelto, senza memoria di
cosa fosse successo prima. Il difetto si vedeva a occhio: Casone di Profecchia
risultava azzerato il 31 agosto per caldo e si riaccendeva al massimo il 1° settembre
perché la media dell'aria su cinque giorni era scesa da 19,3 a 18,7 — sei decimi di
grado — mentre non pioveva dal 25 agosto e l'umidità del suolo continuava a calare da
0,166 a 0,110.

Due errori insieme: uno scalino su una variabile continua, e soprattutto l'assenza di
qualsiasi nozione del tempo di sviluppo del carpoforo. Se il caldo secco di fine agosto
ha fatto abortire i primordi, due gradi in meno il giorno dopo non producono funghi.

### Cosa fa adesso

Si risale alle piogge dei 45 giorni precedenti cercando gli episodi capaci di innescare
una fruttificazione — almeno 20 mm in due giorni, con gli episodi ravvicinati fusi — e
ogni ondata viene seguita nel suo ciclo:

```
ondata = maturità(età) × ampiezza(mm) × sopravvivenza
INDICE = 0,70 × ondata migliore + 0,30 × somma delle altre
```

**Maturità**: niente prima della nascita, pieno nella finestra di raccolta della specie,
poi quattro giorni di coda in cui i funghi ci sono ancora ma sempre meno.

**Ampiezza**: rampa da 20 mm, che innescano appena, a 90 mm, oltre i quali la pioggia in
più non aggiunge fruttificazione.

**Sopravvivenza**: si guarda giorno per giorno cosa è successo fra l'evento e la data
scelta. Un giorno è sfavorevole quando l'aria è calda oltre la soglia della specie senza
pioggia, quando l'umidità del suolo scende sotto 0,08, o quando la temperatura del suolo
esce dai limiti esterni. Prima della nascita un giorno cattivo toglie il 15% di quello
che resta e la perdita è definitiva; dopo la nascita il 7%, perché il fungo c'è già e si
rovina più lentamente.

### Cosa vedi in più

Lo stato dell'ondata, con **i giorni dall'evento sempre dichiarati**: *attesa fra 4
giorni*, *in corso da 3 giorni*, *in esaurimento*, *passata*, *nessun innesco*. Se
l'ondata è stata danneggiata, la scheda dice quanti giorni sfavorevoli ha subito e
quanta parte ne resta. In tabella, CSV ed Excel compaiono quattro colonne nuove: stato,
data dell'ondata, millimetri, percentuale sopravvissuta.

### Verifica sui dati reali

Al 2 settembre, per il porcino: 8 stazioni sopra 40, 25 sopra 20, il resto basso. Le
migliori sono Passo Pradarena, Passo Radici, Casone di Profecchia e Passo del Cerreto —
i passi appenninici di Garfagnana e Lunigiana, che è dove ci si aspettano porcini a
inizio settembre dopo la pioggia del 21 agosto. Casone segna 51: ondata di 111 mm,
matura, ma con due giorni sfavorevoli durante lo sviluppo che ne hanno lasciato il 56%.

### Cosa è sparito

- la somma pesata dei quattro fattori: termico e idrico restano visibili in tabella come
  indicatori dello stato attuale, ma non entrano nel calcolo
- il veto sulla siccità a 30 giorni: se non piove non ci sono ondate, il modello lo dice
  da solo
- il veto sull'aria fredda e il punteggio stagionale: se l'ondata c'è ed è matura, il
  mese conta poco

### Cosa si è deciso di NON fare

**Gradi-giorno al posto dei giorni fissi.** Lo sviluppo del carpoforo dipende dalla
temperatura, e l'accumulo termico sarebbe più corretto in teoria. Ma la soglia di
accumulo non esiste in letteratura e sarebbe un numero inventato, mentre le latenze in
giorni vengono almeno da osservazioni. La struttura resta pronta per il passaggio quando
ci saranno osservazioni di campo per tararlo.

**Ammorbidire lo scalino del veto.** Superato dal cambio di impianto: non ci sono più
soglie che azzerano il giorno.

### Numeri che sono stime, non letteratura

Perdite giornaliere del 15% e 7%, soglia di suolo secco a 0,08, coda di 4 giorni,
saturazione dell'ampiezza a 90 mm. Nessuno di questi ha un riferimento pubblicato: sono
i primi da calibrare quando l'archivio delle osservazioni avrà abbastanza record.

L'unico numero osservato è la soglia del caldo con siccità per *Boletus edulis*,
riportata da 17,5 a 19 °C per prudenza — il dato viene da faggete della Germania
nord-occidentale e il modello non conosce ancora pendenza, esposizione e ritenzione del
terreno. Le soglie delle altre specie sono estrapolazioni.
