# Heuristic Evaluation Notes — HealthBridge Mobile App v2.4.0

**Evaluator:** Dr. James Okwu, Senior UX Researcher
**Date:** February 22-24, 2026
**Platform:** iOS 18.2 (iPhone 15 Pro), Android 15 (Pixel 9 Pro)
**Methodology:** Independent expert evaluation against Nielsen's 10 Usability Heuristics
**Scope:** Core patient-facing flows (login, appointments, medications, lab results, messaging)

---

## H1: Visibility of System Status

### Finding H1-1: No loading feedback on appointment search
- **Severity:** 4 (Catastrophe)
- **Frequency:** High — occurs every appointment search
- **Impact:** High — users tap repeatedly, causing duplicate API calls
- **Persistence:** Permanent — exists in all tested versions
- **Screenshot ref:** `h1-1-appointment-search-no-loader.png`

**Description:** When the user initiates an appointment search by tapping "Find Available Slots," there is no visual feedback for 3-8 seconds while the API processes the request. The button does not change state, no spinner appears, and no skeleton screen is shown. During testing, the evaluator instinctively tapped the button three times before results appeared.

**Recommendation:** Add an immediate button state change (disabled + spinner) and display skeleton loading cards in the results area. Consider a progress indicator if the search typically exceeds 3 seconds.

---

### Finding H1-2: Medication refill status ambiguity
- **Severity:** 4 (Catastrophe)
- **Frequency:** High — affects all medication refill submissions
- **Impact:** Critical — medication safety concern with duplicate submissions
- **Persistence:** Permanent
- **Screenshot ref:** `h1-2-refill-no-confirmation.png`

**Description:** After submitting a medication refill request, a green toast notification appears for approximately 1.5 seconds and then auto-dismisses. The notification text ("Request submitted") is small (12sp) and appears at the bottom of the screen where it may be occluded by the user's thumb. There is no confirmation screen, no summary of the submitted request, and no reference number. The medication list does not visually indicate which items have pending refills.

**Recommendation:** Replace the toast with a dedicated confirmation screen showing: medication name, dosage, pharmacy, estimated ready date, and a reference number. Add a "Pending Refill" badge to affected medications in the list view.

---

### Finding H1-3: Sync status indicator missing
- **Severity:** 2 (Minor)
- **Frequency:** Medium — affects users with intermittent connectivity
- **Impact:** Medium — data freshness uncertainty
- **Persistence:** Permanent
- **Screenshot ref:** `h1-3-no-sync-indicator.png`

**Description:** The app does not indicate when data was last synchronized with the server. Users on mobile data or in areas with poor connectivity have no way to know if they are viewing current information or a cached state.

**Recommendation:** Add a small last-synced timestamp in the header or pull-to-refresh area. Display a warning banner when data is more than 15 minutes old.

---

## H2: Match Between System and the Real World

### Finding H2-1: Medical jargon in lab results without plain-language explanations
- **Severity:** 4 (Catastrophe)
- **Frequency:** High — affects all lab result views
- **Impact:** Critical — health literacy barrier
- **Persistence:** Permanent
- **Screenshot ref:** `h2-1-lab-jargon.png`

**Description:** Lab results display clinical abbreviations and terminology (e.g., "HbA1c: 7.2%," "eGFR: 68 mL/min/1.73m2," "TSH: 3.4 mIU/L") without any patient-friendly explanations, reference ranges context, or educational content. The color coding (red for out-of-range) adds anxiety without understanding. A patient seeing "Creatinine: 1.4 mg/dL" highlighted in red has no way to understand what creatinine is, why it matters, or how concerned they should be.

**Recommendation:** Add expandable "What does this mean?" sections for each lab value with: (1) plain-language name and purpose, (2) what the number means in context, (3) what "normal" looks like, (4) when to be concerned. Partner with the clinical team to validate all explanations.

---

