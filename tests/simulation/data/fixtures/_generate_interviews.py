#!/usr/bin/env python3
"""Generate the large interview compilation fixture (~50KB).
Run: python3 tests/simulation/data/fixtures/_generate_interviews.py
"""

import random
import os

random.seed(99)

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))

participants = [
    {"id": "P01", "name": "Sarah Chen", "age": 29, "role": "Product Designer", "company": "TechFlow", "context": "mobile app redesign project"},
    {"id": "P02", "name": "Marcus Williams", "age": 45, "role": "Engineering Manager", "company": "DataSync Corp", "context": "team collaboration tools"},
    {"id": "P03", "name": "Elena Rodriguez", "age": 34, "role": "UX Researcher", "company": "HealthFirst", "context": "patient portal usability"},
    {"id": "P04", "name": "James Okafor", "age": 52, "role": "VP of Operations", "company": "LogiRoute", "context": "supply chain dashboard"},
    {"id": "P05", "name": "Aisha Patel", "age": 27, "role": "Junior Developer", "company": "StartupLabs", "context": "developer onboarding experience"},
    {"id": "P06", "name": "Robert Kim", "age": 61, "role": "Retired Teacher", "company": "N/A", "context": "educational platform usability"},
    {"id": "P07", "name": "Lisa Fernandez", "age": 38, "role": "Marketing Director", "company": "BrandForge", "context": "analytics dashboard redesign"},
    {"id": "P08", "name": "David Thompson", "age": 43, "role": "Freelance Consultant", "company": "Self-employed", "context": "project management tools"},
    {"id": "P09", "name": "Fatima Al-Hassan", "age": 31, "role": "Data Scientist", "company": "InsightAI", "context": "data visualization tools"},
    {"id": "P10", "name": "Thomas Mueller", "age": 55, "role": "CFO", "company": "FinanceFirst GmbH", "context": "financial reporting platform"},
    {"id": "P11", "name": "Priya Sharma", "age": 26, "role": "Content Strategist", "company": "MediaPulse", "context": "CMS usability evaluation"},
    {"id": "P12", "name": "Carlos Mendes", "age": 48, "role": "Small Business Owner", "company": "Mendes Bakery", "context": "POS and inventory system"},
    {"id": "P13", "name": "Jennifer O'Brien", "age": 36, "role": "Nurse Practitioner", "company": "City Medical Center", "context": "electronic health records"},
    {"id": "P14", "name": "Kwame Asante", "age": 33, "role": "Product Manager", "company": "PayQuick", "context": "mobile payment checkout flow"},
    {"id": "P15", "name": "Marina Volkov", "age": 41, "role": "HR Director", "company": "GlobalStaff Inc", "context": "employee onboarding platform"},
]

