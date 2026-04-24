# Recommended Analysis Methods for Qualitative UX Data

This document maps dataset types to appropriate analysis methods and provides guidance on choosing the right approach for your research questions.

## Overview: Small-N vs. Large-N Analysis

**Small-N Analysis (N < 30):**
- Focus on depth over breadth
- Thematic analysis, coding, case studies
- Detailed, nuanced understanding
- Time-intensive, manual analysis

**Large-N Analysis (N > 30):**
- Focus on patterns and trends
- Topic modeling, sentiment analysis, text mining
- Statistical analysis possible
- Can use automated or semi-automated tools

## Dataset-Specific Recommendations

### User Interviews

**Best Methods:**
- **Thematic Analysis:** Identify patterns and themes across interviews
- **Coding:** Systematic categorization of responses
- **Journey Mapping:** Map user experiences and pain points
- **Affinity Diagramming:** Group related insights

**Tools:**
- NVivo, Atlas.ti (advanced coding)
- Dovetail, Miro (affinity mapping)
- Excel, Google Sheets (simple coding)
- LLMs (automated coding assistance)

**Example Questions:**
- What are the main pain points users experience?
- How do users navigate the product?
- What are users' mental models?
- What emotions do users express?

**Analysis Process:**
1. Transcribe interviews (if not already done)
2. Read through all transcripts to get familiar
3. Code transcripts (inductive or deductive)
4. Identify themes and patterns
5. Create insights and recommendations

### Open-Ended Surveys

**Best Methods:**
- **Topic Modeling:** Discover latent themes in responses
- **Sentiment Analysis:** Understand emotional tone
- **Keyword Analysis:** Identify frequently mentioned terms
- **Thematic Analysis:** Code and categorize responses

**Tools:**
- Python (NLTK, spaCy, gensim)
- R (tm, tidytext, topicmodels)
- Excel (manual coding)
- LLMs (automated analysis)

**Example Questions:**
- What are the main drivers of satisfaction/dissatisfaction?
- What features do users request most?
- How do users describe their experiences?
- What language do users use?

**Analysis Process:**
1. Clean and preprocess text data
2. Explore data (word frequencies, common phrases)
3. Apply topic modeling or coding
4. Analyze sentiment (if relevant)
5. Synthesize findings

### Focus Groups

**Best Methods:**
- **Thematic Analysis:** Identify group themes
- **Consensus Analysis:** Understand agreement/disagreement
- **Social Network Analysis:** Map group dynamics
- **Conversation Analysis:** Understand interaction patterns

**Tools:**
- NVivo, Atlas.ti (coding and analysis)
- Miro, Figma (visualization)
- Excel (simple analysis)
- LLMs (summarization)

**Example Questions:**
- What do participants agree/disagree on?
- How do group dynamics influence responses?
- What themes emerge from discussion?
- How do participants build on each other's ideas?

**Analysis Process:**
1. Transcribe group discussions
2. Code by speaker and theme
3. Identify consensus and disagreement
4. Analyze group dynamics
5. Synthesize group insights

### Diary Studies

**Best Methods:**
- **Longitudinal Analysis:** Track changes over time
- **Pattern Recognition:** Identify recurring themes
- **Emotion Tracking:** Monitor emotional states
- **Context Analysis:** Understand situational factors

**Tools:**
- Excel, Google Sheets (time-series analysis)
- Python, R (statistical analysis)
- NVivo (coding over time)
- Visualization tools (timelines, charts)

**Example Questions:**
- How do experiences change over time?
- What patterns emerge across entries?
- What contexts influence experiences?
- How do emotions fluctuate?

**Analysis Process:**
1. Organize entries by participant and date
2. Code entries for themes, emotions, context
3. Analyze patterns over time
4. Compare across participants
5. Identify trends and insights

### Customer Feedback

