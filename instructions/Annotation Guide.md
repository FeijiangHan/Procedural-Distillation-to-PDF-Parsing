# Annotation Guide

## Setup

1. 确保引入下面的包：

```latex
\usepackage{zref-savepos}
\usepackage{zref-user}
\usepackage{layouts}
```

2. 如果整个页面都是统一布局的（不存在单双混合布局），请在document之前插入columnwidth、textwidth、lineheight：

```latex
\makeatletter
\protected@write\@auxout{}{%
    \string\newlabel{columnwidth}{{\the\columnwidth}}
}
% 写入列宽到 .aux 文件
\protected@write\@auxout{}{%
    \string\newlabel{textwidth}{{\the\textwidth}}
}
% 写入行高（lineheight）到 .aux 文件
\protected@write\@auxout{}{%
    \string\newlabel{lineheight}{{\the\baselineskip}}
}
\makeatother

\begin{document}
```

3. 如果是混合单双栏布局，请在双栏布局后插入columnwidth，此时可以删除\begin{document}前面的columnwidth：

```latex
% 开启双栏正文
\begin{multicols}{2}
% 插入
\makeatletter
\protected@write\@auxout{}{%
    \string\newlabel{columnwidth}{{\the\columnwidth}}
}
\makeatother
```



**The following guide outlines the steps for annotating different elements in a document layout.**

\zsavepos{order-element-idx}中的order是从1开始地增的，所有元素共用。Assign a unique order to each element, starting with `1`.

---

## **Text**

Begin by determining whether the text is single-column or double-column. Then follow the respective instructions.

### **Single-Column Text**

Modify text areas and add position markers `\zsavepos{order-element-idx}` as per the following steps:
1. **Identify Text Areas**: Exclude titles, images, tables, and headings. 
2. **Insert Position Markers**:
   - Place `\zsavepos{order-text-1}` at the beginning.
   - Place `\zsavepos{order-text-2}` at the end.

**Example**:
```latex
\zsavepos{1-text-1}
Machine learning (ML) has become a pivotal tool in the analysis and interpretation of large datasets across a variety of domains. From healthcare to finance, the application of ML techniques has enabled unprecedented insights and efficiency in analyzing and interpreting large datasets across various domains. This section covers core techniques in machine learning, including supervised learning, unsupervised learning, and reinforcement learning, and their effectiveness in different contexts.
\zsavepos{1-text-2}
```

### **Double-Column Text**
If double-column text exists within a single-column layout, modify the markers as follows:
- Use `\zsavepos{order-text2-1}` and `\zsavepos{order-text2-2}` for the double-column text.

**Example**:

```latex
\zsavepos{1-text2-1}
This randomized structure demonstrates how the layout and flow of content can be reorganized while maintaining all original commands, styles, and markers. By rearranging the headers, figures, and text blocks, the document structure is completely altered but remains fully functional.
\zsavepos{1-text2-2}
```

### **Merging Continuous Paragraphs**
If multiple text paragraphs are continuous (i.e., no intervening figures, math, tables, or column/page breaks), merge them under one `text` marker.

**Example**:
```latex
\zsavepos{1-text-1}
The Few-shot CoT scenarios differ significantly from zero-shot scenarios due to the availability of example-based reasoning. This advantage allows LLMs to learn reasoning patterns directly from provided examples, thereby enhancing their accuracy and decision-making process. Through this study, we explore the potential to fine-tune Few-shot CoT for better alignment with human reasoning structures.

The Few-shot CoT scenarios differ significantly from zero-shot scenarios due to the availability of example-based reasoning. This advantage allows LLMs to learn reasoning patterns directly from provided examples, thereby enhancing their accuracy and decision-making process. Through this study, we explore the potential to fine-tune Few-shot CoT for better alignment with human reasoning structures.

The Few-shot CoT scenarios differ significantly from zero-shot scenarios due to the availability of example-based reasoning. This advantage allows LLMs to learn reasoning patterns directly from provided examples, thereby enhancing their accuracy and decision-making process. Through this study, we explore the potential to fine-tune Few-shot CoT for better alignment with human reasoning structures.
\zsavepos{1-text-2}
```

---

## **Images**

### Steps
1. **Identify Each `figure` Block**
2. **Insert Markers**:
   - Use `\zsavepos{1-figure-1}` and `\zsavepos{1-figure-2}` for the figure area.
   - Use `\zsavepos{2-figurecap-1}` and `\zsavepos{2-figurecap-2}` around the caption.

**Example: Single Image**
```latex
\begin{figure}[h]
\zsavepos{1-figure-1} \centering
\includegraphics[width=\linewidth]{max-gpt4o.png}
\zsavepos{1-figure-2}

\zsavepos{2-figurecap-1}\caption{An example of a decision boundary learned by an SVM model.}\zsavepos{2-figurecap-2}
\end{figure}
```

**Example: Multiple Subfigures**

```latex
\zsavepos{1-figure-1-1}
\begin{figure*}[!ht]
    \centering
    \subfigure[MultiArith]{\includegraphics[width=0.24\linewidth]{MultiArith.pdf}}
    \subfigure[GSM8K]{\includegraphics[width=0.24\linewidth]{GSM8K.pdf}}
    \subfigure[AQuA]{\includegraphics[width=0.24\linewidth]{AQuA.pdf}}
    \subfigure[SingleEq]{\includegraphics[width=0.24\linewidth]{SingleEq.pdf}}
    \\
    \subfigure[SAVMP]{\includegraphics[width=0.24\linewidth]{svamp.pdf}}
    \subfigure[StrategyQA]{\includegraphics[width=0.24\linewidth]{strategyqa.pdf}}
    \subfigure[Letter]{\includegraphics[width=0.24\linewidth]{last_letter.pdf}}
    \subfigure[Coin]{\includegraphics[width=0.24\linewidth]{coin_flip.pdf}}
    
    \zsavepos{1-figure-1-2}
    \zsavepos{1-figurecap-1-1}
    \caption{Linear Relationship Between Step Quantity and Accuracy\zsavepos{1-figurecap-1-2}}
    \label{figure1}
\end{figure*}
```

---

## **Headings**

### Steps
1. **Identify Each `section` Command**
2. **Insert Markers**:
   - Place `\zsavepos{order-header-1}` before the heading.
   - Place `\zsavepos{order-header-2}` inside the `\section` command.

**Example**:
```latex
\zsavepos{1-header-1}\section{Figures and Tables\zsavepos{1-header-2}}
```

---

## **Formulas**

### Steps
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

---

## **Tables**

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