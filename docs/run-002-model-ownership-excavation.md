# Run 002: `models.py` dependency and ownership excavation

## Purpose and limits

This document describes the inherited responsibilities and data flows surrounding
`ChatMessage` and `ChatSession`. It is an excavation of current behavior, not a
replacement design. The classifications below name what the existing code does;
they do not assign replacement ownership or propose new types.

The primary declarations are [`simpleaichat/models.py`](../simpleaichat/models.py#L20).
Actual consumers are traced through
[`simpleaichat/chatgpt.py`](../simpleaichat/chatgpt.py#L17) and
[`simpleaichat/simpleaichat.py`](../simpleaichat/simpleaichat.py#L22). Run 001's
offline tests provide executable observations for defaults, serialization, history
selection, and provider lowering
([model characterizations](../tests/test_models_characterization.py#L24),
[provider-lowering characterizations](../tests/test_provider_lowering_characterization.py#L25)).

### Reading the matrices

- **Declared owner** means the class on which a field is declared. It does not
  imply that the class's own methods are the field's principal consumers.
- **Actual consumer** names the production code that reads or acts on the value.
- **Boundary** distinguishes provider request data, transport metadata,
  persistence data, and public session state.
- **Model-visible** means the value is placed in the provider `messages` array.
  Request configuration can affect execution without being model-visible in this
  sense.
- **Causes** means a value selects or changes behavior. **Records** means it stores
  an event or result after the fact. A field may do both.
- **Role** uses only the current responsibilities: provider protocol,
  model-visible data, runtime configuration, history/context, execution result,
  accounting, persistence, identity/metadata, and authority/credential.

## Lifecycle and provider-lowering boundary

The inherited lifecycle is:

```text
session construction
    AIChat.new_session() supplies model, auth, system, and caller kwargs
    Pydantic validates/coerces fields and constructs defaults
        |
request preparation
    prepare_request() reads auth/model/system/params
    and constructs transient system/current ChatMessage objects
        |
history selection
    format_input_messages() selects self.messages using recent_messages
        |
PROVIDER LOWERING BOUNDARY
    ChatMessage.model_dump(include=input_fields, exclude_none=True)
    converts system + selected history + current input
    into {role, content, name?} dictionaries
        |
OpenAI request assembly and dispatch
    prepare_request() installs those dictionaries in data["messages"]
    gen()/stream() sends data, headers, and api_url
        |
response handling
    response data becomes an assistant ChatMessage or parsed schema value
        |
state effects
    add_messages() may mutate history
    gen()/gen_async() mutate cumulative accounting
        |
persistence / inspection
    model dumps feed string rendering and JSON/CSV save paths
```

`AIChat.new_session()` supplies the constructor inputs
([`simpleaichat.py` lines 60-81](../simpleaichat/simpleaichat.py#L60)).
`prepare_request()` creates the transient system and current-input objects before
request assembly
([`chatgpt.py` lines 33-57](../simpleaichat/chatgpt.py#L33)). History selection occurs
before serialization
([`models.py` lines 62-66](../simpleaichat/models.py#L62)). The exact representation
boundary is each `model_dump(include=self.input_fields, exclude_none=True)` call
([`models.py` lines 67-74](../simpleaichat/models.py#L67)); the resulting dictionaries
are then assigned to the OpenAI request's `messages` key
([`chatgpt.py` lines 51-57](../simpleaichat/chatgpt.py#L51)).

The objects are neutral only in the limited sense that they are Python/Pydantic
objects before that boundary. They are already provider-specific in meaning:
`prepare_request()` assigns `system`, `user`, or `function` to `role` while creating
them ([`chatgpt.py` lines 38-49](../simpleaichat/chatgpt.py#L38)), and
`ChatGPTSession.input_fields` explicitly selects `role`, `content`, and `name`
([`chatgpt.py` lines 17-21](../simpleaichat/chatgpt.py#L17)).

The resulting message order is always:

```text
system -> selected stored history -> current input
```

That order is constructed directly by list concatenation
([`models.py` lines 67-74](../simpleaichat/models.py#L67)) and is captured offline by
Run 001 ([`test_provider_lowering_characterization.py` lines 59-99](../tests/test_provider_lowering_characterization.py#L59)).

## `ChatMessage` field matrix

| Field | Declared owner and default | Creation and mutation | Actual consumers and lifecycle timing | Actual role | Boundary and model visibility | Cause or record |
|---|---|---|---|---|---|---|
| `role` | `ChatMessage`; required `str` ([declaration](../simpleaichat/models.py#L21)) | Set to `system`, `user`, or `function` during request preparation; provider response role or literal `assistant` is used for results ([request construction](../simpleaichat/chatgpt.py#L38), [sync result](../simpleaichat/chatgpt.py#L113), [stream result](../simpleaichat/chatgpt.py#L167)). CSV/JSON load can also construct it ([load path](../simpleaichat/simpleaichat.py#L277)). No production code mutates it after construction. | `format_input_messages()` reads it indirectly through `model_dump()` during provider lowering ([lowering](../simpleaichat/models.py#L67)); save/inspection paths serialize it ([save path](../simpleaichat/simpleaichat.py#L237)). | Provider protocol; history/context for stored messages; execution result for returned assistant roles. | Included in normal OpenAI message dictionaries because the subclass selects it ([input fields](../simpleaichat/chatgpt.py#L19)); also persisted in CSV and JSON ([CSV fields](../simpleaichat/simpleaichat.py#L245), [JSON write](../simpleaichat/simpleaichat.py#L264)). Model-visible as provider framing, not content text. | Causes provider interpretation when sent; records the provider's returned message role when received. |
| `content` | `ChatMessage`; required `str` ([declaration](../simpleaichat/models.py#L22)) | Created from the plain prompt, schema JSON, provider response, streamed chunks, or tool-workflow strings ([request construction](../simpleaichat/chatgpt.py#L38), [sync result](../simpleaichat/chatgpt.py#L113), [stream result](../simpleaichat/chatgpt.py#L156), [tool result](../simpleaichat/chatgpt.py#L238)). Load paths reconstruct it. No production mutation follows construction. | Read during provider lowering, generation return, stream accumulation, tool workflow composition, string rendering, and persistence ([lowering](../simpleaichat/models.py#L67), [tool composition](../simpleaichat/chatgpt.py#L226), [message string](../simpleaichat/models.py#L31), [save](../simpleaichat/simpleaichat.py#L237)). | Model-visible data; history/context; execution result; persistence. | Included in provider messages and both persistence formats ([input fields](../simpleaichat/chatgpt.py#L19), [CSV fields](../simpleaichat/simpleaichat.py#L245)). Model-visible whenever its message survives history selection. | Causes generation when sent as system/current/history content; records generated content in assistant messages. |
| `name` | `ChatMessage`; optional `str`, default `None` ([declaration](../simpleaichat/models.py#L23)) | Production assigns it only to schema input messages, using the input schema class name ([schema input](../simpleaichat/chatgpt.py#L42)). JSON load or external construction can also supply it. | Read only through dumps/string rendering; `ChatGPTSession.input_fields` permits it through lowering ([input fields](../simpleaichat/chatgpt.py#L19), [lowering](../simpleaichat/models.py#L67)). | Provider protocol; identity/metadata for a provider message. | Crosses the provider boundary when non-`None`. JSON persistence retains it through the recursive session dump, but the CSV field list has no `name` column ([session dump](../simpleaichat/simpleaichat.py#L237), [CSV fields](../simpleaichat/simpleaichat.py#L245)). Model-visible as provider framing. | Causes provider interpretation of a named function message; otherwise records the schema-derived name. |
| `function_call` | `ChatMessage`; optional `str`, default `None` ([declaration](../simpleaichat/models.py#L24)) | No production generation or request path assigns this field. It can exist through external construction or JSON load. | `__str__()` and unrestricted session dumps can serialize it ([message string](../simpleaichat/models.py#L31), [session dump](../simpleaichat/simpleaichat.py#L237)). The standard lowering path does not select it because `ChatGPTSession.input_fields` omits it ([input fields](../simpleaichat/chatgpt.py#L19)). | Dormant provider protocol; persistence when externally populated. | Does not cross the standard provider-lowering boundary and has no CSV column; JSON can preserve it. It is not model-visible in the inherited `ChatGPTSession` path. | Neither causes nor records an effect in production's standard path. The separate top-level request key named `function_call` is constructed from `output_schema`, not from this field ([request metadata](../simpleaichat/chatgpt.py#L59)). |
| `received_at` | `ChatMessage`; timezone-aware current UTC from `now_tz()` ([declaration](../simpleaichat/models.py#L25), [factory](../simpleaichat/models.py#L14)) | Created automatically for every transient and stored message. CSV loading replaces it with the parsed local timestamp converted to UTC; JSON loading relies on Pydantic reconstruction ([CSV load](../simpleaichat/simpleaichat.py#L277), [JSON load](../simpleaichat/simpleaichat.py#L296)). | `ChatSession.__str__()` reads the most recent stored value; save paths serialize it, with CSV converting it to local time text ([session string](../simpleaichat/models.py#L52), [CSV conversion](../simpleaichat/simpleaichat.py#L256)). | Identity/metadata; persistence. | Removed by normal provider lowering because it is not in `input_fields`; retained in JSON and represented in CSV. Not model-visible. | Records local object construction or restored message time; affects inspection/persistence, not generation. |
| `finish_reason` | `ChatMessage`; optional `str`, default `None` ([declaration](../simpleaichat/models.py#L26)) | Set from the non-streaming provider response in `gen()` and `gen_async()` ([sync result](../simpleaichat/chatgpt.py#L113), [async result](../simpleaichat/chatgpt.py#L269)); absent from streamed messages ([stream result](../simpleaichat/chatgpt.py#L167)). Load paths can restore it. | Read by dumps/string rendering and persistence only; it is not otherwise used for control flow. | Execution result; persistence. | Excluded from normal provider lowering; present in JSON and a CSV column ([lowering filter](../simpleaichat/chatgpt.py#L19), [CSV fields](../simpleaichat/simpleaichat.py#L245)). Not model-visible. | Records a provider execution result. |
| `prompt_length` | `ChatMessage`; optional `int`, default `None` ([declaration](../simpleaichat/models.py#L27)) | Set from `usage.prompt_tokens` on non-streaming, non-output-schema assistant message construction ([sync result](../simpleaichat/chatgpt.py#L113), [async result](../simpleaichat/chatgpt.py#L269)). CSV/JSON loading can restore it. | Persistence and string serialization consume it; no production calculation reads it back from messages. | Accounting; persistence. | Excluded from provider lowering; present in JSON and CSV. Not model-visible ([input fields](../simpleaichat/chatgpt.py#L19), [CSV fields](../simpleaichat/simpleaichat.py#L245)). | Records accounting returned by one execution. |
| `completion_length` | `ChatMessage`; optional `int`, default `None` ([declaration](../simpleaichat/models.py#L28)) | Set from `usage.completion_tokens` on the same non-streaming assistant construction paths ([sync result](../simpleaichat/chatgpt.py#L113), [async result](../simpleaichat/chatgpt.py#L269)). CSV/JSON loading can restore it. | Persistence and string serialization consume it; session totals are updated independently from the provider response rather than derived from message fields ([aggregate update](../simpleaichat/chatgpt.py#L128)). | Accounting; persistence. | Excluded from provider lowering; present in JSON and CSV. Not model-visible. | Records accounting returned by one execution. |
| `total_length` | `ChatMessage`; optional `int`, default `None` ([declaration](../simpleaichat/models.py#L29)) | Set from `usage.total_tokens` on the same non-streaming assistant construction paths ([sync result](../simpleaichat/chatgpt.py#L113), [async result](../simpleaichat/chatgpt.py#L269)). CSV/JSON loading can restore it. | Persistence and string serialization consume it; no aggregate code sums stored message values. | Accounting; persistence. | Excluded from provider lowering; present in JSON and CSV. Not model-visible. | Records accounting returned by one execution. |

## `ChatSession` field matrix

| Field | Declared owner and default | Creation and mutation | Actual consumers and lifecycle timing | Actual role | Boundary and model visibility | Cause or record |
|---|---|---|---|---|---|---|
| `id` | `ChatSession`; either `str` or `UUID`, default factory `uuid4()` ([declaration](../simpleaichat/models.py#L36)) | Direct construction gets a fresh UUID. `AIChat.__init__()` and CSV `load_session()` instead declare `uuid4()` as Python function defaults, so those wrapper defaults are evaluated when their functions are defined and then supplied to session construction ([AIChat default](../simpleaichat/simpleaichat.py#L27), [CSV-load default](../simpleaichat/simpleaichat.py#L272)). JSON load can restore a persisted value. | `AIChat` keys, retrieves, resets, and deletes sessions by it ([registration](../simpleaichat/simpleaichat.py#L78), [lookup](../simpleaichat/simpleaichat.py#L83), [deletion](../simpleaichat/simpleaichat.py#L96)). | Identity/metadata; persistence. | Does not enter the provider request. JSON/session dumps retain it; message-only CSV does not ([save dump](../simpleaichat/simpleaichat.py#L237)). Not model-visible. | Causes session routing and records session identity. |
| `created_at` | `ChatSession`; current UTC from `now_tz()` ([declaration](../simpleaichat/models.py#L37), [factory](../simpleaichat/models.py#L14)) | Constructed by default or restored through JSON. CSV loading constructs a new session and therefore a new session timestamp ([CSV load](../simpleaichat/simpleaichat.py#L293)). | Read by `ChatSession.__str__()` and recursive serialization ([session string](../simpleaichat/models.py#L52), [save dump](../simpleaichat/simpleaichat.py#L237)). | Identity/metadata; persistence. | JSON/session dumps retain it; CSV does not store session-level fields. It does not enter provider data and is not model-visible. | Records session construction/restoration time. |
| `auth` | `ChatSession`; required mapping of `SecretStr` values ([declaration](../simpleaichat/models.py#L38)) | `AIChat.new_session()` obtains `api_key` from kwargs or the environment and constructs the mapping ([construction](../simpleaichat/simpleaichat.py#L65)). JSON save excludes it, so load needs current kwargs/environment rather than persisted credentials ([save exclusion](../simpleaichat/simpleaichat.py#L237), [JSON load](../simpleaichat/simpleaichat.py#L296)). | `ChatGPTSession.prepare_request()` reads `auth['api_key']` and reveals the secret only to construct the authorization header ([header construction](../simpleaichat/chatgpt.py#L33)). `ChatSession` itself has no auth logic. | Authority/credential. | Crosses the transport boundary as an HTTP authorization header, not as provider JSON. Explicitly excluded from save files. Not model-visible. | Causes request authorization; does not record execution. |
| `api_url` | `ChatSession`; required `HttpUrl`, overridden with an OpenAI endpoint default by `ChatGPTSession` ([base declaration](../simpleaichat/models.py#L39), [subclass default](../simpleaichat/chatgpt.py#L18)) | Pydantic constructs/coerces it at session creation. Save excludes it; load reconstructs it from subclass/default/current kwargs ([save exclusion](../simpleaichat/simpleaichat.py#L237)). | Only transport methods read it when opening sync/async POST or stream requests ([sync dispatch](../simpleaichat/chatgpt.py#L104), [stream dispatch](../simpleaichat/chatgpt.py#L149), [async dispatch](../simpleaichat/chatgpt.py#L261)). `ChatSession` has no endpoint logic. | Runtime configuration; provider protocol. | Crosses the transport boundary as the request destination, not request JSON. Excluded from save files and not model-visible. | Causes provider selection at the endpoint level. |
| `model` | `ChatSession`; required `str` ([declaration](../simpleaichat/models.py#L40)) | `AIChat.new_session()` supplies `gpt-3.5-turbo` when absent, or uses caller/JSON data ([construction](../simpleaichat/simpleaichat.py#L60)). No production mutation follows construction. | `new_session()` also uses the string to decide whether it knows how to construct a `ChatGPTSession`; `prepare_request()` inserts it into provider data ([session selection](../simpleaichat/simpleaichat.py#L65), [request assembly](../simpleaichat/chatgpt.py#L51)). | Runtime configuration; provider protocol; persistence. | Crosses as the top-level provider request `model`; retained in JSON/session dumps, not message-only CSV. It affects execution but is not part of the model-visible `messages` array. | Causes provider model selection. |
| `system` | `ChatSession`; required `str`, overridden by `ChatGPTSession` with a default instruction ([base declaration](../simpleaichat/models.py#L41), [subclass default](../simpleaichat/chatgpt.py#L20)) | Built by `AIChat.build_system()` and supplied at session construction; a truthy per-call `system` argument overrides it without mutating the field, while an empty string falls back to the stored value because selection uses `system or self.system` ([builder](../simpleaichat/simpleaichat.py#L170), [request selection](../simpleaichat/chatgpt.py#L38)). Tool workflows synthesize temporary variants, also without assignment to the field ([tool system](../simpleaichat/chatgpt.py#L226)). | `prepare_request()` and tool workflows read it. `ChatSession` itself does not interpret it. | Model-visible data; runtime configuration; persistence. | Becomes `content` of a provider `system` message and is therefore model-visible after lowering. JSON/session dumps retain the stored value; CSV does not. | Causes generation by contributing instruction context; the stored value also records the session default. |
| `params` | `ChatSession`; `Dict[str, Any]`, base default `{}`, subclass default `{'temperature': 0.7}` ([base declaration](../simpleaichat/models.py#L42), [subclass default](../simpleaichat/chatgpt.py#L21)) | Constructed from defaults, caller kwargs, or JSON. Call-level params do not mutate it. Direct caller mutation remains possible. | `prepare_request()` chooses `params or self.params`, then expands the selected mapping last into request data ([selection and expansion](../simpleaichat/chatgpt.py#L51)). Empty call params therefore use session defaults; nonempty call params replace rather than merge with them. Because expansion is last, colliding keys can replace `model`, `messages`, or `stream`. | Runtime configuration; provider protocol; persistence. | Selected entries cross as top-level provider request fields. JSON/session dumps retain session params; CSV does not. They affect execution but are not message content. | Causes provider execution settings and can alter structural request fields through key collision. |
| `messages` | `ChatSession`; list of `ChatMessage`, default `[]` ([declaration](../simpleaichat/models.py#L43)) | `add_messages()` appends user then assistant; reset replaces the list; CSV load replaces it; JSON/Pydantic construction restores it; callers can also pass or mutate it directly ([append](../simpleaichat/models.py#L76), [reset](../simpleaichat/simpleaichat.py#L92), [CSV replacement](../simpleaichat/simpleaichat.py#L293)). | `format_input_messages()` reads it for subsequent requests; `__str__()` reads its count and last timestamp; save paths recursively serialize it ([lowering](../simpleaichat/models.py#L59), [string](../simpleaichat/models.py#L52), [save](../simpleaichat/simpleaichat.py#L237)). | History/context; execution result; persistence. | Selected messages cross into provider request dictionaries. The full list crosses JSON persistence; CSV persists only message rows. Stored content is model-visible only if selected by `recent_messages` and filtered through `input_fields`. | Both: records past inputs/results; selected history causes later generation. Appending/replacing the list is itself a session-state effect. |
| `input_fields` | `ChatSession`; annotated `Set[str]` but base default is the empty dict literal `{}`; subclass default is `{'role', 'content', 'name'}` ([base declaration](../simpleaichat/models.py#L44), [subclass default](../simpleaichat/chatgpt.py#L19)) | Pydantic preserves the unvalidated base default as a per-instance `dict`; caller-supplied iterables are validated as sets. The subclass supplies the normal provider field set. No production code mutates it. Run 001 captures the base default and mutable isolation ([default observation](../tests/test_models_characterization.py#L83), [isolation observation](../tests/test_models_characterization.py#L100)). | Only `format_input_messages()` reads it as the `include` filter for all three message groups ([lowering](../simpleaichat/models.py#L67)). | Runtime configuration; provider protocol. | The value itself does not cross a boundary; it controls which fields do. Save explicitly excludes it ([save exclusion](../simpleaichat/simpleaichat.py#L237)). It controls model visibility indirectly. | Causes the provider serialization shape. An empty value yields one empty mapping per message rather than omitting the messages ([Run 001 observation](../tests/test_models_characterization.py#L203)). |
| `recent_messages` | `ChatSession`; optional `int`, default `None` ([declaration](../simpleaichat/models.py#L45)) | Supplied at session construction or through JSON; no production mutation. There is no range validation in the declaration. | Only `format_input_messages()` reads it, before provider lowering ([selection](../simpleaichat/models.py#L62)). Falsy values (`None` and `0`) retain all history; truthy values use Python slicing `self.messages[-self.recent_messages:]` ([Run 001 observation](../tests/test_models_characterization.py#L177)). | Runtime configuration; history/context; persistence. | The number does not cross the provider boundary, but it controls which stored messages do. JSON retains it when non-`None`; CSV does not. Not model-visible. | Causes context selection before serialization; does not mutate history. |
| `save_messages` | `ChatSession`; optional `bool`, default `True` ([declaration](../simpleaichat/models.py#L46)) | Supplied at construction/JSON load. `add_messages()` also accepts an unvalidated call-level argument: only an actual `bool` is an explicit override; otherwise the field supplies the policy ([branching](../simpleaichat/models.py#L76)). | `add_messages()` is its sole production reader. Generation, streaming, and tool paths pass the call-level override into that operation ([sync call](../simpleaichat/chatgpt.py#L123), [stream call](../simpleaichat/chatgpt.py#L173), [tool call](../simpleaichat/chatgpt.py#L238)). | Runtime configuration; history/context; persistence. | Does not cross the provider boundary and is not model-visible. JSON/session dumps retain it; CSV does not. | Causes or suppresses the history-mutation state effect. It does not control disk persistence. |
| `total_prompt_length` | `ChatSession`; `int`, default `0` ([declaration](../simpleaichat/models.py#L47)) | Incremented directly from non-streaming provider usage in `gen()` and `gen_async()`, including output-schema responses ([sync update](../simpleaichat/chatgpt.py#L128), [async update](../simpleaichat/chatgpt.py#L285)). Streaming does not update it. | Read through `AIChat.message_totals()` and the matching property; serialized in JSON/session dumps ([accessor](../simpleaichat/simpleaichat.py#L304), [save dump](../simpleaichat/simpleaichat.py#L237)). | Accounting; persistence. | Does not cross provider requests and is not model-visible. JSON retains it; CSV stores per-message counts but no session aggregate. | Records cumulative execution accounting. |
| `total_completion_length` | `ChatSession`; `int`, default `0` ([declaration](../simpleaichat/models.py#L48)) | Incremented beside prompt totals in non-streaming sync/async generation ([sync update](../simpleaichat/chatgpt.py#L128), [async update](../simpleaichat/chatgpt.py#L285)); not derived from stored messages and not updated by streaming. | Read through `message_totals()`/property and serialized in JSON/session dumps ([accessors](../simpleaichat/simpleaichat.py#L304)). | Accounting; persistence. | Does not cross provider requests and is not model-visible. JSON retains it; CSV has only per-message values. | Records cumulative execution accounting. |
| `total_length` | `ChatSession`; `int`, default `0` ([declaration](../simpleaichat/models.py#L49)) | Incremented directly from non-streaming provider `usage.total_tokens` ([sync update](../simpleaichat/chatgpt.py#L128), [async update](../simpleaichat/chatgpt.py#L285)). Tool workflows accumulate the internal calls because they invoke `gen()`/`gen_async()` even when intermediate messages are not saved ([sync tool calls](../simpleaichat/chatgpt.py#L193), [async tool calls](../simpleaichat/chatgpt.py#L348)). | Read through `message_totals()`, `total_length`, and the `total_tokens` alias; serialized in JSON/session dumps ([accessors](../simpleaichat/simpleaichat.py#L304)). | Accounting; persistence. | Does not cross provider requests and is not model-visible. JSON retains it; CSV has only per-message values. | Records cumulative execution accounting, including unsaved internal non-streaming calls. |
| `title` | `ChatSession`; optional `str`, default `None` ([declaration](../simpleaichat/models.py#L50)) | Production assigns it only during interactive `AIChat` construction when no explicit system is supplied and console mode is enabled ([assignment](../simpleaichat/simpleaichat.py#L55)). JSON load/external construction can restore or supply it. | No production behavior reads it directly after assignment. Recursive string/save serialization can include it ([AIChat string dump](../simpleaichat/simpleaichat.py#L219), [save dump](../simpleaichat/simpleaichat.py#L237)). `ChatSession.__str__()` does not use it ([session string](../simpleaichat/models.py#L52)). | Identity/metadata; persistence. | JSON/session dumps retain it when non-`None`; CSV does not. It does not cross the provider boundary and is not model-visible. | Records a display label; causes no production behavior after assignment. |

## Operation matrix

This matrix includes methods declared on the two models plus inherited Pydantic
operations on which production explicitly relies.

| Operation | Declared owner / actual caller | Reads | Writes or returns | Responsibilities crossed | Observed behavior |
|---|---|---|---|---|---|
| Default timestamp factory `now_tz()` | Module helper used by both model declarations ([factory and declarations](../simpleaichat/models.py#L14)) | Current system time in UTC. | Returns a timezone-aware `datetime` for each defaulted message/session construction. | Identity/metadata; persistence. | Transient system and current-input messages receive timestamps even though normal provider lowering strips them ([construction](../simpleaichat/chatgpt.py#L38), [filter](../simpleaichat/chatgpt.py#L19)). |
| Pydantic construction and validation | Inherited by `ChatMessage` and `ChatSession`; called by direct callers, `new_session()`, and load paths ([session construction](../simpleaichat/simpleaichat.py#L60), [message load](../simpleaichat/simpleaichat.py#L277)) | Declarations, caller data, subclass defaults, nested message dictionaries. | Validated model instances; parsed URLs, protected secrets, nested `ChatMessage` values, dates, and numeric/boolean field values. Mutable defaults are copied per instance, as Run 001 verifies ([mutable-default observation](../tests/test_models_characterization.py#L100)). | Every stored responsibility enters through this one construction mechanism. | Required base fields have no custom domain validation beyond their annotations. Defaults are not validated by default, exposing the base `input_fields` dict/set mismatch; direct field assignment later is used without a model-level assignment validator ([declarations](../simpleaichat/models.py#L20), [direct mutations](../simpleaichat/simpleaichat.py#L92)). |
| `ChatMessage.model_dump()` / `model_dump_json()` | Inherited; called by `ChatMessage.__str__()`, provider lowering, and recursive session serialization ([message string](../simpleaichat/models.py#L31), [lowering](../simpleaichat/models.py#L67), [session save](../simpleaichat/simpleaichat.py#L237)) | All message fields or `input_fields` subset. | Python/JSON representation. | Provider protocol; model-visible data; execution result; accounting; identity/metadata; persistence. | The same serializer can expose the entire mixed record or, during lowering, strip it to provider-selected fields. `exclude_none=True` still retains `received_at`, as Run 001 records ([serialization observation](../tests/test_models_characterization.py#L71)). |
| `ChatMessage.__str__()` | `ChatMessage`; invoked by callers/inspection ([implementation](../simpleaichat/models.py#L31)) | Every non-`None` field through `model_dump()`. | Python `str(dict)` containing provider data, timestamp, result metadata, and accounting together. | Inspection crosses all co-located message responsibilities. | It is not provider lowering and applies no `input_fields` filter. |
| `ChatSession.model_dump()` / `model_dump_json()` | Inherited; called by `AIChat.__str__()` and `save_session()` ([AIChat string](../simpleaichat/simpleaichat.py#L219), [save](../simpleaichat/simpleaichat.py#L237)) | Session fields and nested messages. | Public string JSON or persistence dictionaries/JSON. | Identity/metadata; configuration; history; result; accounting; credential handling; persistence. | `save_session()` excludes `auth`, `api_url`, and `input_fields`; `AIChat.__str__()` excludes top-level `api_key` and `api_url`, although the declared credential field is named `auth` ([string exclusions](../simpleaichat/simpleaichat.py#L219), [save exclusions](../simpleaichat/simpleaichat.py#L237)). `SecretStr` controls JSON redaction where `auth` remains. |
| `ChatSession.__str__()` | `ChatSession`; invoked by callers/inspection ([implementation](../simpleaichat/models.py#L52)) | `created_at`, `messages[-1].received_at`, and message count. | Human-readable session timing/count string. | Identity/metadata; history/context. | It assumes at least one stored message; an empty default history makes the `messages[-1]` lookup fail before a string is returned. It ignores `title`. |
| `ChatSession.format_input_messages()` | Declared on `ChatSession`; called only by `ChatGPTSession.prepare_request()` ([method](../simpleaichat/models.py#L59), [caller](../simpleaichat/chatgpt.py#L51)) | `messages`, `recent_messages`, `input_fields`, plus transient system/current messages. | Ordered list of provider-shaped dictionaries. It does not mutate session state. | History selection; model-visible context; provider protocol; serialization. | It performs two operations at once: selects history, then lowers all message objects. Falsy `recent_messages` means all history. Runtime metadata is removed only because `input_fields` filters it. Empty `input_fields` yields empty dictionaries, not an empty message list ([Run 001 observations](../tests/test_models_characterization.py#L136)). |
| `ChatSession.add_messages()` | Declared on `ChatSession`; called by sync/async generation, streaming, and tool workflows ([method](../simpleaichat/models.py#L76), [call sites](../simpleaichat/chatgpt.py#L123)) | Call-level `save_messages`, session `save_messages`. | Appends the supplied user message followed by the supplied assistant message, or makes no change. | History/context; execution result; runtime policy; state mutation. | Only an actual call-level `bool` overrides the session field. Saving is pairwise; there is no single-message append path in this operation. Run 001 captures all four boolean/default cases ([observation](../tests/test_models_characterization.py#L113)). |

The unused module helper `orjson_dumps()` converts `orjson` bytes to text
([`models.py` lines 9-11](../simpleaichat/models.py#L9)); no production or test call
site references it. Current model serialization instead uses Pydantic dumps and
direct `orjson.dumps()` in `save_session()`
([`simpleaichat.py` lines 264-270](../simpleaichat/simpleaichat.py#L264)).

## Surrounding lifecycle operation matrix

These operations are not declared on `ChatMessage` or `ChatSession`, but they are
the actual owners or consumers of much of the state declared there.

| Operation | Fields/responsibilities consumed | State or boundary effect | Ownership observation |
|---|---|---|---|
| `AIChat.new_session()` | `model`, `auth`, caller-supplied session configuration, `id` ([implementation](../simpleaichat/simpleaichat.py#L60)) | Constructs and optionally registers a `ChatGPTSession`. | Creation policy for several `ChatSession` fields lives outside both session classes. |
| `ChatGPTSession.prepare_request()` | `auth`, `system`, `model`, `params`, `messages`, `recent_messages`, `input_fields`; plain/schema input and function metadata ([implementation](../simpleaichat/chatgpt.py#L23)) | Creates authorization headers, transient messages, provider-lowered message dictionaries, request controls, and schema/function metadata; returns the current input object for later history mutation. | One operation crosses credentials, runtime configuration, model-visible data, history selection, provider protocol, and schema metadata. It does not dispatch or mutate history. |
| `ChatGPTSession.schema_to_function()` | External Pydantic schema name, docstring, fields, and JSON schema ([implementation](../simpleaichat/chatgpt.py#L76)); recursively removes every `title` key through [`remove_a_key()`](../simpleaichat/utils.py#L93). | Returns OpenAI-era function metadata for the request. | The metadata is request-local and is not represented by `ChatMessage.function_call`; the identically named request concept and message field have separate paths. |
| `gen()` / `gen_async()` | Request configuration plus provider response message, finish, and usage data ([sync implementation](../simpleaichat/chatgpt.py#L90), [async implementation](../simpleaichat/chatgpt.py#L247)) | Dispatches transport, creates assistant results, may mutate history, and always updates aggregate usage after a successfully parsed response. Output-schema paths parse function arguments and update aggregates but do not construct or save an assistant `ChatMessage` ([sync branch](../simpleaichat/chatgpt.py#L112)). | Transport, response parsing, history mutation, schema result parsing, and accounting share one operation. |
| `stream()` / `stream_async()` | Provider stream chunks, history policy ([sync implementation](../simpleaichat/chatgpt.py#L136), [async implementation](../simpleaichat/chatgpt.py#L293)) | Dispatches streaming transport, accumulates content, creates an assistant message, and may mutate history. | Streamed execution records content/history but not per-message or session accounting because token counts are not returned in this path ([sync comment/result](../simpleaichat/chatgpt.py#L167), [async comment/result](../simpleaichat/chatgpt.py#L324)). |
| Tool workflows | `system`, `params`, accounting through internal generation, final history pair ([sync workflow](../simpleaichat/chatgpt.py#L177), [async workflow](../simpleaichat/chatgpt.py#L332)) | Performs one or two unsaved internal model calls, invokes an external callable, then manually stores the original prompt and final response according to history policy. | Recorded history can omit model calls whose usage remains in session accounting; history and accounting therefore describe different scopes. |
| `reset_session()` | `messages` ([implementation](../simpleaichat/simpleaichat.py#L92)) | Replaces history with an empty list; cumulative totals and other session metadata remain unchanged. | History reset ownership lives in `AIChat`, separate from `add_messages()` and accounting. |
| `save_session()` / `load_session()` | Session dump, nested message fields, timestamps, constructor kwargs ([save](../simpleaichat/simpleaichat.py#L229), [load](../simpleaichat/simpleaichat.py#L272)) | JSON round-trips most non-secret session state; CSV writes message rows only and reconstructs them into a newly configured session. CSV normalizes timestamps through local time text. | Persistence format and restoration policy live outside the models but depend directly on their field layout and Pydantic construction. The CSV schema omits `name` and `function_call`, while the recursive dump can contain them when non-`None` ([CSV fields](../simpleaichat/simpleaichat.py#L245)). |
| Accounting accessors | Aggregate total fields ([implementation](../simpleaichat/simpleaichat.py#L304)) | Expose any requested attribute through `getattr`, with named properties for the three totals. | Read ownership is generic and outside `ChatSession`; message-level accounting is not consulted. |

## Pydantic behavior relied on by production

1. **Default construction.** `id`, `created_at`, and `received_at` use factories,
   while mutable mappings/lists/sets are class-level defaults
   ([model declarations](../simpleaichat/models.py#L20)). Pydantic supplies separate
   mutable objects per instance; Run 001 verifies that mutating one session's
   `params`, `input_fields`, or `messages` does not alter another
   ([test](../tests/test_models_characterization.py#L100)).

2. **Validation and coercion at construction.** Production supplies ordinary
   strings for `HttpUrl` and credential values when constructing a
   `ChatGPTSession` ([constructor](../simpleaichat/simpleaichat.py#L65)). Pydantic
   produces the declared `HttpUrl` and `SecretStr` values that later transport
   code consumes ([header](../simpleaichat/chatgpt.py#L33),
   [URL use](../simpleaichat/chatgpt.py#L104)). CSV rows arrive as strings; after
   explicit timestamp conversion, `ChatMessage(**row)` is responsible for
   constructing the declared optional integer fields
   ([CSV load](../simpleaichat/simpleaichat.py#L277)). Nested message dictionaries
   from JSON likewise become `ChatMessage` values through session construction
   ([JSON load](../simpleaichat/simpleaichat.py#L296)).

3. **Defaults are not validated into their annotations.** The base declaration
   says `Set[str]` but uses `{}`, so an omitted `input_fields` is a `dict` in the
   base `ChatSession`; Run 001 captures this exact result
   ([declaration](../simpleaichat/models.py#L44),
   [test](../tests/test_models_characterization.py#L83)). The normal
   `ChatGPTSession` subclass supplies a set instead
   ([subclass declaration](../simpleaichat/chatgpt.py#L19)).

4. **Recursive serialization is the shared mechanism.** The unrestricted message
   dump keeps provider data, timestamps, result metadata, and accounting in one
   mapping ([Run 001 test](../tests/test_models_characterization.py#L43)). Provider
   lowering uses the same operation with `include=input_fields`; persistence uses
   a recursive session dump with top-level exclusions
   ([lowering](../simpleaichat/models.py#L67),
   [persistence dump](../simpleaichat/simpleaichat.py#L237)).

5. **Post-construction state changes are direct assignments or mutations.** The
   code appends messages, replaces the history list, assigns `title`, and increments
   totals directly ([append](../simpleaichat/models.py#L86),
   [reset](../simpleaichat/simpleaichat.py#L92),
   [title assignment](../simpleaichat/simpleaichat.py#L55),
   [accounting update](../simpleaichat/chatgpt.py#L128)). Neither model declares
   custom setters or assignment-validation configuration
   ([complete declarations](../simpleaichat/models.py#L20)).

6. **Exclusion policy is call-site-specific.** Provider lowering includes only
   `input_fields`; `save_session()` excludes `auth`, `api_url`, and `input_fields`;
   `AIChat.__str__()` uses a different exclusion set; `ChatMessage.__str__()`
   excludes only `None` values ([lowering](../simpleaichat/models.py#L67),
   [save](../simpleaichat/simpleaichat.py#L237),
   [AIChat string](../simpleaichat/simpleaichat.py#L219),
   [message string](../simpleaichat/models.py#L31)). There is no single model-level
   serialization policy.

## Observed fossils and asymmetries

These are facts about the inherited behavior, not correction proposals.

- The base `input_fields` annotation/default mismatch produces a runtime `dict`
  when omitted; the provider subclass supplies a `set`
  ([base](../simpleaichat/models.py#L44),
  [subclass](../simpleaichat/chatgpt.py#L19),
  [offline observation](../tests/test_models_characterization.py#L83)).
- `recent_messages=None` and `recent_messages=0` both mean all history because
  selection is based on truthiness. Other integers are accepted without a range
  constraint and are passed through the negated Python slice expression
  ([implementation](../simpleaichat/models.py#L62),
  [offline observation](../tests/test_models_characterization.py#L177)).
- Empty `input_fields` lowers every system/history/current object to `{}` rather
  than removing it ([implementation](../simpleaichat/models.py#L67),
  [offline observation](../tests/test_models_characterization.py#L203)).
- Call-level `params=None` and `{}` both select session defaults. Any nonempty map
  replaces rather than merges with defaults, and its entries are expanded after
  structural request keys ([implementation](../simpleaichat/chatgpt.py#L51),
  [offline observation](../tests/test_provider_lowering_characterization.py#L102)).
- `ChatMessage.function_call` is not populated or selected by the standard path.
  Schema output instead creates a top-level request `function_call` mapping, and
  schema input creates a message whose role is `function`
  ([field](../simpleaichat/models.py#L24),
  [schema request](../simpleaichat/chatgpt.py#L42),
  [request metadata](../simpleaichat/chatgpt.py#L59)).
- Non-streaming assistant messages can carry per-message accounting and finish
  metadata; streamed assistant messages do not. Session aggregates are updated by
  non-streaming calls only ([non-streaming](../simpleaichat/chatgpt.py#L113),
  [streaming](../simpleaichat/chatgpt.py#L167),
  [aggregate update](../simpleaichat/chatgpt.py#L128)).
- Output-schema non-streaming calls update session aggregates but do not call
  `add_messages()` and do not create an assistant message
  ([branch and update](../simpleaichat/chatgpt.py#L112)).
- Tool workflows deliberately suppress history for their internal calls, then
  manually store a different final pair; aggregate accounting still includes the
  internal non-streaming calls ([sync workflow](../simpleaichat/chatgpt.py#L193),
  [manual append](../simpleaichat/chatgpt.py#L238)).
- `ChatSession.__str__()` indexes the final history item and therefore cannot render
  a newly constructed empty session ([implementation](../simpleaichat/models.py#L52));
  `title` is not used by that renderer.
- JSON and CSV persistence have different scopes. JSON retains non-secret session
  state and recursively serialized messages; CSV retains only its seven declared
  message columns. `name` and `function_call` have no CSV columns
  ([save dump](../simpleaichat/simpleaichat.py#L237),
  [CSV fields](../simpleaichat/simpleaichat.py#L245)).
- The `ChatSession.id` factory itself is per-construction, but wrapper signatures
  also contain eager `uuid4()` defaults that are created when the Python function
  definitions execute ([model factory](../simpleaichat/models.py#L36),
  [AIChat signature](../simpleaichat/simpleaichat.py#L27),
  [load signature](../simpleaichat/simpleaichat.py#L272)).
- `orjson_dumps()` remains declared in `models.py` but has no caller; active JSON
  paths use Pydantic serialization or direct `orjson.dumps()`
  ([helper](../simpleaichat/models.py#L9),
  [active JSON write](../simpleaichat/simpleaichat.py#L264)).

## Co-located independent responsibilities and data streams

The following independent streams are currently stored together inside the two
models:

1. **Provider message protocol:** `role`, `name`, the dormant message-level
   `function_call`, and the `input_fields` rule that selects the provider envelope
   ([message fields](../simpleaichat/models.py#L20),
   [selection rule](../simpleaichat/chatgpt.py#L19)).
2. **Model-visible data:** system instruction content, current input content, and
   selected prior message content
   ([message construction](../simpleaichat/chatgpt.py#L38),
   [ordered lowering](../simpleaichat/models.py#L67)).
3. **History/context state:** the mutable `messages` list, ordering, history-window
   selection, and the save/no-save policy
   ([history fields](../simpleaichat/models.py#L43),
   [history operations](../simpleaichat/models.py#L59)).
4. **Runtime and provider configuration:** endpoint, model identifier, request
   parameters, stored system default, and provider-field selection
   ([session fields](../simpleaichat/models.py#L38),
   [provider defaults](../simpleaichat/chatgpt.py#L17)).
5. **Authority and credentials:** the authentication mapping revealed only when
   the transport header is built
   ([credential field](../simpleaichat/models.py#L38),
   [header construction](../simpleaichat/chatgpt.py#L33)).
6. **Execution results:** assistant content and finish metadata returned by the
   provider, including the streamed/non-streamed representation difference
   ([non-streamed result](../simpleaichat/chatgpt.py#L113),
   [streamed result](../simpleaichat/chatgpt.py#L167)).
7. **Accounting:** optional per-message prompt/completion/total counts and separate
   cumulative session counts
   ([message fields](../simpleaichat/models.py#L27),
   [session fields](../simpleaichat/models.py#L47),
   [updates](../simpleaichat/chatgpt.py#L128)).
8. **Identity and chronology:** session id/title/creation time and message receipt
   time ([message time](../simpleaichat/models.py#L25),
   [session metadata](../simpleaichat/models.py#L36)).
9. **Persistence representation:** recursive Pydantic dumps, call-site exclusions,
   JSON session state, CSV message rows, and timestamp normalization during CSV
   save/load ([save](../simpleaichat/simpleaichat.py#L229),
   [load](../simpleaichat/simpleaichat.py#L272)).

These streams interact, but the source shows that they have different producers,
consumers, timing, and boundaries. Their co-location is structural: the fields sit
on two Pydantic models even when their only production consumers live in request
preparation, transport, orchestration, accounting accessors, or persistence code.
The declarations and those external consumers are visible side by side in
[`models.py`](../simpleaichat/models.py#L20),
[`chatgpt.py`](../simpleaichat/chatgpt.py#L23), and
[`simpleaichat.py`](../simpleaichat/simpleaichat.py#L60).

## Ownership gaps and cross-responsibility operations

- `ChatSession` declares credentials, endpoint, model, system, parameters, and
  provider field selection, but their principal consumers are methods on
  `ChatGPTSession`; the base session's own logic uses only history selection,
  serialization selection, save policy, and inspection fields
  ([base methods](../simpleaichat/models.py#L52),
  [provider consumer](../simpleaichat/chatgpt.py#L23)).
- A `ChatMessage` is both the transient request-time carrier and the durable history
  record. The transient system/current objects receive persistence timestamps and
  accounting-capable fields, while stored result objects retain provider envelope,
  execution metadata, and persistence metadata together
  ([message declaration](../simpleaichat/models.py#L20),
  [transient construction](../simpleaichat/chatgpt.py#L38),
  [result construction](../simpleaichat/chatgpt.py#L113)).
- History has multiple mutating owners: `add_messages()` appends pairs,
  `reset_session()` replaces the list, CSV load replaces it after construction,
  JSON load reconstructs it, and direct Pydantic construction accepts it
  ([append](../simpleaichat/models.py#L76),
  [reset](../simpleaichat/simpleaichat.py#L92),
  [load](../simpleaichat/simpleaichat.py#L272)).
- Accounting has separate storage scopes and update paths. Per-message counts are
  populated only on non-streaming assistant messages, while session totals are
  mutated independently and exposed without consulting message history
  ([message/result update](../simpleaichat/chatgpt.py#L113),
  [session update](../simpleaichat/chatgpt.py#L128),
  [accessors](../simpleaichat/simpleaichat.py#L304)).
- Persistence behavior is owned by `AIChat`, but its schemas are implicit products
  of model fields and call-specific dump exclusions. JSON and CSV therefore retain
  different subsets and restore sessions through different construction paths
  ([save](../simpleaichat/simpleaichat.py#L229),
  [load](../simpleaichat/simpleaichat.py#L272)).
- `format_input_messages()` crosses history policy, provider-field policy,
  serialization, and model-visible ordering in one operation
  ([implementation](../simpleaichat/models.py#L59)). `prepare_request()` crosses
  credential handling, system/default resolution, input representation, history
  lowering, provider request configuration, and schema/function metadata
  ([implementation](../simpleaichat/chatgpt.py#L23)). `gen()` and `gen_async()` then
  cross transport, response interpretation, history mutation, and accounting
  ([sync](../simpleaichat/chatgpt.py#L90),
  [async](../simpleaichat/chatgpt.py#L247)).
- `title` has a production writer and serialization consumers but no production
  behavioral reader; `function_call` has a declaration and generic serialization
  path but no standard producer or provider-lowering consumer
  ([title assignment](../simpleaichat/simpleaichat.py#L55),
  [function-call declaration](../simpleaichat/models.py#L24)).

This is the stopping point of the excavation. It identifies current streams,
consumers, effects, boundaries, and missing ownership concentration without naming
or selecting replacements.

## Run 002 verification record

Verification was performed on 2026-08-15 after the excavation was written.

- `git diff --exit-code -- simpleaichat` exited successfully, confirming no tracked
  production-source difference from `HEAD`.
- Run 002 added only this document. The two pre-existing Run 001 test files retained
  their pre-run byte content. Their SHA-256 values were:
  - `605CF0EA043B9944D2284346457D4AC46D5BECF9C206CC5F97E7CFBD4623046C`
    for `tests/test_models_characterization.py`.
  - `37F5D5AF36321A430EF5283F16021A4F08ED5B62089630434A6D96F2F17B7B62`
    for `tests/test_provider_lowering_characterization.py`.
- The test modules were discovered first, after which `socket.socket`,
  `socket.create_connection`, and `socket.getaddrinfo` were replaced with a guard
  that raises on use. All 14 Run 001 tests then passed; no transport mock was used.
- All 280 source links in the draft resolved to existing local files and valid line
  numbers at verification time.
