#!/usr/bin/env python3
"""Generate CSV test data fixtures for ReClaw marathon testing.
Run: python3 tests/simulation/data/fixtures/_generate_csvs.py
"""

import csv
import random
import os
from datetime import datetime, timedelta

random.seed(42)

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))


def generate_ab_test():
    """AB test results - 500 rows."""
    devices = ['desktop', 'mobile', 'tablet']
    device_weights = [0.45, 0.40, 0.15]
    path = os.path.join(FIXTURES_DIR, 'ab-test-results-checkout-flow.csv')

    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['variant', 'user_id', 'converted', 'time_on_page_seconds',
                     'clicks', 'bounce', 'device', 'revenue'])

        for i in range(1, 501):
            variant = random.choice(['A', 'B'])
            user_id = f'usr_{random.randint(100000, 999999)}'
            device = random.choices(devices, weights=device_weights, k=1)[0]

            if variant == 'A':
                conv_prob, avg_time, avg_clicks = 0.09, 45.0, 4.2
                bounce_prob, avg_rev = 0.35, 52.0
            else:
                conv_prob, avg_time, avg_clicks = 0.12, 38.0, 3.5
                bounce_prob, avg_rev = 0.28, 58.0

            if device == 'mobile':
                conv_prob *= 0.85; avg_time *= 1.15; bounce_prob *= 1.1
            elif device == 'tablet':
                conv_prob *= 0.95; avg_time *= 1.05

            converted = random.random() < conv_prob
            time_on_page = max(3.0, random.gauss(avg_time, avg_time * 0.4))
            clicks = max(1, int(random.gauss(avg_clicks, 1.5)))
            bounce = random.random() < bounce_prob if not converted else False
            revenue = round(max(0, random.gauss(avg_rev, 20.0)), 2) if converted else 0.00

            w.writerow([variant, user_id, str(converted).lower(),
                        round(time_on_page, 1), clicks, str(bounce).lower(),
                        device, round(revenue, 2)])

    print(f"  AB test: 500 rows -> {path}")


