# pi packages public API — ground truth (both packages v0.80.10)

Roots: `<repo-root>-pi-replacement/pi-runtime/node_modules/@earendil-works/pi-agent-core/` (agent-core), `.../@earendil-works/pi-ai/` (pi-ai). All refs are `dist/*.d.ts` unless noted.

## 1. Agent class (pi-agent-core)

### Constructor — `AgentOptions` (agent.d.ts:5-24)

```ts
new Agent(options?: AgentOptions)
interface AgentOptions {
  initialState?: Partial<Omit<AgentState, "pendingToolCalls"|"isStreaming"|"streamingMessage"|"errorMessage">>;
  convertToLlm?: (messages: AgentMessage[]) => Message[] | Promise<Message[]>;
  transformContext?: (messages: AgentMessage[], signal?: AbortSignal) => Promise<AgentMessage[]>;
  streamFn?: StreamFn;                       // default: compat streamSimple (agent.js:116)
  getApiKey?: (provider: string) => Promise<string|undefined> | string | undefined;
  onPayload?: SimpleStreamOptions["onPayload"];
  onResponse?: SimpleStreamOptions["onResponse"];
  beforeToolCall?: (ctx: BeforeToolCallContext, signal?) => Promise<BeforeToolCallResult|undefined>;
  afterToolCall?: (ctx: AfterToolCallContext, signal?) => Promise<AfterToolCallResult|undefined>;
  prepareNextTurn? / prepareNextTurnWithContext?;   // return AgentLoopTurnUpdate {context?, model?, thinkingLevel?}
  steeringMode?: QueueMode;   // "all" | "one-at-a-time"
  followUpMode?: QueueMode;
  sessionId?: string;
  thinkingBudgets?: ThinkingBudgets;         // {minimal?,low?,medium?,high?: number}
  transport?: Transport;                     // "sse"|"websocket"|"websocket-cached"|"auto"
  maxRetryDelayMs?: number;
  toolExecution?: ToolExecutionMode;         // "sequential"|"parallel" (default "parallel")
}
```

### `AgentState` (types.d.ts:279-304)

```ts
interface AgentState {
  systemPrompt: string;
  model: Model<any>;
  thinkingLevel: ThinkingLevel;   // "off"|"minimal"|"low"|"medium"|"high"|"xhigh"|"max" (types.d.ts:250)
  tools: AgentTool<any>[];        // accessor; assignment copies top-level array
  messages: AgentMessage[];       // accessor; assignment copies top-level array
  readonly isStreaming: boolean;
  readonly streamingMessage?: AgentMessage;
  readonly pendingToolCalls: ReadonlySet<string>;
  readonly errorMessage?: string;
}
```

### Methods (agent.d.ts:68-109)

```ts
subscribe(listener: (event: AgentEvent, signal: AbortSignal) => Promise<void>|void): () => void
prompt(message: AgentMessage | AgentMessage[]): Promise<void>
prompt(input: string, images?: ImageContent[]): Promise<void>
continue(): Promise<void>              // last message must be user/toolResult
steer(message: AgentMessage): void     // injected after current assistant turn
followUp(message: AgentMessage): void  // injected only when agent would stop
clearSteeringQueue() / clearFollowUpQueue() / clearAllQueues(): void
hasQueuedMessages(): boolean
get signal(): AbortSignal | undefined
abort(): void
waitForIdle(): Promise<void>           // resolves after agent_end listeners settle
reset(): void
```

Note: `steer`/`followUp` take an `AgentMessage` object (e.g. `{role:"user", content:"...", timestamp: Date.now()}`), NOT a string. String-taking `steer(text)` exists only on `AgentHarness` (harness/agent-harness.d.ts:50).

### `AgentEvent` union (types.d.ts:362-400)

| type | key payload fields |
|---|---|
| `agent_start` | — |
| `agent_end` | `messages: AgentMessage[]` |
| `turn_start` | — |
| `turn_end` | `message: AgentMessage`, `toolResults: ToolResultMessage[]` |
| `message_start` / `message_end` | `message: AgentMessage` |
| `message_update` | `message`, `assistantMessageEvent: AssistantMessageEvent` (pi-ai delta event) |
| `tool_execution_start` | `toolCallId`, `toolName`, `args` |
| `tool_execution_update` | `toolCallId`, `toolName`, `args`, `partialResult` |
| `tool_execution_end` | `toolCallId`, `toolName`, `result`, `isError: boolean` |

