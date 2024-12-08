## **Tables**	

Modify Tables and add position markers `\zsavepos{order-element-idx}` as per the following steps:

### Steps

1. **Identify Each `table` Block**
2. **Insert Markers**:
   - Use `\zsavepos{order-table-1}`, `\zsavepos{order-table-2}`, and `\zsavepos{order-table-3}` for the table area.
   - Use `\zsavepos{order-tablecap-1}` and `\zsavepos{order-tablecap-2}` around the caption.

**Example**:

```latex
\begin{table}[h]
\centering
\zsavepos{1-tablecap-1}\caption{Performance of Different Models on Test Dataset}\zsavepos{1-tablecap-2}
\zsavepos{1-table-1}
\begin{tabular}{@{}lc>{\centering\arraybackslash}p{1cm}@{}}
\toprule
Model             & Accuracy & F1 Score\zsavepos{1-table-2} \\
\midrule
Logistic Regression & 85.3\%    & 0.81      \\
Random Forest       & 92.4\%    & 0.89      \\
Support Vector Machine (SVM) & 94.1\%    & 0.91      \\
Neural Network      & 96.2\%    & 0.94      \\
\bottomrule
\end{tabular}
\zsavepos{1-table-3}
\end{table}
```

