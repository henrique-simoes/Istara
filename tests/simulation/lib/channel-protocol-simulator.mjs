/**
 * Channel & Survey Protocol Simulator for Istara live simulation and testing.
 *
 * Provides an HTTP server that simulates authentic upstream SaaS APIs:
 * - Telegram Bot API (getMe, sendMessage, sendDocument, getUpdates)
 * - Slack Web API (auth.test, chat.postMessage, files.upload_v2)
 * - WhatsApp Business Cloud API (phone lookup, messages, media)
 * - SurveyMonkey REST API v3 (users/me, surveys, responses/bulk)
 * - Typeform REST API (me, forms, responses)
 *
 * Also provides cryptographic webhook injectors for authentic inbound
 * delivery testing (HMAC-SHA256, secret token, timestamp replay validation).
 */

import http from "http";
import crypto from "crypto";
import os from "os";

export class ChannelProtocolSimulator {
  constructor(options = {}) {
    this.port = options.port || 18080;
    this.server = null;
    this.sentMessages = [];
    this.recordedRequests = [];
    this.surveyData = new Map();
    this.typeformData = new Map();
  }

  /**
   * Determine the IP that the backend can reach.
   * If running inside Docker host-network mode, finds bridge interface IP (e.g. 172.26.0.1).
   * Otherwise returns 127.0.0.1.
   */
  getReachableHost() {
    const ifaces = os.networkInterfaces();
    for (const name of Object.keys(ifaces)) {
      for (const iface of ifaces[name]) {
        if (iface.family === "IPv4" && !iface.internal) {
          if (iface.address.startsWith("172.26.") || iface.address.startsWith("172.")) {
            return iface.address;
          }
        }
      }
    }
    return "127.0.0.1";
  }

  getBaseUrl() {
    const host = this.getReachableHost();
    return `http://${host}:${this.port}`;
  }

  getLocalUrl() {
    return `http://127.0.0.1:${this.port}`;
  }

  /**
   * Seed responses for a SurveyMonkey survey ID.
   */
  seedSurveyMonkeySurvey(surveyId, title, qaList) {
    this.surveyData.set(surveyId, {
      id: surveyId,
      title: title || "Usability Evaluation Survey 2026",
      responses: qaList.map((answers, idx) => ({
        id: `resp_${surveyId}_${idx + 1}`,
        date_modified: new Date().toISOString(),
        pages: [
          {
            questions: answers.map((qa, qidx) => ({
              id: `q_${qidx + 1}`,
              headings: [{ heading: qa.question }],
              answers: [{ text: qa.answer }],
            })),
          },
        ],
      })),
    });
  }

  /**
   * Seed responses for a Typeform form ID.
   */
  seedTypeformForm(formId, title, qaList) {
    const fields = [];
    if (qaList.length > 0 && qaList[0].length > 0) {
      qaList[0].forEach((qa, idx) => {
        fields.push({
          id: `field_${idx + 1}`,
          title: qa.question,
          type: "long_text",
        });
      });
    }

    const items = qaList.map((answers, idx) => ({
      landing_id: `land_${formId}_${idx + 1}`,
      submitted_at: new Date().toISOString(),
      answers: answers.map((qa, qidx) => ({
        field: { id: `field_${qidx + 1}`, type: "text" },
        type: "text",
        text: qa.answer,
      })),
    }));

    this.typeformData.set(formId, {
      id: formId,
      title: title || "Product Experience Survey",
      fields,
      items,
    });
  }

  async start() {
    return new Promise((resolve, reject) => {
      this.server = http.createServer((req, res) => this._handleRequest(req, res));
      this.server.on("error", (err) => reject(err));
      this.server.listen(this.port, "0.0.0.0", () => {
        resolve(this.getBaseUrl());
      });
    });
  }

  async stop() {
    return new Promise((resolve) => {
      if (this.server) {
        this.server.close(() => resolve());
      } else {
        resolve();
      }
    });
  }

  clear() {
    this.sentMessages = [];
    this.recordedRequests = [];
    this.surveyData.clear();
    this.typeformData.clear();
  }

  async _handleRequest(req, res) {
    const parsedUrl = new URL(req.url, `http://${req.headers.host || "localhost"}`);
    const pathname = parsedUrl.pathname;
    const method = req.method.toUpperCase();

    let bodyRaw = "";
    req.on("data", (chunk) => {
      bodyRaw += chunk;
    });

    req.on("end", () => {
      let body = {};
      if (bodyRaw) {
        try {
          body = JSON.parse(bodyRaw);
        } catch {
          try {
            const params = new URLSearchParams(bodyRaw);
            body = Object.fromEntries(params.entries());
          } catch {
            body = { _raw: bodyRaw };
          }
        }
      }

      this.recordedRequests.push({
        method,
        pathname,
        headers: req.headers,
        body,
        timestamp: Date.now(),
      });

      // ── Telegram Bot API Simulation ──
      if (pathname.includes("/getMe")) {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            ok: true,
            result: {
              id: 99887766,
              is_bot: true,
              first_name: "Istara Test Bot",
              username: "istara_protocol_bot",
              can_join_groups: true,
            },
          })
        );
      }

