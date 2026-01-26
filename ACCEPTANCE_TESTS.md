# Acceptance Test Questions & Expected Outputs

This document contains 6 acceptance test questions for the Sportsbook RAG Assistant, covering:
- 2 bet-specific questions (single bet_id)
- 2 analytics-style questions (aggregations/ranking)
- 2 incident/ops questions (latency/suspensions)

---

## Test 1: Bet-Specific — Single Bet Rejection

**Question:** `Why was bet B0004 rejected?`

**Expected Output:**
```
Bet B0004 was rejected due to a MARKET_SUSPENDED incident. The bet was a £30 BTTS 
(Both Teams To Score) wager on West Ham vs Fullham (football), with the selection 
being "No". The market was suspended at the time of bet placement, which 
automatically triggers rejection. The price delay was 635ms, above the normal 
~200ms average.

Evidence: B0004
```

**Retrieved Context:**
| Bet ID | Customer | Sport    | Event               | Status   | Incident         | Delay |
|--------|----------|----------|---------------------|----------|------------------|-------|
| B0004  | C060     | football | West Ham vs Fullham | REJECTED | MARKET_SUSPENDED | 635ms |

**Key Validation Points:**
- Correctly identifies B0004
- Explains MARKET_SUSPENDED as the rejection reason
- Notes the elevated latency (635ms)

---

## Test 2: Bet-Specific — High Latency Incident

**Question:** `What happened with bet B0059? Explain the incident and latency.`

**Expected Output:**
```
Bet B0059 experienced the highest latency in the system at 4648ms (nearly 5 seconds), 
tagged as a LATENCY_SPIKE incident. This is a £10 Asian Handicap bet on Juvetus vs 
Interr (football) with selection "Away +0.5". Despite the extreme latency, the bet 
was SETTLED successfully. The delay of 4648ms is approximately 23x the normal 
average of ~200ms, indicating severe pricing degradation at the time.

Evidence: B0059
```

**Retrieved Context:**
| Bet ID | Customer | Sport    | Event           | Status  | Incident      | Delay  |
|--------|----------|----------|-----------------|---------|---------------|--------|
| B0059  | C076     | football | Juvetus vs Interr | SETTLED | LATENCY_SPIKE | 4648ms |

**Key Validation Points:**
- Identifies B0059 as highest latency bet
- Notes 4648ms delay
- Explains LATENCY_SPIKE incident
- Notes the bet still settled despite issues

---

## Test 3: Analytics — Top Latency Ranking

**Question:** `Find the top 5 highest price_delay_ms bets and summarize what happened.`

**Expected Output:**
```
The top 5 highest price_delay_ms bets are:

1. B0059 — 4648ms (Juvetus vs Interr, football) - SETTLED
2. B0090 — 2615ms (Nadall vs Sinnner, tennis) - SETTLED  
3. B0032 — 2466ms (Nadall vs Sinnner, tennis) - PENDING
4. B0036 — 2431ms (Lakkers vs Celtcs, basketball) - PENDING
5. B0072 — 2273ms (Atletico Madird vs Valenica, football) - SETTLED

Summary:
- All 5 bets have LATENCY_SPIKE incidents, with delays 10-23x above normal (~200ms)
- 3 bets settled successfully despite the latency issues
- 2 bets remain PENDING, possibly still being processed or under review
- Total stake across these bets: £115
- Sports affected: football (2), tennis (2), basketball (1)

Evidence: B0059, B0090, B0032, B0036, B0072
```

**Key Validation Points:**
- Returns exactly 5 bets
- Correctly ordered by price_delay_ms descending
- All have LATENCY_SPIKE incidents
- Includes aggregated insights

---

## Test 4: Analytics — Customer Summary

**Question:** `For customer C068, summarize all their bets and highlight any incidents.`

**Expected Output:**
```
Customer C068 has placed 4 bets, all of which have been SETTLED with no incidents:

1. B0003 — £40 Asian Handicap on PSG vs Marsielle (football), Home -0.5, 290ms delay
2. B0018 — £15 Match Winner on Brighton vs Wolvees (football), Brighton, 222ms delay
3. B0019 — £20 Over/Under 2.5 on Man Citeh vs Brantford (football), Under 2.5, 121ms delay
4. B0055 — £40 Total Games O/U 21.5 on Raducanu vs Pegulla (tennis), Over 21.5, 312ms delay

Summary:
- Total stake: £115
- All bets settled successfully
- No incidents (all tagged NONE)
- Average latency: 236ms (within normal range)
- Sports: football (3), tennis (1)

This customer has a clean betting history with no operational issues.

Evidence: B0003, B0018, B0019, B0055
```

