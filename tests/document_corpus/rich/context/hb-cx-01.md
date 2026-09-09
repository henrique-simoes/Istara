# HB-CX-01 — Project context: Harbor Ledger small-business banking redesign

> SYNTHETIC program context for Harbor Ledger. Hundreds of lines by design: scenarios fill UI context fields from these files.

Northloop Bank serves 41,000 small businesses across 6 states. The Harbor Ledger program redesigns the business banking app for owners, accountants, bookkeepers, tellers, branch managers, and operations staff, in English and Spanish, across mobile, web, and branch counter.

Business background (para 1/90). I batch on Fridays and half the pile is mystery paper. Whose lunch was this? Business or sorry?

Business background (para 2/90). Mileage, parking, tolls — the small stuff leaks around the edges of every system I've tried.

Business background (para 3/90). A photo of a photo of a receipt. That's what my February looks like. Try auditing that.

Business background (para 4/90). Cash purchases at the supply house never make it in. The owner pays cash, tells me Monday, I believe him on faith.

Business background (para 5/90). Give me a shoebox mode: dump everything in, sort it Sunday, nag me only about the orphans.

Business background (para 6/90). Everything over five hundred needs my sign-off, and I'm on a ladder half the day. The whole company queues behind my phone battery.

Business background (para 7/90). For licensing I need two signatures on file. When one is on vacation, payroll-adjacent spending just waits.

Business background (para 8/90). I do it in batches on Fridays, but approvals don't batch. They rot, one by one, in an inbox nobody owns.

Business background (para 9/90). In our old system, delegation worked: deputy approves under a cap, full audit trail. I measured the delay drop.

Business background (para 10/90). Per our incident review, single-approver chains are a control gap. That is a finding, not feedback.

Business background (para 11/90). The approver sees an amount with no context. Approve what? For whom? Against which job? It's a blind signature.

Business background (para 12/90). Emergency purchases route around the chain entirely, then get scolded retroactively. The system trains circumvention.

Business background (para 13/90). I approved something at a red light once. Never again — but the app let me, no questions asked.

Business background (para 14/90). Weekend approvals pile to Monday and Monday is already full. The chain has no concept of urgency, only order.

Business background (para 15/90). Two partners must both approve, but the app notifies them sequentially. Parallel would halve the wait and nobody can explain why it doesn't.

Business background (para 16/90). The audit trail shows who clicked, not what they knew. That's a signature without informed consent.

Business background (para 17/90). Deputy coverage exists on paper. In practice the deputy can't see the attachments, so they approve blind or not at all.

Business background (para 18/90). The auto-match is magic. Ninety percent right, and I fix the rest with coffee. Don't take it away.

Business background (para 19/90). Boats don't wait for reconciliation. If the feed guesses right, I sail. If not, I fix it in winter.

Business background (para 20/90). The correct treatment is review-then-post, never post-then-review. Auto-posting buries errors where auditors find them.

Business background (para 21/90). I always worry that a wrong match sits there looking correct. Correct-looking wrongness is the most expensive kind.

Business background (para 22/90). Show me confidence per match and I'll review the shaky ten percent gladly. Certainty theater I will not accept.

Business background (para 23/90). Last April it matched a supplier payment to the wrong job. We underbilled by nine hundred and found out in July.

Business background (para 24/90). The override log is where trust lives. If I can see who confirmed what and undo it, I'll let it guess.

Business background (para 25/90). Speed matters more than purity in season. I'll take 90% auto with a clean review queue over 100% manual and drowning.

Business background (para 26/90). My old ERP never guessed. It also never finished. There is a middle I would pay for.

Business background (para 27/90). Duplicate detection is the real hero, not matching. Catch the double-charge and I'll forgive ten bad guesses.

Business background (para 28/90). Quarter-end turns every guess into a fact nobody re-examines. The calendar launders uncertainty.

Business background (para 29/90). Train it on my corrections, visibly. If it learns my vendors, it's a colleague. If not, it's a slot machine.

Business background (para 30/90). Payroll hits Thursday, client payments land Friday. Every week I float the gap on a credit card and pretend it's strategy.

