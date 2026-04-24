# Qualitative Text Datasets for UX Research

A curated collection of realistic qualitative text datasets designed for UX practitioners, researchers, and students to practice topic modeling, thematic analysis, text coding, NLP pipelines, and mixed-methods UX research.

## What is Qualitative Text Data?

Qualitative text data consists of unstructured, natural language responses from users-interview transcripts, open-ended survey responses, diary entries, support tickets, and forum discussions. Unlike quantitative metrics (click rates, completion times), qualitative data reveals the *why* behind user behavior: motivations, frustrations, expectations, and mental models.

This repository provides synthetic but realism-optimized datasets that mirror the complexity, messiness, and nuance of real-world UX research data.

## How to Use These Datasets

### Topic Modeling
Discover latent themes across large volumes of text using algorithms like LDA, NMF, or BERTopic. These datasets are ideal for:
- Identifying recurring pain points across user segments
- Uncovering unexpected feature requests
- Mapping sentiment clusters in customer feedback

### Thematic Analysis
Code and categorize qualitative data to build evidence-based insights. Use these datasets to:
- Practice inductive and deductive coding
- Develop codebooks and coding frameworks
- Identify patterns and relationships between themes

### NLP Pipelines
Build and test natural language processing workflows:
- Sentiment analysis
- Named entity recognition
- Text classification
- Keyword extraction
- Semantic similarity

### UX Research Training
Perfect for:
- Learning qualitative analysis methods
- Practicing coding consistency
- Teaching mixed-methods research
- Portfolio projects and case studies

## Dataset Types

### User Interviews
Moderated, one-on-one conversations exploring user experiences, needs, and behaviors. Includes transcripts from SaaS onboarding, mobile app usability, and healthcare portal studies.

### Open-Ended Surveys
Post-task or follow-up survey responses capturing immediate user reactions, feature requests, and satisfaction feedback.

### Focus Groups
Group discussions revealing social dynamics, consensus, and divergent perspectives on product experiences.

### Diary Studies
Longitudinal, self-reported entries tracking user experiences over time, ideal for understanding context and evolving needs.

### Customer Feedback
Real-world feedback channels including app store reviews, support tickets, and chatbot conversations-often unsolicited and emotionally charged.

### Community Forums
Public discussions from UX forums and product-specific Reddit threads, representing organic, unprompted user discourse.

## Important Notes

**Synthetic Data**: All datasets in this repository are synthetically generated but optimized for realism. They are designed to reflect natural language patterns, realistic UX pain points, and authentic user voices.

**Ethical Use**: These datasets are intended for educational and research purposes. When working with real user data, always follow ethical guidelines for privacy, consent, and data protection. See `documentation/ethical_notes.md` for detailed guidance.

## Recommended Tools

### Python
- **NLTK, spaCy**: Text preprocessing and NLP
- **scikit-learn, gensim**: Topic modeling (LDA, NMF)
- **transformers**: BERT-based topic modeling
- **pandas**: Data manipulation
- **matplotlib, seaborn**: Visualization

### R
- **tm, tidytext**: Text mining
- **topicmodels**: LDA implementation
- **quanteda**: Quantitative analysis of textual data

### Qualitative Analysis Software
- **NVivo**: Advanced coding and analysis
- **Atlas.ti**: Visual coding and theory building
- **Dedoose**: Mixed-methods analysis

### LLMs & AI Tools
- **GPT-4, Claude**: Automated coding assistance
- **BERTopic**: Neural topic modeling
- **ChatGPT API**: Pattern extraction and summarization

## Repository Structure

```
qualitative-text-ux-datasets/
├── datasets/
│   ├── user_interviews/
│   ├── open_ended_surveys/
│   ├── focus_groups/
│   ├── diary_studies/
│   ├── customer_feedback/
│   └── community_forums/
├── documentation/
└── examples/
```

## Getting Started

1. **Choose a dataset** that matches your research question or learning objective
2. **Review the documentation** in `documentation/` to understand data collection methods
3. **Explore examples** in `examples/` for inspiration on analysis approaches
4. **Load the data** into your preferred tool (Python, R, NVivo, etc.)
5. **Begin analysis** using the methods outlined in `documentation/recommended_analysis_methods.md`

## Creator & Contact

**Created by:** Mohsen Rafiei, Ph.D.

**Contact:** admin@puxlab.com

For questions, feedback, or collaboration inquiries, please reach out via email.

## Contributing

This repository is designed as an open educational resource. Contributions, improvements, and additional datasets are welcome. Please ensure all synthetic data maintains realism and follows ethical guidelines.

## License

This repository is provided under an open license for educational and research purposes. See LICENSE file for details.

---

**Created for UX practitioners by UX practitioners.** Optimized for credibility, realism, and practical value.
