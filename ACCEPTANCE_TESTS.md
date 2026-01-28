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