Business background (para 31/90). I measured this, actually: eleven weeks last year where payroll preceded receivables by more than two days.

Business background (para 32/90). For licensing I need payroll records clean to the day. The float makes clean impossible.

Business background (para 33/90). Three times last quarter I moved money between accounts at midnight to make morning payroll. That's not banking, that's parkour.

Business background (para 34/90). Honestly? A calendar that shows cash against payroll dates would change my life more than any report.

Business background (para 35/90). New hires don't know the float exists until their first short Friday. Then they know, loudly.

Business background (para 36/90). Overtime posts late, so Thursday's payroll is always a guess dressed as a number.

Business background (para 37/90). The payroll provider debits a day early 'for processing'. That day costs me sleep and overdraft math.

Business background (para 38/90). I keep a secret spreadsheet called 'Thursday'. My bank has no idea Thursday exists.

Business background (para 39/90). Contractors versus employees, two rhythms, one account. The app shows a balance; I need a choreography.

Business background (para 40/90). Holiday weeks compress everything and nobody warns you. Last Thanksgiving I learned by overdraft.

Business background (para 41/90). If the app said 'this Thursday needs $4,100 you don't have yet', I'd kiss it. Professionally.

Business background (para 42/90). The Spanish version says 'cargo por sobregiro' where the English says 'overdraft protection transfer'. Those are not the same thing and my customers notice.

Business background (para 43/90). Language consistency matters because one unclear word can trigger a phone call. We get forty such calls a week.

Business background (para 44/90). My screen reader says the language attribute flips mid-sentence. It reads Spanish with English pronunciation. Try understanding that at speed.

Business background (para 45/90). The fee schedule has eleven footnotes in English and four in Spanish. Guess which seven fees surprise people.

Business background (para 46/90). Disclosure timing differs: English shows it pre-confirm, Spanish post-confirm. Same bank, different truth.

Business background (para 47/90). Nobody tested this with a keyboard, did they. Tab order follows the English layout even on the Spanish page.

Business background (para 48/90). My mother trusts the Spanish page more and understands it less. That combination should frighten a bank.

Business background (para 49/90). Error messages are translated by someone who never saw the error. 'Inténtelo más tarde' for a locked account is not advice, it's abandonment.

Business background (para 50/90). The glossary contradicts the statements on three terms I counted. I stopped counting after three.

Business background (para 51/90). Bilingual staff improvise translations at the counter. Improvisation is not a localization strategy.

Business background (para 52/90). Statements should carry both languages side by side for key terms. Redundancy here is clarity, not clutter.

Business background (para 53/90). When the app updates, English ships first and Spanish 'follows'. It follows by months. Customers notice the lag before the words.

Business background (para 54/90). A customer starts online, finishes at my window, and I know nothing. They repeat everything, slower, angrier.

Business background (para 55/90). For older customers, starting over isn't an inconvenience, it's a reason to leave the bank.

Business background (para 56/90). I walk them through it, step by step, but I'm walking blind. Their online steps are invisible to me.

Business background (para 57/90). The screen reader reads the whole table, every time. Imagine that, then imagine repeating it to a human who also can't see it.

Business background (para 58/90). At the window you see it all: the apology, the repetition, the sigh when I ask for the account number they already typed.

Business background (para 59/90). The queue display says six minutes. The repeat-story tax makes it eleven. Nobody measures the tax.

Business background (para 60/90). Customers bring screenshots of their own accounts as proof of their own money. Let that sink in.

Business background (para 61/90). Handoff notes exist but nobody writes them because the field is buried three tabs deep during a rush.

Business background (para 62/90). The online flow collects the reason for visit, then drops it. I ask 'what brings you in' to someone who already answered.

Business background (para 63/90). Privacy theater: I can't see their online steps 'for security', but I can see their balance. Explain that logic.

Business background (para 64/90). After a bad handoff they don't blame the channel, they blame me, by name, in surveys.

Business background (para 65/90). A simple 'customer already tried X' banner would save my mornings. It has never existed.

