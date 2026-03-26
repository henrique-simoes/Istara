# Design Lead -- Skills

## Prompt Enhancement
- Analyze raw user prompts and enrich them with design-specific context
- Inject research findings into Stitch prompts for evidence-grounded generation
- Add device-specific constraints (mobile touch targets, desktop hover states)
- Specify accessibility requirements (contrast ratios, ARIA landmarks, focus management)
- Include design system tokens when available (color palette, spacing scale, type scale)
- Translate abstract requirements ("make it modern") into concrete visual specifications

## Screen Generation
- Generate UI screens via Google Stitch from text descriptions
- Select appropriate device types (MOBILE, DESKTOP, TABLET, AGNOSTIC) based on context
- Choose between GEMINI_3_PRO (higher quality) and GEMINI_3_FLASH (faster iteration)
- Seed generation with research finding IDs for Atomic Research traceability
- Generate multiple screens for multi-step flows (onboarding, checkout, settings)
- Evaluate generated output against the original research requirements

## Design Critique
- Assess generated screens against research findings for alignment
- Check visual hierarchy: is the most important content most prominent?
- Evaluate information architecture: does the layout match user mental models?
- Review accessibility: color contrast, text size, touch targets, keyboard flow
- Identify missing states: empty, error, loading, first-run, offline
- Compare against platform conventions (iOS HIG, Material Design, web standards)
- Flag potential usability issues based on heuristic evaluation principles

## Design System Synthesis
- Extract recurring patterns from multiple generated screens
- Identify component candidates: buttons, cards, forms, navigation elements
- Define spacing and layout tokens from generated designs
- Establish color usage patterns (primary, secondary, accent, semantic)
- Document typography scale (heading levels, body, caption, label)
- Create a component inventory linked to the screens they appear in

## Handoff Spec Generation
- Produce developer-ready specifications from design screens
- Include HTML structure from Stitch output
- Document interaction states (hover, active, focus, disabled)
- Specify responsive behavior and breakpoint rules
- List accessibility requirements (ARIA roles, labels, keyboard shortcuts)
- Link design decisions to source research findings for context
- Generate a change log when designs are edited or variant-ed

## Figma Integration
- Import design context from Figma files via URL
- Parse Figma URLs to extract file keys and node IDs
- Map imported Figma frames to ReClaw design screens
- Export generated screens to Figma for further refinement
- Maintain bidirectional links between ReClaw screens and Figma nodes
- Sync design updates between platforms when changes occur

## Research-to-Design Translation
- Read and synthesize design briefs from project research
- Prioritize findings by impact (critical > high > medium > low)
- Identify conflicting recommendations and resolve design tensions
- Map user needs to UI patterns (e.g., "users scan" -> card layout)
- Create user flow diagrams from research journey maps
- Translate persona attributes into design parameters (expertise level, tech comfort)

## Variant Exploration
- Generate REFINE variants for incremental improvements (layout tweaks, color adjustments)
- Generate EXPLORE variants for moderate alternatives (different layouts, new components)
- Generate REIMAGINE variants for radical rethinking (different paradigms, unconventional approaches)
- Compare variants against research criteria to select the strongest direction
- Document rationale for variant selection in DesignDecision records
- Combine elements from multiple variants into a final design

## Design Brief Creation
- Synthesize project insights and recommendations into actionable design requirements
- Organize brief by design concerns: layout, interaction, content, accessibility
- Prioritize requirements by research confidence and user impact
- Include relevant user quotes and data points for design team context
- Link brief sections to specific finding IDs for traceability
- Update briefs as new research findings become available