def generate_nps():
    """NPS scores - 200 rows over 6 quarters."""
    product_areas = ['Dashboard', 'Onboarding', 'Billing', 'Reports',
                     'Notifications', 'Settings', 'Search', 'Mobile App']
    area_weights = [0.20, 0.15, 0.10, 0.15, 0.10, 0.05, 0.15, 0.10]

    promoter_comments = [
        'Love how intuitive the dashboard is. Makes my daily workflow so much smoother.',
        'The recent updates to the search functionality have been a game changer.',
        'Customer support was incredibly helpful when I had an issue last week.',
        'Best tool we have used for project management. Highly recommend.',
        'The mobile app improvements are fantastic. Much more responsive now.',
        'Onboarding was seamless. Our whole team was up and running in a day.',
        'Reports feature saves me hours every week. Very well designed.',
        'Love the new notification settings. Finally have control over what I see.',
        'This product has transformed how our team collaborates. Five stars.',
        'The billing dashboard is transparent and easy to understand.',
        'Incredible value for the price. We tried three competitors before this.',
        'The keyboard shortcuts make power users very happy.',
    ]
    passive_comments = [
        'Good product overall but the reports could be more customizable.',
        'Works well for basic needs but missing some advanced features we need.',
        'Decent platform. A few rough edges but nothing major.',
        'The mobile experience could be better. Desktop is much more polished.',
        'It does what it says but nothing exceptional. Average experience.',
        'Some features feel outdated compared to newer competitors.',
        'Generally reliable but the occasional slowdown is frustrating.',
        'Price is a bit high for what you get. Would like to see more features.',
        'The learning curve was steeper than expected but manageable.',
        'Good for small teams. Starts to show limitations at scale.',
    ]
    detractor_comments = [
        'The search is broken half the time. Very frustrating experience.',
        'Too many bugs in the latest release. Quality has gone downhill.',
        'Pricing increased 40 percent with no new features to justify it.',
        'Customer support takes days to respond. Unacceptable for a paid product.',
        'The mobile app crashes constantly on Android. Nearly unusable.',
        'Onboarding documentation is outdated and misleading.',
        'Lost data twice due to sync issues. Considering switching providers.',
        'The UI redesign made everything harder to find. Poor change management.',
        'Performance has degraded significantly over the past two quarters.',
        'Integration with our existing tools is painful and poorly documented.',
    ]

    quarters = [
        ('2025-Q1', '2025-01-01', '2025-03-31', 30),
        ('2025-Q2', '2025-04-01', '2025-06-30', 32),
        ('2025-Q3', '2025-07-01', '2025-09-30', 35),
        ('2025-Q4', '2025-10-01', '2025-12-31', 33),
        ('2026-Q1', '2026-01-01', '2026-03-31', 36),
        ('2026-Q2', '2026-04-01', '2026-06-30', 34),
    ]

    nps_probs = {
        '2025-Q1': (0.25, 0.40, 0.35),
        '2025-Q2': (0.27, 0.40, 0.33),
        '2025-Q3': (0.28, 0.42, 0.30),
        '2025-Q4': (0.30, 0.42, 0.28),
        '2026-Q1': (0.32, 0.40, 0.28),
        '2026-Q2': (0.35, 0.38, 0.27),
    }

    path = os.path.join(FIXTURES_DIR, 'nps-scores-quarterly-2025-2026.csv')
    counter = 1

    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['respondent_id', 'date', 'score', 'segment',
                     'verbatim_comment', 'product_area'])

        for qname, start_str, end_str, n_rows in quarters:
            start = datetime.strptime(start_str, '%Y-%m-%d')
            end = datetime.strptime(end_str, '%Y-%m-%d')
            p_prom, p_pass, p_det = nps_probs[qname]

            for _ in range(n_rows):
                rid = f'NPS-{counter:04d}'
                counter += 1
                date = start + timedelta(days=random.randint(0, (end - start).days))

                r = random.random()
                if r < p_prom:
                    segment = 'promoter'
                    score = random.choice([9, 9, 9, 10, 10])
                    comment = random.choice(promoter_comments)
                elif r < p_prom + p_pass:
                    segment = 'passive'
                    score = random.choice([7, 7, 8, 8])
                    comment = random.choice(passive_comments)
                else:
                    segment = 'detractor'
                    score = random.choices([0,1,2,3,4,5,6],
                                           weights=[0.02,0.03,0.05,0.10,0.15,0.30,0.35], k=1)[0]
                    comment = random.choice(detractor_comments)

                area = random.choices(product_areas, weights=area_weights, k=1)[0]
                w.writerow([rid, date.strftime('%Y-%m-%d'), score, segment, comment, area])

    print(f"  NPS: {counter-1} rows -> {path}")


def generate_sus():
    """SUS scores - 30 participants x 3 scenarios = 90 rows."""
    scenarios = ['Task A: Account Setup', 'Task B: Report Generation', 'Task C: Data Import']
    path = os.path.join(FIXTURES_DIR, 'sus-scores-usability-study.csv')

    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['participant_id', 'task_scenario', 'q1', 'q2', 'q3', 'q4', 'q5',
                     'q6', 'q7', 'q8', 'q9', 'q10', 'total_sus_score',
                     'task_success', 'time_seconds', 'errors'])

        for pid in range(1, 31):
            base_ability = random.gauss(0, 1)

            for scenario in scenarios:
                if scenario == scenarios[0]:
                    mod, base_time, base_err, succ = 0.3, 120, 1, 0.85
                elif scenario == scenarios[1]:
                    mod, base_time, base_err, succ = -0.2, 240, 2, 0.72
                else:
                    mod, base_time, base_err, succ = -0.5, 360, 3, 0.60

                qs = []
                for qi in range(1, 11):
                    if qi % 2 == 1:
                        mu = 3.2 + base_ability * 0.5 + mod * 0.5
                    else:
                        mu = 2.8 - base_ability * 0.5 - mod * 0.5
                    qs.append(int(round(max(1, min(5, random.gauss(mu, 0.8))))))

                total = sum(qs[i] - 1 if i % 2 == 0 else 5 - qs[i] for i in range(10))
                sus = max(0, min(100, total * 2.5))

                success = random.random() < (succ + base_ability * 0.1)
                time_s = max(30, int(random.gauss(base_time - base_ability*30 - mod*40,
                                                   base_time * 0.3)))
                errors = max(0, int(random.gauss(base_err - base_ability*0.5, 1.2)))

                w.writerow([f'P{pid:03d}', scenario] + qs +
                           [round(sus, 1), str(success).lower(), time_s, errors])

    print(f"  SUS: 90 rows -> {path}")


