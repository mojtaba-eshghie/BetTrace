```sh
(.venv) mojtabae@pool4-36-234 fdjtask % python main.py ask "What is the total stake and count for all SETTLED bets?" --show-context

Question: What is the total stake and count for all SETTLED bets?

SQL Statistics (authoritative):
=== COMPLETE STATUS STATISTICS (from database) ===
Status: SETTLED
Total Bets: 80
Unique Customers: 57
Total Stake: £2230.00
Average Stake: £27.88
Average Delay: 334ms
Incident Breakdown: {'LATENCY_SPIKE': 4, 'MANUAL_REVIEW': 5, 'NONE': 71}

Retrieved Bets (80 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event                        ┃ Status  ┃ Incident      ┃ Delay  ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ B0001  │ C029     │ PSG vs Marsielle             │ SETTLED │ NONE          │ 214ms  │
│ B0002  │ C140     │ Rybakina vs Sabalnka         │ SETTLED │ MANUAL_REVIEW │ 578ms  │
│ B0003  │ C068     │ PSG vs Marsielle             │ SETTLED │ NONE          │ 290ms  │
│ B0005  │ C098     │ Rybakina vs Sabalnka         │ SETTLED │ NONE          │ 46ms   │
│ B0006  │ C128     │ Murray vs Hurkacz            │ SETTLED │ MANUAL_REVIEW │ 198ms  │
│ B0008  │ C069     │ Bucks vs 76ers               │ SETTLED │ NONE          │ 80ms   │
│ B0009  │ C051     │ Brighton vs Wolvees          │ SETTLED │ NONE          │ 99ms   │
│ B0010  │ C018     │ Clippers vs Thunderr         │ SETTLED │ NONE          │ 159ms  │
│ B0011  │ C096     │ Murray vs Hurkacz            │ SETTLED │ NONE          │ 179ms  │
│ B0012  │ C019     │ Warriros vs Suns             │ SETTLED │ NONE          │ 94ms   │
│ B0013  │ C014     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 87ms   │
│ B0014  │ C026     │ Atletico Madird vs Valeni... │ SETTLED │ NONE          │ 191ms  │
│ B0015  │ C117     │ Raducanu vs Pegulla          │ SETTLED │ NONE          │ 76ms   │
│ B0016  │ C015     │ Lakkers vs Celtcs            │ SETTLED │ NONE          │ 253ms  │
│ B0018  │ C068     │ Brighton vs Wolvees          │ SETTLED │ NONE          │ 222ms  │
│ B0019  │ C068     │ Man Citeh vs Brantford       │ SETTLED │ NONE          │ 121ms  │
│ B0020  │ C071     │ Chealsea vs Arsenel          │ SETTLED │ NONE          │ 248ms  │
│ B0021  │ C095     │ Heat vs Knickss              │ SETTLED │ NONE          │ 102ms  │
│ B0026  │ C032     │ Bucks vs 76ers               │ SETTLED │ NONE          │ 186ms  │
│ B0027  │ C104     │ Clippers vs Thunderr         │ SETTLED │ NONE          │ 204ms  │
│ B0029  │ C127     │ Rybakina vs Sabalnka         │ SETTLED │ NONE          │ 203ms  │
│ B0030  │ C136     │ Heat vs Knickss              │ SETTLED │ NONE          │ 186ms  │
│ B0031  │ C062     │ Murray vs Hurkacz            │ SETTLED │ NONE          │ 157ms  │
│ B0033  │ C057     │ Rybakina vs Sabalnka         │ SETTLED │ NONE          │ 163ms  │
│ B0034  │ C007     │ Atletico Madird vs Valeni... │ SETTLED │ NONE          │ 156ms  │
│ B0035  │ C021     │ Nadall vs Sinnner            │ SETTLED │ NONE          │ 208ms  │
│ B0037  │ C097     │ Rybakina vs Sabalnka         │ SETTLED │ NONE          │ 178ms  │
│ B0038  │ C004     │ Murray vs Hurkacz            │ SETTLED │ LATENCY_SPIKE │ 2026ms │
│ B0039  │ C069     │ Rybakina vs Sabalnka         │ SETTLED │ NONE          │ 98ms   │
│ B0040  │ C072     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 235ms  │
│ B0041  │ C063     │ Zverev vs Tsitsipas          │ SETTLED │ NONE          │ 81ms   │
│ B0042  │ C048     │ Man Utd vs Newcatle          │ SETTLED │ NONE          │ 110ms  │
│ B0044  │ C014     │ Liverpol vs Spurs            │ SETTLED │ NONE          │ 213ms  │
│ B0045  │ C079     │ Heat vs Knickss              │ SETTLED │ NONE          │ 125ms  │
│ B0046  │ C009     │ Aston Villla vs Evertoon     │ SETTLED │ NONE          │ 93ms   │
│ B0047  │ C043     │ Medvedev vs Runee            │ SETTLED │ NONE          │ 67ms   │
│ B0048  │ C006     │ Clippers vs Thunderr         │ SETTLED │ MANUAL_REVIEW │ 467ms  │
│ B0049  │ C027     │ Brighton vs Wolvees          │ SETTLED │ NONE          │ 216ms  │
│ B0051  │ C041     │ Nadall vs Sinnner            │ SETTLED │ NONE          │ 200ms  │
│ B0053  │ C126     │ Nottm Forst vs Burnley       │ SETTLED │ NONE          │ 235ms  │
│ B0054  │ C098     │ Djokvich vs Alcaraz          │ SETTLED │ NONE          │ 247ms  │
│ B0055  │ C068     │ Raducanu vs Pegulla          │ SETTLED │ NONE          │ 312ms  │
│ B0056  │ C059     │ Lakkers vs Celtcs            │ SETTLED │ NONE          │ 117ms  │
│ B0057  │ C106     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 203ms  │
│ B0059  │ C076     │ Juvetus vs Interr            │ SETTLED │ LATENCY_SPIKE │ 4648ms │
│ B0060  │ C036     │ Lakkers vs Celtcs            │ SETTLED │ NONE          │ 105ms  │
│ B0061  │ C094     │ Heat vs Knickss              │ SETTLED │ MANUAL_REVIEW │ 457ms  │
│ B0062  │ C102     │ Bucks vs 76ers               │ SETTLED │ NONE          │ 120ms  │
│ B0063  │ C084     │ Warriros vs Suns             │ SETTLED │ NONE          │ 239ms  │
│ B0064  │ C095     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 192ms  │
│ B0065  │ C026     │ Bucks vs 76ers               │ SETTLED │ NONE          │ 190ms  │
│ B0067  │ C034     │ Brighton vs Wolvees          │ SETTLED │ NONE          │ 253ms  │
│ B0068  │ C057     │ Lakkers vs Celtcs            │ SETTLED │ NONE          │ 216ms  │
│ B0069  │ C071     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 449ms  │
│ B0070  │ C059     │ Zverev vs Tsitsipas          │ SETTLED │ NONE          │ 246ms  │
│ B0072  │ C055     │ Atletico Madird vs Valeni... │ SETTLED │ LATENCY_SPIKE │ 2273ms │
│ B0073  │ C007     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 228ms  │
│ B0074  │ C024     │ Heat vs Knickss              │ SETTLED │ NONE          │ 256ms  │
│ B0075  │ C070     │ Raducanu vs Pegulla          │ SETTLED │ NONE          │ 129ms  │
│ B0076  │ C015     │ Man Utd vs Newcatle          │ SETTLED │ NONE          │ 195ms  │
│ B0077  │ C091     │ West Ham vs Fullham          │ SETTLED │ NONE          │ 330ms  │
│ B0078  │ C093     │ West Ham vs Fullham          │ SETTLED │ NONE          │ 193ms  │
│ B0079  │ C090     │ Djokvich vs Alcaraz          │ SETTLED │ MANUAL_REVIEW │ 231ms  │
│ B0080  │ C083     │ Bucks vs 76ers               │ SETTLED │ NONE          │ 240ms  │
│ B0081  │ C024     │ Heat vs Knickss              │ SETTLED │ NONE          │ 146ms  │
│ B0083  │ C014     │ Bulls vs Rapters             │ SETTLED │ NONE          │ 252ms  │
│ B0084  │ C101     │ Real Madird vs Barselona     │ SETTLED │ NONE          │ 268ms  │
│ B0085  │ C055     │ Murray vs Hurkacz            │ SETTLED │ NONE          │ 234ms  │
│ B0086  │ C034     │ Mavs vs Nuggetts             │ SETTLED │ NONE          │ 40ms   │
│ B0087  │ C121     │ Brighton vs Wolvees          │ SETTLED │ NONE          │ 92ms   │
│ B0089  │ C102     │ Bucks vs 76ers               │ SETTLED │ NONE          │ 261ms  │
│ B0090  │ C121     │ Nadall vs Sinnner            │ SETTLED │ LATENCY_SPIKE │ 2615ms │
│ B0091  │ C118     │ Man Citeh vs Brantford       │ SETTLED │ NONE          │ 184ms  │
│ B0092  │ C135     │ Heat vs Knickss              │ SETTLED │ NONE          │ 226ms  │
│ B0095  │ C103     │ Mavs vs Nuggetts             │ SETTLED │ NONE          │ 165ms  │
│ B0096  │ C076     │ Swiatekk vs Gauf             │ SETTLED │ NONE          │ 239ms  │
│ B0097  │ C015     │ Atletico Madird vs Valeni... │ SETTLED │ NONE          │ 242ms  │
│ B0098  │ C009     │ Warriros vs Suns             │ SETTLED │ NONE          │ 224ms  │
│ B0099  │ C128     │ Mavs vs Nuggetts             │ SETTLED │ NONE          │ 232ms  │
│ B0100  │ C023     │ Clippers vs Thunderr         │ SETTLED │ NONE          │ 188ms  │
└────────┴──────────┴──────────────────────────────┴─────────┴───────────────┴────────┘

╭─────────────────────────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────────────────────────╮
│ Based on the database statistics:                                                                                                                                                                    │
│                                                                                                                                                                                                      │
│ • Status: SETTLED                                                                                                                                                                                    │
│ • Total Bets: 80                                                                                                                                                                                     │
│ • Unique Customers: 57                                                                                                                                                                               │
│ • Total Stake: £2230.00                                                                                                                                                                              │
│ • Average Stake: £27.88                                                                                                                                                                              │
│ • Average Delay: 334ms                                                                                                                                                                               │
│ • Incident Breakdown: {'LATENCY_SPIKE': 4, 'MANUAL_REVIEW': 5, 'NONE': 71}                                                                                                                           │
│                                                                                                                                                                                                      │
│ This covers 80 bet(s). Sample: B0001, B0002, B0003, B0005, B0006, B0008, B0009, B0010, B0011, B0012                                                                                                  │
│                                                                                                                                                                                                      │
│ Evidence: B0001, B0002, B0003, B0005, B0006, B0008, B0009, B0010, B0011, B0012                                                                                                                       │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0001, B0002, B0003, B0005, B0006, B0008, B0009, B0010, B0011, B0012
Retrieved 80 bet(s) for context
(.venv) mojtabae@pool4-36-234 fdjtask % python main.py ask "What is the exact total stake for customer C014?" --show-context

Question: What is the exact total stake for customer C014?

SQL Statistics (authoritative):
=== COMPLETE CUSTOMER STATISTICS (from database) ===
Customer: C014
Total Bets: 3
Total Stake: £80.00
Average Stake: £26.67
Average Delay: 184ms
Delay Range: 87ms - 252ms
Status Breakdown: {'SETTLED': 3}
Incident Breakdown: {'NONE': 3}
Sport Breakdown: {'basketball': 2, 'football': 1}

Retrieved Bets (3 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event             ┃ Status  ┃ Incident ┃ Delay ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━┩
│ B0013  │ C014     │ Bulls vs Rapters  │ SETTLED │ NONE     │ 87ms  │
│ B0044  │ C014     │ Liverpol vs Spurs │ SETTLED │ NONE     │ 213ms │
│ B0083  │ C014     │ Bulls vs Rapters  │ SETTLED │ NONE     │ 252ms │
└────────┴──────────┴───────────────────┴─────────┴──────────┴───────┘

╭─────────────────────────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────────────────────────╮
│ The exact total stake for customer C014 is £80.00.                                                                                                                                                   │
│                                                                                                                                                                                                      │
│ Evidence from bets:                                                                                                                                                                                  │
│ - B0013: £30.00                                                                                                                                                                                      │
│ - B0044: £10.00                                                                                                                                                                                      │
│ - B0083: £40.00                                                                                                                                                                                      │
│                                                                                                                                                                                                      │
│ Total = £80.00                                                                                                                                                                                       │
│                                                                                                                                                                                                      │
│ Evidence: [B0013, B0044, B0083]                                                                                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0013, B0044, B0083
Retrieved 3 bet(s) for context
(.venv) mojtabae@pool4-36-234 fdjtask % python main.py ask "What is the total stake at risk from LATENCY_SPIKE incidents?" --show-context

Question: What is the total stake at risk from LATENCY_SPIKE incidents?

SQL Statistics (authoritative):
=== COMPLETE INCIDENT STATISTICS (from database) ===
Incident Type: LATENCY_SPIKE
Total Bets Affected: 7
Unique Customers Affected: 7
Total Stake at Risk: £190.00
Average Stake: £27.14
Average Delay: 2583ms
Delay Range: 1619ms - 4648ms
Status Breakdown: {'PENDING': 3, 'SETTLED': 4}

Customers Ranked by Impact:
  1. C076: 1 bet(s), max delay 4648ms
  2. C121: 1 bet(s), max delay 2615ms
  3. C120: 1 bet(s), max delay 2466ms
  4. C122: 1 bet(s), max delay 2431ms
  5. C055: 1 bet(s), max delay 2273ms
  6. C004: 1 bet(s), max delay 2026ms
  7. C069: 1 bet(s), max delay 1619ms

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

╭─────────────────────────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────────────────────────╮
│ Based on the database statistics:                                                                                                                                                                    │
│                                                                                                                                                                                                      │
│ • Incident Type: LATENCY_SPIKE                                                                                                                                                                       │
│ • Total Bets Affected: 7                                                                                                                                                                             │
│ • Unique Customers Affected: 7                                                                                                                                                                       │
│ • Total Stake at Risk: £190.00                                                                                                                                                                       │
│ • Average Stake: £27.14                                                                                                                                                                              │
│ • Average Delay: 2583ms                                                                                                                                                                              │
│ • Delay Range: 1619ms - 4648ms                                                                                                                                                                       │
│ • Status Breakdown: {'PENDING': 3, 'SETTLED': 4}                                                                                                                                                     │
│ • Customers Ranked by Impact:                                                                                                                                                                        │
│ • 1. C076: 1 bet(s), max delay 4648ms                                                                                                                                                                │
│                                                                                                                                                                                                      │
│ This covers 7 bet(s): B0023, B0032, B0036, B0038, B0059, B0072, B0090                                                                                                                                │
│                                                                                                                                                                                                      │
│ Evidence: B0023, B0032, B0036, B0038, B0059, B0072, B0090                                                                                                                                            │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0023, B0032, B0036, B0038, B0059, B0072, B0090
Retrieved 7 bet(s) for context
(.venv) mojtabae@pool4-36-234 fdjtask % 
```