### Finding H2-2: Appointment type codes instead of human-readable labels
- **Severity:** 3 (Major)
- **Frequency:** High — affects all appointment scheduling
- **Impact:** High — blocks task completion
- **Persistence:** Permanent
- **Screenshot ref:** `h2-2-appointment-codes.png`

**Description:** The appointment type dropdown shows internal system codes like "EST-30-PCP," "NEW-60-BH," "FUP-15-SPEC" instead of readable labels. These codes are meaningful to clinic staff but incomprehensible to patients.

**Recommendation:** Map all internal codes to patient-friendly labels. Example: "EST-30-PCP" should display as "30-Minute Follow-Up Visit with Your Primary Care Doctor."

---

### Finding H2-3: Date and time format inconsistencies
- **Severity:** 2 (Minor)
- **Frequency:** High — appears across multiple screens
- **Impact:** Low — causes momentary confusion
- **Persistence:** Permanent
- **Screenshot ref:** `h2-3-date-formats.png`

**Description:** The app uses at least three date formats: "03/15/2026" on the appointment list, "2026-03-15" in the appointment confirmation email, and "March 15, 2026" on the lab results page. Time formats also vary between 12-hour and 24-hour notation.

**Recommendation:** Standardize on locale-appropriate formatting. For US English: "March 15, 2026" for dates and "2:30 PM" for times. Respect device locale settings.

---

## H3: User Control and Freedom

### Finding H3-1: No undo for appointment cancellation
- **Severity:** 3 (Major)
- **Frequency:** Medium — occurs whenever a user cancels
- **Impact:** High — irreversible action without confirmation
- **Persistence:** Permanent
- **Screenshot ref:** `h3-1-cancel-no-undo.png`

**Description:** Tapping "Cancel Appointment" immediately cancels the appointment with no confirmation dialog, no undo period, and no way to reinstate the same appointment. On the mobile app, the "Cancel" button is positioned dangerously close to the "View Details" button, increasing accidental activation risk. The touch target for "Cancel" is 36x36dp, below the recommended 48x48dp minimum.

**Recommendation:** (1) Add a confirmation dialog with appointment details and a clear "Yes, Cancel" / "Keep Appointment" choice. (2) Implement a 60-second undo window. (3) Increase the touch target to at least 48x48dp. (4) Visually separate destructive actions from informational ones.

---

### Finding H3-2: Back navigation breaks multi-step forms
- **Severity:** 3 (Major)
- **Frequency:** High — affects all multi-step flows
- **Impact:** High — data loss
- **Persistence:** Permanent
- **Screenshot ref:** `h3-2-back-nav-break.png`

**Description:** Using the system back gesture (swipe from left edge on iOS, back button on Android) during multi-step appointment scheduling takes the user back to the dashboard, losing all form progress. The in-app back arrow at step 3 correctly returns to step 2, but the inconsistency with system navigation is disorienting.

**Recommendation:** Intercept system back navigation in multi-step flows. Show a "Discard changes?" dialog when the user attempts to leave. Better yet, auto-save form state so users can resume.

---

### Finding H3-3: Cannot dismiss keyboard easily
- **Severity:** 2 (Minor)
- **Frequency:** High — affects all text input
- **Impact:** Low — minor annoyance
- **Persistence:** Permanent
- **Screenshot ref:** `h3-3-keyboard-dismiss.png`

**Description:** On several screens, the soft keyboard covers content and there is no way to dismiss it other than tapping a non-interactive area. On the messaging screen, the keyboard covers the "Send" button, requiring the user to scroll down while the keyboard is open.

**Recommendation:** Add "Done" toolbar above the keyboard. Ensure the "Send" button remains visible when the keyboard is open by adjusting the scroll position.

---

## H4: Consistency and Standards

### Finding H4-1: Inconsistent navigation patterns
- **Severity:** 3 (Major)
- **Frequency:** High — every screen transition
- **Impact:** Medium — increases cognitive load
- **Persistence:** Permanent
- **Screenshot ref:** `h4-1-nav-inconsistency.png`

