| Condition | P@10 | NDCG@10 | AP@10 | MRR |
|---|---:|---:|---:|---:|
| tfidf | 0.700 | 0.671 | 0.669 | 0.794 |
| flat_bm25 | 0.740 | 0.723 | 0.724 | 0.853 |
| bm25f | 0.776 | 0.793 | 0.767 | 0.841 |
| ablate_no_correction | 0.652 | 0.652 | 0.638 | 0.717 |
| ablate_no_synonyms | 0.720 | 0.734 | 0.708 | 0.798 |
| ablate_no_synonyms_no_correction | 0.596 | 0.593 | 0.580 | 0.673 |
| ablate_title_only | 0.716 | 0.806 | 0.716 | 0.873 |
| ablate_no_dept | 0.748 | 0.771 | 0.727 | 0.842 |
| ablate_equal_weights | 0.788 | 0.795 | 0.794 | 0.868 |
| flat_bm25_deduped | 0.716 | 0.722 | 0.711 | 0.853 |
| bm25f_deduped | 0.756 | 0.790 | 0.756 | 0.841 |