# Questions and participant-specific answer templates
interview_exchanges = [
    {
        "q": "Thank you for joining us today. Could you start by telling me a bit about your role and how you typically use {context_tool} in your daily work?",
        "answers": [
            "Sure, thanks for having me. I'm a {role} at {company} and I've been in this role for about {years} years now. My daily work involves {daily_work}. I typically spend about {hours} hours a day using the tool, mostly for {primary_use}. It's become pretty central to how our team operates.",
            "Of course. As a {role}, my main responsibilities include {responsibilities}. I started using the tool about {months} months ago when {trigger}. Now it's become an essential part of my workflow, especially for {primary_use}.",
            "Happy to be here. I work as a {role} at {company}. My typical day starts with checking {first_check} and then I move into {primary_use}. I'd say the tool is moderately integrated into my workflow — there are some things I love about it and some things that still frustrate me."
        ]
    },
    {
        "q": "Can you walk me through a typical task you perform with the tool? What does the process look like from start to finish?",
        "answers": [
            "So the typical workflow would be: first I open the dashboard and check for any new {items}. Then I navigate to the {section} section to review what needs my attention. From there, I usually need to {action1}, which involves clicking through about {clicks} screens. Then I {action2}. The whole process takes roughly {time} minutes on a good day, but it can stretch to {time2} minutes when the system is slow or I hit an unexpected issue.",
            "Let me walk you through my most common task. I start by logging in — which by the way takes longer than it should because of the {login_issue}. Once I'm in, I go to {section} and look for {items}. Then I need to {action1}. The tricky part is when I need to {action2} because the interface doesn't make it obvious how to do that. I usually end up going back and forth between two or three screens.",
            "A typical task for me involves {action1}. I do this maybe {frequency} times a day. The process starts at the main {section} page where I can see an overview. Then I drill down into the details by clicking on specific {items}. From there I {action2}. What I find frustrating is that there's no way to {missing_feature}, so I end up doing a lot of manual work that could probably be automated."
        ]
    },
    {
        "q": "When you mentioned {reference}, can you tell me more about that experience? What exactly happens and how does it make you feel?",
        "answers": [
            "Yeah, that's a real pain point for me. So what happens is {problem_detail}. This typically occurs about {frequency} times a week. When it happens, I feel {emotion} because {reason}. I've tried {workaround} to get around it, but it's not ideal. I know other people on my team feel the same way because we've discussed it in our retrospectives.",
            "Sure. So the issue is that {problem_detail}. It's been like this since {timeframe}. The thing that really bothers me is {specific_frustration}. I've reported it to support twice and both times they said it was a known issue and would be fixed in the next release, but it's still there. I've developed a workaround where I {workaround}, but it adds about {extra_time} minutes to the task.",
            "Right, so that happens when {trigger}. The system {problem_detail}. It's not just annoying — it actually impacts my productivity because I have to {consequence}. I'd estimate I lose about {lost_time} minutes per day dealing with this. My colleague suggested {workaround} but it only works some of the time."
        ]
    },
    {
        "q": "How does this compare to other tools you've used for similar purposes? What stands out as different?",
        "answers": [
            "I've used {competitor1} and {competitor2} before switching to this tool. Compared to {competitor1}, this is definitely {comparison1}. The thing {competitor1} did better was {strength1}, but this tool wins on {strength2}. Compared to {competitor2}, it's a mixed bag — the interface is cleaner here but {competitor2} had better {feature}. Overall I'd say this is the best option available right now, but there's room for improvement.",
            "Before this, we were using {competitor1} which was {comp1_assessment}. We switched because {switch_reason}. The biggest improvement has been {improvement}. But I do miss {missed_feature} from {competitor1}. I also briefly tried {competitor2} but found it {comp2_assessment}. What really sets this tool apart is {differentiator}.",
            "I've tried a few alternatives. {competitor1} was too {comp1_issue} for our needs. {competitor2} was good but {comp2_issue}. This tool hits a sweet spot in terms of {strength}, although I think it could learn from {competitor1}'s approach to {feature}. The pricing is also more reasonable than the alternatives, which matters for us as a {company_size} company."
        ]
    },
    {
        "q": "If you could change one thing about the tool, what would it be and why?",
        "answers": [
            "That's easy — I would completely redesign the {feature} experience. Right now it requires {current_steps} steps and involves {pain_point}. If I could wave a magic wand, I'd make it so you can {ideal_state}. This would save me at least {time_savings} per week and I think it would make the biggest difference for most users.",
            "Hmm, just one thing? That's tough. I think the most impactful change would be {change}. The reason is that {reason}. Currently I have to {current_process} which is tedious and error-prone. If this were improved, it would benefit not just me but our entire team of {team_size} people who all deal with the same issue.",
            "I would add {feature}. It's something I've been requesting for months. The current workaround is {workaround} but it's clunky and unreliable. Having native support for this would be transformative because {benefit}. I actually checked the feature request board and it's the second most voted request, so clearly I'm not alone in wanting this."
        ]
    },
    {
        "q": "Tell me about a time when the tool really helped you accomplish something important. What happened?",
        "answers": [
            "There was this one time when {situation}. We were under a tight deadline and needed to {urgent_task}. I was able to use the {feature} to {action}. It probably saved us {time_saved} hours compared to doing it manually. My manager was impressed and it actually became a template that our whole department now uses. That's when I really started to appreciate the tool.",
            "Last month we had a {crisis_type} and I needed to {urgent_task} quickly. The tool's {feature} feature was absolutely crucial. I was able to {action} in under {time} minutes, which normally would have taken {manual_time}. It was a real 'this is why we pay for this tool' moment. The team was really grateful.",
            "Yes, actually. During our {event}, I needed to {urgent_task}. The {feature} functionality made it possible to {action}. Without the tool, I would have had to {manual_alternative}, which would have been much slower. It was one of those experiences that justified the investment in the tool."
        ]
    },
    {
        "q": "How do you typically get help when you're stuck? What resources do you turn to?",
        "answers": [
            "First I'll try to figure it out myself by {self_help}. If that doesn't work, I check the {resource1}. The documentation is {doc_quality} — {doc_detail}. If I'm still stuck, I'll ask a colleague or post in our team's {channel}. As a last resort, I contact support, which usually takes {support_time} to get a response. I wish the in-app help was better because right now it's basically {help_assessment}.",
            "I have a few go-to strategies. First, I try the search function within the tool to see if there's a relevant help article. The results are hit-or-miss — sometimes I find exactly what I need, other times the search returns completely irrelevant content. Then I'll check {resource1} or watch a YouTube tutorial. Our team also has a shared document where we document common issues and solutions, which has been really valuable. Support is my last resort because {support_issue}.",
            "Honestly, I usually ask {colleague_name} on my team because they've been using the tool longer than I have. The official documentation is {doc_quality} and {doc_detail}. I've tried the chatbot help feature a few times but it just directs me to generic FAQ articles that don't address my specific issue. What I'd really love is contextual help — like when I'm on a specific screen and I'm confused, I should be able to get help about that exact feature."
        ]
    },
    {
        "q": "What's your experience with the mobile version of the tool, if you've used it?",
        "answers": [
            "I use the mobile version {frequency}. It's {overall_assessment}. The main things I do on mobile are {mobile_tasks}. What works well is {mobile_strength}. What doesn't work well is {mobile_weakness}. I've had the app crash {crash_frequency}, which is {crash_sentiment}. If I had to rate the mobile experience compared to desktop, I'd give it a {rating} out of 10.",
            "I tried the mobile app when it first launched but stopped using it after {timeframe} because {reason}. The layout was {layout_issue} and I couldn't {blocker}. I've heard they've updated it since then, but I haven't given it another chance. For now, if I need to access the tool on the go, I just use the mobile browser which is {browser_assessment}.",
            "The mobile experience is actually one of the stronger aspects. I use it {frequency}, mainly for {mobile_tasks}. The responsive design works well for {mobile_strength}. My main complaint is {mobile_weakness}. Also, the notifications from the app can be {notification_issue}. But overall it's usable and I appreciate having the option when I'm away from my desk."
        ]
    },
    {
        "q": "How has using this tool affected your team's collaboration and communication?",
        "answers": [
            "It's had a {overall_impact} impact on our collaboration. Before we adopted the tool, we were {before_state}. Now we can {capability}. The biggest improvement has been in {area}. However, there are still some gaps — for example, {gap}. I'd say our team communication has improved by about {percentage}% since we started using it, though some of that improvement came from other changes we made around the same time.",
            "Honestly, it's been transformative for certain workflows and neutral for others. The {feature1} feature has completely changed how we {process1} — it used to take us {old_time} and now it takes {new_time}. But the {feature2} feature hasn't lived up to expectations. Our team tried using it for {use_case} but found it too {limitation} and went back to using {alternative}.",
            "The collaboration features are adequate but not exceptional. We use the {feature} for day-to-day coordination, which works fine. But when we need to do {advanced_task}, we still fall back to {alternative} because the tool's version of that functionality is {assessment}. I think if they invested more in the real-time collaboration aspects, it could replace at least two other tools we currently use."
        ]
    },
    {
        "q": "Looking ahead, what features or improvements would make the biggest difference for you over the next six months?",
        "answers": [
            "There are three things on my wish list. First, {wish1} — this would address the biggest daily frustration. Second, {wish2} — this would help us scale better as our team grows. Third, {wish3} — this is more of a nice-to-have but it would really streamline our workflow. If I had to prioritize, {wish1} is by far the most important because {reason}.",
            "For me, the number one priority would be {wish1}. We're planning to {future_plan} and without this feature, we'll likely need to {alternative}. Beyond that, I'd love to see {wish2} and {wish3}. The competitive landscape is changing fast and tools like {competitor} are already offering {competitive_feature}, so there's pressure to keep up.",
            "Better {wish1} is critical. We're losing {time} hours per week because of the current limitations. After that, I'd want {wish2} — especially with {industry_trend}, this is becoming table stakes. And {wish3} would be the cherry on top. I've actually submitted all three as feature requests on the feedback portal, so hopefully the product team is listening."
        ]
    },
    {
        "q": "Is there anything else you'd like to share that we haven't covered?",
        "answers": [
            "Just one more thing — I want to emphasize that despite my criticisms, I do think the tool is {overall_sentiment}. The team behind it seems {team_assessment} and the last few updates have shown they're listening to user feedback. I'm {outlook} about where it's heading. Thank you for taking the time to hear my perspective.",
            "I think we covered most of it. I'd just add that {additional_point}. And I appreciate you doing this research — it makes me feel like the company actually cares about the user experience, which hasn't always been the case with other tools I've used. I hope my feedback is useful.",
            "One thing I forgot to mention — {additional_point}. Also, the pricing model could use some rethinking. Currently we pay per {pricing_unit} which means {pricing_issue}. A more flexible pricing model would help organizations like ours that {org_characteristic}. Other than that, I think this was a thorough conversation. Thanks for including me."
        ]
    }
]

