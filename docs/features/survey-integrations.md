# Survey Platform Integrations

Istara connects to SurveyMonkey, Google Forms, and Typeform to create surveys and ingest responses into the Atomic Research chain.

## Supported Platforms

### SurveyMonkey
- **Auth**: OAuth 2.0 Bearer token
- **Create surveys**: POST /v3/surveys
- **Get responses**: GET /v3/surveys/{id}/responses/bulk
- **Webhooks**: `response_completed` event

### Google Forms
- **Auth**: Google service account or OAuth
- **Create forms**: POST /v1/forms + batchUpdate
- **Get responses**: GET /v1/forms/{id}/responses
- **Webhooks**: Not supported natively. Use Istara Loops/Scheduler for polling.
- **Note**: After March 2026, forms created via API are unpublished by default.

### Typeform
- **Auth**: API token (Bearer)
- **Create forms**: POST /forms
- **Get responses**: GET /forms/{id}/responses
- **Webhooks**: PUT /forms/{id}/webhooks/{tag} with HMAC-SHA256 verification

### Microsoft Forms
- **Not supported**: No Graph API for form operations (only usage analytics available).

## Response Ingestion Pipeline

```
Survey Response (webhook or poll)
    |
    v
Parse Q&A pairs
    |
    v
Create Nuggets (source = survey name, text = "Q: ... A: ...")
    |
    v
Update SurveyLink.response_count
    |
    v
Optionally trigger analysis skills (thematic analysis, survey analysis)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/surveys/integrations | List integrations |
| POST | /api/surveys/integrations | Create integration |
| DELETE | /api/surveys/integrations/{id} | Remove |
| GET | /api/surveys/integrations/{id}/surveys | List surveys |
| POST | /api/surveys/integrations/{id}/create | Create survey |
| POST | /api/surveys/links | Link survey to project |
| GET | /api/surveys/links | List linked surveys |
| POST | /api/surveys/links/{id}/sync | Manual pull |
| GET | /api/surveys/links/{id}/responses | Get responses |
