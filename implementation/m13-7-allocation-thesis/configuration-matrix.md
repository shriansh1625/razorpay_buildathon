# Configuration Matrix

Legitimate documented dimensions only — no tuning knobs introduced.

**LOW-DIFFERENTIATION rows:** 7
**HIGH-DIFFERENTIATION rows (≥5 differing):** 7

| opps | customers | window | profile | seed | competition_retry | conflicts | differing | binding |
|------|-----------|--------|---------|------|-------------------|-----------|-----------|---------|
| 100 | 20 | 21 | BALANCED | 1 | 1.22 | 450 | 8 | contact_allowance |
| 250 | 50 | 21 | BALANCED | 1 | 3.06 | 2910 | 35 | retry_slots,contact_allowance |
| 500 | 100 | 21 | BALANCED | 1 | 5.82 | 11766 | 43 | retry_slots,message_capacity,human_review_slots,contact_allowance |
| 750 | 150 | 21 | BALANCED | 1 | 9.42 | 34656 | 21 | retry_slots,message_capacity,human_review_slots,contact_allowance |
| 500 | 100 | 21 | BALANCED | 1 | 5.82 | 11766 | 43 | retry_slots,message_capacity,human_review_slots,contact_allowance |
| 500 | 100 | 21 | SCARCE | 1 | 15.25 | 13472 | 4 | retry_slots,message_capacity,human_review_slots,contact_allowance |
| 500 | 100 | 21 | BALANCED | 2 | 6.32 | 17604 | 36 | retry_slots,message_capacity,human_review_slots,contact_allowance |
| 500 | 100 | 21 | SCARCE | 2 | 15.80 | 17604 | 5 | retry_slots,message_capacity,human_review_slots,contact_allowance |
| 500 | 100 | 30 | BALANCED | 1 | 6.76 | 0 | 0 | retry_slots,human_review_slots |
| 500 | 100 | 30 | SCARCE | 1 | 17.40 | 0 | 0 | retry_slots,human_review_slots |
| 500 | 100 | 30 | BALANCED | 2 | 7.26 | 0 | 0 | retry_slots,human_review_slots |
| 500 | 100 | 30 | SCARCE | 2 | 18.15 | 0 | 0 | retry_slots,human_review_slots |
| 500 | 50 | 30 | BALANCED | 1 | 6.44 | 0 | 0 | retry_slots,human_review_slots |
| 500 | 100 | 30 | BALANCED | 1 | 6.76 | 0 | 0 | retry_slots,human_review_slots |
| 500 | 200 | 30 | BALANCED | 1 | 7.08 | 0 | 0 | retry_slots,human_review_slots |