**Description:** The app uses a bottom tab bar for top-level navigation (Home, Appointments, Medications, Messages, More) but certain sections use a completely different navigation paradigm. Lab Results are accessed through a hamburger menu inside the "More" tab, Settings use a full-screen modal with a close button, and the Profile section uses a nested stack that doesn't respect the tab bar.

**Recommendation:** Audit all navigation patterns and align to a single paradigm. All primary sections should be reachable from the tab bar. Secondary sections should consistently use stack navigation within tabs.

---

### Finding H4-2: Mixed button styles for equivalent actions
- **Severity:** 2 (Minor)
- **Frequency:** High — visible on every screen
- **Impact:** Low — visual inconsistency
- **Persistence:** Permanent
- **Screenshot ref:** `h4-2-button-styles.png`

**Description:** Primary action buttons appear in four different styles across the app: filled blue rectangle, filled blue with rounded corners (8dp radius), outlined blue, and text-only blue. "Submit," "Confirm," "Save," and "Send" are all primary actions but use different visual treatments.

**Recommendation:** Establish a design token system with a single primary button style. Apply it consistently across all screens.

---

### Finding H4-3: Icon inconsistency
- **Severity:** 1 (Cosmetic)
- **Frequency:** High
- **Impact:** Low
- **Persistence:** Permanent
- **Screenshot ref:** `h4-3-icon-styles.png`

**Description:** The app mixes outlined icons (tab bar), filled icons (action buttons), and a third emoji-like style (status indicators). The "calendar" concept alone has three different visual representations.

**Recommendation:** Standardize on a single icon family (recommend Lucide or SF Symbols for iOS, Material Symbols for Android).

---

## H5: Error Prevention

### Finding H5-1: No input validation on medication dosage field
- **Severity:** 4 (Catastrophe)
- **Frequency:** High — every refill request
- **Impact:** Critical — patient safety risk
- **Persistence:** Permanent
- **Screenshot ref:** `h5-1-dosage-no-validation.png`

**Description:** The medication refill form includes a free-text "Dosage" field that accepts any input without validation. A patient could type "500mg" when their prescription says "50mg" and the system would submit the request without warning. There is no dropdown of valid dosages, no auto-fill from the prescription record, and no range check.

**Recommendation:** Replace the free-text field with a dropdown populated from the patient's active prescription data. If the provider allows dosage adjustments, limit the range to clinically safe values and require a confirmation step for any change.

---

### Finding H5-2: Double-tap submits forms twice
- **Severity:** 3 (Major)
- **Frequency:** Medium — occurs with eager tappers
- **Impact:** High — duplicate submissions
- **Persistence:** Permanent
- **Screenshot ref:** `h5-2-double-submit.png`

**Description:** Submit buttons do not disable after the first tap. A quick double-tap or a tap during a slow network response can submit the same form twice, resulting in duplicate appointment bookings, duplicate refill requests, or duplicate messages.

**Recommendation:** Disable the submit button immediately on first tap. Add debounce logic (300ms minimum) to all form submission handlers.

---

## H6: Recognition Rather Than Recall

### Finding H6-1: No recent items or quick access
- **Severity:** 3 (Major)
- **Frequency:** High — every session
- **Impact:** Medium — increased navigation time
- **Persistence:** Permanent
- **Screenshot ref:** `h6-1-no-recents.png`

**Description:** The home screen shows a generic welcome message and a health news feed. There are no shortcuts to recently viewed labs, upcoming appointments, pending refills, or unread messages. Users must navigate through 2-4 taps to reach their most common destinations every session.

**Recommendation:** Replace the news feed with a personalized dashboard showing: next appointment, pending refills, new lab results, unread messages, and recently viewed items.

---

### Finding H6-2: Provider search requires exact name entry
- **Severity:** 3 (Major)
- **Frequency:** High — every appointment booking
- **Impact:** High — blocks task completion
- **Persistence:** Permanent
- **Screenshot ref:** `h6-2-provider-search.png`