def generate_funnel():
    """Analytics funnel - 90 days x 5 steps = 450 rows."""
    steps = ['landing', 'signup', 'onboard', 'activate', 'retain']
    base_landing = 5000
    conv_rates = {'signup': 0.12, 'onboard': 0.65, 'activate': 0.45, 'retain': 0.30}

    reasons = {
        'landing': ['page_load_slow', 'unclear_value_prop', 'pricing_concerns',
                     'competitor_preference', 'bounce_no_engagement'],
        'signup': ['form_too_long', 'email_verification_abandoned', 'social_login_failed',
                   'privacy_concerns', 'pricing_page_exit'],
        'onboard': ['tutorial_skipped', 'setup_too_complex', 'missing_integration',
                     'time_constraint', 'feature_mismatch'],
        'activate': ['low_engagement', 'missing_key_feature', 'poor_performance',
                      'team_adoption_failed', 'alternative_found'],
        'retain': ['churned_pricing', 'churned_competition', 'churned_no_need',
                   'downgraded', 'seasonal_usage'],
    }

    avg_times = {'landing': 35, 'signup': 120, 'onboard': 300, 'activate': 600, 'retain': 1800}

    path = os.path.join(FIXTURES_DIR, 'analytics-funnel-conversion.csv')
    start = datetime(2025, 12, 1)

    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['date', 'step', 'users', 'conversion_rate',
                     'avg_time_seconds', 'drop_off_reason'])

        for day in range(90):
            date = start + timedelta(days=day)
            is_weekend = date.weekday() >= 5
            wk_factor = 0.6 if is_weekend else 1.0
            growth = 1.0 + day * 0.003
            noise = max(0.7, random.gauss(1.0, 0.08))

            landing = int(base_landing * wk_factor * growth * noise)
            prev = landing

            for si, step in enumerate(steps):
                if si == 0:
                    users = landing
                    cr = 1.0
                else:
                    rate = conv_rates[step] * max(0.5, random.gauss(1.0, 0.05))
                    users = int(prev * rate)
                    cr = users / prev if prev > 0 else 0

                t = max(5, random.gauss(avg_times[step], avg_times[step] * 0.25))
                reason = random.choice(reasons[step])
                w.writerow([date.strftime('%Y-%m-%d'), step, users,
                            round(cr, 4), round(t, 1), reason])
                prev = users

    print(f"  Funnel: 450 rows -> {path}")


def generate_card_sort():
    """Card sort results - 20 participants x 30 cards = 600 rows."""
    cards = [
        ('Dashboard', 'Overview'), ('Activity Feed', 'Overview'),
        ('Notifications', 'Overview'), ('Quick Stats', 'Overview'),
        ('Create Project', 'Projects'), ('Project List', 'Projects'),
        ('Project Templates', 'Projects'), ('Archive Project', 'Projects'),
        ('Team Members', 'Team'), ('Invite Users', 'Team'),
        ('Roles & Permissions', 'Team'), ('Team Activity', 'Team'),
        ('My Profile', 'Account'), ('Billing', 'Account'),
        ('Security Settings', 'Account'), ('Preferences', 'Account'),
        ('Usage Analytics', 'Reports'), ('Export Data', 'Reports'),
        ('Custom Reports', 'Reports'), ('Scheduled Reports', 'Reports'),
        ('API Keys', 'Developer'), ('Webhooks', 'Developer'),
        ('Documentation', 'Developer'), ('Changelog', 'Developer'),
        ('Help Center', 'Support'), ('Contact Support', 'Support'),
        ('Community Forum', 'Support'), ('Video Tutorials', 'Support'),
        ('Integrations', 'Settings'), ('Data Retention', 'Settings'),
    ]

    categories = ['Overview', 'Projects', 'Team', 'Account', 'Reports',
                  'Developer', 'Support', 'Settings', 'Other']

    path = os.path.join(FIXTURES_DIR, 'card-sort-results-navigation.csv')

    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['participant_id', 'card_name', 'category_assigned',
                     'expected_category', 'match', 'time_seconds', 'confidence'])

        for pid in range(1, 21):
            skill = random.gauss(0.7, 0.15)  # participant sorting ability
            for card_name, expected in cards:
                if random.random() < max(0.3, min(0.95, skill)):
                    assigned = expected
                else:
                    others = [c for c in categories if c != expected]
                    assigned = random.choice(others)

                match = str(assigned == expected).lower()
                time_s = round(max(2.0, random.gauss(8.0, 3.0)), 1)
                conf = random.choices([1,2,3,4,5],
                                       weights=[0.05,0.10,0.25,0.35,0.25], k=1)[0]

                w.writerow([f'CS-{pid:03d}', card_name, assigned,
                            expected, match, time_s, conf])

    print(f"  Card sort: 600 rows -> {path}")