### toolExecution modes (types.d.ts:22, README.md:102-109)
- `"parallel"` (default): preflight sequential, execute concurrently; `tool_execution_end` in completion order, toolResult messages in assistant source order.
- `"sequential"`: one-by-one. Per-tool override via `AgentTool.executionMode`; any `"sequential"` tool in a batch forces whole batch sequential.

### Compaction / context management (index.d.ts:5, harness/compaction/compaction.d.ts)

```ts
// exported from package root:
estimateContextTokens(messages: AgentMessage[]): ContextUsageEstimate  // {tokens, usageTokens, trailingTokens, lastUsageIndex}
estimateTokens(message: AgentMessage): number       // char heuristic
calculateContextTokens(usage: Usage): number
shouldCompact(contextTokens, contextWindow, settings: CompactionSettings): boolean
DEFAULT_COMPACTION_SETTINGS: CompactionSettings     // {enabled, reserveTokens, keepRecentTokens}
prepareCompaction(pathEntries: SessionTreeEntry[], settings): Result<CompactionPreparation|undefined, CompactionError>
compact(preparation, models: Models, model, customInstructions?, signal?, thinkingLevel?): Promise<Result<CompactionResult, CompactionError>>  // CompactionResult: {summary, firstKeptEntryId, tokensBefore, details?}
generateSummary(currentMessages, models, model, reserveTokens, signal?, customInstructions?, previousSummary?, thinkingLevel?): Promise<Result<string, CompactionError>>
```
Plain `Agent` has NO built-in compaction — you wire it via `transformContext`/`prepareNextTurn`. Turnkey compaction lives in `AgentHarness.compact()` (harness/agent-harness.d.ts:60).

### Session serialization/restore (harness/session/session.d.ts, jsonl-storage.d.ts)

```ts
class Session<TMetadata> {
  constructor(storage: SessionStorage<TMetadata>, contextBuildOptions?);
  appendMessage(message: AgentMessage): Promise<string>;
  appendCompaction(summary, firstKeptEntryId, tokensBefore, details?, fromHook?): Promise<string>;
  appendModelChange(provider, modelId) / appendThinkingLevelChange(level) / appendActiveToolsChange(names);
  buildContext(options?): Promise<SessionContext>;   // replays entries -> {messages,...} honoring compaction
  getEntries() / getBranch(fromId?) / moveTo(entryId|null, summary?)   // tree navigation/branching
}
class JsonlSessionStorage implements SessionStorage<JsonlSessionMetadata> {
  static open(fs, filePath): Promise<JsonlSessionStorage>;
  static create(fs, filePath, {cwd, sessionId, parentSessionPath?, metadata?}): Promise<JsonlSessionStorage>;
}
// in-memory variants: memory-storage.d.ts / memory-repo.d.ts; uuidv7 exported (index.d.ts:14)
```
`Agent` itself has no serialize/restore — transcript is `agent.state.messages` (plain JSON-serializable objects); set `initialState.messages` to restore.

### Low-level loop (agent-loop.d.ts:12-23)
```ts
agentLoop(prompts: AgentMessage[], context: AgentContext, config: AgentLoopConfig, signal?, streamFn?): EventStream<AgentEvent, AgentMessage[]>
agentLoopContinue(context, config, signal?, streamFn?): EventStream<AgentEvent, AgentMessage[]>
```

### Proxy (proxy.d.ts:59-67) — no OTel anywhere in either package
```ts
streamProxy(model, context, options: ProxyStreamOptions): ProxyMessageEventStream
// ProxyStreamOptions = pick of SimpleStreamOptions + { authToken: string; proxyUrl: string; signal? }
```

## 2. Tool definition (TypeBox)

`AgentTool` (agent-core types.d.ts:327-345) extends pi-ai `Tool` (pi-ai types.d.ts:327-331):

```ts
import { Type, type Static, type TSchema } from "typebox";  // re-exported by pi-ai index.d.ts:1-2

interface Tool<TParameters extends TSchema = TSchema> { name: string; description: string; parameters: TParameters; }

interface AgentTool<TParameters extends TSchema = TSchema, TDetails = any> extends Tool<TParameters> {
  label: string;                                       // UI display
  prepareArguments?: (args: unknown) => Static<TParameters>;
  execute: (toolCallId: string, params: Static<TParameters>, signal?: AbortSignal,
            onUpdate?: AgentToolUpdateCallback<TDetails>) => Promise<AgentToolResult<TDetails>>;
  executionMode?: "sequential" | "parallel";
}
interface AgentToolResult<T> {
  content: (TextContent | ImageContent)[];   // returned to model
  details: T;                                // structured payload for UI/logs
  addedToolNames?: string[];
  terminate?: boolean;                       // stop hint; effective only if whole batch terminates
}
```

