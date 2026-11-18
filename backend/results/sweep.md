# Threshold sweep

100 labelled questions (60 paraphrases, 40 that must NOT hit), 30 FAQs, 90 stored phrasings.
Measured lookup (embed + search): 20.3 ms. LLM latency assumed: 1500 ms.

## Main config: multiple phrasings per FAQ + negation guard

| threshold | hit rate % | false hits | served from cache % | avg latency ms | EN hit % | Hinglish hit % |
|---|---|---|---|---|---|---|
| 0.50 | 51.7 | 27 | 58.0 | 650.3 | 70.0 | 33.3 |
| 0.55 | 46.7 | 24 | 52.0 | 740.3 | 63.3 | 30.0 |
| 0.60 | 36.7 | 22 | 44.0 | 860.3 | 50.0 | 23.3 |
| 0.65 | 33.3 | 16 | 36.0 | 980.3 | 43.3 | 23.3 |
| 0.70 | 26.7 | 14 | 30.0 | 1070.3 | 30.0 | 23.3 |
| 0.75 | 16.7 | 10 | 20.0 | 1220.3 | 16.7 | 16.7 |
| 0.80 | 10.0 | 1 | 7.0 | 1415.3 | 6.7 | 13.3 |
| 0.85 | 5.0 | 0 | 3.0 | 1475.3 | 6.7 | 3.3 |
| 0.90 | 1.7 | 0 | 1.0 | 1505.3 | 3.3 | 0.0 |
| 0.95 | 0.0 | 0 | 0.0 | 1520.3 | 0.0 | 0.0 |

**Chosen threshold: 0.85** (best hit rate with 0 false hits): hit rate 5.0%, LLM calls down 3.0%, avg latency 1500 ms -> 1475.3 ms.

## Ablation at each config's own best threshold

| config | threshold | hit rate % | false hits | Hinglish hit % |
|---|---|---|---|---|
| 1 phrasing per FAQ | 0.70 | 15.0 | 0 | 3.3 |
| multi phrasing, guard OFF | 0.85 | 5.0 | 0 | 3.3 |
| multi phrasing + guard | 0.85 | 5.0 | 0 | 3.3 |

## Negation guard: false hits it stopped

- `order abhi tak nahi aaya, der kyun ho rahi hai?` was 0.808 similar to `galat ya toota hua saaman aaya hai kya karu?` -> skipped cache
- `courier aaya aur main ghar par nahi tha to?` was 0.804 similar to `galat ya toota hua saaman aaya hai kya karu?` -> skipped cache
- `refund nahi mila abhi tak` was 0.769 similar to `refund wallet mein mil sakta hai kya?` -> skipped cache
- `coupon code is not working` was 0.842 similar to `How do I apply a coupon code?` -> skipped cache