def generate_tree_test():
    """Tree test results - 25 participants x 10 tasks = 250 rows."""
    tasks = [
        ('Find your recent lab results',
         'Health Records > Test Results > Laboratory',
         ['Health Records > Test Results > Laboratory',
          'Health Records > Lab Results',
          'My Health > Lab Results']),
        ('Schedule an appointment with Dr. Smith',
         'Appointments > Schedule New > Find Provider',
         ['Appointments > Schedule New > Find Provider',
          'Appointments > New Appointment',
          'Find a Doctor > Schedule']),
        ('Update your insurance information',
         'Account > Profile > Insurance',
         ['Account > Profile > Insurance',
          'Account > Insurance',
          'Settings > Insurance']),
        ('Send a message to your doctor',
         'Messages > Compose New',
         ['Messages > Compose New',
          'Messages > New Message',
          'Contact > Message Doctor']),
        ('View your medication list',
         'Medications > Current Medications',
         ['Medications > Current Medications',
          'Medications > My Medications',
          'Health Records > Medications']),
        ('Pay an outstanding bill',
         'Billing > Outstanding Balance > Pay Now',
         ['Billing > Outstanding Balance > Pay Now',
          'Billing > Pay Bill',
          'Account > Billing > Pay']),
        ('Download your vaccination records',
         'Health Records > Immunizations > Download',
         ['Health Records > Immunizations > Download',
          'Health Records > Vaccines',
          'My Health > Immunizations']),
        ('Change your notification preferences',
         'Settings > Notifications > Preferences',
         ['Settings > Notifications > Preferences',
          'Account > Notifications',
          'Settings > Email Preferences']),
        ('Request a medication refill',
         'Medications > Refill Request',
         ['Medications > Refill Request',
          'Medications > Request Refill',
          'Pharmacy > Refill']),
        ('Find the phone number for your clinic',
         'Locations > My Clinic > Contact Info',
         ['Locations > My Clinic > Contact Info',
          'Contact > Clinic Directory',
          'Help > Contact Us']),
    ]

    path = os.path.join(FIXTURES_DIR, 'tree-test-results-information-architecture.csv')

    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['participant_id', 'task', 'expected_path', 'actual_path',
                     'success', 'time_seconds', 'backtrack_count'])

        for pid in range(1, 26):
            nav_skill = random.gauss(0.6, 0.15)

            for task_label, expected_path, alt_paths in tasks:
                r = random.random()
                adjusted = max(0.1, min(0.95, nav_skill + random.gauss(0, 0.1)))

                if r < adjusted * 0.6:
                    success = 'direct'
                    actual = expected_path
                    backtracks = 0
                    time_s = max(5, random.gauss(15, 5))
                elif r < adjusted * 0.6 + 0.25:
                    success = 'indirect'
                    actual = random.choice(alt_paths)
                    backtracks = random.randint(1, 4)
                    time_s = max(10, random.gauss(35, 12))
                else:
                    success = 'fail'
                    wrong_paths = [
                        'Settings > Account > General',
                        'Help > FAQ > Search',
                        'Home > Dashboard > Overview',
                        'Account > Profile > Personal Info',
                        'Health Records > Summary > Overview',
                    ]
                    actual = random.choice(wrong_paths)
                    backtracks = random.randint(2, 7)
                    time_s = max(15, random.gauss(55, 18))

                w.writerow([f'TT-{pid:03d}', task_label, expected_path,
                            actual, success, round(time_s, 1), backtracks])

    print(f"  Tree test: 250 rows -> {path}")