- **Errors**: `execute()` must THROW on failure (types.d.ts:335, README.md:418-431). Thrown errors become tool results with `isError: true`. Do not encode errors in `content`.
- **Streaming tool progress**: call `onUpdate(partialResult)` inside execute → emits `tool_execution_update` (types.d.ts:325).
- **Args validation**: automatic against TypeBox schema before `beforeToolCall`; helpers `validateToolCall(tools, toolCall)` / `validateToolArguments(tool, toolCall)` (pi-ai utils/validation.d.ts) and `parseStreamingJson<T>(partialJson)` for LLM-side toolcall deltas (utils/json-parse.d.ts).
- Google-safe enums: `StringEnum(values, {description?, default?})` (utils/typebox-helpers.d.ts).

## 3. pi-ai

### Provider catalog — factory functions (dist/providers/*.d.ts, all lines :2 unless noted)

| Factory | Returns `Provider<TApi>` |
|---|---|
| `anthropicProvider()` | `"anthropic-messages"` |
| `openaiProvider()` | `"openai-responses"` |
| `openaiCodexProvider()` | `"openai-codex-responses"` |
| `azureOpenAIResponsesProvider()` | `"azure-openai-responses"` |
| `googleProvider()` | `"google-generative-ai"` |
| `googleVertexProvider()` | `"google-vertex"` |
| `mistralProvider()` | `"mistral-conversations"` |
| `amazonBedrockProvider()` | `"bedrock-converse-stream"` |
| `deepseekProvider()`, `nvidiaProvider()`, `groqProvider()`, `cerebrasProvider()`, `openrouterProvider()`, `zaiProvider()`, `zaiCodingCnProvider()`, `moonshotaiProvider()`, `moonshotaiCnProvider()`, `huggingfaceProvider()`, `togetherProvider()`, `antLingProvider()`, `cloudflareWorkersAIProvider()`, `xiaomiProvider()`, `xiaomiTokenPlanCnProvider()`, `xiaomiTokenPlanAmsProvider()`, `xiaomiTokenPlanSgpProvider()` | `"openai-completions"` |
| `xaiProvider()` | `"openai-completions" \| "openai-responses"` |
| `minimaxProvider()`, `minimaxCnProvider()`, `kimiCodingProvider()`, `vercelAIGatewayProvider()` | `"anthropic-messages"` |
| `fireworksProvider()`, `opencodeGoProvider()` | `"anthropic-messages" \| "openai-completions"` |
| `githubCopilotProvider()`, `cloudflareAIGatewayProvider()` | mixed (`anthropic-messages`/`openai-completions`(/`openai-responses`)) |
| `opencodeProvider()` | 4-API mixed |
| `radiusProvider(options?)` | `"pi-messages"` (dynamic, providers/radius.d.ts:8) |
| `fauxProvider(options?)` | test double (providers/faux.d.ts:96) |
| `builtinProviders()` / `builtinModels(options?)` | all of the above (providers/all.d.ts:19-21) |

**Generic openai-compat / anthropic-compat**: there is NO factory literally named `openaiCompatProvider`. The mechanism is `createProvider()` (models.d.ts:136-158) + API impl modules, with per-model `baseUrl`:

```ts
createProvider<TApi>(input: {
  id: string; name?: string; baseUrl?: string; headers?: ProviderHeaders;
  auth: ProviderAuth;                       // e.g. envApiKeyAuth("Name", ["ENV_VAR"]) or keyless resolve: async () => ({auth:{}})
  models: readonly Model<TApi>[];           // each Model carries its own baseUrl
  fetchModels?; filterModels?;
  api: ProviderStreams | Partial<Record<TApi, ProviderStreams>>;   // openAICompletionsApi() / anthropicMessagesApi() / openAIResponsesApi() from '@earendil-works/pi-ai/api/<id>.lazy'
}): Provider<TApi>
```
README.md:946-1113 shows Ollama/vLLM/proxy examples. Compat knobs: `OpenAICompletionsCompat` (types.d.ts:403-444, incl. `thinkingFormat`, `maxTokensField`, `supportsDeveloperRole`, `cacheControlFormat: "anthropic"`), `AnthropicMessagesCompat` (types.d.ts:457-508), `OpenAIResponsesCompat` (types.d.ts:446-455).

