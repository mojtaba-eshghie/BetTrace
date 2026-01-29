Aggregate query example: 

```bash
(.venv) mojtabae@pool4-36-234 BetTrace % python main.py ask "Sum of bet stakes with delay over 200ms and delay under 400ms and were settled; Do you see any particular patterns about these? " --show-context
[13:24:33] DEBUG MODE: Starting RAG assistant for question: Sum of bet stakes with delay over 200ms and delay under 400ms and were   cli.py:397
           settled; Do you see any particular patterns about these?                                                                            
[13:24:33] DEBUG MODE: load_embeddings_to_memory called                                                                         database.py:540
[13:24:33] DEBUG MODE: Adding batch of embeddings (count: 100)                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                              vector_store.py:111

Question: Sum of bet stakes with delay over 200ms and delay under 400ms and were settled; Do you see any particular patterns about these? 

[13:24:33] DEBUG MODE: Received query: Sum of bet stakes with delay over 200ms and delay under 400ms and were settled; Do you see    rag.py:122
           any particular patterns about these?                                                                                                
[13:24:33] DEBUG MODE: Executing query: 'Sum of bet stakes with delay over 200ms and delay under 400ms and were settled;   query_executor.py:75
           Do you see any particular patterns about these? ' with top_k=100                                                                    
                                                                                                                                               
[13:24:33] DEBUG MODE: :Parsing Query (QueryParser.parse): [Sum of bet stakes with delay over 200ms and delay under 400ms   query_parser.py:392
           and were settled; Do you see any particular patterns about these? ]                                                                 
           DEBUG MODE: :Extracting bet IDs from query: Sum of bet stakes with delay over 200ms and delay under 400ms and    query_parser.py:534
           were settled; Do you see any particular patterns about these?                                                                       
           DEBUG MODE: :Extracting customer IDs from query: Sum of bet stakes with delay over 200ms and delay under 400ms   query_parser.py:556
           and were settled; Do you see any particular patterns about these?                                                                   
           DEBUG MODE: :Extracting filters from query: sum of bet stakes with delay over 200ms and delay under 400ms and    query_parser.py:578
           were settled; do you see any particular patterns about these?                                                                       
           DEBUG MODE: : Extracting stake range from query: sum of bet stakes with delay over 200ms and delay under 400ms   query_parser.py:617
           and were  ; do you see any particular patterns about these?                                                                         
           DEBUG MODE: :Extracting delay range from query: sum of bet stakes with delay over 200ms and delay under 400ms    query_parser.py:646
           and were  ; do you see any particular patterns about these?                                                                         
           DEBUG MODE: :Extracting sorting from query: sum of bet stakes with delay over 200ms and delay under 400ms and    query_parser.py:681
           were  ; do you see any particular patterns about these?                                                                             
           DEBUG MODE: :Extracting limit from query: sum of bet stakes with delay over 200ms and delay under 400ms and were query_parser.py:704
           ; do you see any particular patterns about these?                                                                                   
           DEBUG MODE: :Extracting aggregation from query: sum of bet stakes with delay over 200ms and delay under 400ms    query_parser.py:720
           and were  ; do you see any particular patterns about these?                                                                         
           DEBUG MODE: :Checking for top/bottom N pattern in query: sum of bet stakes with delay over 200ms and delay under query_parser.py:741
           400ms and were settled; do you see any particular patterns about these?                                                             
           DEBUG MODE: :Checking for general aggregate query in: sum of bet stakes with delay over 200ms and delay under    query_parser.py:773
           400ms and were settled; do you see any particular patterns about these?                                                             
           DEBUG MODE: :Detecting invalid entity references in query: sum of bet stakes with delay over 200ms and delay     query_parser.py:463
           under 400ms and were settled; do you see any particular patterns about these?                                                       
           DEBUG MODE: :Detecting incomplete ID queries in query: sum of bet stakes with delay over 200ms and delay under   query_parser.py:510
           400ms and were settled; do you see any particular patterns about these?                                                             
           DEBUG MODE: :Extracting semantic terms from remaining text:   bet stakes with delay over 200ms and delay under   query_parser.py:789
           400ms and were  ; do you see any particular patterns about these?                                                                   
           DEBUG MODE: :Calculating parse confidence for: ParsedQuery(type=aggregate, filters={'status': 'SETTLED',         query_parser.py:830
           'min_delay': 200, 'max_delay': 400}, agg=sum, semantic=['about'])                                                                   
           DEBUG MODE: Executing aggregate query for parsed query: ParsedQuery(type=aggregate, filters={'status':         query_executor.py:195
           'SETTLED', 'min_delay': 200, 'max_delay': 400}, agg=sum, semantic=['about'])                                                        
                                                                                                                                               
           DEBUG MODE: Building calculator filters from: {'status': 'SETTLED', 'min_delay': 200, 'max_delay': 400}        query_executor.py:399
                                                                                                                                               
           DEBUG MODE: Building database filters from parsed query: ParsedQuery(type=aggregate, filters={'status':        query_executor.py:432
           'SETTLED', 'min_delay': 200, 'max_delay': 400}, agg=sum, semantic=['about'])                                                        
                                                                                                                                               
           DEBUG MODE: Computing aggregate stats for parsed query: ParsedQuery(type=aggregate, filters={'status':         query_executor.py:580
           'SETTLED', 'min_delay': 200, 'max_delay': 400}, agg=sum, semantic=['about'])                                                        
                                                                                                                                               
           DEBUG MODE: Building context for LLM from execution results                                                               rag.py:226
           DEBUG MODE: Formatting bet records for context (max_rows=100)                                                             rag.py:275
           DEBUG MODE: Generating answer using LLM                                                                                   rag.py:301
⠋ Thinking...[13:24:55] DEBUG MODE: Extracting citations from answer                                                                              rag.py:421
SQL Statistics (authoritative):
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Filters: Status: SETTLED, Min Delay: 200ms, Max Delay: 400ms

• Total Bets: 34
• Total Stake: £985.00
• Average Stake: £28.97
• Unique Customers: 30
• Average Delay: 239ms

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================
Retrieved Bets (34 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event                        ┃ Status  ┃ Incident      ┃ Delay ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━┩
│ B0001  │ C029     │ PSG vs Marsielle             │ SETTLED │ NONE          │ 214ms │
│ B0003  │ C068     │ PSG vs Marsielle             │ SETTLED │ NONE          │ 290ms │
│ B0016  │ C015     │ Lakkers vs Celtcs            │ SETTLED │ NONE          │ 253ms │
│ B0018  │ C068     │ Brighton vs Wolvees          │ SETTLED │ NONE          │ 222ms │
│ B0020  │ C071     │ Chealsea vs Arsenel          │ SETTLED │ NONE          │ 248ms │
│ B0027  │ C104     │ Clippers vs Thunderr         │ SETTLED │ NONE          │ 204ms │
│ B0029  │ C127     │ Rybakina vs Sabalnka         │ SETTLED │ NONE          │ 203ms │
│ B0035  │ C021     │ Nadall vs Sinnner            │ SETTLED │ NONE          │ 208ms │
│ B0040  │ C072     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 235ms │
│ B0044  │ C014     │ Liverpol vs Spurs            │ SETTLED │ NONE          │ 213ms │
│ B0049  │ C027     │ Brighton vs Wolvees          │ SETTLED │ NONE          │ 216ms │
│ B0051  │ C041     │ Nadall vs Sinnner            │ SETTLED │ NONE          │ 200ms │
│ B0053  │ C126     │ Nottm Forst vs Burnley       │ SETTLED │ NONE          │ 235ms │
│ B0054  │ C098     │ Djokvich vs Alcaraz          │ SETTLED │ NONE          │ 247ms │
│ B0055  │ C068     │ Raducanu vs Pegulla          │ SETTLED │ NONE          │ 312ms │
│ B0057  │ C106     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 203ms │
│ B0063  │ C084     │ Warriros vs Suns             │ SETTLED │ NONE          │ 239ms │
│ B0067  │ C034     │ Brighton vs Wolvees          │ SETTLED │ NONE          │ 253ms │
│ B0068  │ C057     │ Lakkers vs Celtcs            │ SETTLED │ NONE          │ 216ms │
│ B0070  │ C059     │ Zverev vs Tsitsipas          │ SETTLED │ NONE          │ 246ms │
│ B0073  │ C007     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 228ms │
│ B0074  │ C024     │ Heat vs Knickss              │ SETTLED │ NONE          │ 256ms │
│ B0077  │ C091     │ West Ham vs Fullham          │ SETTLED │ NONE          │ 330ms │
│ B0079  │ C090     │ Djokvich vs Alcaraz          │ SETTLED │ MANUAL_REVIEW │ 231ms │
│ B0080  │ C083     │ Bucks vs 76ers               │ SETTLED │ NONE          │ 240ms │
│ B0083  │ C014     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 252ms │
│ B0084  │ C101     │ Real Madird vs Barselona     │ SETTLED │ NONE          │ 268ms │
│ B0085  │ C055     │ Murray vs Hurkacz            │ SETTLED │ NONE          │ 234ms │
│ B0089  │ C102     │ Bucks vs 76ers               │ SETTLED │ NONE          │ 261ms │
│ B0092  │ C135     │ Heat vs Knickss              │ SETTLED │ NONE          │ 226ms │
│ B0096  │ C076     │ Swiatekk vs Gauf             │ SETTLED │ NONE          │ 239ms │
│ B0097  │ C015     │ Atletico Madird vs Valeni... │ SETTLED │ NONE          │ 242ms │
│ B0098  │ C009     │ Warriros vs Suns             │ SETTLED │ NONE          │ 224ms │
│ B0099  │ C128     │ Mavs vs Nuggetts             │ SETTLED │ NONE          │ 232ms │
└────────┴──────────┴──────────────────────────────┴─────────┴───────────────┴───────┘

╭────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────╮
│ There are 34 bets with a total stake of £985.00.                                                                                            │
│                                                                                                                                             │
│ Summary: Average Stake £28.97, Average Delay 239ms, Unique Customers 30; incident tags are largely NONE with one MANUAL_REVIEW (B0079);     │
│ bets span football, basketball and tennis with no obvious clustering by sport within the 200–400ms delay range. Evidence: [B0001, B0003,    │
│ B0016, B0018, B0020, B0027, B0029, B0035, B0040, B0044, B0049, B0051, B0053, B0054, B0055, B0057, B0063, B0067, B0068, B0070, B0073, B0074, │
│ B0077, B0079, B0080, B0083, B0084, B0085, B0089, B0092, B0096, B0097, B0098, B0099]                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0079, B0001, B0003, B0016, B0018, B0020, B0027, B0029, B0035, B0040, B0044, B0049, B0051, B0053, B0054, B0055, B0057, B0063, B0067, 
B0068, B0070, B0073, B0074, B0077, B0080, B0083, B0084, B0085, B0089, B0092, B0096, B0097, B0098, B0099
Retrieved 34 bet(s) for context
```