def generate_large_survey():
    """Large survey - 5000 rows with 15 columns."""
    roles = ['Product Manager', 'UX Designer', 'Developer', 'QA Engineer',
             'Data Analyst', 'Marketing Manager', 'Sales Representative',
             'Customer Support', 'Executive', 'Freelancer']
    role_weights = [0.12, 0.15, 0.20, 0.08, 0.10, 0.10, 0.08, 0.07, 0.05, 0.05]
    company_sizes = ['1-10', '11-50', '51-200', '201-1000', '1001-5000', '5000+']
    size_weights = [0.15, 0.20, 0.25, 0.20, 0.12, 0.08]

    open_responses_positive = [
        'The dashboard redesign is a significant improvement over the previous version.',
        'I appreciate the quick response time from the support team.',
        'The new reporting features save me considerable time each week.',
        'Integration with our existing tools was straightforward.',
        'The mobile app has been reliable and well-designed.',
        'Onboarding new team members has become much easier.',
        'The search functionality works exactly as expected.',
        'Data export options are comprehensive and flexible.',
        'The notification system keeps me informed without being overwhelming.',
        'The collaborative features have improved our team communication.',
        'The custom report builder is incredibly powerful.',
        'The API documentation is thorough and well-organized.',
        'Performance has been consistently fast even with large datasets.',
        'The dark mode option is a welcome addition.',
        'The keyboard shortcuts significantly speed up my workflow.',
    ]
    open_responses_neutral = [
        'The product works fine for our basic needs but could offer more advanced features.',
        'Some aspects are intuitive while others require documentation to understand.',
        'The interface is clean but occasionally confusing for new users.',
        'Works as advertised but nothing stands out as exceptional.',
        'Adequate for small teams but shows limitations at enterprise scale.',
        'The learning curve is moderate compared to alternatives.',
        'Pricing seems fair for the feature set provided.',
        'Some recent updates improved things while others added unnecessary complexity.',
        'The mobile experience is acceptable but not as polished as desktop.',
        'Generally stable with occasional minor issues that are quickly resolved.',
    ]
    open_responses_negative = [
        'The latest update broke several workflows that were previously reliable.',
        'Search results are often irrelevant or incomplete.',
        'The mobile app crashes frequently when handling large files.',
        'Customer support response times have gotten worse recently.',
        'The pricing increase was not justified by the features added.',
        'Performance degrades significantly during peak hours.',
        'The integration with our CRM tool has persistent sync issues.',
        'The reporting feature lacks important customization options.',
        'Accessibility improvements are badly needed for screen reader users.',
        'The onboarding experience is confusing and poorly documented.',
    ]

    path = os.path.join(FIXTURES_DIR, 'large-survey-dataset-5000.csv')
    start_date = datetime(2025, 7, 1)
    end_date = datetime(2026, 3, 15)
    date_range = (end_date - start_date).days

    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['respondent_id', 'timestamp', 'age', 'role', 'company_size',
                     'q1_ease_of_use', 'q2_feature_completeness', 'q3_reliability',
                     'q4_support_quality', 'q5_value_for_money',
                     'open_positive', 'open_negative', 'open_suggestion',
                     'nps_score', 'sus_score', 'task_completion_time_seconds'])

        for i in range(1, 5001):
            rid = f'R-{i:05d}'
            date = start_date + timedelta(
                days=random.randint(0, date_range),
                hours=random.randint(6, 22),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            timestamp = date.strftime('%Y-%m-%dT%H:%M:%SZ')

            age = int(max(18, min(75, random.gauss(38, 12))))
            role = random.choices(roles, weights=role_weights, k=1)[0]
            csize = random.choices(company_sizes, weights=size_weights, k=1)[0]

            # Correlated satisfaction: base satisfaction affects all Likert questions
            base_sat = random.gauss(3.4, 0.8)
            q1 = int(max(1, min(5, round(base_sat + random.gauss(0, 0.5)))))
            q2 = int(max(1, min(5, round(base_sat + random.gauss(-0.2, 0.6)))))
            q3 = int(max(1, min(5, round(base_sat + random.gauss(0.1, 0.5)))))
            q4 = int(max(1, min(5, round(base_sat + random.gauss(-0.1, 0.7)))))
            q5 = int(max(1, min(5, round(base_sat + random.gauss(0, 0.6)))))

            avg_q = (q1 + q2 + q3 + q4 + q5) / 5
            if avg_q >= 4.0:
                op = random.choice(open_responses_positive)
                on = random.choice(open_responses_neutral + ['No major complaints.', 'Nothing comes to mind.'])
            elif avg_q >= 3.0:
                op = random.choice(open_responses_positive + open_responses_neutral)
                on = random.choice(open_responses_neutral + open_responses_negative)
            else:
                op = random.choice(open_responses_neutral + ['Hard to find positives right now.'])
                on = random.choice(open_responses_negative)

            suggestions = [
                'Add more keyboard shortcuts for power users.',
                'Improve the mobile app performance.',
                'Add better data visualization options.',
                'Provide more detailed API documentation.',
                'Improve the search with fuzzy matching.',
                'Add dark mode support across all screens.',
                'Reduce the number of clicks for common tasks.',
                'Improve the onboarding experience for new users.',
                'Add more export format options.',
                'Improve accessibility for screen reader users.',
                'Add offline mode for the mobile app.',
                'Provide more granular notification controls.',
                'Add support for custom workflows.',
                'Improve the billing and invoicing module.',
                'Add team analytics and productivity metrics.',
            ]
            osug = random.choice(suggestions)

            # NPS correlated with satisfaction
            nps_base = (avg_q - 1) * 2.5  # maps 1-5 to 0-10
            nps = int(max(0, min(10, round(nps_base + random.gauss(0, 1.5)))))

            # SUS score (correlated)
            sus_base = 20 + avg_q * 14 + random.gauss(0, 8)
            sus = round(max(12.5, min(100, sus_base)), 1)

            # Task completion time
            tct = round(max(15, random.gauss(180, 80)), 1)

            w.writerow([rid, timestamp, age, role, csize,
                        q1, q2, q3, q4, q5,
                        op, on, osug,
                        nps, sus, tct])

    print(f"  Large survey: 5000 rows -> {path}")


def generate_edge_very_long_survey():
    """Very long survey - 2000 rows with long open-ended responses."""
    long_responses = [
        "I have been using this product for approximately six months now and my experience has been quite mixed. On one hand the core functionality is solid and the interface is generally well-designed with clear visual hierarchy and consistent patterns across most screens. The onboarding process was smooth and I was able to get my team up and running within a couple of days which was impressive. The dashboard provides a good overview of key metrics and the reporting feature has saved me significant time compared to our previous manual process. The integration with Slack has been particularly valuable for keeping the team informed about project updates without requiring everyone to log into the platform constantly. However there are several areas where I think significant improvements are needed. The search functionality is frustratingly limited and often returns irrelevant results. The mobile experience is poor with frequent crashes and a layout that clearly was not designed for smaller screens. The pricing has increased substantially over the past year without corresponding feature improvements. Customer support response times have deteriorated from hours to days. The data export feature is unreliable and occasionally produces corrupted files. I would give an overall rating of three out of five with the potential to be a five if these issues are addressed in the next few releases.",
        "From a technical perspective the platform demonstrates solid engineering fundamentals. The API is well-documented and follows RESTful conventions consistently which made our custom integration straightforward to implement. Response times are generally under 200 milliseconds for standard queries which is acceptable for our use case. The webhook system works reliably and we have built several automated workflows around it. However I have noticed that performance degrades significantly when working with datasets larger than 10000 records. Pagination helps but the initial load time for filtered views can exceed 5 seconds which disrupts workflow. The batch operations API has a hard limit of 100 items per request which requires us to implement our own batching logic for larger operations. I would appreciate seeing improvements in bulk data handling and perhaps a dedicated analytics query engine for large dataset operations. The current approach of loading everything through the standard REST API creates unnecessary overhead for data-intensive use cases. Additionally the lack of GraphQL support means we often over-fetch data when we only need specific fields from complex nested objects.",
        "As a UX designer I want to share detailed feedback about the interaction patterns in the application. The navigation model works well for the primary workflows but falls apart for secondary and tertiary tasks. Users frequently get lost when trying to access settings or help documentation because these are buried under a generic More menu that provides no information scent. The form validation approach is inconsistent across the application. Some forms validate inline as you type while others only show errors after submission. The error messages themselves vary from helpful and specific to generic and unhelpful. For example the login form shows specific messages about incorrect passwords while the registration form simply says validation failed without indicating which fields need attention. The modal usage is excessive with some workflows requiring users to navigate through three or four stacked modals which creates a claustrophobic and disorienting experience. I would strongly recommend converting multi-step modal workflows into dedicated pages with proper URL routing and browser back button support. The color system needs work as well. The current palette does not provide sufficient contrast ratios for WCAG AA compliance particularly for the gray text on white backgrounds used extensively in secondary content areas.",
        "Our organization has been evaluating this tool against three competitors for our enterprise deployment and I want to share our findings. In terms of feature completeness this product scores highest with coverage across all twelve capability areas we evaluated. However it scores lowest on ease of use which is a critical factor for our deployment where we need to onboard over 500 non-technical users. The administrative controls are comprehensive but overwhelming. The permissions system alone has over forty distinct permission flags which is far more granular than necessary for our use case and creates a significant configuration burden. We would prefer a role-based system with five to seven predefined roles that cover common use cases with the option to create custom roles for edge cases. The single sign-on integration was the most complex we have encountered. While it does support SAML 2.0 and OIDC the configuration process required direct database access for some settings which is unacceptable from a security perspective. The documentation for SSO setup was outdated and referenced UI elements that no longer exist in the current version. Our IT security team spent three days getting SSO working correctly. The audit logging capability is basic compared to what we need for compliance. We require detailed logs of all data access and modification events with tamper-proof storage and configurable retention policies. The current system only logs authentication events and high-level actions without the granularity needed for SOC 2 compliance.",
        "I wanted to provide feedback specifically about the collaborative features since our team relies heavily on real-time collaboration. The concurrent editing feature for documents works reasonably well for two to three users but we have experienced significant issues with more than five simultaneous editors. Changes sometimes conflict and the resolution mechanism is not transparent about what happened to conflicting edits. We have lost content on at least two occasions when multiple people were editing the same section simultaneously. The commenting system is functional but lacks threading which makes it difficult to follow conversations on documents with many comments. We end up creating separate chat threads to discuss document feedback which defeats the purpose of in-context commenting. The sharing model is confusing because it mixes organization-level permissions with document-level permissions and it is not always clear which takes precedence. We had a situation where a document was shared with an external stakeholder who could see it even after we revoked their organization access because the document-level share was still active. This is a security concern that needs to be addressed. The notification system for collaborative activities generates too much noise. When a document has ten collaborators every edit by every person generates a notification to everyone else. We need more intelligent notification batching and the ability to watch specific sections rather than entire documents.",
    ]

    path = os.path.join(FIXTURES_DIR, 'edge-very-long-survey.csv')

    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['respondent_id', 'timestamp', 'age', 'role', 'q1_rating',
                     'q2_rating', 'open_ended_response', 'nps_score'])

        roles = ['Product Manager', 'UX Designer', 'Developer', 'QA Engineer',
                 'Data Analyst', 'Marketing Manager', 'Customer Support']
        start_date = datetime(2025, 10, 1)

        for i in range(1, 2001):
            rid = f'VL-{i:05d}'
            date = start_date + timedelta(days=random.randint(0, 150),
                                          hours=random.randint(7, 21))
            age = int(max(20, min(65, random.gauss(36, 10))))
            role = random.choice(roles)
            q1 = random.randint(1, 5)
            q2 = random.randint(1, 5)

            # Each response is one of the long ones, slightly varied
            base_resp = random.choice(long_responses)
            # Add some variation by appending a unique sentence
            extras = [
                f" This feedback is based on {random.randint(2, 24)} months of daily usage.",
                f" Our team of {random.randint(3, 50)} people depends on this tool for critical workflows.",
                f" I have submitted {random.randint(1, 8)} support tickets about these issues.",
                f" We are currently on the {random.choice(['Basic', 'Pro', 'Enterprise', 'Team'])} plan.",
                f" Response submitted from {random.choice(['desktop', 'mobile', 'tablet'])} device.",
            ]
            response = base_resp + random.choice(extras)

            nps = random.randint(0, 10)
            w.writerow([rid, date.strftime('%Y-%m-%dT%H:%M:%SZ'), age, role,
                        q1, q2, response, nps])

    print(f"  Edge very-long survey: 2000 rows -> {path}")