### Model shape (types.d.ts:602-621)

```ts
interface Model<TApi> {
  id: string; name: string; api: TApi; provider: ProviderId;
  baseUrl: string;                    // per-model endpoint — this is the openai-compat hook
  reasoning: boolean;
  thinkingLevelMap?: ThinkingLevelMap;
  input: ("text"|"image")[];          // vision capability flag
  cost: ModelCost;                    // per-Mtok rates {input,output,cacheRead,cacheWrite,tiers?}
  contextWindow: number; maxTokens: number;
  headers?: Record<string,string>;
  compat?: ...;                       // per-API compat overrides
}
```

### Registry / lookup
- New API: `createModels(options?): MutableModels` (models.d.ts:135); `models.getModel(provider, id)`, `getModels(provider?)`, `getProviders()`, `getAvailable()`, `checkAuth()`, `getAuth()`, `refresh()`, `setProvider()` (models.d.ts:82-129); `hasApi(model, api)` type guard (models.d.ts:169).
- Static catalog: `getBuiltinModel(provider, modelId)`, `getBuiltinModels(provider)`, `getBuiltinProviders()` (providers/all.d.ts:15-17).
- Compat (deprecated but exported; used by agent-core): `getModel`/`getModels`/`getProviders` + global `stream`/`complete`/`streamSimple`/`completeSimple` with env API-key auto-injection (compat.d.ts:33-66; injection at compat.js:148).

### complete / stream APIs
```ts
models.stream(model, context, options?): AssistantMessageEventStream       // async-iterable; .result(): Promise<AssistantMessage>
models.complete(model, context, options?): Promise<AssistantMessage>
models.streamSimple / completeSimple(model, context, options?: SimpleStreamOptions)
```
`StreamOptions` (types.d.ts:46-122): `temperature?`, `maxTokens?`, `signal?`, `apiKey?`, `transport?`, `cacheRetention?: "none"|"short"|"long"` (default "short"), `sessionId?`, `onPayload?`, `onResponse?`, `headers?`, `timeoutMs?`, `websocketConnectTimeoutMs?`, `maxRetries?`, `maxRetryDelayMs?` (default 60000), `metadata?`, `env?`.
`SimpleStreamOptions` adds `reasoning?: ThinkingLevel` = `"minimal"|"low"|"medium"|"high"|"xhigh"|"max"` (types.d.ts:22,213-217) and `thinkingBudgets?`. (`"off"` exists only in `ModelThinkingLevel`/agent-core.)
Per-API options: `AnthropicOptions` (`thinkingEnabled`, `thinkingBudgetTokens`, `effort`, `thinkingDisplay`, `interleavedThinking`, `toolChoice`, `client?: Anthropic`) — api/anthropic-messages.d.ts:5-68; `OpenAICompletionsOptions` (`toolChoice`, `reasoningEffort`) — api/openai-completions.d.ts:3-11; `OpenAIResponsesOptions` (`reasoningEffort`, `reasoningSummary`, `serviceTier`, `toolChoice`) — api/openai-responses.d.ts:3-8.

