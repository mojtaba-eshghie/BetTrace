# Acceptance Test Questions 

This document contains 7 acceptance test questions for the Sportsbook RAG Assistant, covering:
- 2 bet-specific questions (single bet_id & two bets)
- 2 analytics-style questions (aggregations/ranking)
- 2 incident/ops questions (latency/suspensions)
- 1 Semantic search for teams/players

---


## Test 1: Bet-Specific — Single & Two Bets Rejection 

Add the `--show-context` at the end of all commands if you wish to view the summary of information added to the context before sending to the LLM.

```bash
python main.py ask "Why was bet B0004 rejected?" 
python main.py ask "Why were bets B0004 and B0022 rejected?" 
```

### Results for Test 1
```bash
% python main.py ask "Why was bet B0004 rejected?" 

Question: Why was bet B0004 rejected?

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary: 1 bet — Stake £30.00; Status: REJECTED; Incident: MARKET_SUSPENDED; Delay: 635ms.                                                                  │
│                                                                                                                                                             │
│ - B0004 (Customer C060): West Ham vs Fullham — Market: BTTS (No). Status: REJECTED. Incident: MARKET_SUSPENDED. Price delay: 635ms (above typical ~200ms    │
│ but below the 1000ms issue threshold).                                                                                                                      │
│                                                                                                                                                             │
│ Key insight: The bet was rejected due to the MARKET_SUSPENDED incident (the market was closed/suspended). The observed delay of 635ms is elevated compared  │
│ with normal latency but is below the >1000ms threshold that typically indicates major issues, so the primary cause is the market suspension.                │
│                                                                                                                                                             │
│ Evidence: [B0004]                                                                                                                                           │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0004
Retrieved 1 bet(s) for context

```

```bash
% python main.py ask "Why were bets B0004 and B0022 rejected?" 


Question: Why were bets B0004 and B0022 rejected?

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary: Both bets were REJECTED and the recorded incident for both is MARKET_SUSPENDED. Reported delays were 635ms and 839ms; stakes were £30.00 and       │
│ £15.00 respectively.                                                                                                                                        │
│                                                                                                                                                             │
│ - B0004 (Customer C060): West Ham vs Fullham, football — Status: REJECTED, Incident: MARKET_SUSPENDED, Delay: 635ms. The delay (635ms) is elevated relative │
│ to normal (~200ms) but below the 1000ms issue threshold.                                                                                                    │
│ - B0022 (Customer C105): Bulls vs Rapters, basketball — Status: REJECTED, Incident: MARKET_SUSPENDED, Delay: 839ms. The delay (839ms) is also elevated vs   │
│ normal but remains under 1000ms.                                                                                                                            │
│                                                                                                                                                             │
│ Patterns / observations:                                                                                                                                    │
│ - Both rejections share the same incident type: MARKET_SUSPENDED, indicating the market being closed/suspended was the reason for rejection in each case.   │
│ - Delays for both bets are higher than typical (~200ms) but do not cross the >1000ms threshold that normally signals severe latency issues. The common      │
│ factor is the market suspension rather than extreme latency.                                                                                                │
│ - Bets span different sports/markets (football BTTS → No, basketball Moneyline → Bulls), so the suspension appears not limited to one sport or market type. │
│                                                                                                                                                             │
│ Conclusion: The bets were rejected because the markets were suspended (incident = MARKET_SUSPENDED). Elevated latency was present but not at the >1000ms    │
│ level; the primary cause recorded is market suspension.                                                                                                     │
│                                                                                                                                                             │
│ Evidence: [B0004, B0022]                                                                                                                                    │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0004, B0022
Retrieved 2 bet(s) for context
```


## Test 2: Bet-Specific — High Latency Incident


```bash
python main.py ask "What happened with bet B0059? Explain the incident and latency." 
```

### Results for Test 2

