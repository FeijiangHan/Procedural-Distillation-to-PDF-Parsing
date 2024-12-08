### Math Block
Modify math blocks and add position markers `\zsavepos{order-element-idx}` as per the following steps:

1. **Identify Each `equation` Block**
2. **Insert Markers**:
   - Use `\zsavepos{order-math-1}`, `\zsavepos{order-math-2}`, `\zsavepos{order-math-3}`, and `\zsavepos{order-math-4}` around the formula.

**Example**:

```latex
\zsavepos{1-math-1}
\begin{equation}
    \zsavepos{1-math-2}J(\theta) = \frac{1}{2m} \sum_{i=1}^{m} (h_\theta(x^{(i)}) - y^{(i)})^2
    \zsavepos{1-math-3}
\end{equation}\zsavepos{1-math-4}
```