Business background (para 66/90). Ninety percent of these are noise. I cleared forty-three before lunch. Every false alarm teaches customers to ignore the real one.

Business background (para 67/90). Per our incident review, alert coverage is a control gap. That is a finding, not feedback. We need more signals, not fewer.

Business background (para 68/90). My phone buzzes at 2am for a twelve-dollar charge I made myself. I have started sleeping through the real ones too.

Business background (para 69/90). Ha. Ask me in April. The winter fraud wave is real and the alerts saved us twice. Annoying and necessary.

Business background (para 70/90). If an auditor asks, I want the alert log complete. If you ask me as a human, I want half of them gone.

Business background (para 71/90). For licensing I need the fraud review documented. Nobody said it has to buzz.

Business background (para 72/90). Severity levels are decoration: everything arrives as URGENT. When everything is urgent, triage is astrology.

Business background (para 73/90). Let me snooze a merchant, not the channel. My grocery store is not a threat model.

Business background (para 74/90). The alert never says what TO do, only what happened. Actionable would be a button, not a paragraph.

Business background (para 75/90). Weekend alerts route to whoever is awake, which is whoever is newest. Experience sleeps through nothing, but gets no alerts.

Business background (para 76/90). Digest mode exists, they told me, buried in settings I need a map to find. Discovery is part of the product.

Business background (para 77/90). Two genuine frauds last year, both caught by customers calling us, not by alerts. Sit with that before adding more.

Business background (para 78/90). Every month I export PDFs, screenshot the weird ones, and email my accountant a puzzle. She bills me to solve it.

Business background (para 79/90). Technically that's a broken workflow. Shared access with scoped permissions would end the screenshot era.

Business background (para 80/90). I tell every client this: give me view access and we both save three hours. Nobody does. They fear I'll see everything.

Business background (para 81/90). Caregiver access has to say exactly what is shared — same for accountants. Granular scopes or nothing.

Business background (para 82/90). I check it twice because once I sent the wrong month and paid for the hour it took to unsee it.

Business background (para 83/90). The month-end email thread has fourteen messages and zero decisions. Decisions live in calls the software never sees.

Business background (para 84/90). Comment threads on transactions would end this. Annotate the weird one where it lives, not in email exile.

Business background (para 85/90). My accountant's portal login expired silently. I found out at 11pm on the 31st. Notifications are a feature.

Business background (para 86/90). Permissions are all-or-nothing, so I choose nothing and pay in screenshots. The pricing page should say that.

Business background (para 87/90). Version control for books: who changed what, when, with what note. Git for money. I'd pay double.

Business background (para 88/90). She asked for 'the backup'. I sent a zip of inscrutable exports. We both pretended that was fine.

Business background (para 89/90). Scoped access needs an expiry date or owners will never grant it. Trust with a timer.

Business background (para 90/90). We outgrew the deposit limit on a good month and found out via a rejected check. Success, punished.

Stage: discovery synthesis complete (this corpus); delivery decisions pending human approval. Success = measurable drops in receivables chase time, receipt loss, approval latency, reconciliation rework, payroll-float scrambles, Spanish support calls, handoff repeats, false-alarm fatigue, screenshot accounting, and deposit-limit surprises.

Success criteria (para 1/70). Technically that's a substantiation failure. No receipt, no deduction. I tell every client this.

Success criteria (para 2/70). Thermal paper fades. By March the January receipts are blank ghosts and I'm reconstructing from card statements.

Success criteria (para 3/70). The app wants the total, the tax, the category, and my patience — in that order, at the busiest minute of the day.

Success criteria (para 4/70). I batch on Fridays and half the pile is mystery paper. Whose lunch was this? Business or sorry?

Success criteria (para 5/70). Mileage, parking, tolls — the small stuff leaks around the edges of every system I've tried.

Success criteria (para 6/70). A photo of a photo of a receipt. That's what my February looks like. Try auditing that.

Success criteria (para 7/70). Cash purchases at the supply house never make it in. The owner pays cash, tells me Monday, I believe him on faith.