# Fill-in values for generating varied responses
fill_values = {
    "years": [2, 3, 4, 5, 6, 7, 8],
    "months": [3, 6, 8, 12, 14, 18],
    "hours": [2, 3, 4, 5, 6],
    "clicks": [3, 4, 5, 6, 7, 8],
    "time": [5, 8, 10, 12, 15, 20],
    "time2": [15, 20, 25, 30, 40],
    "frequency": ["2-3", "4-5", "daily", "a few", "several", "many"],
    "team_size": [4, 6, 8, 10, 12, 15, 20],
    "percentage": [20, 30, 40, 50, 60],
    "rating": [4, 5, 6, 7, 8],
    "time_saved": [2, 3, 5, 8, 10],
    "time_savings": ["2 hours", "3 hours", "half a day", "4 hours", "a full day"],
    "extra_time": [5, 10, 15, 20],
    "lost_time": [10, 15, 20, 30, 45],
    "daily_work": [
        "managing project timelines and resource allocation",
        "analyzing user data and creating reports",
        "coordinating between design and engineering teams",
        "reviewing customer feedback and prioritizing features",
        "managing client relationships and project deliverables",
    ],
    "primary_use": [
        "tracking project progress and assigning tasks",
        "generating reports and sharing insights with stakeholders",
        "managing team workloads and deadlines",
        "communicating with clients and documenting decisions",
        "analyzing data trends and creating visualizations",
    ],
    "responsibilities": [
        "overseeing the design system and conducting user research",
        "leading the engineering team and reviewing technical architecture",
        "managing product strategy and stakeholder alignment",
        "coordinating cross-functional projects and reporting to leadership",
        "building and maintaining data pipelines and dashboards",
    ],
    "section": ["projects", "dashboard", "analytics", "team", "reports", "settings"],
    "items": ["updates", "notifications", "tasks", "messages", "alerts", "requests"],
    "competitor1": ["Notion", "Asana", "Monday.com", "Jira", "ClickUp", "Basecamp"],
    "competitor2": ["Trello", "Linear", "Slack", "Figma", "Miro", "Airtable"],
    "trigger": [
        "our previous tool was discontinued",
        "we needed better reporting capabilities",
        "the team outgrew our spreadsheet-based system",
        "our client requested we use this specific platform",
        "we evaluated several options and this scored highest",
    ],
    "first_check": ["notifications", "the dashboard", "my inbox", "the task board", "team updates"],
    "action1": [
        "create a new entry and fill in the required fields",
        "review the pending items and update their status",
        "filter the data by date range and department",
        "export the results and format them for the stakeholder presentation",
        "assign tasks to team members and set due dates",
    ],
    "action2": [
        "share it with the relevant team members for review",
        "cross-reference it with data from another system",
        "add comments and tag specific people for follow-up",
        "generate a summary report and send it to leadership",
        "archive the completed items and move to the next batch",
    ],
    "problem_detail": [
        "the page freezes for about 10 seconds whenever I try to filter a large dataset",
        "the auto-save feature sometimes fails silently and I lose my changes",
        "the search function returns results that don't match my query at all",
        "the export takes forever and sometimes produces a corrupted file",
        "the notification system sends alerts for things I've explicitly turned off",
    ],
    "emotion": ["frustrated", "anxious", "annoyed", "overwhelmed", "confused"],
    "reason": [
        "I'm on a deadline and can't afford to lose time to tool issues",
        "it undermines my confidence in the system's reliability",
        "I've already reported this and nothing has changed",
        "it disrupts my flow and takes me out of deep work",
        "other people depend on my work being accurate and timely",
    ],
    "workaround": [
        "refreshing the page and starting over",
        "using a different browser",
        "exporting the data and working in a spreadsheet",
        "asking a colleague to do it from their account",
        "breaking the task into smaller pieces",
    ],
    "situation": [
        "our quarterly review was moved up by a week",
        "a major client requested a comprehensive analysis",
        "we discovered a critical data issue right before a presentation",
        "the team needed to onboard 15 new people in one week",
        "we had to migrate data from our old system on short notice",
    ],
    "feature": ["batch processing", "template", "automation", "reporting", "integration"],
    "doc_quality": ["decent", "mediocre", "okay but incomplete", "quite good", "outdated"],
    "resource1": ["the knowledge base", "the community forum", "Stack Overflow", "YouTube tutorials"],
    "support_time": ["a few hours", "about a day", "2-3 days", "up to a week"],
    "overall_assessment": ["decent but limited", "adequate for basic tasks", "improving but not great", "surprisingly good"],
    "mobile_tasks": ["checking notifications and quick updates", "reviewing dashboards on the go", "approving requests and responding to messages"],
    "mobile_strength": ["the notification system and quick actions", "the responsive layout on most screens", "the offline caching of recent data"],
    "mobile_weakness": ["the data entry experience on small screens", "the navigation menu is hard to reach one-handed", "complex features are hidden or unavailable"],
    "overall_impact": ["significant positive", "moderately positive", "mixed", "noticeable"],
    "before_state": [
        "passing spreadsheets back and forth via email",
        "having long meetings to sync on project status",
        "using three different tools that didn't integrate well",
        "relying on tribal knowledge that wasn't documented anywhere",
    ],
    "wish1": [
        "better search with natural language support",
        "automated reporting with scheduled delivery",
        "a proper API for custom integrations",
        "offline mode that syncs when back online",
        "customizable dashboards with drag-and-drop widgets",
    ],
    "wish2": [
        "role-based access control with more granularity",
        "native integration with our existing tools",
        "real-time collaboration on documents",
        "advanced analytics with predictive capabilities",
    ],
    "wish3": [
        "a mobile app that matches the desktop experience",
        "dark mode across the entire interface",
        "keyboard shortcuts for power users",
        "AI-powered suggestions for task assignment",
    ],
    "overall_sentiment": ["a solid product with good potential", "one of the better options available", "valuable despite its flaws", "heading in the right direction"],
    "team_assessment": ["responsive to feedback", "committed to improvement", "transparent about their roadmap"],
    "outlook": ["cautiously optimistic", "optimistic", "hopeful"],
    "additional_point": [
        "the onboarding experience for new team members could be much smoother",
        "the accessibility of the tool needs significant improvement for screen reader users",
        "data privacy controls should be more prominent given current regulations",
        "the performance during peak hours really needs attention",
    ],
}