**Key Validation Points:**
- Finds all 4 bets for C068
- Notes all SETTLED with NONE incidents
- Calculates correct totals
- Highlights the absence of issues

---

## Test 5: Incident/Ops — Latency Spike Impact

**Question:** `Which customers were affected by LATENCY_SPIKE and how severely?`

**Expected Output:**
```
7 customers were affected by LATENCY_SPIKE incidents:

| Customer | Bet ID | Delay (ms) | Status  | Severity |
|----------|--------|------------|---------|----------|
| C076     | B0059  | 4648       | SETTLED | Critical |
| C121     | B0090  | 2615       | SETTLED | High     |
| C120     | B0032  | 2466       | PENDING | High     |
| C122     | B0036  | 2431       | PENDING | High     |
| C055     | B0072  | 2273       | SETTLED | High     |
| C004     | B0038  | 2026       | SETTLED | High     |
| C069     | B0023  | 1619       | PENDING | Moderate |

Summary:
- Each customer was affected by 1 LATENCY_SPIKE bet
- C076 experienced the most severe impact (4648ms delay)
- 4 customers had bets settle despite latency; 3 remain pending
- Average delay across affected bets: 2583ms (~13x normal)
- Total stake at risk: £190

Evidence: B0059, B0090, B0032, B0036, B0072, B0038, B0023
```

**Key Validation Points:**
- Identifies all 7 LATENCY_SPIKE bets
- Lists all 7 affected customers
- Ranks by severity (delay)
- Notes pending vs settled status

---

## Test 6: Incident/Ops — Feed Outage Analysis

**Question:** `How many bets were voided due to FEED_OUTAGE? List them and explain.`

**Expected Output:**
```
4 bets were voided with FEED_OUTAGE incidents:

1. B0094 — £50 Total Games O/U 21.5 on Medvedev vs Runee (tennis)
   - Delay: 1194ms, Status: VOID
   
2. B0066 — £20 Moneyline on Warriros vs Suns (basketball)  
   - Delay: 1078ms, Status: VOID
   
3. B0050 — £5 BTTS on Man Utd vs Newcatle (football)
   - Delay: 1073ms, Status: VOID
   
4. B0028 — £20 Match Winner on Zverev vs Tsitsipas (tennis)
   - Delay: 495ms, Status: VOID

Explanation:
FEED_OUTAGE indicates the pricing data feed was unavailable or unreliable. When 
this occurs, bets cannot be fairly priced or settled, so they are voided to 
protect both the customer and the platform. All 4 bets show elevated latency 
(495-1194ms), confirming feed issues at the time.

Total voided stake: £95
Customers affected: C011, C033, C106, C022

Note: There is 1 additional VOID bet (B0025) with incident_tag NONE, which was 
likely voided for a different reason.

Evidence: B0094, B0066, B0050, B0028
```

**Key Validation Points:**
- Identifies all 4 FEED_OUTAGE + VOID bets
- Explains the relationship between FEED_OUTAGE and VOID
- Notes the elevated latencies
- Correctly excludes B0025 (VOID but NONE incident)

---

## Running the Tests

```bash
# Run all 6 acceptance tests
python run_acceptance_tests.py

# Save results to markdown file
python run_acceptance_tests.py --output acceptance_results.md

# Or run individual questions via CLI
python main.py ask "Why was bet B0004 rejected?"
python main.py ask "What happened with bet B0059?"
python main.py ask "Find the top 5 highest price_delay_ms bets and summarize"
python main.py ask "For customer C068, summarize all their bets"
python main.py ask "Which customers were affected by LATENCY_SPIKE?"
python main.py ask "How many bets were voided due to FEED_OUTAGE?"
```

---

## Validation Criteria

| Test | Category | Key Elements to Check |
|------|----------|----------------------|
| 1 | Bet-Specific | B0004, REJECTED, MARKET_SUSPENDED |
| 2 | Bet-Specific | B0059, 4648ms, LATENCY_SPIKE, SETTLED |
| 3 | Analytics | Top 5 bet IDs in correct order, all LATENCY_SPIKE |
| 4 | Analytics | All 4 C068 bets, NONE incidents, £115 total |
| 5 | Incident/Ops | 7 customers, 7 bets, delay ranking |
| 6 | Incident/Ops | 4 VOID+FEED_OUTAGE bets, excludes B0025 |