**Best Methods:**
- **Topic Modeling:** Discover main themes
- **Sentiment Analysis:** Understand emotional tone
- **Trend Analysis:** Track changes over time
- **Priority Analysis:** Identify most critical issues

**Tools:**
- Python (NLTK, spaCy, transformers)
- R (text mining packages)
- Excel (manual analysis)
- Specialized tools (Medallia, Qualtrics)

**Example Questions:**
- What are the main pain points?
- How is sentiment changing over time?
- What issues are most critical?
- What language do users use?

**Analysis Process:**
1. Collect and clean feedback data
2. Apply topic modeling or coding
3. Analyze sentiment
4. Identify trends over time
5. Prioritize issues by frequency/severity

### Community Forums

**Best Methods:**
- **Topic Modeling:** Discover discussion themes
- **Network Analysis:** Map user interactions
- **Trend Analysis:** Track topics over time
- **Influence Analysis:** Identify key contributors

**Tools:**
- Python (networkx, gensim)
- R (igraph, topicmodels)
- Gephi (network visualization)
- LLMs (summarization)

**Example Questions:**
- What topics are discussed most?
- How do discussions evolve?
- Who are the key contributors?
- What are the main concerns?

**Analysis Process:**
1. Collect forum data (posts, comments, threads)
2. Preprocess and clean text
3. Apply topic modeling
4. Analyze network structure (if relevant)
5. Synthesize findings

## Method-Specific Guidance

### Thematic Analysis

**When to use:** When you want to identify patterns and themes in qualitative data.

**Process:**
1. Familiarize yourself with data
2. Generate initial codes
3. Search for themes
4. Review themes
5. Define and name themes
6. Write up analysis

**Best for:** Interviews, focus groups, open-ended surveys

### Topic Modeling

**When to use:** When you have large amounts of text and want to discover latent themes.

**Methods:**
- **LDA (Latent Dirichlet Allocation):** Probabilistic topic modeling
- **NMF (Non-negative Matrix Factorization):** Matrix factorization approach
- **BERTopic:** Neural topic modeling using transformers

**Best for:** Large-N datasets, customer feedback, community forums

**Tools:** Python (gensim, scikit-learn, BERTopic), R (topicmodels)

### Sentiment Analysis

**When to use:** When you want to understand emotional tone or attitude.

**Methods:**
- **Rule-based:** Dictionary-based approaches
- **Machine Learning:** Trained classifiers
- **Deep Learning:** Neural network models

**Best for:** Customer feedback, app reviews, support tickets

**Tools:** Python (TextBlob, VADER, transformers), R (sentimentr)

### Coding

**When to use:** When you want systematic categorization of qualitative data.

**Approaches:**
- **Inductive:** Codes emerge from data
- **Deductive:** Codes based on existing theory
- **Hybrid:** Combination of both

**Best for:** Interviews, focus groups, diary studies

**Tools:** NVivo, Atlas.ti, Dovetail, Excel

## Choosing the Right Method

**Consider:**
1. **Research question:** What are you trying to learn?
2. **Data size:** Small-N vs. Large-N
3. **Resources:** Time, budget, tools, skills
4. **Output needs:** What format do you need?
5. **Stakeholder expectations:** What will resonate?

**Common Combinations:**
- Thematic analysis + sentiment analysis
- Topic modeling + coding
- Quantitative + qualitative analysis
- Multiple methods for triangulation

## Best Practices

1. **Start with research questions:** Let questions guide method choice
2. **Use multiple methods:** Triangulate findings
3. **Document your process:** Keep analysis transparent
4. **Validate findings:** Check interpretations with data
5. **Consider bias:** Be aware of your own assumptions
6. **Iterate:** Analysis is iterative, not linear

## Further Reading

- "Thematic Analysis" by Braun & Clarke
- "Qualitative Data Analysis" by Miles & Huberman
- "Text Mining with R" by Silge & Robinson
- "Natural Language Processing with Python" by Bird, Klein & Loper