def fill_template(template, participant):
    """Replace placeholders with random values."""
    result = template
    result = result.replace("{role}", participant["role"])
    result = result.replace("{company}", participant["company"])
    result = result.replace("{context_tool}", participant["context"])

    for key, values in fill_values.items():
        placeholder = "{" + key + "}"
        while placeholder in result:
            val = random.choice(values)
            result = result.replace(placeholder, str(val), 1)

    # Replace any remaining unfilled placeholders with generic text
    import re
    result = re.sub(r'\{[a-z_]+\}', 'that particular aspect', result)
    return result


def generate_interview(participant, interview_num):
    """Generate a single interview transcript."""
    lines = []
    date = f"2026-{random.randint(1,3):02d}-{random.randint(1,28):02d}"
    start_hour = random.randint(9, 16)
    start_min = random.choice([0, 15, 30, 45])

    lines.append("=" * 78)
    lines.append(f"INTERVIEW TRANSCRIPT #{interview_num:02d}")
    lines.append(f"Participant: {participant['name']} ({participant['id']})")
    lines.append(f"Role: {participant['role']} at {participant['company']}")
    lines.append(f"Date: {date}")
    lines.append(f"Duration: {random.randint(35, 55)} minutes")
    lines.append(f"Interviewer: Research Team")
    lines.append(f"Context: {participant['context']}")
    lines.append("=" * 78)
    lines.append("")

    current_min = 0
    exchange_count = 0

    for exchange in interview_exchanges:
        # Generate timestamp
        total_min = start_min + current_min
        hour = start_hour + total_min // 60
        minute = total_min % 60
        timestamp = f"[{hour:02d}:{minute:02d}]"

        # Interviewer question
        question = exchange["q"].replace("{context_tool}", participant["context"])
        if "{reference}" in question:
            references = ["the loading issue", "the search problems", "the navigation confusion",
                         "the error messages", "the mobile experience", "the performance issues"]
            question = question.replace("{reference}", random.choice(references))

        lines.append(f"{timestamp} Interviewer:")
        lines.append(f"  {question}")
        lines.append("")

        # Participant response
        current_min += random.randint(1, 3)
        total_min = start_min + current_min
        hour = start_hour + total_min // 60
        minute = total_min % 60
        timestamp = f"[{hour:02d}:{minute:02d}]"

        answer_template = random.choice(exchange["answers"])
        answer = fill_template(answer_template, participant)

        lines.append(f"{timestamp} {participant['name']}:")
        # Wrap long answers
        words = answer.split()
        current_line = "  "
        for word in words:
            if len(current_line) + len(word) + 1 > 78:
                lines.append(current_line)
                current_line = "  " + word
            else:
                current_line += " " + word if current_line.strip() else "  " + word
        if current_line.strip():
            lines.append(current_line)
        lines.append("")

        # Sometimes add a follow-up probe
        if random.random() < 0.3 and exchange_count < len(interview_exchanges) - 1:
            current_min += 1
            total_min = start_min + current_min
            hour = start_hour + total_min // 60
            minute = total_min % 60
            timestamp = f"[{hour:02d}:{minute:02d}]"

            probes = [
                "Could you elaborate on that a bit more?",
                "That's interesting. Can you give me a specific example?",
                "When you say that, what does that look like in practice?",
                "How did that affect your overall workflow?",
                "Did anyone else on your team experience the same thing?",
            ]
            lines.append(f"{timestamp} Interviewer:")
            lines.append(f"  {random.choice(probes)}")
            lines.append("")

            current_min += random.randint(1, 2)
            total_min = start_min + current_min
            hour = start_hour + total_min // 60
            minute = total_min % 60
            timestamp = f"[{hour:02d}:{minute:02d}]"

            followups = [
                f"Sure. So basically what happened was that I was trying to complete a task and the system kept giving me errors. After the third attempt, I decided to try a completely different approach, which actually ended up being faster. But it shouldn't require that level of workaround for a basic operation.",
                f"Yeah, so for example last Tuesday I needed to generate a report for our weekly standup. Normally this takes about five minutes, but the filters weren't working correctly and I spent almost twenty minutes getting the right data set. I ended up just exporting everything and filtering in a spreadsheet.",
                f"In practice, it means I've developed a whole set of habits around avoiding the problematic parts of the interface. I know which buttons to avoid, which workflows to use instead, and which features are reliable. It shouldn't be this way, but after using the tool for months you learn to navigate around the rough edges.",
                f"It definitely slowed things down. Our team has a target of completing these tasks within two hours, and on days when the tool is acting up, we can barely finish within four. That has a cascading effect on everything else we need to do that day.",
                f"Actually yes. I brought it up in our last team meeting and three other people said they had the exact same issue. One person had even created a detailed bug report with screenshots. So it's not just me being picky — it's a widespread problem that affects our whole department.",
            ]
            lines.append(f"{timestamp} {participant['name']}:")
            followup = random.choice(followups)
            words = followup.split()
            current_line = "  "
            for word in words:
                if len(current_line) + len(word) + 1 > 78:
                    lines.append(current_line)
                    current_line = "  " + word
                else:
                    current_line += " " + word if current_line.strip() else "  " + word
            if current_line.strip():
                lines.append(current_line)
            lines.append("")

        current_min += random.randint(2, 5)
        exchange_count += 1

    # Add closing
    lines.append(f"[END OF INTERVIEW — {participant['id']}]")
    lines.append("")
    lines.append("")

    return "\n".join(lines)


