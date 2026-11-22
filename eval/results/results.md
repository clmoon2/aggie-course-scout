| Condition | P@10 | NDCG@10 | AP@10 | MRR |
|---|---:|---:|---:|---:|
| tfidf | 0.740 | 0.761 | 0.670 | 0.911 |
| flat_bm25 | 0.788 | 0.827 | 0.746 | 0.980 |
| bm25f | 0.828 | 0.898 | 0.788 | 0.973 |
| ablate_no_correction | 0.664 | 0.712 | 0.620 | 0.789 |
| ablate_no_synonyms | 0.772 | 0.843 | 0.726 | 0.933 |
| ablate_no_synonyms_no_correction | 0.608 | 0.657 | 0.558 | 0.749 |
| ablate_title_only | 0.788 | 0.905 | 0.770 | 0.980 |
| ablate_no_dept | 0.808 | 0.879 | 0.771 | 0.973 |
| ablate_equal_weights | 0.840 | 0.884 | 0.806 | 0.973 |
