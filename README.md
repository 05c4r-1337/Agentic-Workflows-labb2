# Automatiserad koddokumentation med agentiskt arbetsflöde

Systemet är ett multi-agent-arbetsflöde som automatiskt genererar Markdown-dokumentation för Python- och C#-källkodsfiler. En Orchestrator koordinerar fem specialiserade agenter som arbetar i en iterativ loop tills all dokumentation är godkänd eller maximalt antal försök uppnåtts.

## Körning

```bash
pip install requests
python main.py sample_code/example.py docs/
```

För baseline-jämförelse (ett pass utan review-loop eller faktakontroll):

```bash
python main.py sample_code/example.py docs/ --baseline
```

För att jämföra resultaten:

```bash
python compare.py docs/example_baseline_eval.json docs/example_eval.json
```

Kräver att [Ollama](https://ollama.com) körs lokalt på port 11434 med modellen `llama3.1:8b`:

```bash
ollama pull llama3.1:8b
ollama serve
```

All konfiguration finns i `config.py`:

| Inställning | Standard | Beskrivning |
|---|---|---|
| `MODEL` | `llama3.1:8b` | Ollama-modell som används av alla agenter |
| `APPROVAL_THRESHOLD` | `7` | Minsta godkänd recensionspoäng (1–10) |
| `MAX_RETRIES` | `3` | Max omskrivningsförsök per element |
| `MAX_CYCLES` | `10` | Max antal write/review-cykler |
| `ABSTRACTION` | `10` | Abstraktionsnivå i genererad dokumentation (1–10) |

## Miljö och indata

Agenten tar emot en källkodsfil och en utdatakatalog som argument. Filen parsas med AST-analys (Python) eller regex (C#) för att extrahera kodelementens signaturer och källkod.

## Arkitektur

```
main.py → Orchestrator
              ├── AnalyzerAgent       – AST-parsning av källkodsfilen
              ├── DocWriterAgent      – Genererar dokumentation via Ollama
              ├── ReviewerAgent       – Kvalitetsgranskning (poäng 1–10)
              ├── FactCheckerAgent    – Faktakontroll mot källkoden
              ├── SummaryWriterAgent  – Övergripande filsammanfattning
              └── OutputAgent         – Skriver Markdown-filen
```

**Delat minne:** `SessionMemory` håller en lista av `DocEntry`-objekt, ett per kodelement. Varje entry bär sitt tillstånd: dokumentation, poäng, feedback, antal försök och faktakontrollstatus.

## Agenter

- **AnalyzerAgent** – Läser och tolkar källkodsfilen, skapar en `DocEntry` per kodelement i `SessionMemory`.
- **DocWriterAgent** – Anropar Ollama och genererar Markdown-dokumentation. Vid omskrivning skickas reviewer-feedback med i prompten.
- **ReviewerAgent** – Utvärderar dokumentationens kvalitet med LLM. Underkänner element under tröskelvärdet och skickar dem tillbaka till DocWriter.
- **FactCheckerAgent** – Jämför godkänd dokumentation mot faktisk källkod. Vid faktafel avkänns elementet och skickas tillbaka för omskrivning med specificerade fel som feedback. Varje element kan maximalt fact-checkas en gång.
- **SummaryWriterAgent** – Genererar en övergripande sammanfattning av filen.
- **OutputAgent** – Sammanställer all godkänd dokumentation till en strukturerad Markdown-fil.

## Arbetsflöde

Orchestratorn kör en **plan → skriv → granska → faktakolla**-loop upp till `MAX_CYCLES` iterationer:

```
1. AnalyzerAgent   – Extraherar kodelementens signaturer och källkod
2. Orchestrator    – Skapar dokumentationsplan
3. loop (max MAX_CYCLES):
     DocWriterAgent   – Skriver/skriver om dokumentation för ej godkända element
     ReviewerAgent    – Granskar kvalitet, underkänner vid poäng < APPROVAL_THRESHOLD
     FactCheckerAgent – Kontrollerar fakta, avkänner vid fel
   (avsluta om alla element godkänns)
4. SummaryWriterAgent – Genererar filsammanfattning
5. OutputAgent        – Skriver Markdown-filen
```

## Felhantering

Systemet hanterar tre fellägen:

- **Kvalitetsfel** – ReviewerAgent underkänner och skickar tillbaka med feedback
- **Faktafel** – FactCheckerAgent avkänner och skickar tillbaka med specificerade fel
- **Max försök nått** – Element force-godkänns för att undvika att systemet fastnar; OutputAgent hanterar element utan dokumentation med fallback-text