def main():
    path = os.path.join(FIXTURES_DIR, 'large-interview-compilation.txt')

    content_parts = []
    content_parts.append("=" * 78)
    content_parts.append("     INTERVIEW COMPILATION — UX RESEARCH STUDY 2026-Q1")
    content_parts.append("     HealthBridge Patient Portal & Productivity Tools")
    content_parts.append("     15 Participant Interviews | Collected Jan-Mar 2026")
    content_parts.append("=" * 78)
    content_parts.append("")
    content_parts.append("TABLE OF CONTENTS")
    content_parts.append("-" * 40)
    for i, p in enumerate(participants, 1):
        content_parts.append(f"  Interview #{i:02d}: {p['name']} ({p['id']}) — {p['role']}")
    content_parts.append("-" * 40)
    content_parts.append("")
    content_parts.append("")

    header = "\n".join(content_parts)

    interviews = []
    for i, participant in enumerate(participants, 1):
        interviews.append(generate_interview(participant, i))

    full_content = header + "\n".join(interviews)

    with open(path, 'w') as f:
        f.write(full_content)

    size_kb = len(full_content.encode('utf-8')) / 1024
    print(f"  Large interview compilation: 15 interviews, {size_kb:.1f} KB -> {path}")


if __name__ == '__main__':
    main()
