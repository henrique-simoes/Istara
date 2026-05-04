# Example Topic Modeling Results

This document shows example outputs from topic modeling analysis on the qualitative datasets. These examples demonstrate what topic modeling can reveal in UX research data.

## Example 1: SaaS Onboarding Interviews

**Dataset:** `user_interviews/saas_onboarding_interviews.csv`

**Method:** LDA Topic Modeling (5 topics)

**Results:**

### Topic 1: Onboarding Overwhelm (28% of responses)
**Keywords:** overwhelming, confusing, too much, don't know, where to start, lost, stuck

**Example Quotes:**
- "There's so much... stuff. I don't even know where to start. It's overwhelming, you know?"
- "I'm looking around and there's just... a lot going on. Like, where do I start?"

**Interpretation:** Users feel overwhelmed by the amount of information and options presented during onboarding. The onboarding process lacks clear guidance or prioritization.

### Topic 2: Feature Discovery Challenges (22% of responses)
**Keywords:** hidden, can't find, discover, stumble, accidentally, didn't know, exists

**Example Quotes:**
- "I had no idea this feature even existed until I accidentally stumbled on it."
- "I've been using the tool for three weeks and I'm still finding new things."

**Interpretation:** Users struggle to discover features. Features are not prominently displayed or explained during onboarding, leading to low feature awareness.

### Topic 3: Learning Curve Frustration (20% of responses)
**Keywords:** learning curve, steep, difficult, hard, struggle, fighting, against

**Example Quotes:**
- "I'm frustrated, honestly. I know this tool can do what I need, but I feel like I'm fighting against it."
- "The learning curve wasn't so steep at the beginning."

**Interpretation:** Users find the tool difficult to learn and use. The initial learning experience is challenging, creating frustration and potential abandonment.

### Topic 4: Missing Guidance (18% of responses)
**Keywords:** guidance, help, tutorial, show me, explain, don't understand, missing

**Example Quotes:**
- "I wish there was a way to say 'hey, I'm new, show me around' or 'I know what I'm doing, skip this'."
- "The onboarding covers the basics, but not the 'why'."

**Interpretation:** Users want more guidance and explanation. The onboarding provides basic instruction but lacks context and rationale for actions.

### Topic 5: Positive Adaptation (12% of responses)
**Keywords:** growing, getting better, worth it, powerful, impressed, stick with it

**Example Quotes:**
- "It's growing on me. The first week was rough, but now that I've figured out the basics, I can see the value."
- "Once you get past the initial confusion, it's powerful."

**Interpretation:** Some users persist through initial challenges and find value. However, this represents a minority, suggesting many users may not reach this point.

## Example 2: E-commerce Checkout Feedback

**Dataset:** `open_ended_surveys/ecommerce_checkout_feedback.csv`

**Method:** BERTopic (8 topics)

**Results:**

### Topic 1: Shipping Cost Issues (24% of responses)
**Keywords:** shipping, cost, expensive, free shipping, charge, too much

**Example Quotes:**
- "The shipping costs were way higher than I expected."
- "It said 'free shipping over $50' but my cart was $52 and it still wanted to charge me $12 for shipping."

**Interpretation:** Shipping costs are a major barrier to checkout completion. Users expect free shipping thresholds to work as advertised.

### Topic 2: Form Usability Problems (18% of responses)
**Keywords:** form, confusing, hard to fill, fields, order, address, autocomplete

**Example Quotes:**
- "The shipping address form was annoying. It kept asking me to verify my address even though I've used it before."
- "The autocomplete didn't work properly - it suggested addresses that weren't even close to mine."

**Interpretation:** Form design and functionality create friction. Address autocomplete and form validation need improvement.

### Topic 3: Payment Process Friction (16% of responses)
**Keywords:** payment, card, confusing, too many steps, confirm, security

**Example Quotes:**
- "The payment form was confusing. It asked for my card number, then my name, then my billing address, but the fields were in a weird order."
- "There were too many confirmation screens."

**Interpretation:** Payment process has unnecessary steps and confusing field ordering, creating friction and potential abandonment.

### Topic 4: Discount Code Discovery (14% of responses)
**Keywords:** discount, code, promo, can't find, hidden, apply, coupon