```sh
(.venv) mojtabae@pool4-36-234 fdjtask % python main.py ask "Compare bets B0001 and B0002" --show-context

Question: Compare bets B0001 and B0002

Retrieved Bets (2 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event                ┃ Status  ┃ Incident      ┃ Delay ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━┩
│ B0001  │ C029     │ PSG vs Marsielle     │ SETTLED │ NONE          │ 214ms │
│ B0002  │ C140     │ Rybakina vs Sabalnka │ SETTLED │ MANUAL_REVIEW │ 578ms │
└────────┴──────────┴──────────────────────┴─────────┴───────────────┴───────┘

╭─────────────────────────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────────────────────────╮
│ Direct answer: Both bets were settled, but they differ by sport, market, stake, customer, incident tag, and latency. Evidence: [B0001, B0002]                                                        │
│                                                                                                                                                                                                      │
│ Relevant details:                                                                                                                                                                                    │
│ - B0001: Customer C029, football (PSG vs Marsielle), Market BTTS, Selection Yes, Stake £10.0, Status SETTLED, Incident NONE, Price Delay 214ms. Evidence: [B0001]                                    │
│ - B0002: Customer C140, tennis (Rybakina vs Sabalnka), Market Set 1 Winner, Selection Sabalnka, Stake £5.0, Status SETTLED, Incident MANUAL_REVIEW, Price Delay 578ms. Evidence: [B0002]             │
│                                                                                                                                                                                                      │
│ Operational notes:                                                                                                                                                                                   │
│ - Both bets reached final status (SETTLED) per the records [B0001, B0002].                                                                                                                           │
│ - Incident comparison: B0001 had no incident (NONE) while B0002 was flagged MANUAL_REVIEW, indicating it was subject to review during processing [B0002].                                            │
│ - Latency comparison: B0001’s price delay (214ms) is very close to normal (~200ms) [B0001]; B0002’s delay (578ms) is elevated relative to normal and may have contributed to the manual review       │
│ consideration [B0002].                                                                                                                                                                               │
│                                                                                                                                                                                                      │
│ Evidence: [B0001, B0002]                                                                                                                                                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0001, B0002
Retrieved 2 bet(s) for context
(.venv) mojtabae@pool4-36-234 fdjtask % 
```