Success criteria (para 8/70). Give me a shoebox mode: dump everything in, sort it Sunday, nag me only about the orphans.

Success criteria (para 9/70). Everything over five hundred needs my sign-off, and I'm on a ladder half the day. The whole company queues behind my phone battery.

Success criteria (para 10/70). For licensing I need two signatures on file. When one is on vacation, payroll-adjacent spending just waits.

Success criteria (para 11/70). I do it in batches on Fridays, but approvals don't batch. They rot, one by one, in an inbox nobody owns.

Success criteria (para 12/70). In our old system, delegation worked: deputy approves under a cap, full audit trail. I measured the delay drop.

Success criteria (para 13/70). Per our incident review, single-approver chains are a control gap. That is a finding, not feedback.

Success criteria (para 14/70). The approver sees an amount with no context. Approve what? For whom? Against which job? It's a blind signature.

Success criteria (para 15/70). Emergency purchases route around the chain entirely, then get scolded retroactively. The system trains circumvention.

Success criteria (para 16/70). I approved something at a red light once. Never again — but the app let me, no questions asked.

Success criteria (para 17/70). Weekend approvals pile to Monday and Monday is already full. The chain has no concept of urgency, only order.

Success criteria (para 18/70). Two partners must both approve, but the app notifies them sequentially. Parallel would halve the wait and nobody can explain why it doesn't.

Success criteria (para 19/70). The audit trail shows who clicked, not what they knew. That's a signature without informed consent.

Success criteria (para 20/70). Deputy coverage exists on paper. In practice the deputy can't see the attachments, so they approve blind or not at all.

Success criteria (para 21/70). The auto-match is magic. Ninety percent right, and I fix the rest with coffee. Don't take it away.

Success criteria (para 22/70). Boats don't wait for reconciliation. If the feed guesses right, I sail. If not, I fix it in winter.

Success criteria (para 23/70). The correct treatment is review-then-post, never post-then-review. Auto-posting buries errors where auditors find them.

Success criteria (para 24/70). I always worry that a wrong match sits there looking correct. Correct-looking wrongness is the most expensive kind.

Success criteria (para 25/70). Show me confidence per match and I'll review the shaky ten percent gladly. Certainty theater I will not accept.

Success criteria (para 26/70). Last April it matched a supplier payment to the wrong job. We underbilled by nine hundred and found out in July.

Success criteria (para 27/70). The override log is where trust lives. If I can see who confirmed what and undo it, I'll let it guess.

Success criteria (para 28/70). Speed matters more than purity in season. I'll take 90% auto with a clean review queue over 100% manual and drowning.

Success criteria (para 29/70). My old ERP never guessed. It also never finished. There is a middle I would pay for.

Success criteria (para 30/70). Duplicate detection is the real hero, not matching. Catch the double-charge and I'll forgive ten bad guesses.

Success criteria (para 31/70). Quarter-end turns every guess into a fact nobody re-examines. The calendar launders uncertainty.

Success criteria (para 32/70). Train it on my corrections, visibly. If it learns my vendors, it's a colleague. If not, it's a slot machine.

Success criteria (para 33/70). Payroll hits Thursday, client payments land Friday. Every week I float the gap on a credit card and pretend it's strategy.

Success criteria (para 34/70). I measured this, actually: eleven weeks last year where payroll preceded receivables by more than two days.

Success criteria (para 35/70). For licensing I need payroll records clean to the day. The float makes clean impossible.

Success criteria (para 36/70). Three times last quarter I moved money between accounts at midnight to make morning payroll. That's not banking, that's parkour.

Success criteria (para 37/70). Honestly? A calendar that shows cash against payroll dates would change my life more than any report.

Success criteria (para 38/70). New hires don't know the float exists until their first short Friday. Then they know, loudly.

Success criteria (para 39/70). Overtime posts late, so Thursday's payroll is always a guess dressed as a number.

Success criteria (para 40/70). The payroll provider debits a day early 'for processing'. That day costs me sleep and overdraft math.

