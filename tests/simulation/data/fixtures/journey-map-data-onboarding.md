# Journey Map — Patient Onboarding to HealthBridge Portal

**Persona:** Elena Torres, 42, first-time patient portal user
**Context:** Elena's primary care provider recently switched to HealthBridge. She received an email invitation to create her portal account.
**Goal:** Successfully set up her account and complete her first meaningful task (view lab results from a recent blood draw).
**Date of research:** February 2026
**Data sources:** 12 usability sessions, 30 survey responses, 8 support ticket analysis

---

## Phase 1: Awareness

**Duration:** 1-3 days (from receiving invitation to deciding to act)

### User Actions
- Receives email invitation from healthcare provider's office
- Reads the email subject line: "Activate Your HealthBridge Patient Portal Account"
- Scans the email body for key information
- Checks if the email is legitimate (looks for provider name, official branding)
- Decides whether to act now or later
- Clicks the activation link in the email

### Touchpoints
- Email client (Gmail, Outlook, Apple Mail)
- Healthcare provider's office (initial mention during visit)
- Paper handout received at checkout (URL and activation code)
- Provider's website (if searching for portal independently)

### Emotions (1-5 scale)
- Curiosity: 3.2
- Motivation: 2.8
- Anxiety: 3.5
- Trust: 2.4
- Excitement: 2.1

### Pain Points
1. **Email deliverability:** 18% of invitation emails landed in spam/promotions folders. Patients who didn't receive the email had no alternative activation path on the website.
2. **Trust concerns:** 6 of 12 participants hesitated before clicking the email link, citing phishing awareness. The email did not include enough trust signals (provider logo was small, no personalization beyond name).
3. **Timing mismatch:** The activation email arrived 3-5 days after the office visit, by which time the initial motivation had faded. 40% of invitations went unactivated for over 2 weeks.
4. **Paper handout confusion:** The paper handout listed a different URL than the email link (healthbridge.com/activate vs. portal.healthbridge.com/register), causing confusion about which was correct.

### Opportunities
- Send activation email within 1 hour of the office visit while motivation is highest
- Add prominent provider branding, doctor's name, and a personal message to the email
- Include a QR code on the paper handout that links directly to the activation page
- Add SMS as an alternative activation channel for patients who don't check email regularly
- Implement a "Didn't receive the email?" self-service recovery flow on the website

---

## Phase 2: Consideration

**Duration:** 5-15 minutes (evaluating the portal before committing to registration)