Hybrid query example: 

```bash

(.venv) mojtabae@pool4-36-234 BetTrace % python main.py ask "Bets with delay over 200ms and delay under 400ms and were settled" --show-context
[13:26:56] DEBUG MODE: Starting RAG assistant for question: Bets with delay over 200ms and delay under 400ms and were settled        cli.py:397
[13:26:56] DEBUG MODE: load_embeddings_to_memory called                                                                         database.py:540
[13:26:56] DEBUG MODE: Adding batch of embeddings (count: 100)                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                              vector_store.py:111
           DEBUG MODE: Adding batch of embeddings (count: 100)                                                              vector_store.py:111

Question: Bets with delay over 200ms and delay under 400ms and were settled

[13:26:56] DEBUG MODE: Received query: Bets with delay over 200ms and delay under 400ms and were settled                             rag.py:122
[13:26:56] DEBUG MODE: Executing query: 'Bets with delay over 200ms and delay under 400ms and were settled' with top_k=100 query_executor.py:75
                                                                                                                                               
[13:26:56] DEBUG MODE: :Parsing Query (QueryParser.parse): [Bets with delay over 200ms and delay under 400ms and were       query_parser.py:392
           settled]                                                                                                                            
           DEBUG MODE: :Extracting bet IDs from query: Bets with delay over 200ms and delay under 400ms and were settled    query_parser.py:534
           DEBUG MODE: :Extracting customer IDs from query: Bets with delay over 200ms and delay under 400ms and were       query_parser.py:556
           settled                                                                                                                             
           DEBUG MODE: :Extracting filters from query: bets with delay over 200ms and delay under 400ms and were settled    query_parser.py:578
           DEBUG MODE: : Extracting stake range from query: bets with delay over 200ms and delay under 400ms and were       query_parser.py:617
           DEBUG MODE: :Extracting delay range from query: bets with delay over 200ms and delay under 400ms and were        query_parser.py:646
           DEBUG MODE: :Extracting sorting from query: bets with delay over 200ms and delay under 400ms and were            query_parser.py:681
           DEBUG MODE: :Extracting limit from query: bets with delay over 200ms and delay under 400ms and were              query_parser.py:704
           DEBUG MODE: :Extracting aggregation from query: bets with delay over 200ms and delay under 400ms and were        query_parser.py:720
           DEBUG MODE: :Checking for top/bottom N pattern in query: bets with delay over 200ms and delay under 400ms and    query_parser.py:741
           were settled                                                                                                                        
           DEBUG MODE: :Checking for general aggregate query in: bets with delay over 200ms and delay under 400ms and were  query_parser.py:773
           settled                                                                                                                             
           DEBUG MODE: :Detecting invalid entity references in query: bets with delay over 200ms and delay under 400ms and  query_parser.py:463
           were settled                                                                                                                        
           DEBUG MODE: :Detecting incomplete ID queries in query: bets with delay over 200ms and delay under 400ms and were query_parser.py:510
           settled                                                                                                                             
           DEBUG MODE: :Extracting semantic terms from remaining text: bets with delay over 200ms and delay under 400ms and query_parser.py:789
           were                                                                                                                                
           DEBUG MODE: :Calculating parse confidence for: ParsedQuery(type=hybrid, filters={'status': 'SETTLED',            query_parser.py:830
           'min_delay': 200, 'max_delay': 400}, semantic=['delay', 'over', '200ms', 'delay', 'under'])                                         
           DEBUG MODE: Executing hybrid query for parsed query: ParsedQuery(type=hybrid, filters={'status': 'SETTLED',    query_executor.py:264
           'min_delay': 200, 'max_delay': 400}, semantic=['delay', 'over', '200ms', 'delay', 'under'])                                         
                                                                                                                                               
           DEBUG MODE: Building database filters from parsed query: ParsedQuery(type=hybrid, filters={'status':           query_executor.py:432
           'SETTLED', 'min_delay': 200, 'max_delay': 400}, semantic=['delay', 'over', '200ms', 'delay', 'under'])                              
                                                                                                                                               
[13:26:56]                                                                                                                     retrieval.py:245
           DEBUG MODE: Performing semantic search: 'delay over 200ms delay under' (top_k=200, threshold=None,                                  
           use_dual_embeddings=True, team_only=False)                                                                                          
[13:26:56] DEBUG MODE: Embedding single text: 'delay over 200ms delay under'                                           embedding_service.py:119
           DEBUG MODE: Starting retry with backoff for function: _call_api                                              embedding_service.py:78
⠼ Thinking...[13:26:57] DEBUG MODE: semantic_search_dual called                                                                              database.py:751
⠴ Thinking...[13:26:57] DEBUG MODE: Searching for top_k=400 similar vectors                                                              vector_store.py:152
           DEBUG MODE: Searching for top_k=400 similar vectors                                                              vector_store.py:152
           DEBUG MODE: Searching for top_k=400 similar vectors                                                              vector_store.py:152
[13:26:57] DEBUG MODE: Building calculator filters from: {'status': 'SETTLED', 'min_delay': 200, 'max_delay': 400}        query_executor.py:399
                                                                                                                                               
           DEBUG MODE: Computing filter stats for parsed query: ParsedQuery(type=hybrid, filters={'status': 'SETTLED',    query_executor.py:643
           'min_delay': 200, 'max_delay': 400}, semantic=['delay', 'over', '200ms', 'delay', 'under'])                                         
                                                                                                                                               
           DEBUG MODE: Computing aggregate stats for parsed query: ParsedQuery(type=hybrid, filters={'status': 'SETTLED', query_executor.py:580
           'min_delay': 200, 'max_delay': 400}, semantic=['delay', 'over', '200ms', 'delay', 'under'])                                         
                                                                                                                                               
[13:26:57] DEBUG MODE: Building context for LLM from execution results                                                               rag.py:226
           DEBUG MODE: Formatting bet records for context (max_rows=100)                                                             rag.py:275
           DEBUG MODE: Generating answer using LLM                                                                                   rag.py:301
⠋ Thinking...[13:27:25] DEBUG MODE: Generating fallback answer due to empty LLM response                                                          rag.py:378
           DEBUG MODE: Extracting citations from answer                                                                              rag.py:421
SQL Statistics (authoritative):
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Filters: Status: SETTLED, Min Delay: 200ms, Max Delay: 400ms

• Total Bets: 34
• Total Stake: £985.00
• Average Stake: £28.97
• Unique Customers: 30
• Average Delay: 239ms

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================
Retrieved Bets (34 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event                        ┃ Status  ┃ Incident      ┃ Delay ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━┩
│ B0001  │ C029     │ PSG vs Marsielle             │ SETTLED │ NONE          │ 214ms │
│ B0003  │ C068     │ PSG vs Marsielle             │ SETTLED │ NONE          │ 290ms │
│ B0016  │ C015     │ Lakkers vs Celtcs            │ SETTLED │ NONE          │ 253ms │
│ B0018  │ C068     │ Brighton vs Wolvees          │ SETTLED │ NONE          │ 222ms │
│ B0020  │ C071     │ Chealsea vs Arsenel          │ SETTLED │ NONE          │ 248ms │
│ B0027  │ C104     │ Clippers vs Thunderr         │ SETTLED │ NONE          │ 204ms │
│ B0029  │ C127     │ Rybakina vs Sabalnka         │ SETTLED │ NONE          │ 203ms │
│ B0035  │ C021     │ Nadall vs Sinnner            │ SETTLED │ NONE          │ 208ms │
│ B0040  │ C072     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 235ms │
│ B0044  │ C014     │ Liverpol vs Spurs            │ SETTLED │ NONE          │ 213ms │
│ B0049  │ C027     │ Brighton vs Wolvees          │ SETTLED │ NONE          │ 216ms │
│ B0051  │ C041     │ Nadall vs Sinnner            │ SETTLED │ NONE          │ 200ms │
│ B0053  │ C126     │ Nottm Forst vs Burnley       │ SETTLED │ NONE          │ 235ms │
│ B0054  │ C098     │ Djokvich vs Alcaraz          │ SETTLED │ NONE          │ 247ms │
│ B0055  │ C068     │ Raducanu vs Pegulla          │ SETTLED │ NONE          │ 312ms │
│ B0057  │ C106     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 203ms │
│ B0063  │ C084     │ Warriros vs Suns             │ SETTLED │ NONE          │ 239ms │
│ B0067  │ C034     │ Brighton vs Wolvees          │ SETTLED │ NONE          │ 253ms │
│ B0068  │ C057     │ Lakkers vs Celtcs            │ SETTLED │ NONE          │ 216ms │
│ B0070  │ C059     │ Zverev vs Tsitsipas          │ SETTLED │ NONE          │ 246ms │
│ B0073  │ C007     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 228ms │
│ B0074  │ C024     │ Heat vs Knickss              │ SETTLED │ NONE          │ 256ms │
│ B0077  │ C091     │ West Ham vs Fullham          │ SETTLED │ NONE          │ 330ms │
│ B0079  │ C090     │ Djokvich vs Alcaraz          │ SETTLED │ MANUAL_REVIEW │ 231ms │
│ B0080  │ C083     │ Bucks vs 76ers               │ SETTLED │ NONE          │ 240ms │
│ B0083  │ C014     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 252ms │
│ B0084  │ C101     │ Real Madird vs Barselona     │ SETTLED │ NONE          │ 268ms │
│ B0085  │ C055     │ Murray vs Hurkacz            │ SETTLED │ NONE          │ 234ms │
│ B0089  │ C102     │ Bucks vs 76ers               │ SETTLED │ NONE          │ 261ms │
│ B0092  │ C135     │ Heat vs Knickss              │ SETTLED │ NONE          │ 226ms │
│ B0096  │ C076     │ Swiatekk vs Gauf             │ SETTLED │ NONE          │ 239ms │
│ B0097  │ C015     │ Atletico Madird vs Valeni... │ SETTLED │ NONE          │ 242ms │
│ B0098  │ C009     │ Warriros vs Suns             │ SETTLED │ NONE          │ 224ms │
│ B0099  │ C128     │ Mavs vs Nuggetts             │ SETTLED │ NONE          │ 232ms │
└────────┴──────────┴──────────────────────────────┴─────────┴───────────────┴───────┘

╭────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────╮
│ Found 34 matching bets.                                                                                                                     │
│ Total stake: £985.00.                                                                                                                       │
│ Average delay: 239ms.                                                                                                                       │
│                                                                                                                                             │
│ Evidence: [B0001, B0003, B0016, B0018, B0020, B0027, B0029, B0035, B0040, B0044]                                                            │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0001, B0003, B0016, B0018, B0020, B0027, B0029, B0035, B0040, B0044
Retrieved 34 bet(s) for context
(.venv) mojtabae@pool4-36-234 BetTrace % 
```