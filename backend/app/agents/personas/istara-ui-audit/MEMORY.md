# Pixel -- UI Audit Agent Memory

## Learnings Log

### Known UI Issues
- Dark mode contrast on slate-400 text against slate-900 backgrounds can fall below 4.5:1 in some components
- The `istara-600` primary color meets AA contrast against white backgrounds but not against light istara tints
- Some interactive elements use `div` with onClick instead of semantic `button` elements -- impacts keyboard accessibility
- Agent avatar fallback (initial letter) uses hardcoded colors not from the design system palette

### Design System Reference
- Primary palette: istara-50 through istara-950
- Semantic states: success (green), warning (yellow/orange), error (red), info (blue)
- Border radius: rounded-lg (8px) for cards, rounded-xl (12px) for modals, rounded-full for avatars/pills
- Spacing: 4px base unit (p-1 = 4px, p-2 = 8px, p-3 = 12px, p-4 = 16px)
- Typography: text-xs (12px), text-sm (14px), text-base (16px), text-lg (18px)
- Shortcuts: documented in HomeClient.tsx, must remain accessible

### Component Scores History
_Tracked per evaluation cycle._
- Initial baseline: not yet established
- Target: 85+ overall score for all views

### Accessibility Patterns
- All modals must trap focus and close on Escape
- All form inputs must have associated labels (not just placeholders)
- All dynamic content updates must use ARIA live regions
- Tab order must follow visual layout order (no tabindex > 0)
- Touch targets must be minimum 44x44px for mobile views

### Error Patterns & Resolutions
- When encountering 'No compute nodes available for chat', resolve by: Returned task to backlog for retry
- When encountering 'No compute nodes available for chat', resolve by: Returned task to backlog for retry
- When encountering 'Client error '400 Bad Request' for url 'http://localhost:1234/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400', resolve by: Returned task to backlog for retry