Success criteria (para 41/70). I keep a secret spreadsheet called 'Thursday'. My bank has no idea Thursday exists.

Success criteria (para 42/70). Contractors versus employees, two rhythms, one account. The app shows a balance; I need a choreography.

Success criteria (para 43/70). Holiday weeks compress everything and nobody warns you. Last Thanksgiving I learned by overdraft.

Success criteria (para 44/70). If the app said 'this Thursday needs $4,100 you don't have yet', I'd kiss it. Professionally.

Success criteria (para 45/70). The Spanish version says 'cargo por sobregiro' where the English says 'overdraft protection transfer'. Those are not the same thing and my customers notice.

Success criteria (para 46/70). Language consistency matters because one unclear word can trigger a phone call. We get forty such calls a week.

Success criteria (para 47/70). My screen reader says the language attribute flips mid-sentence. It reads Spanish with English pronunciation. Try understanding that at speed.

Success criteria (para 48/70). The fee schedule has eleven footnotes in English and four in Spanish. Guess which seven fees surprise people.

Success criteria (para 49/70). Disclosure timing differs: English shows it pre-confirm, Spanish post-confirm. Same bank, different truth.

Success criteria (para 50/70). Nobody tested this with a keyboard, did they. Tab order follows the English layout even on the Spanish page.

Success criteria (para 51/70). My mother trusts the Spanish page more and understands it less. That combination should frighten a bank.

Success criteria (para 52/70). Error messages are translated by someone who never saw the error. 'Inténtelo más tarde' for a locked account is not advice, it's abandonment.

Success criteria (para 53/70). The glossary contradicts the statements on three terms I counted. I stopped counting after three.

Success criteria (para 54/70). Bilingual staff improvise translations at the counter. Improvisation is not a localization strategy.

Success criteria (para 55/70). Statements should carry both languages side by side for key terms. Redundancy here is clarity, not clutter.

Success criteria (para 56/70). When the app updates, English ships first and Spanish 'follows'. It follows by months. Customers notice the lag before the words.

Success criteria (para 57/70). A customer starts online, finishes at my window, and I know nothing. They repeat everything, slower, angrier.

Success criteria (para 58/70). For older customers, starting over isn't an inconvenience, it's a reason to leave the bank.

Success criteria (para 59/70). I walk them through it, step by step, but I'm walking blind. Their online steps are invisible to me.

Success criteria (para 60/70). The screen reader reads the whole table, every time. Imagine that, then imagine repeating it to a human who also can't see it.

Success criteria (para 61/70). At the window you see it all: the apology, the repetition, the sigh when I ask for the account number they already typed.

Success criteria (para 62/70). The queue display says six minutes. The repeat-story tax makes it eleven. Nobody measures the tax.

Success criteria (para 63/70). Customers bring screenshots of their own accounts as proof of their own money. Let that sink in.

Success criteria (para 64/70). Handoff notes exist but nobody writes them because the field is buried three tabs deep during a rush.

Success criteria (para 65/70). The online flow collects the reason for visit, then drops it. I ask 'what brings you in' to someone who already answered.

Success criteria (para 66/70). Privacy theater: I can't see their online steps 'for security', but I can see their balance. Explain that logic.

Success criteria (para 67/70). After a bad handoff they don't blame the channel, they blame me, by name, in surveys.

Success criteria (para 68/70). A simple 'customer already tried X' banner would save my mornings. It has never existed.

Success criteria (para 69/70). Ninety percent of these are noise. I cleared forty-three before lunch. Every false alarm teaches customers to ignore the real one.

Success criteria (para 70/70). Per our incident review, alert coverage is a control gap. That is a finding, not feedback. We need more signals, not fewer.

Constraints: no core-banking replacement; accessibility WCAG 2.2 AA throughout; Spanish parity is a launch gate, not fast-follow; every automation ships with an undo path and an audit trail.

Constraints (para 1/70). I want one screen: who, how much, how late, last touch, next nudge — and a button that does the nudge.

Constraints (para 2/70). The receipt is in my apron pocket, then the van, then the laundry. By Friday it's a rumor.