```bash
(.venv) mojtabae@MBP2023A BetTrace % python main.py ask "How many bets are there?" --show-context       

Question: How many bets are there?

SQL Statistics (authoritative):
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Overall Statistics (All Bets)

• Total Bets: 100
• Total Stake: £2765.00
• Average Stake: £27.65
• Unique Customers: 69
• Average Delay: 427ms

Status Breakdown:
  • SETTLED: 80 bets, £2230.00 total
  • REJECTED: 8 bets, £220.00 total
  • PENDING: 7 bets, £180.00 total
  • VOID: 5 bets, £135.00 total

Incident Breakdown:
  • NONE: 75 bets
  • MARKET_SUSPENDED: 8 bets
  • LATENCY_SPIKE: 7 bets
  • MANUAL_REVIEW: 6 bets
  • FEED_OUTAGE: 4 bets

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================
Retrieved Bets (3 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event                ┃ Status  ┃ Incident      ┃ Delay ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━┩
│ B0001  │ C029     │ PSG vs Marsielle     │ SETTLED │ NONE          │ 214ms │
│ B0002  │ C140     │ Rybakina vs Sabalnka │ SETTLED │ MANUAL_REVIEW │ 578ms │
│ B0003  │ C068     │ PSG vs Marsielle     │ SETTLED │ NONE          │ 290ms │
└────────┴──────────┴──────────────────────┴─────────┴───────────────┴───────┘

╭────────────────────────────────────────────────────────────────── Answer ──────────────────────────────────────────────────────────────────╮
│ There are 100 bets. Evidence: [B0001, B0002, B0003]                                                                                        │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0001, B0002, B0003
Retrieved 3 bet(s) for context
(.venv) mojtabae@MBP2023A BetTrace % python main.py ask "Give me an overview of all bets" --show-context

Question: Give me an overview of all bets

SQL Statistics (authoritative):
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Overall Statistics (All Bets)

• Total Bets: 100
• Total Stake: £2765.00
• Average Stake: £27.65
• Unique Customers: 69
• Average Delay: 427ms

Status Breakdown:
  • SETTLED: 80 bets, £2230.00 total
  • REJECTED: 8 bets, £220.00 total
  • PENDING: 7 bets, £180.00 total
  • VOID: 5 bets, £135.00 total

Incident Breakdown:
  • NONE: 75 bets
  • MARKET_SUSPENDED: 8 bets
  • LATENCY_SPIKE: 7 bets
  • MANUAL_REVIEW: 6 bets
  • FEED_OUTAGE: 4 bets

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================
Retrieved Bets (3 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event                ┃ Status  ┃ Incident      ┃ Delay ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━┩
│ B0001  │ C029     │ PSG vs Marsielle     │ SETTLED │ NONE          │ 214ms │
│ B0002  │ C140     │ Rybakina vs Sabalnka │ SETTLED │ MANUAL_REVIEW │ 578ms │
│ B0003  │ C068     │ PSG vs Marsielle     │ SETTLED │ NONE          │ 290ms │
└────────┴──────────┴──────────────────────┴─────────┴───────────────┴───────┘

╭────────────────────────────────────────────────────────────────── Answer ──────────────────────────────────────────────────────────────────╮
│ There are 100 bets with a total stake of £2765.00, average stake £27.65, 69 unique customers, and average delay 427ms; status breakdown:   │
│ SETTLED 80 bets (£2230.00), REJECTED 8 bets (£220.00), PENDING 7 bets (£180.00), VOID 5 bets (£135.00); incident breakdown: NONE 75,       │
│ MARKET_SUSPENDED 8, LATENCY_SPIKE 7, MANUAL_REVIEW 6, FEED_OUTAGE 4. Evidence: [B0001, B0002, B0003]                                       │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0001, B0002, B0003
Retrieved 3 bet(s) for context
(.venv) mojtabae@MBP2023A BetTrace % 
```