def generate_portuguese_survey():
    """Portuguese satisfaction survey - 50 rows."""
    comments_pos = [
        'O sistema e muito facil de usar. Consigo resolver tudo sem precisar ligar para o atendimento.',
        'A interface e moderna e intuitiva. Parabens pela equipe de design.',
        'O tempo de resposta do sistema e excelente. Nunca tive problemas de lentidao.',
        'O suporte ao cliente e muito atencioso e resolve os problemas rapidamente.',
        'As novas funcionalidades de relatorio sao muito uteis para o meu trabalho.',
        'A integracao com o sistema do governo funcionou perfeitamente.',
        'O aplicativo mobile e muito pratico para consultas rapidas.',
        'A seguranca do sistema me passa confianca para fazer transacoes.',
    ]
    comments_neu = [
        'O sistema funciona bem para as necessidades basicas mas poderia ter mais opcoes.',
        'Algumas telas sao confusas mas no geral da para usar.',
        'O tempo de carregamento poderia ser melhor em horarios de pico.',
        'Nao encontrei tudo que precisava mas o basico funciona.',
        'Poderia ter mais opcoes de acessibilidade.',
        'A navegacao poderia ser mais intuitiva em algumas secoes.',
    ]
    comments_neg = [
        'O sistema cai frequentemente nos horarios de maior movimento.',
        'Nao consigo usar o sistema no celular. A tela fica toda desconfigurada.',
        'O processo de login e muito complicado e demora muito.',
        'Perdi dados preenchidos porque o sistema deu erro na hora de salvar.',
        'O suporte tecnico demora dias para responder.',
        'A linguagem usada no sistema e muito tecnica e dificil de entender.',
    ]

    path = os.path.join(FIXTURES_DIR, 'pesquisa-satisfacao-pt.csv')

    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['respondent_id', 'data', 'satisfacao', 'facilidade_uso', 'comentario_aberto'])

        start = datetime(2025, 10, 1)
        for i in range(1, 51):
            rid = f'BR-{i:04d}'
            date = start + timedelta(days=random.randint(0, 160))

            sat = random.choices([1,2,3,4,5], weights=[0.05,0.10,0.25,0.35,0.25], k=1)[0]
            ease = random.choices([1,2,3,4,5], weights=[0.05,0.12,0.28,0.30,0.25], k=1)[0]

            avg = (sat + ease) / 2
            if avg >= 4:
                comment = random.choice(comments_pos)
            elif avg >= 3:
                comment = random.choice(comments_neu)
            else:
                comment = random.choice(comments_neg)

            w.writerow([rid, date.strftime('%Y-%m-%d'), sat, ease, comment])

    print(f"  Portuguese survey: 50 rows -> {path}")


if __name__ == '__main__':
    print("Generating CSV test data fixtures...")
    generate_ab_test()
    generate_nps()
    generate_sus()
    generate_funnel()
    generate_card_sort()
    generate_tree_test()
    generate_large_survey()
    generate_edge_very_long_survey()
    generate_portuguese_survey()
    print("Done!")