### User Actions
- Lands on the activation/registration page
- Reads the value proposition messaging
- Reviews what information will be required
- Checks the privacy policy and terms of service
- Looks for social proof (other patients' experiences)
- Decides to proceed with registration or abandon

### Touchpoints
- Portal registration landing page
- Terms of service page (opened in new tab by 60% of participants)
- Privacy policy page
- Provider's main website (opened by 3 of 12 participants for verification)
- Browser (bookmarking, checking URL legitimacy)

### Emotions (1-5 scale)
- Curiosity: 3.8
- Motivation: 3.1
- Anxiety: 4.1
- Trust: 2.9
- Excitement: 2.4

### Pain Points
1. **Value proposition unclear:** The landing page focused on features ("View lab results, manage appointments") rather than benefits ("Get your lab results 2 days earlier, skip phone hold times"). Participants couldn't quickly understand what the portal would do for them.
2. **Registration form length:** Seeing the full form (14 fields) before starting was discouraging. 3 participants commented that it "looked like a lot of work." The estimated time to complete was not communicated.
3. **Privacy anxiety:** Healthcare data is particularly sensitive. The privacy policy was 12 pages of legal text with no plain-language summary. Participants who clicked it spent an average of 8 seconds before closing it, indicating scanning rather than reading.
4. **No social proof:** There were no testimonials, usage statistics, or trust badges on the registration page. Participants in the 55+ age group were particularly hesitant.

### Opportunities
- Redesign the landing page to lead with patient benefits and estimated setup time
- Break the registration into a multi-step wizard with progress indicator
- Add a plain-language privacy summary (3-5 bullet points) above the legal version
- Include trust elements: HIPAA compliance badge, patient testimonials, security certifications
- Show a preview of the portal dashboard to give patients a concrete picture of what they'll get

---

## Phase 3: Onboarding (Account Creation)

**Duration:** 8-25 minutes (registration, verification, initial setup)

### User Actions
- Enters personal information (name, date of birth, email, phone)
- Creates username and password
- Enters the activation code from the email/paper handout
- Verifies identity (last 4 of SSN or insurance member ID)
- Completes email verification (clicks link in verification email)
- Logs in for the first time
- Encounters the (empty) dashboard

### Touchpoints
- Registration form (multi-page)
- Email client (for verification email)
- Identity verification screen
- Password strength indicator
- First login screen
- Dashboard (first view)

### Emotions (1-5 scale)
- Curiosity: 2.6
- Motivation: 2.3
- Anxiety: 4.4
- Trust: 2.7
- Excitement: 1.9

### Pain Points
1. **Activation code confusion:** 5 of 12 participants couldn't locate the activation code. Those who received the code by email had to switch between browser and email. Those with the paper handout couldn't find where to enter it on the form. Two participants entered their insurance ID instead.
2. **Identity verification failure:** The identity verification step (last 4 of SSN or insurance member ID) failed for 2 participants because their records had a maiden name. There was no clear error message — just "Verification failed. Please try again." with no guidance on what to check or how to resolve.
3. **Password requirements frustrating:** The password required 12+ characters, uppercase, lowercase, number, and special character. The requirements were only shown after the first failed attempt. One participant needed 4 attempts to create an acceptable password.
4. **Email verification delay:** The verification email took 2-7 minutes to arrive. 3 participants clicked "Resend" multiple times, then received 4-5 verification emails, causing confusion about which link to click.
5. **Empty dashboard shock:** After completing registration (average 15 minutes), participants landed on a dashboard with a generic "Welcome to HealthBridge" message and no personalized content, no guidance on what to do next, and no indication of available features. The emotional payoff for the registration effort was zero.

### Opportunities
- Pre-fill the activation code from the email link (eliminate the code entry step entirely)
- Provide specific guidance on verification failures ("The name in our records may be different — check with your provider's office at 555-0100")
- Show password requirements before the first attempt, with a real-time strength meter
- Reduce verification email delay or offer SMS verification as alternative
- Replace the empty dashboard with a personalized welcome: show upcoming appointments, available lab results, and a guided "Try these first" walkthrough

---

## Phase 4: First Use

**Duration:** 10-30 minutes (first meaningful interaction with the portal)

### User Actions
- Explores the navigation trying to find lab results
- Clicks through several menu items
- Locates the lab results section
- Views lab result summary list
- Opens a specific lab result detail
- Tries to understand the values and their meaning
- Attempts to download or print results
- Considers trying other features (scheduling, messaging)

### Touchpoints
- Dashboard
- Navigation menu (sidebar on desktop, hamburger on mobile)
- Lab results list page
- Lab result detail page
- Download/print functionality
- Appointment scheduling page (if explored)
- Secure messaging (if explored)

### Emotions (1-5 scale)
- Curiosity: 4.1
- Motivation: 3.7
- Anxiety: 3.8
- Trust: 3.2
- Excitement: 2.8

### Pain Points
1. **Feature discovery failure:** 4 of 12 participants could not find lab results within 2 minutes. Lab results were hidden under "Health Records" > "Test Results" > "Laboratory" — a three-level navigation path that didn't match participants' mental model. Most expected a top-level "Lab Results" or "Test Results" link.
2. **Medical terminology barrier:** All 12 participants expressed some confusion about lab values. "Hemoglobin A1c: 7.2%" was meaningless to 8 participants. The lack of plain-language explanations, reference range context, or trending information made the lab results page intimidating rather than empowering.
3. **No "What's New" indicator:** Participants who came specifically to view recent lab results had no way to quickly identify which results were new since their last visit. Everything looked the same — no unread indicators, no date highlighting.
4. **Download frustration:** The PDF download button generated a file named "report_20260215_847291.pdf" — not human-readable. On mobile, the PDF opened in a tiny viewer with no zoom controls. 2 participants could not figure out how to share the PDF with a family member.

### Opportunities
- Promote "Lab Results" to a top-level navigation item
- Add "New" badges to results that arrived since the patient's last login
- Implement the plain-language lab result explanations (see H2-1)
- Generate user-friendly PDF filenames ("Elena_Torres_Bloodwork_Feb2026.pdf")
- Add one-tap sharing via native share sheet (email, Messages, AirDrop)
- Include a "First Visit Guide" overlay that highlights key features

---

## Phase 5: Retention

**Duration:** 2-12 weeks (establishing habitual use patterns)

### User Actions
- Returns to check for new lab results
- Attempts to schedule a follow-up appointment
- Tries sending a secure message to provider
- Manages notification preferences
- Considers using the mobile app
- Evaluates whether the portal is worth continuing to use

### Touchpoints
- Email notifications (new results, appointment reminders)
- Mobile browser / app (if downloaded)
- Desktop browser (bookmarked portal)
- Phone call to provider's office (for tasks that failed on portal)
- In-person visit (mentions portal experience to staff)

### Emotions (1-5 scale)
- Curiosity: 2.4
- Motivation: 2.9
- Anxiety: 2.2
- Trust: 3.6
- Excitement: 2.0

### Pain Points
1. **Re-login friction:** Returning users face the full login process every time. There is no "Remember me" option, no biometric login, and sessions expire after 15 minutes with no warning. 5 of 30 survey respondents mentioned login friction as a reason they don't use the portal more often.
2. **Notification overload then silence:** The default notification settings send emails for everything (new results, appointment reminders, billing updates, promotional content). After 2 weeks, 3 participants had turned off all notifications. Then they missed a new lab result notification because the important alert was indistinguishable from promotional emails.
3. **Appointment scheduling abandonment:** 7 of 12 participants who attempted appointment scheduling gave up and called the office instead. The provider search, appointment type selection, and time slot browsing were all too complex for a task that takes 2 minutes on the phone.
4. **No habit triggers:** The portal sends no proactive engagement beyond transactional notifications. There are no "Your annual checkup is coming up" reminders, no medication adherence nudges, no health tips, and no "It's been 3 months since your last login" re-engagement.

### Opportunities
- Implement biometric login and "Remember me" (see H7-1)
- Create tiered notification settings: "Essential only" (results, appointments) vs. "Everything"
- Redesign appointment scheduling to be completable in under 2 minutes
- Build proactive engagement features: preventive care reminders, medication adherence, health education
- Add gamification elements: completion percentage for health profile, streaks for portal check-ins
- Create a "Quick Actions" widget for the phone's home screen (iOS Widget / Android widget)

---

## Cross-Phase Metrics Summary

| Metric | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|--------|---------|---------|---------|---------|---------|
| Avg emotion score (1-5) | 2.8 | 3.3 | 2.8 | 3.5 | 2.6 |
| Drop-off rate | 22% | 15% | 8% | 12% | 35% (by week 8) |
| Support tickets generated | 0.1/user | 0.2/user | 0.8/user | 0.4/user | 0.6/user |
| Avg time in phase | 2 days | 10 min | 15 min | 20 min | Ongoing |
| Task success rate | N/A | N/A | 83% | 71% | 62% |

## Key Insights

1. **The emotional valley is at onboarding (Phase 3):** Motivation peaks during consideration and drops sharply during registration. The "empty dashboard" after a 15-minute registration process is a particularly damaging moment.

2. **Trust builds slowly, breaks quickly:** Trust scores start low (2.4) and only reach 3.6 by the retention phase. A single failed verification or confusing error can reset trust to Phase 1 levels.

3. **The "phone call escape hatch":** When portal tasks are difficult, patients default to calling the office. This represents both a retention risk (they may stop trying the portal) and an opportunity (if we can match the phone's simplicity, we win).

4. **Feature discovery is the biggest barrier to retention:** Patients who found and successfully used 3+ features in their first week had 4.2x higher 8-week retention than those who only used 1 feature.

5. **Notification design is a retention lever:** The current all-or-nothing approach pushes patients to disable notifications, which eliminates the primary re-engagement channel.