```bash
 % python main.py ask "What happened with bet B0059? Explain the incident and latency." 

Question: What happened with bet B0059? Explain the incident and latency.

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary: There is 1 bet with a total stake of £10.00. It is SETTLED but experienced a LATENCY_SPIKE with a delay of 4648ms.                                 │
│                                                                                                                                                             │
│ - B0059 (Customer C076): Juvetus vs Interr, Asian Handicap → Away +0.5. Status: SETTLED. Incident: LATENCY_SPIKE. Delay: 4648ms — notably high (normal is   │
│ ~200ms; delays above 1000ms indicate issues).                                                                                                               │
│                                                                                                                                                             │
│ Notable observations:                                                                                                                                       │
│ - The bet was settled despite the severe latency (4648ms), so the wager was completed rather than voided or rejected.                                       │
│ - The LATENCY_SPIKE indicates a significant delay in price/market data for this event, which could have affected price freshness or customer experience.    │
│                                                                                                                                                             │
│ Evidence: [B0059]                                                                                                                                           │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0059
Retrieved 1 bet(s) for context
```

## Test 3: Analytics — Top Latency Ranking

```bash
python main.py ask "What happened with bet B0059? Explain the incident and latency." 
```

### Results for Test 3

```bash
% python main.py ask "What happened with bet B0059? Explain the incident and latency." 

Question: What happened with bet B0059? Explain the incident and latency.

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary (from computed facts):                                                                                                                              │
│ Bet B0059 — Customer C076, Stake £10.00, Sport: football, Event: Juvetus vs Interr, Market: Asian Handicap → Away +0.5. Status: SETTLED. Incident:          │
│ LATENCY_SPIKE. Delay: 4648ms.                                                                                                                               │
│                                                                                                                                                             │
│ List and description:                                                                                                                                       │
│ - B0059 (Customer C076): Juvetus vs Interr — Status: SETTLED, Incident: LATENCY_SPIKE, Delay: 4648ms — This delay is notably high (normal is ~200ms; above  │
│ 1000ms indicates issues), indicating a severe latency spike during this bet's pricing/placement.                                                            │
│                                                                                                                                                             │
│ Key insights:                                                                                                                                               │
│ - The bet experienced a severe latency event (4648ms) well above the 1000ms issue threshold, yet the bet was ultimately settled.                            │
│ - This is an anomaly worth reviewing for potential pricing integrity or customer-impact assessment given the magnitude of the delay.                        │
│                                                                                                                                                             │
│ Evidence: [B0059]                                                                                                                                           │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0059
Retrieved 1 bet(s) for context
```

## Test 4: Analytics — Customer Summary


```bash
python main.py ask "For customer C068, summarize all their bets and highlight any incidents." 
```

### Results for Test 4

```bash
% python main.py ask "For customer C068, summarize all their bets and highlight any incidents." 

Question: For customer C068, summarize all their bets and highlight any incidents.

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary (from computed facts)                                                                                                                               │
│ - Total Bets: 4                                                                                                                                             │
│ - Total Stake: £115.00                                                                                                                                      │
│ - Average Stake: £28.75                                                                                                                                     │
│ - Average Delay: 236ms                                                                                                                                      │
│ - Maximum Delay: 312ms                                                                                                                                      │
│ - Status Breakdown: {'SETTLED': 4}                                                                                                                          │
│                                                                                                                                                             │
│ Individual bets                                                                                                                                             │
│ - B0003 (Customer C068): PSG vs Marsielle. Status: SETTLED. Incident: NONE. Price Delay: 290ms — elevated above normal (~200ms).                            │
│ - B0018 (Customer C068): Brighton vs Wolvees. Status: SETTLED. Incident: NONE. Price Delay: 222ms — slightly above normal.                                  │
│ - B0019 (Customer C068): Man Citeh vs Brantford. Status: SETTLED. Incident: NONE. Price Delay: 121ms — within normal range.                                 │
│ - B0055 (Customer C068): Raducanu vs Pegulla. Status: SETTLED. Incident: NONE. Price Delay: 312ms — highest observed for this customer and elevated above   │
│ normal.                                                                                                                                                     │
│                                                                                                                                                             │
│ Patterns and notable observations                                                                                                                           │
│ - All 4 bets are SETTLED and none have incident flags (all Incident: NONE).                                                                                 │
│ - Latency: average delay is 236ms with a maximum of 312ms. While no delays exceed the 1000ms issue threshold, three bets show delays above the ~200ms       │
│ nominal level (B0003, B0018, B0055), with B0055 having the maximum delay.                                                                                   │
│ - Stakes are spread across football and tennis; stakes per bet range as shown in the records, contributing to the total stake of £115.00.                   │
│                                                                                                                                                             │
│ Key insights                                                                                                                                                │
│ - No operational incidents were recorded for customer C068’s activity; all bets completed normally.                                                         │
│ - Monitor bets with delays around 290–312ms (B0003, B0055) as they are elevated relative to the ~200ms norm, though not at issue levels.                    │
│                                                                                                                                                             │
│ Evidence: [B0003, B0018, B0019, B0055]                                                                                                                      │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0003, B0018, B0019, B0055
Retrieved 4 bet(s) for context

```


