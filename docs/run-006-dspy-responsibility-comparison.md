# Run 006: DSPy 3.3.0 responsibility comparison

## Purpose and stopping rule

This artifact compares the model-call responsibilities exposed by Runs 001–005
with DSPy 3.3.0. It asks where Ars Modulus can stop owning model-realization
machinery without giving DSPy ownership of Ars semantics.

It is not an integration design, migration plan, or accepted architecture
decision. It introduces no replacement types and proposes no production edits.
Its stopping rule is:

```text
evidence gathered
    ↓
hypotheses tested
    ↓
surviving dependency boundary identified
    ↓
STOP
```

The decision question is:

> At what exact level should Ars stop owning machinery and begin depending on
> DSPy?

## Evidence and version policy

### Pinned subjects

- **Ars/SimpleAIChat:** repository commit
  [`53affcdb784b39a62ac428497129c556902f77ce`](https://github.com/Tpanarchist/Ars_Modulus/tree/53affcdb784b39a62ac428497129c556902f77ce),
  the Run 005 completion commit. Local source links in this document describe
  that commit.
- **DSPy:** stable release
  [`3.3.0`](https://github.com/stanfordnlp/dspy/releases/tag/3.3.0), release
  commit
  [`e4e97aae29b8ad8aa2fb7e99ffae6fd52970fad8`](https://github.com/stanfordnlp/dspy/commit/e4e97aae29b8ad8aa2fb7e99ffae6fd52970fad8).
  The repository lock also names `dspy==3.3.0` and
  `litellm==1.96.2`
  ([lock file](../requirements-lock.txt#L16),
  [LiteLLM pin](../requirements-lock.txt#L37)). DSPy implementation links use
  the immutable `3.3.0` tag.

The installed DSPy package was used only to inspect the version-matched source.
No DSPy model call or provider call is evidence in this artifact.

The release-linked migration guide was retrieved on 2026-08-15 to classify the
3.3 transition. Tagged 3.3.0 implementation is authoritative for executable
behavior if that living guide later changes.

### Deliberately excluded source

DSPy's `main`-branch roadmap is not evidence for current architecture. The file
itself says it is from August 2024 and is “highly outdated”
([roadmap warning](https://github.com/stanfordnlp/dspy/blob/main/docs/docs/roadmap.md#L1-L4)).
Current-state claims instead use the 3.3.0 release, tagged implementation, and
the public typed-LM migration plan.

### Maturity labels

| Label | Meaning in this artifact |
| --- | --- |
| **Default** | Runs without an experimental switch or a custom typed LM contract in DSPy 3.3.0. |
| **Compatibility** | Executes in 3.3.0 to preserve legacy behavior while the typed boundary is introduced. |
| **Experimental** | Public and importable, but direct typed calls require `dspy.context(experimental=True)`. |
| **Alternative contract** | Available to a custom LM that explicitly declares `forward_contract = "typed_lm"`; not the built-in `dspy.LM` default. |
| **Planned** | Described as a later migration step or TODO, not current behavior. |

DSPy's migration guide says default calls still return legacy outputs, typed
direct calls are opt-in, and the migration spans the 3.3–3.6/4.0 series
([migration status](https://dspy.ai/community/normalized-lm-api-migration/#guide-for-dspy-users),
[version sequence](https://dspy.ai/community/normalized-lm-api-migration/#version-sequence)).
The built-in `dspy.LM` explicitly declares the legacy contract
([`LM.forward_contract`](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/lm.py#L56-L62)).

### Semantic test used in the comparison

Ars already distinguishes type, guarantee, evidence, requirement, and policy,
and says they must not silently substitute for one another
([design principles](../README.md#L69)). It also says model context does not
create authority and runtime provenance is not model privilege
([authority principle](../README.md#L59)). Those statements are design criteria,
not claims that the inherited implementation already realizes them.

For every candidate field or boundary, this artifact keeps three questions
separate:

1. **Representable:** can a DSPy object contain a value with this label or shape?
2. **Meaning-preserving:** does DSPy's actual path retain what the value means,
   rather than merely retaining bytes or an arbitrary mapping entry?
3. **Semantically enforced:** does DSPy interpret the meaning and constrain
   behavior because of it?

An arbitrary `metadata` dictionary can make a value representable. That fact
alone does not establish meaning preservation or enforcement.

Statements labeled **Ownership evidence**, **Result**, or **boundary** below are
Run 006 inferences from the linked behavior. They are not claims made by DSPy and
not accepted Ars architecture decisions.

## The two model-call stacks

### Exposed SimpleAIChat stack

```text
ChatSession.messages + recent_messages
    ↓ select_history()
selected original ChatMessage objects
    ↓ lower_messages()
OpenAI-shaped {role, content, name?} dictionaries
    ↓ assemble_request()
OpenAI request body
    ↓ send_request() / send_request_async()
HTTP POST + response.json()
    ↓
raw decoded provider object
    ↓ ChatGPTSession.gen() / gen_async()
content/schema interpretation
    + ChatMessage construction
    + history mutation
    + accounting mutation
```

The stages and their evidence are:

- `select_history()` applies inherited truthiness and Python slicing directly to
  session history ([selection](../simpleaichat/models.py#L95)).
- `lower_messages()` orders system, selected history, and current input, then
  applies `model_dump(include=input_fields, exclude_none=True)` to each message
  ([lowering](../simpleaichat/models.py#L101)). This is the exact boundary where
  the current objects become provider-shaped dictionaries.
- `prepare_request()` assigns provider roles before lowering, resolves schemas
  and parameters, and delegates final body construction
  ([preparation](../simpleaichat/chatgpt.py#L23)).
- `assemble_request()` constructs the provider body and preserves the inherited
  parameter-overwrite ordering ([assembly](../simpleaichat/chatgpt.py#L396)).
- The sync and async transport seams stringify the URL, dispatch with
  `timeout=None`, and call `response.json()`
  ([sync transport](../simpleaichat/chatgpt.py#L419),
  [async transport](../simpleaichat/chatgpt.py#L429)).
- `gen()` and `gen_async()` still interpret OpenAI response keys, construct
  `ChatMessage`, mutate history, and increment accounting
  ([sync interpretation](../simpleaichat/chatgpt.py#L95),
  [async interpretation](../simpleaichat/chatgpt.py#L246)).

### Actual DSPy 3.3 default program stack

DSPy's 3.3 release describes a typed direction, but the default program path is
transitional. The implementation executes this stack:

```text
Signature + inputs + demos
    ↓ Predict.forward()
Adapter preprocessing
    ↓ Adapter.format()
OpenAI-chat-shaped {role, content} dictionaries
    ↓ Adapter._coerce_lm_messages()
LMMessage objects
    ↓ Adapter._render_request()
LMRequest
    ↓ Adapter._legacy_call_kwargs()
OpenAI/LiteLLM-shaped messages + kwargs
    ↓ built-in dspy.LM (legacy BaseLM path)
LiteLLM/provider dispatch
    ↓
OpenAI-like provider response
    ↓ BaseLM processing
legacy list[str | dict] + LM history/usage effects
    ↓ Adapter._normalize_legacy_outputs()
LMResponse
    ↓ legacy_outputs_from_lm_response()
legacy adapter outputs
    ↓ Adapter._call_postprocess() / parse()
typed field dictionaries
    ↓ Prediction.from_completions()
Prediction
```

`Predict.forward()` chooses the configured adapter or `ChatAdapter`, invokes it,
and turns returned field dictionaries into a `Prediction`
([predict path](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/predict/predict.py#L250-L275)).
The adapter formats the signature, demos, history, and current inputs before it
constructs an `LMRequest`
([adapter call](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/base.py#L314-L364)).

The normalization does not yet remove provider-shaped intermediates:

- `Adapter.format()` currently emits dictionaries whose roles are `system`,
  `user`, `assistant`, and sometimes `tool`
  ([format ordering](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/base.py#L366-L441)).
- Those dictionaries are coerced to `LMMessage`; a TODO says direct typed
  rendering is later work
  ([message bridge](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/base.py#L266-L303)).
- The adapter constructs `LMRequest`, converts it back with
  `to_openai_chat_request()`, calls `BaseLM` with provider-shaped kwargs, wraps
  the legacy outputs in `LMResponse`, and converts them back for existing parser
  behavior
  ([request bridge](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/base.py#L208-L264),
  [response bridge](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/base.py#L305-L347)).
- The built-in `LM.forward()` chooses a LiteLLM completion function and passes a
  request containing `model`, `messages`, and merged kwargs
  ([LM dispatch](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/lm.py#L209-L265),
  [LiteLLM call](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/lm.py#L495-L510)).

This matches the release's explicit account of the compatibility path:
`adapter messages → LMRequest → OpenAI/LiteLLM kwargs → current BaseLM →
LMResponse → existing adapter postprocess`
([3.3.0 release](https://github.com/stanfordnlp/dspy/releases/tag/3.3.0)).

### DSPy's other 3.3 call paths

The typed vocabulary is real and public, but it has three distinct execution
conditions:

| Condition | Request path | Returned form | Maturity |
| --- | --- | --- | --- |
| Built-in `dspy.LM`, ordinary direct call | `prompt/messages → legacy forward()` | `list[str | dict]` | Default |
| Explicit `LMRequest` or `experimental=True` with built-in `dspy.LM` | `LMRequest → OpenAI-shaped kwargs → legacy forward() → LMResponse` | `LMResponse` | Experimental/compatibility |
| Custom `BaseLM` with `forward_contract = "typed_lm"` | `LMRequest → custom forward() → LMResponse` | `LMResponse`, or legacy outputs when the caller did not request a typed result | Alternative contract |

`BaseLM.__call__()` selects among these paths and deliberately retains legacy
outputs by default
([call selection](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/base_lm.py#L321-L406),
[normalization gate](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/base_lm.py#L408-L430)).
For a legacy LM on the typed path, `BaseLM` converts the normalized request back
to OpenAI kwargs before calling `forward()`
([legacy typed bridge](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/base_lm.py#L479-L576)).
Only a class that opts into `typed_lm` implements the direct
`forward(LMRequest) -> LMResponse` contract
([contract declaration](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/base_lm.py#L208-L264)).

## DSPy 3.3 representation inventory

| Object or layer | What it currently represents | What it currently owns | Maturity |
| --- | --- | --- | --- |
| `Signature` | Named Pydantic input/output fields plus instructions and field metadata. Every field must be explicitly input or output ([signature validation](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/signatures/signature.py#L184-L237)). | Task-facing field declaration consumed by modules and adapters; it does not itself dispatch or parse a provider response. | Default |
| `History` | A frozen list of dictionaries whose keys belong to the associated signature ([history type](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/types/history.py#L6-L68)). | Explicit conversation-history input. It is not implicit LM session state. | Default |
| Adapter-formatted messages | System instructions, demos, explicit history, and current input represented as role/content dictionaries ([format path](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/base.py#L366-L441)). | Model-visible rendering and ordering. | Default, provider-shaped |
| `LMMessage` and `LMPart` | A role, typed content parts, optional name, and arbitrary metadata. Parts cover text, media, documents, tool calls/results, reasoning, citations, refusals, and opaque binary data ([parts](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L50-L244), [message](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L247-L290)). | Provider-neutral message vocabulary and validation. | Public; used inside compatibility path |
| `LMRequest` | Model, typed messages, tools, generation config, and arbitrary metadata ([request](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L624-L686)). | Normalized model-call description. It does not itself perform transport or enforce application policy. | Public; direct typed calls experimental |
| `LMConfig` | Common generation controls plus an `extensions` mapping for unknown/provider-specific kwargs ([config](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L470-L496)). | Request configuration normalization and override merging. | Public; used in compatibility path |
| `LMResponse` / `LMOutput` | Typed output parts, finish reason, usage, cost, cache state, provider response/data, and arbitrary metadata ([output](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L725-L806), [response](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L809-L925)). | Provider-neutral result representation and legacy-output conversion. | Public; direct typed returns experimental by default |
| `BaseLM` | Model configuration, callbacks, retry/cache defaults, call history, and legacy/typed contract dispatch ([construction](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/base_lm.py#L171-L206), [contracts](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/base_lm.py#L208-L264)). | Shared LM runtime and normalized call/history boundary. | Default base class; dual contract during migration |
| `dspy.LM` | Provider/model selection, LiteLLM-backed calls, caching/retries, capability checks, and provider-error normalization ([LM class](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/lm.py#L56-L163), [dispatch](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/lm.py#L209-L265)). | Built-in provider realization. | Default, legacy contract |
| DSPy LM errors | Configuration, auth, billing, rate limit, invalid request, context window, unsupported model/feature, timeout, server, transport, and unexpected boundary failures with structured metadata ([error hierarchy](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/utils/exceptions.py#L8-L221)). | Normalized classification of failures at or below the LM boundary. | Default for `dspy.LM` |

## Responsibility-by-responsibility comparison

### Model-visible input representation

**SimpleAIChat.** `ChatMessage` co-locates provider role/content/name with runtime
timestamps, finish state, and accounting
([message fields](../simpleaichat/models.py#L20)). The normal request path creates
system/user/function roles before lowering
([message construction](../simpleaichat/chatgpt.py#L38)).

**DSPy.** A `Signature` preserves named task fields and annotations until the
adapter formats them. `ChatAdapter` then renders field names, types, instructions,
and values into system/user text
([field rendering](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/chat_adapter.py#L116-L200)).
The current adapter base still represents the rendered call as provider-shaped
role/content dictionaries before coercion to `LMMessage`.

**Ownership evidence.** DSPy owns a richer task-to-model rendering mechanism than
SimpleAIChat. It does not own the decision that an Ars value is eligible or safe
to become model-visible. That decision must occur before values enter Signature
inputs or direct `LMMessage` parts.

### History selection and meaning

**SimpleAIChat.** History is implicit mutable session state. `recent_messages`
selects a slice before lowering, and selected objects are the original
`ChatMessage` instances
([session fields](../simpleaichat/models.py#L35),
[selection](../simpleaichat/models.py#L95)).

**DSPy.** Conversation history is an explicit `History` input. The adapter removes
the history field from a copy of current inputs and renders each history dictionary
as user/assistant turns, with additional native tool-call handling
([history formatting](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/base.py#L603-L711)).
Separately, `BaseLM.history` records LM calls; it is execution history, not
automatically reused model context
([runtime history construction](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/base_lm.py#L171-L203),
[history recording](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/base_lm.py#L588-L604)).

**Ownership evidence.** DSPy can render supplied history and record LM execution,
but it does not provide SimpleAIChat's implicit session-history selection policy.
Selection, retention, visibility, and the semantic meaning of context remain
caller concerns.

### Provider lowering

**SimpleAIChat.** `lower_messages()` is directly and exclusively OpenAI-shaped:
role/content/name dictionaries filtered by `input_fields`
([lowering](../simpleaichat/models.py#L101)).

**DSPy.** Adapters own field-aware prompt formatting. DSPy's typed vocabulary can
then represent messages and multimodal/tool content, while
`to_openai_chat_request()` owns conversion to Chat Completions kwargs
([typed request conversion](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/openai_format.py#L70-L112)).
The current adapter formatter nevertheless produces role/content dictionaries
before typed coercion, so its provider neutrality is incomplete in 3.3.

**Ownership evidence.** Rebuilding `lower_messages()` into a general provider
adapter would duplicate DSPy's active area of ownership. DSPy's exact internal
typed seam is still transitional, so Ars should depend on DSPy's higher-level
realization behavior rather than mirror or expose its 3.3 conversion sequence as
Ars semantics.

### Request assembly and configuration

**SimpleAIChat.** `assemble_request()` creates one OpenAI request dictionary and
allows arbitrary params to overwrite `model`, `messages`, and `stream`, followed
by schema metadata overwrites
([assembly](../simpleaichat/chatgpt.py#L396)).

**DSPy.** `LMRequest` separates model, messages, tools, config, and metadata.
`LMConfig` gives common parameters named fields, groups reasoning/tool/cache
controls, and places unknown keys in `extensions`
([request](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L624-L686),
[config normalization](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L470-L570)).
Provider conversion then selects the Chat, Responses, or text-completion wire
shape
([Chat conversion](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/openai_format.py#L77-L112),
[Responses conversion](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/openai_format.py#L124-L170),
[text conversion](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/openai_format.py#L221-L235)).

**Ownership evidence.** DSPy owns substantially more request-configuration and
provider-shaping machinery. `LMRequest` is a useful DSPy boundary, but its
experimental/default split makes it a poor candidate for an Ars domain type in
3.3.

### Transport

**SimpleAIChat.** The Run 005 seam owns one HTTP POST, URL conversion,
`timeout=None`, and JSON decoding; caller-supplied clients and credentials remain
session concerns ([transport](../simpleaichat/chatgpt.py#L419)). Exceptions pass
through without classification.

**DSPy.** The built-in `LM` routes sync and async calls through LiteLLM, supplies
retry configuration, participates in DSPy caching, supports several endpoint
styles, and normalizes LiteLLM/provider exceptions
([sync/async dispatch](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/lm.py#L209-L323),
[LiteLLM functions](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/lm.py#L495-L615)).
The 3.3 release says LiteLLM is lazy-loaded but remains the built-in compatibility
bridge; making it optional is a later direction
([release notes](https://github.com/stanfordnlp/dspy/releases/tag/3.3.0)).

**Ownership evidence.** Ordinary provider transport, retries, caching, endpoint
routing, and provider exception normalization are established DSPy/LiteLLM
responsibilities. No current Ars semantic requirement justifies rebuilding them.

### Response normalization and interpretation

**SimpleAIChat.** `gen()` knows OpenAI `choices`, `message`, `function_call`, and
`usage` keys. It couples provider interpretation to message construction,
history, and cumulative accounting
([interpretation](../simpleaichat/chatgpt.py#L111)).

**DSPy.** `LMResponse` and `LMOutput` represent typed content, finish state, usage,
cost, cache state, provider response/data, and metadata. The default adapter path
currently wraps legacy outputs only to convert them back for existing parsers
([response types](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L725-L925),
[compatibility conversion](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/openai_format.py#L977-L1018)).

**Ownership evidence.** Provider response decoding and normalization fit DSPy's
LM responsibility. Whether a parsed value satisfies an Ars requirement, may
cause an effect, or changes Ars-owned state remains above that boundary.

### Structured input and output

**SimpleAIChat.** `schema_to_function()` turns one Pydantic schema into OpenAI
function metadata; schema input becomes a provider `function` message; schema
output parses JSON arguments
([schema construction](../simpleaichat/chatgpt.py#L41),
[`schema_to_function`](../simpleaichat/chatgpt.py#L81),
[schema response parsing](../simpleaichat/chatgpt.py#L123)).

**DSPy.** Signatures separate input and output fields. `ChatAdapter` checks for all
declared output fields and parses values through their annotations
([Chat parsing](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/chat_adapter.py#L218-L253),
[Pydantic-backed value parsing](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/utils.py#L149-L198)).
`JSONAdapter` can request provider-native structured outputs when supported,
fall back to JSON mode for local schema/setup problems, and still validate the
returned field set and values
([structured-output selection](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/json_adapter.py#L40-L119),
[JSON parsing](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/json_adapter.py#L167-L200),
[schema construction](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/json_adapter.py#L231-L300)).

**Ownership evidence.** DSPy substantially subsumes provider schema construction,
format instructions, response parsing, and shape/type validation. Successful
parsing can enforce a syntactic postcondition—such as a `Literal` member or a
Pydantic shape—but it does not prove semantic correctness, satisfy an
application requirement, grant authority, or choose the policy for a parse
failure. DSPy mechanisms can contribute to an Ars guarantee without being the
whole guarantee.

### Errors

**SimpleAIChat.** Transport exceptions are untranslated; missing expected response
keys become a broad `KeyError` containing the decoded object
([transport](../simpleaichat/chatgpt.py#L419),
[response failure](../simpleaichat/chatgpt.py#L130)).

**DSPy.** `dspy.LM` maps provider failures into a structured `LMError` hierarchy
and retains model, provider, provider code, status, request ID, and retry delay
when available
([mapping](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/lm.py#L185-L207),
[hierarchy](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/utils/exceptions.py#L8-L221)).
Adapters distinguish LM failures from adapter parse failures so provider errors
do not trigger format fallbacks
([Chat fallback](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/chat_adapter.py#L76-L114),
[`AdapterParseError`](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/utils/exceptions.py#L224-L260)).

**Ownership evidence.** DSPy's error objects describe failures at the realization
boundary. They do not decide Ars recovery, acceptance, escalation, or effect
policy; they are inputs to that policy.

## Information-loss ledger

The ledger evaluates the information dimensions supplied for Run 006. “Yes” in
the first column never implies “yes” in the next two.

| Dimension | Representable in DSPy 3.3? | Meaning preserved by the actual path? | Semantics enforced by DSPy? | Exact evidence and boundary consequence |
| --- | --- | --- | --- | --- |
| **Model-visible value** | Yes. Signature inputs, message parts, tools, and config all carry values. | Yes for the serialized/model-visible form supported by the selected adapter/provider. Original Python identity and non-rendered structure need not survive formatting. | DSPy validates supported object shapes; it does not enforce the truth or suitability of the value. | Adapters serialize signature fields into prompt text ([Chat formatting](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/chat_adapter.py#L149-L200)); typed parts are then converted to provider content ([part conversion](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/openai_format.py#L250-L353)). Ars must decide what value is eligible before this rendering. |
| **Origin** | Partly. Signature field names, message roles, names, and arbitrary metadata can label origin. | Only declared model-facing distinctions survive automatically. Arbitrary origin metadata is not emitted by `message_to_openai_chat()`. | No general origin semantics are enforced. A role affects provider rendering, not application trust. | `LMMessage` has role/name/metadata ([message type](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L247-L290)); Chat conversion emits role/name/content but ignores message metadata ([conversion](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/openai_format.py#L88-L112)). Keep authoritative origin outside the model-visible representation. |
| **Provenance** | Mechanically yes in `metadata` mappings on parts, messages, requests, outputs, and responses. | Not generally. Current adapters do not populate a provenance contract; OpenAI request conversion ignores request/message metadata and most part metadata. A request retained in typed LM history can keep bytes locally, but DSPy assigns no provenance meaning to them. | No. DSPy does not interpret arbitrary metadata as provenance or propagate provenance-derived policy. | Metadata declarations exist ([parts/messages](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L50-L56), [request](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L624-L633), [response](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L809-L822)); provider conversion reads the typed request's model/messages/config/tools, not its metadata ([Chat request](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/openai_format.py#L77-L85)). Ars provenance must remain an Ars-owned side channel. |
| **Taint** | Mechanically yes as arbitrary metadata or as an application value. | No defined propagation appears through signature formatting, adapter conversion, provider generation, or parsed output. | No taint contract is declared or consumed by the inspected Signature → Adapter → LMRequest → provider path. | The only generic carrier is metadata, while conversion ignores that carrier as above. Encoding taint into model text would make it an instruction, not an enforced runtime property. |
| **Authority** | A label or token can be stored as data. | Byte preservation is possible in selected fields, but authority meaning is not preserved merely by entering a prompt, typed part, or metadata dictionary. | No authority/capability contract is declared or consumed by the inspected LM boundary. DSPy validates and parses tool arguments before calling the function, but argument validation is not authorization ([tool call](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/types/tool.py#L120-L200)). | Ars states model context does not create authority ([principle](../README.md#L59)); DSPy adapters render inputs into model-visible messages ([adapter format](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/base.py#L366-L441)). Authority resolution must precede or follow DSPy, never be delegated to generated text. |
| **Visibility** | Model-facing visibility is representable by deciding which fields/messages enter a call. | DSPy preserves only the selected rendered view. It does not retain an application-level visibility lattice through provider conversion. | No access-control or disclosure contract is declared or consumed by the inspected path. | `Signature` and `History` tell the adapter what to render, and the adapter emits those values as messages ([history/current ordering](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/base.py#L413-L441)). Ars must perform visibility filtering before the DSPy call. |
| **Closed output type or shape** | Yes, through Signature annotations and Pydantic-backed adapters. | Yes on a successful parse into the declared type. Provider-native schema support can also constrain generation when available. | Partly. DSPy enforces field presence and type/domain parsing for successful adapter results; invalid outputs raise `AdapterParseError`. It does not guarantee that a call succeeds or that a typed value is semantically correct. | Chat and JSON parsers require exactly the declared output keys and validate each value ([Chat parse](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/chat_adapter.py#L218-L253), [JSON parse](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/json_adapter.py#L167-L200)). Ars may rely on the checked shape as one mechanism, but must own the larger guarantee and failure policy. |
| **Requirement satisfaction** | A requirement can be described in instructions, field descriptions, a metric, or caller metadata. | The description may survive as prompt text; the requirement as a normative runtime fact does not. | Not in general. Parsing checks representation, and evaluation measures configured behavior; neither proves the result meets an application-specific requirement. | `ChatAdapter` places signature instructions and output requirements in model-visible messages ([system/task rendering](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/chat_adapter.py#L116-L147), [user reminder](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/chat_adapter.py#L172-L200)). Ars explicitly separates requirement from type, guarantee, evidence, and policy ([principles](../README.md#L69)). |
| **Provider result metadata** | Yes. `LMOutput`/`LMResponse` carry finish reason, usage, cost, cache state, provider data, and excluded raw provider objects. | Often, within the typed response path. The adapter compatibility round-trip prefers original legacy output objects when present, but its current `LMResponse` wrapper is temporary. | DSPy validates the response container; it does not turn provider metadata into Ars acceptance or effect policy. | Response fields and legacy conversion are explicit ([response types](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L725-L925), [legacy conversion](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/openai_format.py#L987-L1011)). Treat these as realization observations. |
| **Execution/accounting record** | Yes. `BaseLM` records call history and optional usage; `LMResponse` carries usage. | Yes for DSPy-recorded call data, subject to cache/history settings and provider reporting. It is not conversation context unless supplied separately. | DSPy performs the recording effect; it does not assign application-level accounting meaning. | Legacy calls record prompt/messages/kwargs/response/outputs/usage/cost ([legacy history](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/base_lm.py#L286-L319)); typed calls record the canonical request/response ([typed history](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/base_lm.py#L588-L604)). Ars can consume this evidence without making it Ars session state. |

## Mechanism assessment: what not to rebuild

The following machinery has an active DSPy owner and no demonstrated need for an
Ars-specific duplicate:

1. **Signature-aware prompt and message formatting.** Adapters render field
   descriptions, task instructions, demos, explicit history, current inputs,
   output-format reminders, multimodal values, and tools
   ([adapter responsibilities](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/base.py#L34-L49)).
2. **Structured result extraction.** Chat/JSON adapters parse complete field sets
   and validate annotated values; JSONAdapter negotiates native structured output
   or JSON mode as supported
   ([JSON path](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/json_adapter.py#L40-L200)).
3. **Provider request/response normalization.** DSPy has typed request, message,
   content, tool, usage, and response objects plus OpenAI Chat/Responses/text
   conversion
   ([typed vocabulary](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/core/types.py#L17-L47),
   [provider conversion](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/openai_format.py#L70-L235)).
4. **Provider bridge behavior.** The built-in LM already owns provider routing,
   sync/async calls, retry handoff, caching, capability checks, and LiteLLM
   compatibility
   ([LM runtime](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/lm.py#L56-L183),
   [dispatch functions](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/clients/lm.py#L495-L615)).
5. **LM-boundary error normalization.** DSPy separates provider/transport errors
   from adapter parse errors and preserves useful provider metadata
   ([exceptions](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/utils/exceptions.py#L8-L260)).
6. **Learned-function realization and optimization.** Signatures feed ordinary
   modules such as `Predict`, while DSPy's optimizer machinery operates on DSPy
   programs. SimpleAIChat has no analogue in the isolated stack
   ([Predict realization](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/predict/predict.py#L250-L275),
   [DSPy 3.3.0 optimization features](https://github.com/stanfordnlp/dspy/releases/tag/3.3.0)).

The typed LM migration is not a reason to rebuild these capabilities. It is a
reason not to make DSPy 3.3's internal `LMRequest` compatibility sequence part of
Ars's public semantics.

## Falsification of the three dependency hypotheses

### Hypothesis A: DSPy replaces almost everything below Ars semantics

**Claim under test:** after Ars supplies source/invocation semantics, DSPy
Signatures, Adapters, LM types, and provider machinery can own the rest.

**Falsifiers:**

- Ars semantic state must cross the provider boundary intact and return with its
  meaning enforced by the realization engine.
- DSPy lacks necessary rendering, structured I/O, provider, error, or optimization
  machinery.
- Depending above `LMRequest` forces Ars to adopt provider-shaped messages.

**Evidence:** DSPy has the machinery, and its Signature/Adapter entry is above
provider-shaped request construction. But DSPy metadata does not preserve or
enforce provenance, taint, authority, or visibility. A direct one-to-one mapping
from Ars semantics into DSPy fields would therefore flatten those meanings.

**Result:** **survives only with a strict compilation boundary.** “Below Ars
semantics” must mean that Ars first retains policy-bearing state outside DSPy and
passes only the deliberately model-visible projection into a transient DSPy
realization. If A means DSPy objects become the storage or enforcement model for
Ars semantics, it is falsified.

### Hypothesis B: Ars keeps its own neutral request/response boundary

**Claim under test:** Ars needs durable request/response objects below its semantic
layer, with DSPy used as one realization engine.

**Falsifiers:**

- No Ars-only invariant needs to be carried inside a model request or response.
- A side channel can retain Ars semantics while DSPy owns the complete model call.
- Ars request/response objects would duplicate DSPy/provider conversion without
  adding enforcement.

**Evidence:** provenance, authority, visibility, policy, and requirements should
not be delegated into model request metadata because DSPy neither interprets nor
enforces them. They can remain associated with the invocation outside the model
call. DSPy's provider-neutral types cover the model-call data itself, although
their default path is still transitional.

**Result:** **not supported as the default ownership choice by current evidence.**
It remains a contingency if a later concrete invariant must travel through
multiple realization engines in one stable wire-neutral form. Run 006 found no
such requirement strong enough to justify duplicating request/response machinery
now.

### Hypothesis C: hybrid semantic/realization split

**Claim under test:** Ars owns meaning, provenance, requirements, guarantees,
effects, policy, context selection, and authority; DSPy owns learned-function
realization, adaptation, provider calls, normalized LM results/errors, and
optimization.

**Falsifiers:**

- DSPy owns and enforces the Ars semantic dimensions, making the Ars layer
  redundant.
- DSPy fails to own enough realization/provider machinery to retire the inherited
  stack.
- The boundary requires Ars authority or policy data to become model-visible.

**Evidence:** DSPy owns substantial realization machinery, but none of the generic
metadata carriers establishes provenance, taint, visibility, authority, or
application policy. Signature types and adapter validation provide useful shape
mechanisms without supplying semantic correctness or effect authorization. Ars
can select a model-visible projection before DSPy and evaluate the parsed result
after DSPy without placing policy-bearing state in the prompt.

**Result:** **survives all current falsifiers.** Its important qualification is
that DSPy 3.3's `LMRequest`/`LMResponse` path is a DSPy implementation boundary in
transition, not the semantic boundary Ars should expose.

## Narrowest defensible dependency boundary

The evidence supports this boundary:

```text
Ars-owned semantic state
    source meaning
    provenance / taint
    authority / visibility
    context selection
    requirements / guarantees / policy
    effect eligibility
        ↓ deliberate model-visible projection
TRANSIENT DSPy REALIZATION BOUNDARY
    Signature + inputs + selected module/configuration
        ↓
    Adapter formatting and structured parsing
        ↓
    DSPy LM / LMRequest / LMResponse compatibility machinery
        ↓
    LiteLLM/provider transport
        ↓
    Prediction or DSPy LM/adapter failure
        ↓ observation returned to Ars
Ars-owned acceptance, guarantee, policy, and effects
```

The dependency begins at a DSPy program/Signature invocation, after Ars has
selected and compiled the model-visible view. It does **not** begin by adopting
`LMRequest`, `LMResponse`, `LMMessage`, or DSPy metadata as Ars domain objects.
Those are DSPy realization objects whose 3.3 execution path is deliberately
transitional.

At the return boundary:

- a parsed `Prediction` is a typed realization result, not proof of semantic
  correctness;
- an `LMError` or `AdapterParseError` is a structured observation, not an Ars
  recovery policy;
- an output satisfying a Pydantic/`Literal` parser has passed that mechanism, not
  every Ars requirement;
- no generated value gains authority merely because DSPy parsed it successfully.

Under this boundary, the inherited provider stack in `chatgpt.py` has no
demonstrated long-term responsibility that DSPy does not already own more broadly.
That is decision evidence for progressive retirement, not a migration plan and
not authorization to remove it.

## Unresolved evidence gaps

Run 006 does not resolve:

1. How stable the typed direct-LM contract will be after DSPy's staged migration.
   This does not block the higher Signature/module boundary, but it argues against
   making the 3.3 typed objects Ars public API.
2. How Ars should associate source-level identity and evaluation evidence with
   DSPy-optimized program variants. DSPy optimization exists; the required Ars
   evidence identity has not been designed.
3. How authority-bearing tool references should be resolved before DSPy tool
   execution. DSPy validates and calls tools, but Run 006 found no general
   authority model at that boundary
   ([tool validation/execution](https://github.com/stanfordnlp/dspy/blob/3.3.0/dspy/adapters/types/tool.py#L120-L200)).
4. Whether streaming and native tool lifecycles require additional Ars effect
   boundaries. Runs 003–005 isolated only the non-streaming call path, so this
   comparison does not generalize that ownership conclusion to their lifecycle
   semantics.
5. Whether a future second realization engine creates a concrete need for an
   Ars-owned neutral request/response protocol. No such need exists in the current
   repository evidence.

These are later decision inputs. They are not implementation tasks in Run 006.

## Synthesis

DSPy 3.3.0 already owns the machinery between a declared learned task and a
provider call more comprehensively than SimpleAIChat: field-aware formatting,
structured parsing, provider conversion, sync/async dispatch, retries, caching,
usage/history capture, normalized LM errors, and optimization. Its new typed LM
objects are real, useful, and public, but the built-in path still converts through
OpenAI/LiteLLM-shaped compatibility layers and returns legacy outputs by default.

DSPy can represent arbitrary metadata. Its current path does not thereby preserve
the meaning of provenance, taint, authority, or visibility, and it does not enforce
those semantics. Typed parsing can enforce a declared result shape on successful
return; it cannot substitute for semantic correctness, application requirements,
effect authorization, or failure policy.

The surviving boundary is therefore the hybrid one: Ars owns meaning and control
on both sides of the learned call; DSPy owns the learned realization between
them. This is the narrowest boundary that avoids rebuilding provider machinery
without renaming DSPy representations into Ars semantics.

The artifact stops here. It does not define replacement types, choose integration
steps, or alter production code.

## Run 006 verification record

Verification was performed on 2026-08-15 after the comparison was written.

- The worktree contained only this new document relative to the Run 005 commit.
- SHA-256 was recomputed for every pre-existing file under `simpleaichat/`,
  `tests/`, and `docs/`. All production files, all five Run 001–005 test files,
  the Run 002 artifact, and the four pre-existing images matched their frozen
  pre-Run 006 hashes.
- The document contained 114 source links. All 105 local or immutable DSPy 3.3.0
  source-line links resolved to existing version-matched files and valid line
  numbers. The remaining links are the pinned release/commit, public migration
  guide, excluded roadmap, or repository identity destinations.
- The 33 existing tests passed after test discovery with DNS and every
  non-loopback connection replaced by a guard that raises. Loopback remained
  available only for Python's Windows async-test event loop.
- No DSPy model invocation, provider request, integration code, or dependency
  change was introduced.
