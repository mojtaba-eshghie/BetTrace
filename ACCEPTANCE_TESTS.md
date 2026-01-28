# Acceptance Test Questions 

This document contains 7 acceptance test questions for the Sportsbook RAG Assistant, covering:
- 2 bet-specific questions (single bet_id & two bets)
- 2 analytics-style questions (aggregations/ranking)
- 2 incident/ops questions (latency/suspensions)
- 1 Semantic search for teams/players

---

## Test 1: Bet-Specific — Single & Two Bets Rejection 
```bash
python main.py ask "Why was bet B0004 rejected?" --show-context
python main.py ask "Why were bets B0004 and B0022 rejected?" --show-context
```


## Test 2: Bet-Specific — High Latency Incident

```bash
python main.py ask "What happened with bet B0059? Explain the incident and latency." --show-context
```

## Test 3: Analytics — Top Latency Ranking

```bash
python main.py ask "What happened with bet B0059? Explain the incident and latency." --show-context
```

## Test 4: Analytics — Customer Summary


```bash
python main.py ask "For customer C068, summarize all their bets and highlight any incidents." --show-context
```



## Test 5: Incident/Ops — Latency Spike Impact

```bash
python main.py ask "Which customers were affected by LATENCY_SPIKE and how severely?" --show-context
```



## Test 6: Incident/Ops — Feed Outage Analysis

```bash
python main.py ask "How many bets were voided due to FEED_OUTAGE? List them and explain." --show-context
```


## Test 7: Semantic Search for Team/Players
```bash
python main.py ask "All bets involving Thundr" --show-context
```








# Acceptance Test Question Results