## Test 5: Incident/Ops — Latency Spike Impact

```bash
python main.py ask "Which customers were affected by LATENCY_SPIKE and how severely?" 
```


### Results for Test 5

```bash
% python main.py ask "Which customers were affected by LATENCY_SPIKE and how severely?" 

Question: Which customers were affected by LATENCY_SPIKE and how severely?

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary (from computed facts):                                                                                                                              │
│ • Total Bets: 7                                                                                                                                             │
│ • Total Stake: £190.00                                                                                                                                      │
│ • Average Stake: £27.14                                                                                                                                     │
│ • Unique Customers: 7                                                                                                                                       │
│ • Average Delay: 2583ms                                                                                                                                     │
│                                                                                                                                                             │
│ Status Breakdown (provided):                                                                                                                                │
│   • SETTLED: 80 bets, £2230.00                                                                                                                              │
│   • REJECTED: 8 bets, £220.00                                                                                                                               │
│   • PENDING: 7 bets, £180.00                                                                                                                                │
│   • VOID: 5 bets, £135.00                                                                                                                                   │
│                                                                                                                                                             │
│ List of affected bets and severity (each delay is above the 1000ms issue threshold):                                                                        │
│                                                                                                                                                             │
│ - B0023 (Customer C069): Bayern Munchen vs Dortmundd. Stake: £50.00. Status: PENDING. Incident: LATENCY_SPIKE. Delay: 1619ms — notably high.                │
│ - B0032 (Customer C120): Nadall vs Sinnner. Stake: £10.00. Status: PENDING. Incident: LATENCY_SPIKE. Delay: 2466ms — severe.                                │
│ - B0036 (Customer C122): Lakkers vs Celtcs. Stake: £25.00. Status: PENDING. Incident: LATENCY_SPIKE. Delay: 2431ms — severe.                                │
│ - B0038 (Customer C004): Murray vs Hurkacz. Stake: £50.00. Status: SETTLED. Incident: LATENCY_SPIKE. Delay: 2026ms — severe.                                │
│ - B0059 (Customer C076): Juvetus vs Interr. Stake: £10.00. Status: SETTLED. Incident: LATENCY_SPIKE. Delay: 4648ms — extremely high.                        │
│ - B0072 (Customer C055): Atletico Madird vs Valenica. Stake: £30.00. Status: SETTLED. Incident: LATENCY_SPIKE. Delay: 2273ms — severe.                      │
│ - B0090 (Customer C121): Nadall vs Sinnner. Stake: £15.00. Status: SETTLED. Incident: LATENCY_SPIKE. Delay: 2615ms — severe.                                │
│                                                                                                                                                             │
│ Patterns and notable observations:                                                                                                                          │
│ - All 7 affected customers experienced elevated delays (each individual delay exceeds the 1000ms issue threshold).                                          │
│ - Average Delay is 2583ms (computed), indicating the incident-wide latency was severe.                                                                      │
│ - There is a mix of PENDING and SETTLED outcomes among affected bets; stakes are varied (from £10.00 to £50.00), and each affected bet corresponds to a     │
│ distinct customer (Unique Customers: 7).                                                                                                                    │
│ - One particularly extreme case is B0059 (Customer C076) with 4648ms delay, suggesting a pronounced outlier in severity.                                    │
│                                                                                                                                                             │
│ Key insights:                                                                                                                                               │
│ - All identified customers were exposed to materially elevated price delays (average 2583ms), increasing the risk of stale prices or mismatched execution.  │
│ - Attention should be prioritized to bets like B0059 and others above ~2000ms for potential customer-impact reviews or remediation.                         │
│                                                                                                                                                             │
│ Evidence: [B0023, B0032, B0036, B0038, B0059, B0072, B0090]                                                                                                 │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0023, B0032, B0036, B0038, B0059, B0072, B0090
Retrieved 7 bet(s) for context
```


## Test 6: Incident/Ops — Feed Outage Analysis