```bash
(.venv) mojtabae@MBP2023A BetTrace % python main.py ask "Show me REJECTED bets" --show-context

Question: Show me REJECTED bets

SQL Statistics (authoritative):
============================================================
COMPUTED FACTS (pre-calculated, DO NOT recalculate)
============================================================
Status: REJECTED

• Total Bets: 8
• Unique Customers: 8
• Total Stake: £220.00
• Average Stake: £27.50
• Average Delay: 536ms
• Incident Breakdown: {'MARKET_SUSPENDED': 8}

⚠️ USE THESE EXACT VALUES - DO NOT RECALCULATE
============================================================
Retrieved Bets (8 shown):
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Bet ID ┃ Customer ┃ Event                ┃ Status   ┃ Incident         ┃ Delay ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ B0004  │ C060     │ West Ham vs Fullham  │ REJECTED │ MARKET_SUSPENDED │ 635ms │
│ B0007  │ C040     │ Warriros vs Suns     │ REJECTED │ MARKET_SUSPENDED │ 146ms │
│ B0022  │ C105     │ Bulls vs Rapters     │ REJECTED │ MARKET_SUSPENDED │ 839ms │
│ B0043  │ C033     │ Clippers vs Thunderr │ REJECTED │ MARKET_SUSPENDED │ 374ms │
│ B0052  │ C063     │ Djokvich vs Alcaraz  │ REJECTED │ MARKET_SUSPENDED │ 618ms │
│ B0071  │ C096     │ Leeds vs Sheff Utd   │ REJECTED │ MARKET_SUSPENDED │ 689ms │
│ B0082  │ C088     │ Lakkers vs Celtcs    │ REJECTED │ MARKET_SUSPENDED │ 601ms │
│ B0088  │ C027     │ Clippers vs Thunderr │ REJECTED │ MARKET_SUSPENDED │ 389ms │
└────────┴──────────┴──────────────────────┴──────────┴──────────────────┴───────┘

╭────────────────────────────────────────────────────────────────── Answer ──────────────────────────────────────────────────────────────────╮
│ There are 8 REJECTED bets (Unique Customers: 8; Total Stake: £220.00; Average Stake: £27.50; Average Delay: 536ms; Incident Breakdown:     │
│ {'MARKET_SUSPENDED': 8}). Evidence: [B0004, B0007, B0022]                                                                                  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0004, B0007, B0022
Retrieved 8 bet(s) for context
(.venv) mojtabae@MBP2023A BetTrace % 
```