**Description:** To schedule an appointment, patients must type their provider's full name correctly. There is no auto-suggest, no "My Providers" list, no browse-by-specialty option, and no fuzzy matching. Searching for "Dr. Smith" returns no results if the system has "Smith, John A., MD."

**Recommendation:** Add a "My Care Team" section showing the patient's assigned providers. Implement fuzzy search with auto-suggest. Allow browsing by specialty and location.

---

## H7: Flexibility and Efficiency of Use

### Finding H7-1: No biometric quick-login
- **Severity:** 2 (Minor)
- **Frequency:** High — every session
- **Impact:** Medium — friction at entry point
- **Persistence:** Permanent
- **Screenshot ref:** `h7-1-no-biometric.png`

**Description:** The app requires full username/password entry on every launch. There is no Face ID, Touch ID, or fingerprint login option. For a healthcare app that patients may access multiple times per day, this creates significant friction.

**Recommendation:** Implement biometric authentication (Face ID/Touch ID on iOS, fingerprint/face on Android) with a fallback to PIN. Maintain full credential login as an option.

---

### Finding H7-2: No pharmacy preference saving
- **Severity:** 2 (Minor)
- **Frequency:** High — every refill request
- **Impact:** Medium — adds 3-4 unnecessary taps per refill
- **Persistence:** Permanent
- **Screenshot ref:** `h7-2-no-pharmacy-default.png`

**Description:** Each medication refill requires manually selecting a pharmacy from a scrollable list. There is no saved preference, no default, and no "last used" shortcut.

**Recommendation:** Add a default pharmacy setting in the patient profile. Pre-select it on the refill form. Allow one-tap change if needed.

---

## H8: Aesthetic and Minimalist Design

### Finding H8-1: Information overload on lab results detail screen
- **Severity:** 2 (Minor)
- **Frequency:** Medium
- **Impact:** Medium — cognitive overload
- **Persistence:** Permanent
- **Screenshot ref:** `h8-1-lab-detail-overload.png`

**Description:** The lab result detail view shows 15+ data points on a single screen without progressive disclosure: result value, reference range (low and high), units, collection date, collection time, ordering provider, performing lab, methodology, specimen type, fasting status, historical values (chart), and provider notes. The actual result value (the primary information) is not visually differentiated from secondary metadata.

**Recommendation:** Use progressive disclosure: show the result value, status, and a simple trend chart at the top. Place reference ranges, collection details, and methodology in expandable sections below.

---

### Finding H8-2: Dense typography on small screens
- **Severity:** 2 (Minor)
- **Frequency:** High — all text content
- **Impact:** Medium — readability concern
- **Persistence:** Permanent
- **Screenshot ref:** `h8-2-dense-typography.png`

**Description:** Body text uses 12sp font size with 1.3 line height throughout the app. The medication instructions section, which contains critical health information, uses the same dense formatting. At arm's length, this text is difficult to read, especially for older patients.

**Recommendation:** Increase body text to 14sp minimum with 1.5 line height. Use 16sp for critical health information. Support Dynamic Type (iOS) and font scaling (Android).

---

## H9: Help Users Recognize, Diagnose, and Recover from Errors

### Finding H9-1: Generic error screens with no recovery path
- **Severity:** 3 (Major)
- **Frequency:** Medium — occurs during network issues
- **Impact:** High — dead end for users
- **Persistence:** Permanent
- **Screenshot ref:** `h9-1-generic-error.png`

**Description:** Network errors and server errors display a white screen with "Something went wrong" and no additional context, no error code, no "retry" button, and no "go home" option. The user is stranded and must force-close the app to recover.

**Recommendation:** Design a branded error screen with: (1) a human-readable description of what happened, (2) a "Try Again" button, (3) a "Go Home" button, (4) a "Contact Support" link with the error ID pre-filled. Log errors for monitoring.