Constraints (para 3/70). My shortcut is snapping it at the register, but half the time the photo is blurry and the app rejects it without saying why.

Constraints (para 4/70). I check it twice because once I lost a four-hundred-dollar receipt and Mara trusts me and that terrifies me.

Constraints (para 5/70). If it takes more than three clicks I hate it. At the counter there are no three clicks to spare.

Constraints (para 6/70). Technically that's a substantiation failure. No receipt, no deduction. I tell every client this.

Constraints (para 7/70). Thermal paper fades. By March the January receipts are blank ghosts and I'm reconstructing from card statements.

Constraints (para 8/70). The app wants the total, the tax, the category, and my patience — in that order, at the busiest minute of the day.

Constraints (para 9/70). I batch on Fridays and half the pile is mystery paper. Whose lunch was this? Business or sorry?

Constraints (para 10/70). Mileage, parking, tolls — the small stuff leaks around the edges of every system I've tried.

Constraints (para 11/70). A photo of a photo of a receipt. That's what my February looks like. Try auditing that.

Constraints (para 12/70). Cash purchases at the supply house never make it in. The owner pays cash, tells me Monday, I believe him on faith.

Constraints (para 13/70). Give me a shoebox mode: dump everything in, sort it Sunday, nag me only about the orphans.

Constraints (para 14/70). Everything over five hundred needs my sign-off, and I'm on a ladder half the day. The whole company queues behind my phone battery.

Constraints (para 15/70). For licensing I need two signatures on file. When one is on vacation, payroll-adjacent spending just waits.

Constraints (para 16/70). I do it in batches on Fridays, but approvals don't batch. They rot, one by one, in an inbox nobody owns.

Constraints (para 17/70). In our old system, delegation worked: deputy approves under a cap, full audit trail. I measured the delay drop.

Constraints (para 18/70). Per our incident review, single-approver chains are a control gap. That is a finding, not feedback.

Constraints (para 19/70). The approver sees an amount with no context. Approve what? For whom? Against which job? It's a blind signature.

Constraints (para 20/70). Emergency purchases route around the chain entirely, then get scolded retroactively. The system trains circumvention.

Constraints (para 21/70). I approved something at a red light once. Never again — but the app let me, no questions asked.

Constraints (para 22/70). Weekend approvals pile to Monday and Monday is already full. The chain has no concept of urgency, only order.

Constraints (para 23/70). Two partners must both approve, but the app notifies them sequentially. Parallel would halve the wait and nobody can explain why it doesn't.

Constraints (para 24/70). The audit trail shows who clicked, not what they knew. That's a signature without informed consent.

Constraints (para 25/70). Deputy coverage exists on paper. In practice the deputy can't see the attachments, so they approve blind or not at all.

Constraints (para 26/70). The auto-match is magic. Ninety percent right, and I fix the rest with coffee. Don't take it away.

Constraints (para 27/70). Boats don't wait for reconciliation. If the feed guesses right, I sail. If not, I fix it in winter.

Constraints (para 28/70). The correct treatment is review-then-post, never post-then-review. Auto-posting buries errors where auditors find them.

Constraints (para 29/70). I always worry that a wrong match sits there looking correct. Correct-looking wrongness is the most expensive kind.

Constraints (para 30/70). Show me confidence per match and I'll review the shaky ten percent gladly. Certainty theater I will not accept.

Constraints (para 31/70). Last April it matched a supplier payment to the wrong job. We underbilled by nine hundred and found out in July.

Constraints (para 32/70). The override log is where trust lives. If I can see who confirmed what and undo it, I'll let it guess.

Constraints (para 33/70). Speed matters more than purity in season. I'll take 90% auto with a clean review queue over 100% manual and drowning.

Constraints (para 34/70). My old ERP never guessed. It also never finished. There is a middle I would pay for.

Constraints (para 35/70). Duplicate detection is the real hero, not matching. Catch the double-charge and I'll forgive ten bad guesses.

Constraints (para 36/70). Quarter-end turns every guess into a fact nobody re-examines. The calendar launders uncertainty.

