# Automatiserad koddokumentation med agentiskt arbetsflöde

Systemet är ett multi-agent-arbetsflöde som automatiskt genererar Markdown-dokumentation för Python- och C#-källkodsfiler. En Orchestrator koordinerar fyra specialiserade agenter som arbetar i en iterativ loop tills dokumentationen är godkänd eller maximalt antal cykler uppnåtts.

## Körning

```bash
pip install requests
python main.py sample_code/RagQueryService.cs docs/
```

Alternativ:

```bash
# Baseline: ett pass utan review-loop eller faktakontroll
python main.py sample_code/RagQueryService.cs docs/ --baseline

# Skriv full agent-logg till logs/
python main.py sample_code/RagQueryService.cs docs/ --verbose
```

Jämför en baseline mot full körning:

```bash
python compare.py docs/RagQueryService_baseline_eval_*.json docs/RagQueryService_eval_*.json
```

## Benchmark

För att svara på frågan *"förbättrar den agentiska loopen faktiskt resultatet jämfört med ett enda DocWriter-pass?"* finns `benchmark.py`. Scriptet kör baseline och full N gånger vardera på samma fil och presenterar resultatet sida vid sida.

```bash
python benchmark.py sample_code/RagQueryService.cs --runs 3
```

Scriptet:

- Kör baseline N gånger och sedan full N gånger (per-körning-output dämpas, bara en sammanfattningsrad per körning visas).
- Skriver ut en jämförelsetabell med genomsnitt/std/min/max för recensionspoäng, godkännandegrad, cykler, fact-check-retries och runtime, med Δ-pilar.
- Ger en verdict-rad i klartext (t.ex. *"Full workflow scores +4.3 higher on average"*).
- Sparar `benchmarks/benchmark_<stem>_<timestamp>.json` (komplett per-körnings-data + aggregat) och en `.csv` för vidare analys i kalkylark.

Notera: med gemma tar en full körning ~10 minuter, så `--runs 5` på båda lägena är i praktiken en timme+. Börja med `--runs 3`.

Kräver att [Ollama](https://ollama.com) körs lokalt på port 11434 med modellerna som anges i `config.py`:

```bash
ollama pull gemma4:e4b
ollama pull llama3.1:8b
ollama serve
```

## Konfiguration

All konfiguration finns i `config.py`:

| Inställning | Standard | Beskrivning |
|---|---|---|
| `MODEL` | `gemma4:e4b` | Fallback-modell om ingen agent-specifik modell sätts |
| `DOC_WRITER_MODEL` | `gemma4:e4b` | Modell som genererar dokumentationen |
| `REVIEWER_MODEL` | `gemma4:e4b` | Modell som kvalitetsgranskar |
| `FACT_CHECKER_MODEL` | `gemma4:e4b` | Modell som faktakontrollerar mot källkoden |
| `FORMATTER_MODEL` | `llama3.1:8b` | Modell som omformar granskningen till poäng + issue-lista |
| `APPROVAL_THRESHOLD` | `7` | Minsta godkänd recensionspoäng (1–10) |
| `MAX_RETRIES` | `6` | Max antal faktakontroll-omskrivningar |
| `MAX_CYCLES` | `10` | Max antal write/review-cykler |
| `ABSTRACTION` | `1` | Abstraktionsnivå i genererad dokumentation (1 = detaljerad, 10 = abstrakt) |

Temperaturer per agent och `OLLAMA_TIMEOUT` finns också i `config.py`.

## Arkitektur

```
main.py → Orchestrator
              ├── DocWriterAgent    – Genererar Markdown via Ollama
              ├── ReviewerAgent     – Bedömer klarhet och fullständighet (poäng 1–10)
              │     └── FormattingAgent – Normaliserar granskningen till issue-lista + poäng
              ├── FactCheckerAgent  – Jämför dokumentationens påståenden mot källkoden
              └── OutputAgent       – Skriver slutgiltiga Markdown-filen
```

**Delat minne:** `SessionMemory` håller hela tillståndet för körningen — källkod, aktuell dokumentation, granskningspoäng, faktafel-lista och, viktigt, en **best-so-far-spårning** (`best_documentation`, `best_score`, `best_fact_clean`) som behåller det bästa kandidat-dokumentet över alla cykler. Om sista cykeln presterar sämre än en tidigare skrivs den tidigare till fil.

## Agenter

- **DocWriterAgent** – Anropar Ollama och producerar Markdown för hela filen. Vid omskrivning skickas den tidigare dokumentationen och feedback (både kvalitet och fakta) med i prompten. Sampling-parametrar (`repeat_penalty=1.15`, `num_ctx=16384`, `num_predict=4096`) sätts explicit för att undvika repetitions-loopar.
- **ReviewerAgent** – Kör en 9-punkts checklista ([A] syfte … [I] kodexempel) på dokumentationen. Den ser **inte** källkoden — den bedömer enbart klarhet och fullständighet. Resultatet skickas vidare till FormattingAgent.
- **FormattingAgent** – Omformar den fria granskningstexten till en kompakt `Issues: …` + `FINAL SCORE: N`-struktur som både användaren och DocWriterAgent kan konsumera.
- **FactCheckerAgent** – Jämför dokumentationen mot råa källkoden och flaggar felaktiga metodnamn, parametertyper, saknade metoder, motsägelsefull logik osv. Vid fel sätts elementet tillbaka till icke-godkänt och issues läggs till i feedback-kanalen.
- **OutputAgent** – Skriver slutgiltiga Markdown-filen. Föredrar `best_documentation` över senast genererade om den är tydligt bättre.

## Arbetsflöde

Orchestratorn kör en **skriv → granska → faktakolla**-loop upp till `MAX_CYCLES` iterationer:

```
1. Läs källkodsfilen
2. loop (max MAX_CYCLES):
     DocWriterAgent   – Skriver/skriver om dokumentationen
     ReviewerAgent    – Bedömer (underkänner vid poäng < APPROVAL_THRESHOLD)
     FactCheckerAgent – Kontrollerar fakta mot källkoden
     SessionMemory    – Spara kandidaten om den är bäst-hittills
     (avsluta om både review godkänd och fakta rena)
3. OutputAgent – Skriver bästa kandidaten till .md-filen
4. Skriv eval-rapport (JSON) och, om --verbose, agent-loggen
```

## Felhantering

- **Kvalitetsfel** – ReviewerAgent underkänner och skickar tillbaka feedback.
- **Faktafel** – FactCheckerAgent avkänner och lägger till felen i feedback-kanalen.
- **Max cykler eller max retries nått** – OutputAgent faller tillbaka till bästa fact-clean-kandidat. Finns ingen sådan används bästa poäng även om faktafel kvarstår.
- **Ollama otillgänglig** – `tools/ollama_tools.py` ger ett tydligt felmeddelande och avbryter körningen.

## Utdata

Varje körning producerar tre filer i `output_dir`:

- `<stem>_docs_<timestamp>.md` – den genererade dokumentationen
- `<stem>_eval_<timestamp>.json` – körningsmetrik (cykler, runtime, slutpoäng)
- `<stem>_verbose_<timestamp>.txt` – komplett agent-logg (bara med `--verbose`)