---

### Finding H9-2: Form validation feedback appears only at top of page
- **Severity:** 3 (Major)
- **Frequency:** High — all form submissions with errors
- **Impact:** High — users cannot find the specific field with the error
- **Persistence:** Permanent
- **Screenshot ref:** `h9-2-validation-top-only.png`

**Description:** When a form submission fails validation, a red banner appears at the top of the screen listing all errors. The form does not scroll to the first error, individual fields are not highlighted, and on mobile, the error banner may be offscreen if the user had scrolled down to the submit button.

**Recommendation:** (1) Scroll to the first field with an error. (2) Highlight individual fields with inline error messages. (3) Use real-time validation where possible (e.g., email format, required fields). (4) If a top banner is used, also highlight the corresponding fields.

---

## H10: Help and Documentation

### Finding H10-1: No contextual help or tooltips
- **Severity:** 2 (Minor)
- **Frequency:** High — affects complex fields and features
- **Impact:** Medium — users must guess or abandon
- **Persistence:** Permanent
- **Screenshot ref:** `h10-1-no-contextual-help.png`

**Description:** No screen in the app provides tooltips, info icons, or inline help text. The "Help" section is a static FAQ page that has not been updated since 2024 and returns "No results" for all search queries.

**Recommendation:** Add (i) info icons next to complex form fields with popover explanations. Create a searchable, up-to-date knowledge base. Consider an AI chatbot for common questions.

---

### Finding H10-2: No onboarding or first-use guidance
- **Severity:** 2 (Minor)
- **Frequency:** Low — affects new users only, but critical for first impression
- **Impact:** Medium — missed feature discovery
- **Persistence:** Permanent
- **Screenshot ref:** `h10-2-no-onboarding.png`

**Description:** New users are dropped directly into the home screen with no orientation, feature tour, or setup wizard. Key features like secure messaging and medication refills may not be discovered for weeks.

**Recommendation:** Implement a brief (3-5 step) onboarding flow for first-time users: welcome, set up notifications, choose default pharmacy, explore key features.

---

## Summary Matrix

| Heuristic | Findings | Critical (4) | Major (3) | Minor (2) | Cosmetic (1) |
|-----------|----------|--------------|-----------|-----------|---------------|
| H1: Visibility of System Status | 3 | 2 | 0 | 1 | 0 |
| H2: Match Between System and Real World | 3 | 1 | 1 | 1 | 0 |
| H3: User Control and Freedom | 3 | 0 | 2 | 1 | 0 |
| H4: Consistency and Standards | 3 | 0 | 1 | 1 | 1 |
| H5: Error Prevention | 2 | 1 | 1 | 0 | 0 |
| H6: Recognition Rather Than Recall | 2 | 0 | 2 | 0 | 0 |
| H7: Flexibility and Efficiency | 2 | 0 | 0 | 2 | 0 |
| H8: Aesthetic and Minimalist Design | 2 | 0 | 0 | 2 | 0 |
| H9: Error Recovery | 2 | 0 | 2 | 0 | 0 |
| H10: Help and Documentation | 2 | 0 | 0 | 2 | 0 |
| **TOTAL** | **24** | **4** | **9** | **10** | **1** |

### Severity Score Calculation

Using the formula: Severity = (Frequency + Impact + Persistence) / 3

- **Critical issues (4):** 4 findings — immediate remediation required
- **Major issues (3):** 9 findings — should be fixed in next sprint
- **Minor issues (2):** 10 findings — plan for short-term fix
- **Cosmetic issues (1):** 1 finding — fix when convenient

### Top 5 Priority Fixes

1. **H5-1:** Medication dosage input validation (patient safety)
2. **H1-2:** Medication refill confirmation screen (patient safety)
3. **H1-1:** Appointment search loading feedback (core usability)
4. **H3-1:** Appointment cancellation confirmation (data loss)
5. **H2-1:** Plain-language lab result explanations (health literacy)
