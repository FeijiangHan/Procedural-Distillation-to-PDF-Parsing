## **Headings**

Modify heading areas and add position markers `\zsavepos{order-element-idx}` as per the following steps:

1. **Identify Each heading sections**
2. **Insert Markers**:
   - Place `\zsavepos{order-header-1}` before the heading.
   - Place `\zsavepos{order-header-2}` inside the `\section` command.

**Example**:

```latex
\zsavepos{1-header-1}\section{Heading1\zsavepos{1-header-2}}
\zsavepos{2-header-1}\subsection{Heading2\zsavepos{2-header-2}}
```