```bash

(.venv) mojtabae@MBP2023A BetTrace % python main.py ask "Why was bet B0004 rejected?" --show-context

[22:37:32] DEBUG MODE: Starting RAG assistant for question: Why was bet B0004 rejected?                                                              cli.py:396
[22:37:32] DEBUG MODE: load_embeddings_to_memory called                                                                                         database.py:540
[22:37:32] DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111

Question: Why was bet B0004 rejected?

[22:37:32] DEBUG MODE: Received query: Why was bet B0004 rejected?                                                                                   rag.py:122
[22:37:32] DEBUG MODE: Executing query: 'Why was bet B0004 rejected?' with top_k=100                                                       query_executor.py:75
                                                                                                                                                               
[22:37:32] DEBUG MODE: :Parsing Query (QueryParser.parse): [Why was bet B0004 rejected?]                                                    query_parser.py:392
           DEBUG MODE: :Extracting bet IDs from query: Why was bet B0004 rejected?                                                          query_parser.py:534
           DEBUG MODE: :Extracting customer IDs from query: Why was bet B0004 rejected?                                                     query_parser.py:556
           DEBUG MODE: :Extracting filters from query: why was bet   rejected?                                                              query_parser.py:578
           DEBUG MODE: : Extracting stake range from query: why was bet    ?                                                                query_parser.py:617
           DEBUG MODE: :Extracting delay range from query: why was bet    ?                                                                 query_parser.py:646
           DEBUG MODE: :Extracting sorting from query: why was bet    ?                                                                     query_parser.py:681
           DEBUG MODE: :Extracting limit from query: why was bet    ?                                                                       query_parser.py:704
           DEBUG MODE: :Extracting aggregation from query: why was bet    ?                                                                 query_parser.py:720
           DEBUG MODE: :Checking for top/bottom N pattern in query: why was bet b0004 rejected?                                             query_parser.py:741
           DEBUG MODE: :Checking for general aggregate query in: why was bet b0004 rejected?                                                query_parser.py:773
           DEBUG MODE: :Detecting invalid entity references in query: why was bet b0004 rejected?                                           query_parser.py:463
           DEBUG MODE: :Detecting incomplete ID queries in query: why was bet b0004 rejected?                                               query_parser.py:510
           DEBUG MODE: :Extracting semantic terms from remaining text: why was bet    ?                                                     query_parser.py:789
           DEBUG MODE: :Calculating parse confidence for: ParsedQuery(type=entity_lookup, bet_ids=['B0004'], filters={'status':             query_parser.py:830
           'REJECTED'}, semantic=['why'])                                                                                                                      
           DEBUG MODE: Executing entity lookup for parsed query: ParsedQuery(type=entity_lookup, bet_ids=['B0004'], filters={'status':    query_executor.py:110
           'REJECTED'}, semantic=['why'])                                                                                                                      
                                                                                                                                                               
           DEBUG MODE: Computing bet stats for results: [RetrievalResult(bet=Bet(bet_id='B0004', customer_id='C060', sport='football',    query_executor.py:494
           event_name='West Ham vs Fullham', market='BTTS', selection='No', stake_gbp=Decimal('30.00'), status='REJECTED',                                     
           incident_tag='MARKET_SUSPENDED', price_delay_ms=635, stored_document='Bet B0004: Customer C060 placed a £30.00 BTTS bet on                          
           West Ham vs Fullham (football). Selection: No. Status: REJECTED. Incident: MARKET_SUSPENDED. High latency: 635ms.'),                                
           score=1.0, match_type='exact')]                                                                                                                     
                                                                                                                                                               
           DEBUG MODE: Building context for LLM from execution results                                                                               rag.py:226
           DEBUG MODE: Formatting bet records for context (max_rows=100)                                                                             rag.py:275
           DEBUG MODE: Generating answer using LLM                                                                                                   rag.py:301
⠴ Thinking...
⠹ Thinking...[22:37:46] DEBUG MODE: Extracting citations from answer                                                                                              rag.py:421
SQL Statistics (authoritative):
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Bet B0004:
  • Customer: C060
  • Sport: football
  • Event: West Ham vs Fullham
  • Market: BTTS → No
  • Stake: £30.00
  • Status: REJECTED
  • Incident: MARKET_SUSPENDED
  • Delay: 635ms

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================
Retrieved Bets (1 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event               ┃ Status   ┃ Incident         ┃ Delay ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ B0004  │ C060     │ West Ham vs Fullham │ REJECTED │ MARKET_SUSPENDED │ 635ms │
└────────┴──────────┴─────────────────────┴──────────┴──────────────────┴───────┘

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ There was 1 bet rejected due to MARKET_SUSPENDED with a total stake of £30.00:                                                                              │
│                                                                                                                                                             │
│ - B0004 (Customer C060): West Ham vs Fullham, Market BTTS → No. Status: REJECTED. Incident: MARKET_SUSPENDED. Delay: 635ms — elevated compared with normal  │
│ (~200ms) but below the >1000ms issue threshold.                                                                                                             │
│                                                                                                                                                             │
│ Observations:                                                                                                                                               │
│ - The recorded incident for B0004 is MARKET_SUSPENDED, which is the explicit reason given for the rejection.                                                │
│ - The price delay (635ms) is higher than typical latency but not in the critical (>1000ms) range, so the primary cause in the data is the market suspension │
│ rather than extreme latency.                                                                                                                                │
│                                                                                                                                                             │
│ Key insight: The bet was rejected because the market was suspended at the time of placement (Incident: MARKET_SUSPENDED). The delay was elevated but not    │
│ beyond the threshold that the data defines as indicative of severe issues.                                                                                  │
│                                                                                                                                                             │
│ Evidence: [B0004]                                                                                                                                           │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0004
Retrieved 1 bet(s) for context
(.venv) mojtabae@MBP2023A BetTrace % 
(.venv) mojtabae@MBP2023A BetTrace % python main.py ask "Why were bets B0004 and B0022 rejected?" --show-context

[22:37:54] DEBUG MODE: Starting RAG assistant for question: Why were bets B0004 and B0022 rejected?                                                  cli.py:396
[22:37:54] DEBUG MODE: load_embeddings_to_memory called                                                                                         database.py:540
[22:37:54] DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111

Question: Why were bets B0004 and B0022 rejected?

[22:37:54] DEBUG MODE: Received query: Why were bets B0004 and B0022 rejected?                                                                       rag.py:122
[22:37:54] DEBUG MODE: Executing query: 'Why were bets B0004 and B0022 rejected?' with top_k=100                                           query_executor.py:75
                                                                                                                                                               
[22:37:54] DEBUG MODE: :Parsing Query (QueryParser.parse): [Why were bets B0004 and B0022 rejected?]                                        query_parser.py:392
           DEBUG MODE: :Extracting bet IDs from query: Why were bets B0004 and B0022 rejected?                                              query_parser.py:534
           DEBUG MODE: :Extracting customer IDs from query: Why were bets B0004 and B0022 rejected?                                         query_parser.py:556
           DEBUG MODE: :Extracting filters from query: why were bets   and   rejected?                                                      query_parser.py:578
           DEBUG MODE: : Extracting stake range from query: why were bets   and    ?                                                        query_parser.py:617
           DEBUG MODE: :Extracting delay range from query: why were bets   and    ?                                                         query_parser.py:646
           DEBUG MODE: :Extracting sorting from query: why were bets   and    ?                                                             query_parser.py:681
           DEBUG MODE: :Extracting limit from query: why were bets   and    ?                                                               query_parser.py:704
           DEBUG MODE: :Extracting aggregation from query: why were bets   and    ?                                                         query_parser.py:720
           DEBUG MODE: :Checking for top/bottom N pattern in query: why were bets b0004 and b0022 rejected?                                 query_parser.py:741
           DEBUG MODE: :Checking for general aggregate query in: why were bets b0004 and b0022 rejected?                                    query_parser.py:773
           DEBUG MODE: :Detecting invalid entity references in query: why were bets b0004 and b0022 rejected?                               query_parser.py:463
           DEBUG MODE: :Detecting incomplete ID queries in query: why were bets b0004 and b0022 rejected?                                   query_parser.py:510
           DEBUG MODE: :Extracting semantic terms from remaining text: why were bets   and    ?                                             query_parser.py:789
           DEBUG MODE: :Calculating parse confidence for: ParsedQuery(type=entity_lookup, bet_ids=['B0004', 'B0022'], filters={'status':    query_parser.py:830
           'REJECTED'}, semantic=['why'])                                                                                                                      
           DEBUG MODE: Executing entity lookup for parsed query: ParsedQuery(type=entity_lookup, bet_ids=['B0004', 'B0022'],              query_executor.py:110
           filters={'status': 'REJECTED'}, semantic=['why'])                                                                                                   
                                                                                                                                                               
           DEBUG MODE: Computing bet stats for results: [RetrievalResult(bet=Bet(bet_id='B0004', customer_id='C060', sport='football',    query_executor.py:494
           event_name='West Ham vs Fullham', market='BTTS', selection='No', stake_gbp=Decimal('30.00'), status='REJECTED',                                     
           incident_tag='MARKET_SUSPENDED', price_delay_ms=635, stored_document='Bet B0004: Customer C060 placed a £30.00 BTTS bet on                          
           West Ham vs Fullham (football). Selection: No. Status: REJECTED. Incident: MARKET_SUSPENDED. High latency: 635ms.'),                                
           score=1.0, match_type='exact'), RetrievalResult(bet=Bet(bet_id='B0022', customer_id='C105', sport='basketball',                                     
           event_name='Bulls vs Rapters', market='Moneyline', selection='Bulls', stake_gbp=Decimal('15.00'), status='REJECTED',                                
           incident_tag='MARKET_SUSPENDED', price_delay_ms=839, stored_document='Bet B0022: Customer C105 placed a £15.00 Moneyline bet                        
           on Bulls vs Rapters (basketball). Selection: Bulls. Status: REJECTED. Incident: MARKET_SUSPENDED. High latency: 839ms.'),                           
           score=1.0, match_type='exact')]                                                                                                                     
                                                                                                                                                               
           DEBUG MODE: Building context for LLM from execution results                                                                               rag.py:226
           DEBUG MODE: Formatting bet records for context (max_rows=100)                                                                             rag.py:275
           DEBUG MODE: Generating answer using LLM                                                                                                   rag.py:301
⠸ Thinking...[22:38:10] DEBUG MODE: Extracting citations from answer                                                                                              rag.py:421
SQL Statistics (authoritative):
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Bet B0004:
  • Customer: C060
  • Sport: football
  • Event: West Ham vs Fullham
  • Market: BTTS → No
  • Stake: £30.00
  • Status: REJECTED
  • Incident: MARKET_SUSPENDED
  • Delay: 635ms

Bet B0022:
  • Customer: C105
  • Sport: basketball
  • Event: Bulls vs Rapters
  • Market: Moneyline → Bulls
  • Stake: £15.00
  • Status: REJECTED
  • Incident: MARKET_SUSPENDED
  • Delay: 839ms

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================
Retrieved Bets (2 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event               ┃ Status   ┃ Incident         ┃ Delay ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ B0004  │ C060     │ West Ham vs Fullham │ REJECTED │ MARKET_SUSPENDED │ 635ms │
│ B0022  │ C105     │ Bulls vs Rapters    │ REJECTED │ MARKET_SUSPENDED │ 839ms │
└────────┴──────────┴─────────────────────┴──────────┴──────────────────┴───────┘

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary: Both bets were REJECTED due to the incident type MARKET_SUSPENDED. Stakes and delays from the computed facts are: B0004 — Stake £30.00, Delay      │
│ 635ms; B0022 — Stake £15.00, Delay 839ms.                                                                                                                   │
│                                                                                                                                                             │
│ - B0004 (Customer C060): West Ham vs Fullham — Market: BTTS → No. Status: REJECTED. Incident: MARKET_SUSPENDED. Delay: 635ms (above the normal ~200ms but   │
│ below the 1000ms threshold that indicates major issues).                                                                                                    │
│ - B0022 (Customer C105): Bulls vs Rapters — Market: Moneyline → Bulls. Status: REJECTED. Incident: MARKET_SUSPENDED. Delay: 839ms (also elevated relative   │
│ to ~200ms but under 1000ms).                                                                                                                                │
│                                                                                                                                                             │
│ Key insights:                                                                                                                                               │
│ - The explicit reason recorded for both rejections is MARKET_SUSPENDED, so the market being closed/suspended is the proximate cause.                        │
│ - Both bets show elevated price delays compared with the typical ~200ms, but neither exceeds 1000ms; therefore the rejections are attributed to market      │
│ suspension rather than extreme latency or feed outage.                                                                                                      │
│ - The two bets are on different sports and customers, indicating a market-level suspension rather than a customer-specific or sport-specific issue.         │
│                                                                                                                                                             │
│ Evidence: [B0004, B0022]                                                                                                                                    │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0004, B0022
Retrieved 2 bet(s) for context
(.venv) mojtabae@MBP2023A BetTrace % python main.py ask "What happened with bet B0059? Explain the incident and latency." --show-context

[22:38:17] DEBUG MODE: Starting RAG assistant for question: What happened with bet B0059? Explain the incident and latency.                          cli.py:396
[22:38:17] DEBUG MODE: load_embeddings_to_memory called                                                                                         database.py:540
[22:38:17] DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111

Question: What happened with bet B0059? Explain the incident and latency.

[22:38:17] DEBUG MODE: Received query: What happened with bet B0059? Explain the incident and latency.                                               rag.py:122
[22:38:17] DEBUG MODE: Executing query: 'What happened with bet B0059? Explain the incident and latency.' with top_k=100                   query_executor.py:75
                                                                                                                                                               
[22:38:17] DEBUG MODE: :Parsing Query (QueryParser.parse): [What happened with bet B0059? Explain the incident and latency.]                query_parser.py:392
           DEBUG MODE: :Extracting bet IDs from query: What happened with bet B0059? Explain the incident and latency.                      query_parser.py:534
           DEBUG MODE: :Extracting customer IDs from query: What happened with bet B0059? Explain the incident and latency.                 query_parser.py:556
           DEBUG MODE: :Extracting filters from query: what happened with bet  ? explain the incident and latency.                          query_parser.py:578
           DEBUG MODE: : Extracting stake range from query: what happened with bet  ? explain the incident and latency.                     query_parser.py:617
           DEBUG MODE: :Extracting delay range from query: what happened with bet  ? explain the incident and latency.                      query_parser.py:646
           DEBUG MODE: :Extracting sorting from query: what happened with bet  ? explain the incident and latency.                          query_parser.py:681
           DEBUG MODE: :Extracting limit from query: what happened with bet  ? explain the incident and latency.                            query_parser.py:704
           DEBUG MODE: :Extracting aggregation from query: what happened with bet  ? explain the incident and latency.                      query_parser.py:720
           DEBUG MODE: :Checking for top/bottom N pattern in query: what happened with bet b0059? explain the incident and latency.         query_parser.py:741
           DEBUG MODE: :Checking for general aggregate query in: what happened with bet b0059? explain the incident and latency.            query_parser.py:773
           DEBUG MODE: :Detecting invalid entity references in query: what happened with bet b0059? explain the incident and latency.       query_parser.py:463
           DEBUG MODE: :Detecting incomplete ID queries in query: what happened with bet b0059? explain the incident and latency.           query_parser.py:510
           DEBUG MODE: :Extracting semantic terms from remaining text: what happened with bet  ? explain the incident and latency.          query_parser.py:789
           DEBUG MODE: :Calculating parse confidence for: ParsedQuery(type=entity_lookup, bet_ids=['B0059'], semantic=['happened',          query_parser.py:830
           'explain', 'incident', 'latency.'])                                                                                                                 
           DEBUG MODE: Executing entity lookup for parsed query: ParsedQuery(type=entity_lookup, bet_ids=['B0059'], semantic=['happened', query_executor.py:110
           'explain', 'incident', 'latency.'])                                                                                                                 
                                                                                                                                                               
           DEBUG MODE: Computing bet stats for results: [RetrievalResult(bet=Bet(bet_id='B0059', customer_id='C076', sport='football',    query_executor.py:494
           event_name='Juvetus vs Interr', market='Asian Handicap', selection='Away +0.5', stake_gbp=Decimal('10.00'), status='SETTLED',                       
           incident_tag='LATENCY_SPIKE', price_delay_ms=4648, stored_document='Bet B0059: Customer C076 placed a £10.00 Asian Handicap                         
           bet on Juvetus vs Interr (football). Selection: Away +0.5. Status: SETTLED. Incident: LATENCY_SPIKE. High latency: 4648ms.'),                       
           score=1.0, match_type='exact')]                                                                                                                     
                                                                                                                                                               
           DEBUG MODE: Building context for LLM from execution results                                                                               rag.py:226
           DEBUG MODE: Formatting bet records for context (max_rows=100)                                                                             rag.py:275
           DEBUG MODE: Generating answer using LLM                                                                                                   rag.py:301
⠙ Thinking...[22:38:31] DEBUG MODE: Extracting citations from answer                                                                                              rag.py:421
SQL Statistics (authoritative):
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Bet B0059:
  • Customer: C076
  • Sport: football
  • Event: Juvetus vs Interr
  • Market: Asian Handicap → Away +0.5
  • Stake: £10.00
  • Status: SETTLED
  • Incident: LATENCY_SPIKE
  • Delay: 4648ms

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================
Retrieved Bets (1 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event             ┃ Status  ┃ Incident      ┃ Delay  ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ B0059  │ C076     │ Juvetus vs Interr │ SETTLED │ LATENCY_SPIKE │ 4648ms │
└────────┴──────────┴───────────────────┴─────────┴───────────────┴────────┘

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary (from COMPUTED FACTS):                                                                                                                              │
│ - Bet B0059 — Stake: £10.00; Status: SETTLED; Incident: LATENCY_SPIKE; Delay: 4648ms.                                                                       │
│                                                                                                                                                             │
│ Details:                                                                                                                                                    │
│ - B0059 (Customer C076): Juvetus vs Interr, football — Asian Handicap, selection Away +0.5.                                                                 │
│   - Status: SETTLED                                                                                                                                         │
│   - Incident type: LATENCY_SPIKE                                                                                                                            │
│   - Price delay: 4648ms — notably high (normal ~200ms; above 1000ms indicates issues).                                                                      │
│                                                                                                                                                             │
│ Observations and interpretation:                                                                                                                            │
│ - The bet experienced a significant latency spike (4648ms), well above normal operating latency and the 1000ms issue threshold from the field definitions.  │
│ - Despite the latency, the bet was completed and marked SETTLED rather than VOID or REJECTED, so the stake was accepted and the outcome resolved.           │
│ - This pattern (high delay but settled) can indicate a delayed price/feed update at order time; it should be reviewed to confirm price integrity and        │
│ whether any customer-impacting anomalies occurred.                                                                                                          │
│                                                                                                                                                             │
│ Key insight:                                                                                                                                                │
│ - High latency (4648ms) was recorded for B0059 under a LATENCY_SPIKE incident; investigate the timing and feed/matching systems for that event to ensure    │
│ prices and settlement were correct.                                                                                                                         │
│                                                                                                                                                             │
│ Evidence: [B0059]                                                                                                                                           │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0059
Retrieved 1 bet(s) for context
(.venv) mojtabae@MBP2023A BetTrace % python main.py ask "What happened with bet B0059? Explain the incident and latency." --show-context

[22:38:35] DEBUG MODE: Starting RAG assistant for question: What happened with bet B0059? Explain the incident and latency.                          cli.py:396
[22:38:35] DEBUG MODE: load_embeddings_to_memory called                                                                                         database.py:540
[22:38:35] DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111

Question: What happened with bet B0059? Explain the incident and latency.

[22:38:35] DEBUG MODE: Received query: What happened with bet B0059? Explain the incident and latency.                                               rag.py:122
[22:38:35] DEBUG MODE: Executing query: 'What happened with bet B0059? Explain the incident and latency.' with top_k=100                   query_executor.py:75
                                                                                                                                                               
[22:38:35] DEBUG MODE: :Parsing Query (QueryParser.parse): [What happened with bet B0059? Explain the incident and latency.]                query_parser.py:392
           DEBUG MODE: :Extracting bet IDs from query: What happened with bet B0059? Explain the incident and latency.                      query_parser.py:534
           DEBUG MODE: :Extracting customer IDs from query: What happened with bet B0059? Explain the incident and latency.                 query_parser.py:556
           DEBUG MODE: :Extracting filters from query: what happened with bet  ? explain the incident and latency.                          query_parser.py:578
           DEBUG MODE: : Extracting stake range from query: what happened with bet  ? explain the incident and latency.                     query_parser.py:617
           DEBUG MODE: :Extracting delay range from query: what happened with bet  ? explain the incident and latency.                      query_parser.py:646
           DEBUG MODE: :Extracting sorting from query: what happened with bet  ? explain the incident and latency.                          query_parser.py:681
           DEBUG MODE: :Extracting limit from query: what happened with bet  ? explain the incident and latency.                            query_parser.py:704
           DEBUG MODE: :Extracting aggregation from query: what happened with bet  ? explain the incident and latency.                      query_parser.py:720
           DEBUG MODE: :Checking for top/bottom N pattern in query: what happened with bet b0059? explain the incident and latency.         query_parser.py:741
           DEBUG MODE: :Checking for general aggregate query in: what happened with bet b0059? explain the incident and latency.            query_parser.py:773
           DEBUG MODE: :Detecting invalid entity references in query: what happened with bet b0059? explain the incident and latency.       query_parser.py:463
           DEBUG MODE: :Detecting incomplete ID queries in query: what happened with bet b0059? explain the incident and latency.           query_parser.py:510
           DEBUG MODE: :Extracting semantic terms from remaining text: what happened with bet  ? explain the incident and latency.          query_parser.py:789
           DEBUG MODE: :Calculating parse confidence for: ParsedQuery(type=entity_lookup, bet_ids=['B0059'], semantic=['happened',          query_parser.py:830
           'explain', 'incident', 'latency.'])                                                                                                                 
           DEBUG MODE: Executing entity lookup for parsed query: ParsedQuery(type=entity_lookup, bet_ids=['B0059'], semantic=['happened', query_executor.py:110
           'explain', 'incident', 'latency.'])                                                                                                                 
                                                                                                                                                               
           DEBUG MODE: Computing bet stats for results: [RetrievalResult(bet=Bet(bet_id='B0059', customer_id='C076', sport='football',    query_executor.py:494
           event_name='Juvetus vs Interr', market='Asian Handicap', selection='Away +0.5', stake_gbp=Decimal('10.00'), status='SETTLED',                       
           incident_tag='LATENCY_SPIKE', price_delay_ms=4648, stored_document='Bet B0059: Customer C076 placed a £10.00 Asian Handicap                         
           bet on Juvetus vs Interr (football). Selection: Away +0.5. Status: SETTLED. Incident: LATENCY_SPIKE. High latency: 4648ms.'),                       
           score=1.0, match_type='exact')]                                                                                                                     
                                                                                                                                                               
           DEBUG MODE: Building context for LLM from execution results                                                                               rag.py:226
           DEBUG MODE: Formatting bet records for context (max_rows=100)                                                                             rag.py:275
           DEBUG MODE: Generating answer using LLM                                                                                                   rag.py:301
⠹ Thinking...[22:38:50] DEBUG MODE: Extracting citations from answer                                                                                              rag.py:421
SQL Statistics (authoritative):
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Bet B0059:
  • Customer: C076
  • Sport: football
  • Event: Juvetus vs Interr
  • Market: Asian Handicap → Away +0.5
  • Stake: £10.00
  • Status: SETTLED
  • Incident: LATENCY_SPIKE
  • Delay: 4648ms

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================
Retrieved Bets (1 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event             ┃ Status  ┃ Incident      ┃ Delay  ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ B0059  │ C076     │ Juvetus vs Interr │ SETTLED │ LATENCY_SPIKE │ 4648ms │
└────────┴──────────┴───────────────────┴─────────┴───────────────┴────────┘

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary (from computed facts):                                                                                                                              │
│ There is 1 bet: stake £10.00, status SETTLED, incident LATENCY_SPIKE, delay 4648ms.                                                                         │
│                                                                                                                                                             │
│ - B0059 (Customer C076): Juvetus vs Interr, football — Market: Asian Handicap → Away +0.5. Status: SETTLED. Incident: LATENCY_SPIKE. Delay: 4648ms —        │
│ notably high (normal ~200ms; delays above 1000ms indicate issues).                                                                                          │
│                                                                                                                                                             │
│ Observations and key insights:                                                                                                                              │
│ - The bet was settled despite the latency spike.                                                                                                            │
│ - The recorded delay of 4648ms is well above the 1000ms issue threshold, indicating a significant latency event that could have impacted price timeliness   │
│ for this wager.                                                                                                                                             │
│ - In this dataset B0059 appears as an isolated LATENCY_SPIKE incident (no other bets shown for comparison).                                                 │
│                                                                                                                                                             │
│ Evidence: [B0059]                                                                                                                                           │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0059
Retrieved 1 bet(s) for context
(.venv) mojtabae@MBP2023A BetTrace % python main.py ask "For customer C068, summarize all their bets and highlight any incidents." --show-context

[22:38:55] DEBUG MODE: Starting RAG assistant for question: For customer C068, summarize all their bets and highlight any incidents.                 cli.py:396
[22:38:55] DEBUG MODE: load_embeddings_to_memory called                                                                                         database.py:540
[22:38:55] DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111

Question: For customer C068, summarize all their bets and highlight any incidents.

[22:38:55] DEBUG MODE: Received query: For customer C068, summarize all their bets and highlight any incidents.                                      rag.py:122
[22:38:55] DEBUG MODE: Executing query: 'For customer C068, summarize all their bets and highlight any incidents.' with top_k=100          query_executor.py:75
                                                                                                                                                               
[22:38:55] DEBUG MODE: :Parsing Query (QueryParser.parse): [For customer C068, summarize all their bets and highlight any incidents.]       query_parser.py:392
           DEBUG MODE: :Extracting bet IDs from query: For customer C068, summarize all their bets and highlight any incidents.             query_parser.py:534
           DEBUG MODE: :Extracting customer IDs from query: For customer C068, summarize all their bets and highlight any incidents.        query_parser.py:556
           DEBUG MODE: :Extracting filters from query: for customer  , summarize all their bets and highlight any incidents.                query_parser.py:578
           DEBUG MODE: : Extracting stake range from query: for customer  , summarize all their bets and highlight any incidents.           query_parser.py:617
           DEBUG MODE: :Extracting delay range from query: for customer  , summarize all their bets and highlight any incidents.            query_parser.py:646
           DEBUG MODE: :Extracting sorting from query: for customer  , summarize all their bets and highlight any incidents.                query_parser.py:681
           DEBUG MODE: :Extracting limit from query: for customer  , summarize all their bets and highlight any incidents.                  query_parser.py:704
           DEBUG MODE: :Extracting aggregation from query: for customer  , summarize all their bets and highlight any incidents.            query_parser.py:720
           DEBUG MODE: :Checking for top/bottom N pattern in query: for customer c068, summarize all their bets and highlight any           query_parser.py:741
           incidents.                                                                                                                                          
           DEBUG MODE: :Checking for general aggregate query in: for customer c068, summarize all their bets and highlight any incidents.   query_parser.py:773
           DEBUG MODE: :Detecting invalid entity references in query: for customer c068, summarize all their bets and highlight any         query_parser.py:463
           incidents.                                                                                                                                          
           DEBUG MODE: :Detecting incomplete ID queries in query: for customer c068, summarize all their bets and highlight any incidents.  query_parser.py:510
           DEBUG MODE: :Extracting semantic terms from remaining text: for customer  , summarize all their bets and highlight   incidents.  query_parser.py:789
           DEBUG MODE: :Calculating parse confidence for: ParsedQuery(type=entity_lookup, customer_ids=['C068'], agg=count,                 query_parser.py:830
           semantic=['customer', 'summarize', 'their', 'highlight', 'incidents.'])                                                                             
           DEBUG MODE: Executing entity lookup for parsed query: ParsedQuery(type=entity_lookup, customer_ids=['C068'], agg=count,        query_executor.py:110
           semantic=['customer', 'summarize', 'their', 'highlight', 'incidents.'])                                                                             
                                                                                                                                                               
           DEBUG MODE: Computing customer stats for IDs: ['C068']                                                                         query_executor.py:461
                                                                                                                                                               
           DEBUG MODE: Building context for LLM from execution results                                                                               rag.py:226
           DEBUG MODE: Formatting bet records for context (max_rows=100)                                                                             rag.py:275
           DEBUG MODE: Generating answer using LLM                                                                                                   rag.py:301
⠸ Thinking...[22:39:19] DEBUG MODE: Extracting citations from answer                                                                                              rag.py:421
SQL Statistics (authoritative):
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Customer(s): C068

• Total Bets: 4
• Total Stake: £115.00
• Average Stake: £28.75
• Average Delay: 236ms
• Maximum Delay: 312ms
• Status Breakdown: {'SETTLED': 4}

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================
Retrieved Bets (4 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event                  ┃ Status  ┃ Incident ┃ Delay ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━┩
│ B0003  │ C068     │ PSG vs Marsielle       │ SETTLED │ NONE     │ 290ms │
│ B0018  │ C068     │ Brighton vs Wolvees    │ SETTLED │ NONE     │ 222ms │
│ B0019  │ C068     │ Man Citeh vs Brantford │ SETTLED │ NONE     │ 121ms │
│ B0055  │ C068     │ Raducanu vs Pegulla    │ SETTLED │ NONE     │ 312ms │
└────────┴──────────┴────────────────────────┴─────────┴──────────┴───────┘

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary (from computed facts):                                                                                                                              │
│ - Total Bets: 4                                                                                                                                             │
│ - Total Stake: £115.00                                                                                                                                      │
│ - Average Stake: £28.75                                                                                                                                     │
│ - Average Delay: 236ms                                                                                                                                      │
│ - Maximum Delay: 312ms                                                                                                                                      │
│ - Status Breakdown: {'SETTLED': 4}                                                                                                                          │
│                                                                                                                                                             │
│ Detailed bet list and observations:                                                                                                                         │
│                                                                                                                                                             │
│ - B0003 (Customer C068): PSG vs Marsielle. Status: SETTLED. Incident: NONE. Price Delay: 290ms — elevated versus the normal ~200ms latency.                 │
│   - Sport/market: football, Asian Handicap. Stake: £40.00.                                                                                                  │
│                                                                                                                                                             │
│ - B0018 (Customer C068): Brighton vs Wolvees. Status: SETTLED. Incident: NONE. Price Delay: 222ms — near the normal ~200ms latency.                         │
│   - Sport/market: football, Match Winner. Stake: £15.00.                                                                                                    │
│                                                                                                                                                             │
│ - B0019 (Customer C068): Man Citeh vs Brantford. Status: SETTLED. Incident: NONE. Price Delay: 121ms — below typical latency (~200ms).                      │
│   - Sport/market: football, Over/Under 2.5. Stake: £20.00.                                                                                                  │
│                                                                                                                                                             │
│ - B0055 (Customer C068): Raducanu vs Pegulla. Status: SETTLED. Incident: NONE. Price Delay: 312ms — the maximum delay reported (312ms) and elevated versus  │
│ normal.                                                                                                                                                     │
│   - Sport/market: tennis, Total Games O/U 21.5. Stake: £40.00.                                                                                              │
│                                                                                                                                                             │
│ Patterns and notable observations:                                                                                                                          │
│ - All 4 bets are SETTLED and none have any incident flags (all Incident: NONE).                                                                             │
│ - Stakes are concentrated in two larger £40.00 bets and two smaller bets (£20.00 and £15.00); overall Average Stake is £28.75.                              │
│ - Latency varies across bets with Average Delay 236ms and Maximum Delay 312ms. Two bets (B0003 and B0055) show elevated delays relative to the ~200ms norm, │
│ while B0019 shows low delay.                                                                                                                                │
│ - Sports mix: three football bets and one tennis bet (the tennis bet corresponds to the maximum observed delay).                                            │
│                                                                                                                                                             │
│ Key insights:                                                                                                                                               │
│ - No operational incidents affected these bets (no LATENCY_SPIKE, FEED_OUTAGE, MARKET_SUSPENDED, or MANUAL_REVIEW).                                         │
│ - While all bets settled, monitoring of higher-than-normal delays on B0003 and B0055 may be warranted given the Maximum Delay of 312ms.                     │
│                                                                                                                                                             │
│ Evidence: [B0003, B0018, B0019, B0055]                                                                                                                      │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0003, B0018, B0019, B0055
Retrieved 4 bet(s) for context
(.venv) mojtabae@MBP2023A BetTrace % python main.py ask "Which customers were affected by LATENCY_SPIKE and how severely?" --show-context

[22:39:25] DEBUG MODE: Starting RAG assistant for question: Which customers were affected by LATENCY_SPIKE and how severely?                         cli.py:396
[22:39:25] DEBUG MODE: load_embeddings_to_memory called                                                                                         database.py:540
[22:39:25] DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111

Question: Which customers were affected by LATENCY_SPIKE and how severely?

[22:39:25] DEBUG MODE: Received query: Which customers were affected by LATENCY_SPIKE and how severely?                                              rag.py:122
[22:39:25] DEBUG MODE: Executing query: 'Which customers were affected by LATENCY_SPIKE and how severely?' with top_k=100                  query_executor.py:75
                                                                                                                                                               
[22:39:25] DEBUG MODE: :Parsing Query (QueryParser.parse): [Which customers were affected by LATENCY_SPIKE and how severely?]               query_parser.py:392
           DEBUG MODE: :Extracting bet IDs from query: Which customers were affected by LATENCY_SPIKE and how severely?                     query_parser.py:534
           DEBUG MODE: :Extracting customer IDs from query: Which customers were affected by LATENCY_SPIKE and how severely?                query_parser.py:556
           DEBUG MODE: :Extracting filters from query: which customers were affected by latency_spike and how severely?                     query_parser.py:578
           DEBUG MODE: : Extracting stake range from query: which customers were affected by   and how severely?                            query_parser.py:617
           DEBUG MODE: :Extracting delay range from query: which customers were affected by   and how severely?                             query_parser.py:646
           DEBUG MODE: :Extracting sorting from query: which customers were affected by   and how severely?                                 query_parser.py:681
           DEBUG MODE: :Extracting limit from query: which customers were affected by   and how severely?                                   query_parser.py:704
           DEBUG MODE: :Extracting aggregation from query: which customers were affected by   and how severely?                             query_parser.py:720
           DEBUG MODE: :Checking for top/bottom N pattern in query: which customers were affected by latency_spike and how severely?        query_parser.py:741
           DEBUG MODE: :Checking for general aggregate query in: which customers were affected by latency_spike and how severely?           query_parser.py:773
           DEBUG MODE: :Detecting invalid entity references in query: which customers were affected by latency_spike and how severely?      query_parser.py:463
           DEBUG MODE: :Detecting incomplete ID queries in query: which customers were affected by latency_spike and how severely?          query_parser.py:510
           DEBUG MODE: :Extracting semantic terms from remaining text: which customers were affected by   and how severely?                 query_parser.py:789
           DEBUG MODE: :Calculating parse confidence for: ParsedQuery(type=hybrid, filters={'incident_tag': 'LATENCY_SPIKE'},               query_parser.py:830
           semantic=['customers', 'affected', 'severely?'])                                                                                                    
           DEBUG MODE: Executing hybrid query for parsed query: ParsedQuery(type=hybrid, filters={'incident_tag': 'LATENCY_SPIKE'},       query_executor.py:264
           semantic=['customers', 'affected', 'severely?'])                                                                                                    
                                                                                                                                                               
           DEBUG MODE: Building database filters from parsed query: ParsedQuery(type=hybrid, filters={'incident_tag': 'LATENCY_SPIKE'},   query_executor.py:432
           semantic=['customers', 'affected', 'severely?'])                                                                                                    
                                                                                                                                                               
[22:39:25]                                                                                                                                     retrieval.py:245
           DEBUG MODE: Performing semantic search: 'customers affected severely?' (top_k=200, threshold=None, use_dual_embeddings=True,                        
           team_only=False)                                                                                                                                    
[22:39:25] DEBUG MODE: Embedding single text: 'customers affected severely?'                                                           embedding_service.py:119
           DEBUG MODE: Starting retry with backoff for function: _call_api                                                              embedding_service.py:78
⠏ Thinking...[22:39:26] DEBUG MODE: semantic_search_dual called                                                                                              database.py:750
[22:39:26] DEBUG MODE: Searching for top_k=400 similar vectors                                                                              vector_store.py:152
           DEBUG MODE: Searching for top_k=400 similar vectors                                                                              vector_store.py:152
           DEBUG MODE: Searching for top_k=400 similar vectors                                                                              vector_store.py:152
[22:39:26] DEBUG MODE: Building calculator filters from: {'incident_tag': 'LATENCY_SPIKE'}                                                query_executor.py:399
                                                                                                                                                               
           DEBUG MODE: Computing filter stats for parsed query: ParsedQuery(type=hybrid, filters={'incident_tag': 'LATENCY_SPIKE'},       query_executor.py:643
           semantic=['customers', 'affected', 'severely?'])                                                                                                    
                                                                                                                                                               
           DEBUG MODE: Computing aggregate stats for parsed query: ParsedQuery(type=hybrid, filters={'incident_tag': 'LATENCY_SPIKE'},    query_executor.py:580
           semantic=['customers', 'affected', 'severely?'])                                                                                                    
                                                                                                                                                               
[22:39:26] DEBUG MODE: Building context for LLM from execution results                                                                               rag.py:226
           DEBUG MODE: Formatting bet records for context (max_rows=100)                                                                             rag.py:275
           DEBUG MODE: Generating answer using LLM                                                                                                   rag.py:301
⠏ Thinking...[22:39:48] DEBUG MODE: Extracting citations from answer                                                                                              rag.py:421
SQL Statistics (authoritative):
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Filters: Incident: LATENCY_SPIKE

• Total Bets: 7
• Total Stake: £190.00
• Average Stake: £27.14
• Unique Customers: 7
• Average Delay: 2583ms

Status Breakdown:
  • SETTLED: 80 bets, £2230.00
  • REJECTED: 8 bets, £220.00
  • PENDING: 7 bets, £180.00
  • VOID: 5 bets, £135.00

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================
Retrieved Bets (7 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event                        ┃ Status  ┃ Incident      ┃ Delay  ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ B0023  │ C069     │ Bayern Munchen vs Dortmun... │ PENDING │ LATENCY_SPIKE │ 1619ms │
│ B0032  │ C120     │ Nadall vs Sinnner            │ PENDING │ LATENCY_SPIKE │ 2466ms │
│ B0036  │ C122     │ Lakkers vs Celtcs            │ PENDING │ LATENCY_SPIKE │ 2431ms │
│ B0038  │ C004     │ Murray vs Hurkacz            │ SETTLED │ LATENCY_SPIKE │ 2026ms │
│ B0059  │ C076     │ Juvetus vs Interr            │ SETTLED │ LATENCY_SPIKE │ 4648ms │
│ B0072  │ C055     │ Atletico Madird vs Valeni... │ SETTLED │ LATENCY_SPIKE │ 2273ms │
│ B0090  │ C121     │ Nadall vs Sinnner            │ SETTLED │ LATENCY_SPIKE │ 2615ms │
└────────┴──────────┴──────────────────────────────┴─────────┴───────────────┴────────┘

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary (from computed facts):                                                                                                                              │
│ • Total Bets: 7                                                                                                                                             │
│ • Total Stake: £190.00                                                                                                                                      │
│ • Average Stake: £27.14                                                                                                                                     │
│ • Unique Customers: 7                                                                                                                                       │
│ • Average Delay: 2583ms                                                                                                                                     │
│                                                                                                                                                             │
│ Affected customers and severity (each record):                                                                                                              │
│                                                                                                                                                             │
│ - B0023 (Customer C069): Bayern Munchen vs Dortmundd. Status: PENDING. Incident: LATENCY_SPIKE. Delay: 1619ms — high latency (above 1000ms).                │
│ - B0032 (Customer C120): Nadall vs Sinnner. Status: PENDING. Incident: LATENCY_SPIKE. Delay: 2466ms — high latency.                                         │
│ - B0036 (Customer C122): Lakkers vs Celtcs. Status: PENDING. Incident: LATENCY_SPIKE. Delay: 2431ms — high latency.                                         │
│ - B0038 (Customer C004): Murray vs Hurkacz. Status: SETTLED. Incident: LATENCY_SPIKE. Delay: 2026ms — high latency.                                         │
│ - B0059 (Customer C076): Juvetus vs Interr. Status: SETTLED. Incident: LATENCY_SPIKE. Delay: 4648ms — severely high latency (notably elevated).             │
│ - B0072 (Customer C055): Atletico Madird vs Valenica. Status: SETTLED. Incident: LATENCY_SPIKE. Delay: 2273ms — high latency.                               │
│ - B0090 (Customer C121): Nadall vs Sinnner. Status: SETTLED. Incident: LATENCY_SPIKE. Delay: 2615ms — high latency.                                         │
│                                                                                                                                                             │
│ Patterns and notable observations:                                                                                                                          │
│ - Every affected bet shows latency well above the 1000ms threshold; the computed average delay is 2583ms, indicating widespread severe latency for these    │
│ customers.                                                                                                                                                  │
│ - All seven bets are from distinct customers (Unique Customers: 7).                                                                                         │
│ - Stakes vary (Average Stake: £27.14) and include both PENDING and SETTLED outcomes; one bet (B0059) shows an especially extreme delay at 4648ms.           │
│                                                                                                                                                             │
│ Key insight:                                                                                                                                                │
│ All seven customers experienced significant latency (all delays >1000ms), with an average delay of 2583ms and one particularly severe outlier (B0059 at     │
│ 4648ms), suggesting a systemic latency incident affecting multiple customers and markets.                                                                   │
│                                                                                                                                                             │
│ Evidence: [B0023, B0032, B0036, B0038, B0059, B0072, B0090]                                                                                                 │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0023, B0032, B0036, B0038, B0059, B0072, B0090
Retrieved 7 bet(s) for context
(.venv) mojtabae@MBP2023A BetTrace % python main.py ask "How many bets were voided due to FEED_OUTAGE? List them and explain." --show-context

[22:40:23] DEBUG MODE: Starting RAG assistant for question: How many bets were voided due to FEED_OUTAGE? List them and explain.                     cli.py:396
[22:40:23] DEBUG MODE: load_embeddings_to_memory called                                                                                         database.py:540
[22:40:23] DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111

Question: How many bets were voided due to FEED_OUTAGE? List them and explain.

[22:40:23] DEBUG MODE: Received query: How many bets were voided due to FEED_OUTAGE? List them and explain.                                          rag.py:122
[22:40:23] DEBUG MODE: Executing query: 'How many bets were voided due to FEED_OUTAGE? List them and explain.' with top_k=100              query_executor.py:75
                                                                                                                                                               
[22:40:23] DEBUG MODE: :Parsing Query (QueryParser.parse): [How many bets were voided due to FEED_OUTAGE? List them and explain.]           query_parser.py:392
           DEBUG MODE: :Extracting bet IDs from query: How many bets were voided due to FEED_OUTAGE? List them and explain.                 query_parser.py:534
           DEBUG MODE: :Extracting customer IDs from query: How many bets were voided due to FEED_OUTAGE? List them and explain.            query_parser.py:556
           DEBUG MODE: :Extracting filters from query: how many bets were voided due to feed_outage? list them and explain.                 query_parser.py:578
           DEBUG MODE: : Extracting stake range from query: how many bets were  ed due to  ? list them and explain.                         query_parser.py:617
           DEBUG MODE: :Extracting delay range from query: how many bets were  ed due to  ? list them and explain.                          query_parser.py:646
           DEBUG MODE: :Extracting sorting from query: how many bets were  ed due to  ? list them and explain.                              query_parser.py:681
           DEBUG MODE: :Extracting limit from query: how many bets were  ed due to  ? list them and explain.                                query_parser.py:704
           DEBUG MODE: :Extracting aggregation from query: how many bets were  ed due to  ? list them and explain.                          query_parser.py:720
           DEBUG MODE: :Checking for top/bottom N pattern in query: how many bets were voided due to feed_outage? list them and explain.    query_parser.py:741
           DEBUG MODE: :Checking for general aggregate query in: how many bets were voided due to feed_outage? list them and explain.       query_parser.py:773
           DEBUG MODE: :Detecting invalid entity references in query: how many bets were voided due to feed_outage? list them and explain.  query_parser.py:463
           DEBUG MODE: :Detecting incomplete ID queries in query: how many bets were voided due to feed_outage? list them and explain.      query_parser.py:510
           DEBUG MODE: :Extracting semantic terms from remaining text:   bets were  ed due to  ? list them and explain.                     query_parser.py:789
           DEBUG MODE: :Calculating parse confidence for: ParsedQuery(type=aggregate, filters={'status': 'VOID', 'incident_tag':            query_parser.py:830
           'FEED_OUTAGE'}, agg=count, semantic=['ed', 'due', 'them', 'explain.'])                                                                              
           DEBUG MODE: Executing aggregate query for parsed query: ParsedQuery(type=aggregate, filters={'status': 'VOID', 'incident_tag': query_executor.py:195
           'FEED_OUTAGE'}, agg=count, semantic=['ed', 'due', 'them', 'explain.'])                                                                              
                                                                                                                                                               
           DEBUG MODE: Building calculator filters from: {'status': 'VOID', 'incident_tag': 'FEED_OUTAGE'}                                query_executor.py:399
                                                                                                                                                               
           DEBUG MODE: Building database filters from parsed query: ParsedQuery(type=aggregate, filters={'status': 'VOID',                query_executor.py:432
           'incident_tag': 'FEED_OUTAGE'}, agg=count, semantic=['ed', 'due', 'them', 'explain.'])                                                              
                                                                                                                                                               
           DEBUG MODE: Computing aggregate stats for parsed query: ParsedQuery(type=aggregate, filters={'status': 'VOID', 'incident_tag': query_executor.py:580
           'FEED_OUTAGE'}, agg=count, semantic=['ed', 'due', 'them', 'explain.'])                                                                              
                                                                                                                                                               
           DEBUG MODE: Building context for LLM from execution results                                                                               rag.py:226
           DEBUG MODE: Formatting bet records for context (max_rows=100)                                                                             rag.py:275
           DEBUG MODE: Generating answer using LLM                                                                                                   rag.py:301
⠹ Thinking...[22:40:46] DEBUG MODE: Extracting citations from answer                                                                                              rag.py:421
SQL Statistics (authoritative):
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Filters: Status: VOID, Incident: FEED_OUTAGE

• Total Bets: 4
• Total Stake: £95.00
• Average Stake: £23.75
• Unique Customers: 4
• Average Delay: 960ms

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================
Retrieved Bets (4 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event               ┃ Status ┃ Incident    ┃ Delay  ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━┩
│ B0028  │ C022     │ Zverev vs Tsitsipas │ VOID   │ FEED_OUTAGE │ 495ms  │
│ B0050  │ C106     │ Man Utd vs Newcatle │ VOID   │ FEED_OUTAGE │ 1073ms │
│ B0066  │ C033     │ Warriros vs Suns    │ VOID   │ FEED_OUTAGE │ 1078ms │
│ B0094  │ C011     │ Medvedev vs Runee   │ VOID   │ FEED_OUTAGE │ 1194ms │
└────────┴──────────┴─────────────────────┴────────┴─────────────┴────────┘

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary (from computed facts):                                                                                                                              │
│ Total Bets: 4                                                                                                                                               │
│ Total Stake: £95.00                                                                                                                                         │
│ Average Stake: £23.75                                                                                                                                       │
│ Unique Customers: 4                                                                                                                                         │
│ Average Delay: 960ms                                                                                                                                        │
│                                                                                                                                                             │
│ There were 4 bets voided due to FEED_OUTAGE:                                                                                                                │
│                                                                                                                                                             │
│ - B0028 (Customer C022): Zverev vs Tsitsipas, tennis. Status: VOID, Incident: FEED_OUTAGE, Delay: 495ms — below the 1000ms issue threshold (moderately      │
│ elevated relative to ~200ms normal).                                                                                                                        │
│ - B0050 (Customer C106): Man Utd vs Newcatle, football. Status: VOID, Incident: FEED_OUTAGE, Delay: 1073ms — notably high (above 1000ms).                   │
│ - B0066 (Customer C033): Warriros vs Suns, basketball. Status: VOID, Incident: FEED_OUTAGE, Delay: 1078ms — notably high (above 1000ms).                    │
│ - B0094 (Customer C011): Medvedev vs Runee, tennis. Status: VOID, Incident: FEED_OUTAGE, Delay: 1194ms — highest delay and notably high (above 1000ms).     │
│                                                                                                                                                             │
│ Patterns / notable observations:                                                                                                                            │
│ - All listed bets share the same incident tag (FEED_OUTAGE) and status (VOID), confirming cancellation due to data feed problems.                           │
│ - Delays vary substantially: one bet (B0028) has a sub-1000ms delay (495ms), while B0050, B0066, and B0094 show delays above the 1000ms threshold that      │
│ indicates feed issues.                                                                                                                                      │
│ - Stakes are varied across customers; computed totals show a combined stake of £95.00 and an average stake of £23.75.                                       │
│                                                                                                                                                             │
│ Key insights:                                                                                                                                               │
│ - The FEED_OUTAGE incident caused cancellations across multiple sports (tennis, football, basketball) and affected different customers.                     │
│ - Several bets exhibit delays above the 1000ms threshold, pointing to significant feed instability during these events; one bet had a lower delay but was   │
│ still voided under the same incident tag.                                                                                                                   │
│                                                                                                                                                             │
│ Evidence: [B0028, B0050, B0066, B0094]                                                                                                                      │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0028, B0050, B0066, B0094
Retrieved 4 bet(s) for context
(.venv) mojtabae@MBP2023A BetTrace % python main.py ask "All bets involving Thundr" --show-context                                           

[22:40:54] DEBUG MODE: Starting RAG assistant for question: All bets involving Thundr                                                                cli.py:396
[22:40:54] DEBUG MODE: load_embeddings_to_memory called                                                                                         database.py:540
[22:40:54] DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                                              vector_store.py:111

Question: All bets involving Thundr

[22:40:54] DEBUG MODE: Received query: All bets involving Thundr                                                                                     rag.py:122
[22:40:54] DEBUG MODE: Executing query: 'All bets involving Thundr' with top_k=100                                                         query_executor.py:75
                                                                                                                                                               
[22:40:54] DEBUG MODE: :Parsing Query (QueryParser.parse): [All bets involving Thundr]                                                      query_parser.py:392
           DEBUG MODE: :Extracting bet IDs from query: All bets involving Thundr                                                            query_parser.py:534
           DEBUG MODE: :Extracting customer IDs from query: All bets involving Thundr                                                       query_parser.py:556
           DEBUG MODE: :Extracting filters from query: all bets involving thundr                                                            query_parser.py:578
           DEBUG MODE: : Extracting stake range from query: all bets involving thundr                                                       query_parser.py:617
           DEBUG MODE: :Extracting delay range from query: all bets involving thundr                                                        query_parser.py:646
           DEBUG MODE: :Extracting sorting from query: all bets involving thundr                                                            query_parser.py:681
           DEBUG MODE: :Extracting limit from query: all bets involving thundr                                                              query_parser.py:704
           DEBUG MODE: :Extracting aggregation from query: all bets involving thundr                                                        query_parser.py:720
           DEBUG MODE: :Checking for top/bottom N pattern in query: all bets involving thundr                                               query_parser.py:741
           DEBUG MODE: :Checking for general aggregate query in: all bets involving thundr                                                  query_parser.py:773
           DEBUG MODE: :Detecting invalid entity references in query: all bets involving thundr                                             query_parser.py:463
           DEBUG MODE: :Detecting incomplete ID queries in query: all bets involving thundr                                                 query_parser.py:510
           DEBUG MODE: :Extracting semantic terms from remaining text: all bets involving thundr                                            query_parser.py:789
           DEBUG MODE: :Calculating parse confidence for: ParsedQuery(type=semantic, agg=count, semantic=['involving', 'thundr'])           query_parser.py:830
           DEBUG MODE: Executing semantic query for parsed query: ParsedQuery(type=semantic, agg=count, semantic=['involving', 'thundr']) query_executor.py:320
                                                                                                                                                               
           DEBUG MODE: Checking if query is a team/player search: 'All bets involving Thundr'                                             query_executor.py:359
[22:40:54]                                                                                                                                     retrieval.py:245
           DEBUG MODE: Performing semantic search: 'All bets involving Thundr' (top_k=100, threshold=0.7, use_dual_embeddings=True,                            
           team_only=True)                                                                                                                                     
                                                                                                                                               retrieval.py:315
           DEBUG MODE: Extracting team terms from query: 'All bets involving Thundr'                                                                           
[22:40:54] DEBUG MODE: Phonetic normalizing text: 'Thundr'                                                                                        models.py:313
[22:40:54] DEBUG MODE: Embedding single text: 'THNDR'                                                                                  embedding_service.py:119
           DEBUG MODE: Starting retry with backoff for function: _call_api                                                              embedding_service.py:78
⠦ Thinking...[22:40:55] DEBUG MODE: semantic_search_teams called                                                                                             database.py:705
[22:40:55] DEBUG MODE: Searching for top_k=200 similar vectors                                                                              vector_store.py:152
           DEBUG MODE: Searching for top_k=200 similar vectors                                                                              vector_store.py:152
[22:40:55] DEBUG MODE: Building context for LLM from execution results                                                                               rag.py:226
           DEBUG MODE: Formatting bet records for context (max_rows=100)                                                                             rag.py:275
           DEBUG MODE: Generating answer using LLM                                                                                                   rag.py:301
⠹ Thinking...[22:41:17] DEBUG MODE: Extracting citations from answer                                                                                              rag.py:421
Retrieved Bets (6 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event                ┃ Status   ┃ Incident         ┃ Delay ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ B0088  │ C027     │ Clippers vs Thunderr │ REJECTED │ MARKET_SUSPENDED │ 389ms │
│ B0027  │ C104     │ Clippers vs Thunderr │ SETTLED  │ NONE             │ 204ms │
│ B0048  │ C006     │ Clippers vs Thunderr │ SETTLED  │ MANUAL_REVIEW    │ 467ms │
│ B0010  │ C018     │ Clippers vs Thunderr │ SETTLED  │ NONE             │ 159ms │
│ B0043  │ C033     │ Clippers vs Thunderr │ REJECTED │ MARKET_SUSPENDED │ 374ms │
│ B0100  │ C023     │ Clippers vs Thunderr │ SETTLED  │ NONE             │ 188ms │
└────────┴──────────┴──────────────────────┴──────────┴──────────────────┴───────┘

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary stats: This requires computation (no pre-computed aggregates provided).                                                                             │
│                                                                                                                                                             │
│ All bets for the event recorded as "Clippers vs Thunderr":                                                                                                  │
│                                                                                                                                                             │
│ - B0088 — Customer C027 — Market: Total Points O/U 215.5 — Selection: Over 215.5 — Stake: £15.00 — Status: REJECTED — Incident: MARKET_SUSPENDED — Price    │
│ Delay: 389ms                                                                                                                                                │
│ - B0027 — Customer C104 — Market: Moneyline — Selection: Thunderr — Stake: £80.00 — Status: SETTLED — Incident: NONE — Price Delay: 204ms                   │
│ - B0048 — Customer C006 — Market: Spread — Selection: Home -3.5 — Stake: £15.00 — Status: SETTLED — Incident: MANUAL_REVIEW — Price Delay: 467ms            │
│ - B0010 — Customer C018 — Market: Moneyline — Selection: Clippers — Stake: £15.00 — Status: SETTLED — Incident: NONE — Price Delay: 159ms                   │
│ - B0043 — Customer C033 — Market: Spread — Selection: Home -3.5 — Stake: £25.00 — Status: REJECTED — Incident: MARKET_SUSPENDED — Price Delay: 374ms        │
│ - B0100 — Customer C023 — Market: Spread — Selection: Away +3.5 — Stake: £25.00 — Status: SETTLED — Incident: NONE — Price Delay: 188ms                     │
│                                                                                                                                                             │
│ Patterns / anomalies:                                                                                                                                       │
│ - Two bets were REJECTED and show incident MARKET_SUSPENDED: B0088 and B0043.                                                                               │
│ - One settled bet was flagged MANUAL_REVIEW: B0048.                                                                                                         │
│ - Price delays recorded: 389ms (B0088), 204ms (B0027), 467ms (B0048), 159ms (B0010), 374ms (B0043), 188ms (B0100). (Normal ~200ms; >1000ms would indicate   │
│ issues — none exceed 1000ms.)                                                                                                                               │
│                                                                                                                                                             │
│ Evidence: [B0088, B0027, B0048, B0010, B0043, B0100]                                                                                                        │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0088, B0027, B0048, B0010, B0043, B0100
Retrieved 6 bet(s) for context
(.venv) mojtabae@MBP2023A BetTrace % 

```