```bash
python main.py ask "How many bets were voided due to FEED_OUTAGE? List them and explain." 
```

### Results for Test 6
```bash
% python main.py ask "How many bets were voided due to FEED_OUTAGE? List them and explain." 

Question: How many bets were voided due to FEED_OUTAGE? List them and explain.

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ There were 4 bets voided due to FEED_OUTAGE with a total stake of £95.00 (Average stake £23.75, Unique customers 4, Average delay 960ms).                   │
│                                                                                                                                                             │
│ - B0028 (Customer C022): Zverev vs Tsitsipas, tennis. Status: VOID, Incident: FEED_OUTAGE. Delay: 495ms — above typical (~200ms) but below the 1000ms issue │
│ threshold.                                                                                                                                                  │
│ - B0050 (Customer C106): Man Utd vs Newcatle, football. Status: VOID, Incident: FEED_OUTAGE. Delay: 1073ms — notably high (exceeds 1000ms).                 │
│ - B0066 (Customer C033): Warriros vs Suns, basketball. Status: VOID, Incident: FEED_OUTAGE. Delay: 1078ms — also elevated (exceeds 1000ms).                 │
│ - B0094 (Customer C011): Medvedev vs Runee, tennis. Status: VOID, Incident: FEED_OUTAGE. Delay: 1194ms — highest of the group (exceeds 1000ms).             │
│                                                                                                                                                             │
│ Patterns / notable observations:                                                                                                                            │
│ - Average delay across these voided bets is 960ms, close to the 1000ms issue threshold, indicating overall feed instability during these events.            │
│ - Three of four bets (B0050, B0066, B0094) had delays above 1000ms, directly signaling problematic feed performance; one bet (B0028) had a moderate delay   │
│ (495ms).                                                                                                                                                    │
│ - The voids affected multiple sports (tennis, football, basketball) and four unique customers, suggesting the outage was broad rather than isolated to a    │
│ single market or user.                                                                                                                                      │
│                                                                                                                                                             │
│ Key insight: These voids appear driven by a general FEED_OUTAGE with several instances exceeding the 1000ms threshold — remediation should focus on feed    │
│ stability across markets.                                                                                                                                   │
│                                                                                                                                                             │
│ Evidence: [B0028, B0050, B0066, B0094]                                                                                                                      │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0028, B0050, B0066, B0094
Retrieved 4 bet(s) for context

```


## Test 7: Semantic Search for Team/Players
```bash
python main.py ask "All bets involving Thundr" 
```

### Results for Test 7

```bash
% python main.py ask "All bets involving Thundr" 

Question: All bets involving Thundr

╭────────────────────────────────────────────────────────────────────────── Answer ───────────────────────────────────────────────────────────────────────────╮
│ Summary: Listed below are all bets involving the event "Clippers vs Thunderr". Aggregate counts or stake totals require computation.                        │
│                                                                                                                                                             │
│ B0043 — Customer C033 — Market: Spread — Selection: Home -3.5 — Stake: £25.00 — Status: REJECTED — Incident: MARKET_SUSPENDED — Price Delay: 374ms          │
│ B0100 — Customer C023 — Market: Spread — Selection: Away +3.5 — Stake: £25.00 — Status: SETTLED — Incident: NONE — Price Delay: 188ms                       │
│ B0010 — Customer C018 — Market: Moneyline — Selection: Clippers — Stake: £15.00 — Status: SETTLED — Incident: NONE — Price Delay: 159ms                     │
│ B0088 — Customer C027 — Market: Total Points O/U 215.5 — Selection: Over 215.5 — Stake: £15.00 — Status: REJECTED — Incident: MARKET_SUSPENDED — Price      │
│ Delay: 389ms                                                                                                                                                │
│ B0027 — Customer C104 — Market: Moneyline — Selection: Thunderr — Stake: £80.00 — Status: SETTLED — Incident: NONE — Price Delay: 204ms                     │
│ B0048 — Customer C006 — Market: Spread — Selection: Home -3.5 — Stake: £15.00 — Status: SETTLED — Incident: MANUAL_REVIEW — Price Delay: 467ms              │
│                                                                                                                                                             │
│ Evidence: [B0043, B0100, B0010, B0088, B0027, B0048]                                                                                                        │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Evidence: B0043, B0100, B0010, B0088, B0027, B0048
Retrieved 6 bet(s) for context
```