**Example Quotes:**
- "I couldn't find where to apply my discount code. I looked everywhere, but it wasn't obvious."
- "I finally found it, but it was hidden in a dropdown menu."

**Interpretation:** Discount code entry is not discoverable. Users want to use codes but can't find where to enter them.

### Topic 5: Mobile Experience Issues (12% of responses)
**Keywords:** mobile, phone, small, hard to use, keyboard, screen

**Example Quotes:**
- "I was trying to checkout on my phone, but the form was too small and hard to fill out."
- "The keyboard kept covering up the fields I was trying to fill."

**Interpretation:** Mobile checkout experience has usability issues. Forms are not optimized for mobile devices.

### Topic 6: Trust and Security Concerns (8% of responses)
**Keywords:** trust, secure, worried, afraid, wrong, mistake, error

**Example Quotes:**
- "I'm worried I'll send it to the wrong person."
- "I'm afraid I'll do something wrong or see something I'm not supposed to see."

**Interpretation:** Users lack confidence in the checkout process. Security and error prevention need to be more clearly communicated.

### Topic 7: Performance and Speed (5% of responses)
**Keywords:** slow, loading, takes forever, fast, speed, performance

**Example Quotes:**
- "The page kept refreshing while I was filling out the form."
- "The checkout process was taking too long."

**Interpretation:** Performance issues create frustration. Pages load slowly or refresh unexpectedly, disrupting the checkout flow.

### Topic 8: Feature Requests (3% of responses)
**Keywords:** wish, want, need, should, could, would like

**Example Quotes:**
- "I wish I could see the total cost until the very end."
- "I wish there was a way to save my payment method for next time."

**Interpretation:** Users want additional features like cost visibility and saved payment methods. These are enhancement opportunities.

## Example 3: App Store Reviews

**Dataset:** `customer_feedback/app_store_reviews.csv`

**Method:** Sentiment Analysis + Topic Modeling

**Results:**

### Positive Topics (60% of reviews):

**Topic 1: Organization and Productivity (35%)**
**Keywords:** organized, productive, helpful, essential, recommend

**Sentiment:** Highly positive
**Example:** "Love this app! It's helped me stay organized and get so much done."

**Topic 2: Interface and Design (25%)**
**Keywords:** clean, beautiful, intuitive, easy to use, simple

**Sentiment:** Positive
**Example:** "The interface is clean, the features are powerful, and it's actually fun to use."

### Negative Topics (40% of reviews):

**Topic 3: Technical Issues (45%)**
**Keywords:** crashes, broken, buggy, slow, freezes, doesn't work

**Sentiment:** Highly negative
**Example:** "Crashes constantly. I'll be in the middle of adding a task and the app just closes."

**Topic 4: Sync Problems (30%)**
**Keywords:** sync, doesn't work, broken, not showing up, missing

**Sentiment:** Negative
**Example:** "The sync is broken. I add tasks on my phone, but they don't show up on my iPad."

**Topic 5: Data Loss (25%)**
**Keywords:** deleted, lost, gone, disappeared, restore, backup

**Sentiment:** Highly negative
**Example:** "This app deleted all my tasks! I had hundreds of tasks organized into categories, and after the latest update, everything is gone."

## Key Insights from Topic Modeling

1. **Onboarding:** Users feel overwhelmed and lack guidance. Feature discovery is poor.

2. **Checkout:** Shipping costs and form usability are major barriers. Mobile experience needs improvement.

3. **App Reviews:** Technical issues (crashes, sync) are the primary source of negative sentiment, while organization and design drive positive sentiment.

4. **Actionable Recommendations:**
   - Simplify onboarding with progressive disclosure
   - Improve feature discoverability
   - Fix technical issues (crashes, sync)
   - Optimize checkout forms and mobile experience
   - Clarify shipping cost policies

## Using Topic Modeling in UX Research

**Benefits:**
- Discover unexpected themes
- Analyze large volumes of text
- Identify patterns across data
- Prioritize issues by frequency

**Limitations:**
- May miss nuance and context
- Requires interpretation
- Can be influenced by preprocessing
- May not capture all themes

**Best Practices:**
- Use multiple methods (topic modeling + coding)
- Validate findings with qualitative review
- Consider topic coherence and interpretability
- Document preprocessing steps
- Iterate on number of topics
