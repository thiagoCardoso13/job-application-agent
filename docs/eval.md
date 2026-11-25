# Evaluation

### Keyword baseline (category only)

| Metric | Score |
|---|---|
| Category | 63% (19/30) |
| Company | 17% (5/30) |
| Role | 17% (5/30) |
| Due date | 60% (18/30) |

| Category | Accuracy |
|---|---|
| interview | 67% (4/6) |
| test | 100% (4/4) |
| rejection | 50% (3/6) |
| info_request | 0% (0/3) |
| acknowledgement | 50% (3/6) |
| other | 100% (5/5) |

Misclassified:
- e03: expected interview, got other
- e04: expected interview, got other
- e14: expected rejection, got other
- e15: expected rejection, got interview
- e16: expected rejection, got interview
- e17: expected info_request, got other
- e18: expected info_request, got other
- e19: expected info_request, got other
- e20: expected acknowledgement, got other
- e23: expected acknowledgement, got other
- e25: expected acknowledgement, got other

### LLM classifier (Gemini, structured output)

| Metric | Score |
|---|---|
| Category | 100% (30/30) |
| Company | 100% (30/30) |
| Role | 100% (30/30) |
| Due date | 100% (30/30) |

| Category | Accuracy |
|---|---|
| interview | 100% (6/6) |
| test | 100% (4/4) |
| rejection | 100% (6/6) |
| info_request | 100% (3/3) |
| acknowledgement | 100% (6/6) |
| other | 100% (5/5) |