**Structured output: DOES NOT EXIST.** No `response_format`, no JSON mode, no schema-constrained-output option anywhere in dist/*.d.ts or README (grep-confirmed). The only mechanisms are: (a) force a tool call via `toolChoice: "required"` / `{type:"function",function:{name}}` (openai-completions) or `{type:"tool",name}` (anthropic), then read `toolCall.arguments`; (b) prompt-and-parse.

### Usage/cost — exact fields (types.d.ts:251-272, on `AssistantMessage.usage`)
```ts
interface Usage {
  input: number; output: number; cacheRead: number; cacheWrite: number;
  cacheWrite1h?: number; reasoning?: number;   // reasoning is subset of output
  totalTokens: number;
  cost: { input: number; output: number; cacheRead: number; cacheWrite: number; total: number };  // USD
}
```
`AssistantMessage` also carries `stopReason: "stop"|"length"|"toolUse"|"error"|"aborted"`, `errorMessage?`, `model`, `provider`, `api` (types.d.ts:279-292). `calculateCost(model, usage)` exported (models.d.ts:170).

### Token counting / context-window
- pi-ai has NO tokenizer/counting helper (grep-confirmed; no tiktoken). Context window is metadata: `model.contextWindow`, `model.maxTokens`. Overflow detection: `isContextOverflow(message, contextWindow?)` (utils/overflow.d.ts). Retry classification: `isRetryableAssistantError(message)` (utils/retry.d.ts).
- Estimation helpers live in agent-core (`estimateTokens`, `estimateContextTokens` — see section 1).

### Stream event union (`AssistantMessageEvent`, types.d.ts:345-398)
`start` | `text_start/text_delta/text_end` | `thinking_start/thinking_delta/thinking_end` | `toolcall_start` | `toolcall_delta` (`delta`: partial JSON args string) | `toolcall_end` (`toolCall: ToolCall {id,name,arguments}`) | `done {reason, message}` | `error {reason, error: AssistantMessage}`. All partial events carry `partial: AssistantMessage`.

## 4. Presence/absence confirmations

| Capability | Status | Evidence |
|---|---|---|
| Embeddings API | **ABSENT** | zero matches for "embedding" in either package's dist or READMEs |
| Image/vision input | **PRESENT** | `UserMessage.content: string \| (TextContent\|ImageContent)[]` (types.d.ts:274-278); `ImageContent {type:"image", data: base64, mimeType}` (types.d.ts:239-243); `ToolResultMessage.content` also accepts images; gate on `model.input.includes("image")`; `agent.prompt(text, images?)` |
| Image generation | PRESENT (separate) | `ImagesModel`, `generateImages`, `openrouterImagesProvider()` (types.d.ts:164-166, providers/openrouter-images.d.ts) |
| Prompt caching controls | **PRESENT** | `cacheRetention: "none"\|"short"\|"long"` + `sessionId` (types.d.ts:36,56-66); usage reports `cacheRead/cacheWrite`; compat `cacheControlFormat:"anthropic"`, `supportsLongCacheRetention`, `sendSessionAffinityHeaders` |
| Retry/timeout at provider level | **PRESENT** | `timeoutMs`, `maxRetries`, `maxRetryDelayMs`, `websocketConnectTimeoutMs` on `StreamOptions` (types.d.ts:86-109) |
| Structured output | **ABSENT** (tool-forcing only) | see section 3 |
| OTel | **ABSENT** | no opentelemetry/telemetry matches; observability = `onPayload`/`onResponse` callbacks |
| Proxy | PRESENT | `streamProxy` (agent-core proxy.d.ts:67) |

## 5. Worked example (verified APIs only)

```ts
import { Agent, type AgentTool } from "@earendil-works/pi-agent-core";
import { Type, type Model } from "@earendil-works/pi-ai";

const model: Model<"openai-completions"> = {
  id: "llama-3.1-8b", name: "Llama 3.1 8B", api: "openai-completions", provider: "local",
  baseUrl: "http://localhost:11434/v1", reasoning: false, input: ["text"],
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
  contextWindow: 128000, maxTokens: 32000,
  compat: { supportsDeveloperRole: false, supportsReasoningEffort: false },
};
const readFile: AgentTool = {
  name: "read_file", label: "Read File", description: "Read a file",
  parameters: Type.Object({ path: Type.String() }),
  execute: async (_id, params) => ({ content: [{ type: "text", text: await Bun.file(params.path).text() }], details: {} }),
};
const agent = new Agent({
  initialState: { systemPrompt: "You are helpful.", model, tools: [readFile] },
  getApiKey: () => process.env.LOCAL_API_KEY,        // omit for keyless servers
});
agent.subscribe((ev) => {
  if (ev.type === "message_update" && ev.assistantMessageEvent.type === "text_delta")
    process.stdout.write(ev.assistantMessageEvent.delta);
  if (ev.type === "turn_end" && "usage" in ev.message)
    console.log(`\ntokens in=${ev.message.usage.input} out=${ev.message.usage.output} cost=$${ev.message.usage.cost.total}`);
});
const run = agent.prompt("Summarize package.json");
agent.steer({ role: "user", content: "Keep it to one sentence.", timestamp: Date.now() });
await run;   // or await agent.waitForIdle()
```

Notes for the example: default `streamFn` is compat `streamSimple` (agent.js:116), which dispatches on `model.api` via the auto-registered api-registry (compat.js:137) and injects `getApiKey(provider)` / env keys (compat.js:146-151, agent-loop.js:193-196). Custom `provider` ids get no env-key auto-detection, hence `getApiKey`.