```bash
(.venv) BetTrace % python main.py ask "Show customer C929 bets" --show-context



Question: Show customer C929 bets

╭───────────────────────────────────────────────────────────────────────────── Answer ──────────────────────────────────────────────────────────────────────────────╮
│ I couldn't find any relevant bet records for your query. Please provide a specific bet_id (e.g., B0042) or customer_id (e.g., C068) to look up, or ask about      │
│ specific incidents like LATENCY_SPIKE or MARKET_SUSPENDED.                                                                                                        │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
Retrieved 0 bet(s) for context

⚠ The answer may be incomplete due to insufficient evidence.


(.venv) mojtabae@pool4-36-234 BetTrace % python main.py ask "Show customer C0029 bets"

Question: Show customer C0029 bets

╭───────────────────────────────────────────────────────────────────────────── Answer ──────────────────────────────────────────────────────────────────────────────╮
│ You asked for C0029 — I have records for customer C029 (assuming that's the intended customer).                                                                   │
│                                                                                                                                                                   │
│ Computed facts for Customer: C029 — Total Bets: 1; Total Stake: £10.00; Average Stake: £10.00; Average Delay: 214ms; Maximum Delay: 214ms; Status Breakdown:      │
│ {'SETTLED': 1}.                                                                                                                                                   │
│                                                                                                                                                                   │
│ Bet:                                                                                                                                                              │
│ • Bet ID: B0001 — Sport: football; Event: PSG vs Marsielle; Market: BTTS; Selection: Yes; Stake: £10.00; Status: SETTLED; Incident: NONE; Price Delay: 214ms.     │
│                                                                                                                                                                   │
│ Evidence: [B0001]                                                                                                                                                 │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0001
Retrieved 1 bet(s) for context


```