Constraints (para 37/70). Train it on my corrections, visibly. If it learns my vendors, it's a colleague. If not, it's a slot machine.

Constraints (para 38/70). Payroll hits Thursday, client payments land Friday. Every week I float the gap on a credit card and pretend it's strategy.

Constraints (para 39/70). I measured this, actually: eleven weeks last year where payroll preceded receivables by more than two days.

Constraints (para 40/70). For licensing I need payroll records clean to the day. The float makes clean impossible.

Constraints (para 41/70). Three times last quarter I moved money between accounts at midnight to make morning payroll. That's not banking, that's parkour.

Constraints (para 42/70). Honestly? A calendar that shows cash against payroll dates would change my life more than any report.

Constraints (para 43/70). New hires don't know the float exists until their first short Friday. Then they know, loudly.

Constraints (para 44/70). Overtime posts late, so Thursday's payroll is always a guess dressed as a number.

Constraints (para 45/70). The payroll provider debits a day early 'for processing'. That day costs me sleep and overdraft math.

Constraints (para 46/70). I keep a secret spreadsheet called 'Thursday'. My bank has no idea Thursday exists.

Constraints (para 47/70). Contractors versus employees, two rhythms, one account. The app shows a balance; I need a choreography.

Constraints (para 48/70). Holiday weeks compress everything and nobody warns you. Last Thanksgiving I learned by overdraft.

Constraints (para 49/70). If the app said 'this Thursday needs $4,100 you don't have yet', I'd kiss it. Professionally.

Constraints (para 50/70). The Spanish version says 'cargo por sobregiro' where the English says 'overdraft protection transfer'. Those are not the same thing and my customers notice.

Constraints (para 51/70). Language consistency matters because one unclear word can trigger a phone call. We get forty such calls a week.

Constraints (para 52/70). My screen reader says the language attribute flips mid-sentence. It reads Spanish with English pronunciation. Try understanding that at speed.

Constraints (para 53/70). The fee schedule has eleven footnotes in English and four in Spanish. Guess which seven fees surprise people.

Constraints (para 54/70). Disclosure timing differs: English shows it pre-confirm, Spanish post-confirm. Same bank, different truth.

Constraints (para 55/70). Nobody tested this with a keyboard, did they. Tab order follows the English layout even on the Spanish page.

Constraints (para 56/70). My mother trusts the Spanish page more and understands it less. That combination should frighten a bank.

Constraints (para 57/70). Error messages are translated by someone who never saw the error. 'Inténtelo más tarde' for a locked account is not advice, it's abandonment.

Constraints (para 58/70). The glossary contradicts the statements on three terms I counted. I stopped counting after three.

Constraints (para 59/70). Bilingual staff improvise translations at the counter. Improvisation is not a localization strategy.

Constraints (para 60/70). Statements should carry both languages side by side for key terms. Redundancy here is clarity, not clutter.

Constraints (para 61/70). When the app updates, English ships first and Spanish 'follows'. It follows by months. Customers notice the lag before the words.

Constraints (para 62/70). A customer starts online, finishes at my window, and I know nothing. They repeat everything, slower, angrier.

Constraints (para 63/70). For older customers, starting over isn't an inconvenience, it's a reason to leave the bank.

Constraints (para 64/70). I walk them through it, step by step, but I'm walking blind. Their online steps are invisible to me.

Constraints (para 65/70). The screen reader reads the whole table, every time. Imagine that, then imagine repeating it to a human who also can't see it.

Constraints (para 66/70). At the window you see it all: the apology, the repetition, the sigh when I ask for the account number they already typed.

Constraints (para 67/70). The queue display says six minutes. The repeat-story tax makes it eleven. Nobody measures the tax.

Constraints (para 68/70). Customers bring screenshots of their own accounts as proof of their own money. Let that sink in.

Constraints (para 69/70). Handoff notes exist but nobody writes them because the field is buried three tabs deep during a rush.

Constraints (para 70/70). The online flow collects the reason for visit, then drops it. I ask 'what brings you in' to someone who already answered.