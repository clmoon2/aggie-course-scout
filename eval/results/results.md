| Condition | P@10 | NDCG@10 | AP@10 | MRR |
|---|---:|---:|---:|---:|
| tfidf | 0.700 | 0.674 | 0.670 | 0.794 |
| flat_bm25 | 0.740 | 0.725 | 0.725 | 0.853 |
| bm25f | 0.776 | 0.801 | 0.773 | 0.871 |
| ablate_no_correction | 0.660 | 0.662 | 0.644 | 0.743 |
| ablate_no_synonyms | 0.728 | 0.744 | 0.719 | 0.808 |
| ablate_no_synonyms_no_correction | 0.612 | 0.606 | 0.590 | 0.680 |
| ablate_title_only | 0.716 | 0.806 | 0.716 | 0.873 |
| ablate_no_dept | 0.744 | 0.777 | 0.730 | 0.872 |
| ablate_equal_weights | 0.776 | 0.786 | 0.791 | 0.893 |
| equal_expansion_no_phrase | 0.752 | 0.771 | 0.754 | 0.853 |
| flat_bm25_deduped | 0.716 | 0.723 | 0.712 | 0.853 |
| bm25f_deduped | 0.756 | 0.799 | 0.763 | 0.871 |
