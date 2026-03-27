# Messaging Integrations

ReClaw supports multi-instance messaging channel integration with Telegram, Slack, WhatsApp, and Google Chat.

## Architecture

Each messaging connection is a `ChannelInstance` record in the database, linked to a platform-specific `ChannelAdapter` in the `ChannelRouter`. Users can have multiple instances per platform (e.g., two different Telegram bots for different studies).

```
ChannelInstance (DB) <-> ChannelAdapter (in-memory) <-> Platform API
```

## Supported Platforms

### Telegram
- **Auth**: Bot token from @BotFather
- **Transport**: Long polling (no server exposure needed)
- **Features**: Text, voice messages, photos, documents, inline keyboards
- **Setup**: Create bot via @BotFather -> copy token -> paste in ReClaw setup wizard

### Slack
- **Auth**: Bot token (xoxb-...) + Signing secret
- **Transport**: Socket Mode (no public URL needed) or Events API
- **Features**: Text, files, Block Kit interactive components, threaded messages
- **Setup**: Create Slack App -> enable Socket Mode -> copy tokens -> paste in wizard

### WhatsApp Business
- **Auth**: Phone number ID + access token from Meta Business
- **Transport**: Webhooks (requires public URL or tunnel)
- **Features**: Text, audio, images, documents, message templates
- **Limitation**: 24-hour conversation window for outbound messages
- **Setup**: Meta Business account -> WhatsApp Cloud API -> copy credentials

### Google Chat
- **Auth**: Service account JSON or webhook URL
- **Transport**: Webhooks
- **Features**: Text, Cards v2 for rich formatting
- **Setup**: Google Cloud Console -> enable Chat API -> create service account

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/channels | List all instances |
| POST | /api/channels | Create instance |
| GET | /api/channels/{id} | Instance details |
| PATCH | /api/channels/{id} | Update config |
| DELETE | /api/channels/{id} | Delete instance |
| POST | /api/channels/{id}/start | Start adapter |
| POST | /api/channels/{id}/stop | Stop adapter |
| GET | /api/channels/{id}/health | Health check |
| GET | /api/channels/{id}/messages | Message history |
| GET | /api/channels/{id}/conversations | Conversations |
| POST | /api/channels/{id}/send | Send message |

## Webhooks

WhatsApp and Google Chat use webhooks at:
- `POST /webhooks/whatsapp/{instance_id}`
- `GET /webhooks/whatsapp/{instance_id}` (verification)
- `POST /webhooks/google-chat/{instance_id}`

## Troubleshooting

- **"Adapter not enabled"**: Missing credentials in config. Check the setup wizard.
- **WhatsApp messages not arriving**: Verify webhook URL is publicly accessible. Check Meta webhook configuration.
- **Slack events not received**: Ensure Socket Mode is enabled or Event Subscriptions are configured.
- **Health check failing**: Verify API credentials are still valid. Tokens may have expired.