      if (pathname.includes("/sendMessage")) {
        const rawChatId = body.chat_id || parsedUrl.searchParams.get("chat_id") || "88776655";
        const chatId = Number.isFinite(Number(rawChatId)) ? Number(rawChatId) : 88776655;
        const text = body.text || parsedUrl.searchParams.get("text") || "";
        this.sentMessages.push({
          platform: "telegram",
          recipient: String(rawChatId),
          text: text,
          payload: body,
          timestamp: Date.now(),
        });
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            ok: true,
            result: {
              message_id: Math.floor(Math.random() * 1000000) + 1,
              date: Math.floor(Date.now() / 1000),
              chat: { id: chatId, type: "private" },
              text: text,
            },
          })
        );
      }

      if (pathname.includes("/sendDocument")) {
        const rawChatId = body.chat_id || parsedUrl.searchParams.get("chat_id") || "88776655";
        const chatId = Number.isFinite(Number(rawChatId)) ? Number(rawChatId) : 88776655;
        this.sentMessages.push({
          platform: "telegram",
          recipient: String(rawChatId),
          document: true,
          payload: body,
          timestamp: Date.now(),
        });
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            ok: true,
            result: {
              message_id: Math.floor(Math.random() * 1000000) + 1,
              date: Math.floor(Date.now() / 1000),
              chat: { id: chatId, type: "private" },
              document: { file_id: "doc_test_123" },
            },
          })
        );
      }

      if (pathname.includes("/getUpdates")) {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ ok: true, result: [] }));
      }

      if (pathname.includes("/deleteWebhook") || pathname.includes("/setWebhook")) {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ ok: true, result: true }));
      }

      if (pathname.includes("/getWebhookInfo")) {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            ok: true,
            result: {
              url: "",
              has_custom_certificate: false,
              pending_update_count: 0,
            },
          })
        );
      }

      // ── Slack Web API Simulation ──
      if (pathname.endsWith("/auth.test")) {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            ok: true,
            url: "https://simulated-workspace.slack.com/",
            team: "Istara Simulated Workspace",
            user: "istara_bot",
            team_id: "T_SIM12345",
            user_id: "U_SIM12345",
            bot_id: "B_SIM12345",
          })
        );
      }

      if (pathname.endsWith("/chat.postMessage")) {
        this.sentMessages.push({
          platform: "slack",
          recipient: body.channel,
          text: body.text,
          payload: body,
          timestamp: Date.now(),
        });
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            ok: true,
            channel: body.channel,
            ts: `${Date.now() / 1000}.000100`,
            message: { text: body.text, bot_id: "B_SIM12345" },
          })
        );
      }

      if (pathname.endsWith("/files.upload_v2") || pathname.endsWith("/files.upload")) {
        this.sentMessages.push({
          platform: "slack",
          recipient: body.channel,
          document: true,
          payload: body,
          timestamp: Date.now(),
        });
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ ok: true, file: { id: "F_SIM12345" } }));
      }

      // ── WhatsApp Cloud API Simulation ──
      const waMsgMatch = pathname.match(/^\/([^/]+)\/messages$/);
      if (waMsgMatch && method === "POST") {
        const text = body.text?.body || body.template?.name || "";
        this.sentMessages.push({
          platform: "whatsapp",
          recipient: body.to,
          text,
          payload: body,
          timestamp: Date.now(),
        });
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            messaging_product: "whatsapp",
            contacts: [{ input: body.to, wa_id: body.to }],
            messages: [{ id: `wamid.SIM_${Date.now()}` }],
          })
        );
      }

      const waHealthMatch = pathname.match(/^\/([^/]+)$/);
      if (waHealthMatch && method === "GET" && !pathname.startsWith("/users") && !pathname.startsWith("/forms") && !pathname.startsWith("/me")) {
        const phoneId = waHealthMatch[1];
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            id: phoneId,
            display_phone_number: "+1 555-0199",
            verified_name: "Istara Research Simulator",
            quality_rating: "GREEN",
          })
        );
      }

      // ── SurveyMonkey REST API v3 Simulation ──
      if (pathname.endsWith("/users/me")) {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            id: "sm_usr_9988",
            username: "istara_researcher",
            email: "researcher@istara.test",
          })
        );
      }

      const smBulkMatch = pathname.match(/\/surveys\/([^/]+)\/responses\/bulk/);
      if (smBulkMatch) {
        const sId = smBulkMatch[1];
        const sData = this.surveyData.get(sId);
        const responses = sData ? sData.responses : [];
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            data: responses,
            per_page: 50,
            page: 1,
            total: responses.length,
          })
        );
      }

      if (pathname.endsWith("/surveys") && method === "POST") {
        const newId = `sm_srv_${Date.now()}`;
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            id: newId,
            title: body.title || "Created Survey",
            preview: `${this.getBaseUrl()}/surveys/${newId}/preview`,
          })
        );
      }

      if (pathname.endsWith("/surveys") && method === "GET") {
        const list = Array.from(this.surveyData.values()).map((s) => ({
          id: s.id,
          title: s.title,
          href: `${this.getBaseUrl()}/surveys/${s.id}`,
        }));
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            data: list,
            per_page: 50,
            page: 1,
            total: list.length,
          })
        );
      }

      // ── Typeform REST API Simulation ──
      if (pathname === "/me") {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            user_id: "tf_usr_7766",
            alias: "Istara Evaluator",
            email: "evaluator@istara.test",
          })
        );
      }

      const tfFormMatch = pathname.match(/^\/forms\/([^/]+)$/);
      if (tfFormMatch && method === "GET") {
        const formId = tfFormMatch[1];
        const fData = this.typeformData.get(formId);
        if (fData) {
          res.writeHead(200, { "Content-Type": "application/json" });
          return res.end(
            JSON.stringify({
              id: fData.id,
              title: fData.title,
              fields: fData.fields,
            })
          );
        }
      }

      const tfRespMatch = pathname.match(/^\/forms\/([^/]+)\/responses$/);
      if (tfRespMatch && method === "GET") {
        const formId = tfRespMatch[1];
        const fData = this.typeformData.get(formId);
        const items = fData ? fData.items : [];
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            total_items: items.length,
            page_count: 1,
            items,
          })
        );
      }

      if (pathname === "/forms" && method === "POST") {
        const newFormId = `tf_form_${Date.now()}`;
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(
          JSON.stringify({
            id: newFormId,
            title: body.title || "Created Form",
            _links: { display: `${this.getBaseUrl()}/to/${newFormId}` },
          })
        );
      }

      // Default fallback
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: true, note: "simulated fallback" }));
    });
  }

  // ── Inbound Webhook Dispatchers (Sending real webhook payloads to Istara backend) ──

  async injectTelegramInbound(backendUrl, instanceId, { text, chatId = 88776655, secretToken = "" }) {
    const payload = {
      update_id: Math.floor(Math.random() * 100000) + 1,
      message: {
        message_id: Math.floor(Math.random() * 100000) + 1,
        date: Math.floor(Date.now() / 1000),
        chat: { id: chatId, type: "private", first_name: "Participant Alex" },
        from: { id: chatId, is_bot: false, first_name: "Participant Alex", username: "alex_eval" },
        text,
      },
    };

    const headers = { "Content-Type": "application/json" };
    if (secretToken) {
      headers["x-telegram-bot-api-secret-token"] = secretToken;
    }

    const res = await fetch(`${backendUrl}/webhooks/telegram/${instanceId}`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    return { status: res.status, ok: res.ok, data: await res.json().catch(() => ({})) };
  }

  async injectSlackInbound(backendUrl, instanceId, { text, channel = "C_RESEARCH", user = "U_ALEX", signingSecret }) {
    const payload = {
      type: "event_callback",
      event_id: `Ev_SIM_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      event_time: Math.floor(Date.now() / 1000),
      event: {
        type: "message",
        user,
        text,
        channel,
        ts: `${Date.now() / 1000}.000100`,
      },
    };

    const rawBody = JSON.stringify(payload);
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const sigBasestring = `v0:${timestamp}:${rawBody}`;
    const signature = "v0=" + crypto.createHmac("sha256", signingSecret).update(sigBasestring).digest("hex");

    const res = await fetch(`${backendUrl}/webhooks/slack/${instanceId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-slack-request-timestamp": timestamp,
        "x-slack-signature": signature,
      },
      body: rawBody,
    });

    return { status: res.status, ok: res.ok, data: await res.json().catch(() => ({})) };
  }

  async injectWhatsAppInbound(backendUrl, instanceId, { text, from = "15550198765", appSecret, phoneId = "sim_phone_123" }) {
    const payload = {
      object: "whatsapp_business_account",
      entry: [
        {
          id: "WABA_SIM_123",
          changes: [
            {
              field: "messages",
              value: {
                messaging_product: "whatsapp",
                metadata: {
                  display_phone_number: "15550199",
                  phone_number_id: phoneId,
                },
                contacts: [
                  {
                    profile: { name: "Participant Jordan" },
                    wa_id: from,
                  },
                ],
                messages: [
                  {
                    from,
                    id: `wamid.SIM_IN_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
                    timestamp: Math.floor(Date.now() / 1000).toString(),
                    text: { body: text },
                    type: "text",
                  },
                ],
              },
            },
          ],
        },
      ],
    };

    const rawBody = JSON.stringify(payload);
    const signature = "sha256=" + crypto.createHmac("sha256", appSecret).update(rawBody).digest("hex");

    const res = await fetch(`${backendUrl}/webhooks/whatsapp/${instanceId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-hub-signature-256": signature,
      },
      body: rawBody,
    });

    return { status: res.status, ok: res.ok, data: await res.json().catch(() => ({})) };
  }
}
