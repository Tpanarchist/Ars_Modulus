# Ars Modulus

> **Status: initial fork / design stage**

**Ars Modulus** is an experimental Python environment where learned models are treated as native computational primitives.

Traditional functions describe *how* a computation is performed. Ars Modulus explores a complementary idea: model-defined computation, where a programmer specifies the intended behavior, inputs, outputs, context, constraints, and runtime conditions while a learned model realizes the transformation.

The long-term question is simple:

```python
def total(invoice: Invoice) -> Money:
    return sum(item.price for item in invoice.items)

@model
def read_invoice(document: Document) -> Invoice:
    """Recover the invoice represented by the document."""
```

What would programming look like if both forms of computation belonged naturally to the language?

Ars Modulus begins as a fork of [minimaxir/simpleaichat](https://github.com/minimaxir/simpleaichat), preserving its preference for a small, understandable Python codebase while using it as an experimental foundation for a broader model-aware programming environment.

## Current State

Ars Modulus has only just been forked.

No new Ars Modulus API, runtime, model syntax, retrieval layer, optimizer, or Textual interface should be considered implemented yet. Unless and until the code changes, the repository still behaves as the inherited `simpleaichat` codebase.

That distinction is intentional: the design will be worked out before the implementation is allowed to imply semantics that have not been decided.

## Direction

The project is exploring a programming model in which learned inference can coexist with ordinary explicit computation without pretending the two behave the same way.

Several influences currently define the design space:

- **simpleaichat** — minimal model interaction, hackability, and a codebase small enough to understand.
- **DSPy** — model behavior expressed as programmable functions and signatures rather than hand-managed prompt strings.
- **txtai** — retrieval, embeddings, knowledge, indexing, and composable data workflows.
- **Textual** — a first-class terminal environment for interacting with, inspecting, and eventually developing model-aware programs.

These are influences, not a commitment to simply bundle the projects together.

The goal is to reduce the ideas behind modern model programming into a coherent set of primitives rather than accumulating features such as “RAG,” “agents,” “chains,” and “tools” as unrelated abstractions.

## Design Principles

The current design work has established several distinctions that Ars Modulus intends to preserve.

### Learned computation is computation, but not ordinary computation

A normal function contains an implementation supplied by the programmer.

A model-defined function delegates part of that implementation to a learned system.

Those should compose naturally, but the runtime should retain the distinction between them.

### Model context does not create authority

Information can influence a model without gaining permission to affect the outside world.

A particularly important rule is:

> **Runtime provenance is not model privilege.**

Instructions, user content, retrieved documents, tool results, examples, and other model-visible material may ultimately enter the same learned computation. The runtime can preserve where information came from even when the model itself does not honor those boundaries.

### Structure, certainty, measurement, need, and control are different things

Ars Modulus currently treats five concepts as fundamentally separate:

1. **Type** — what shape of value may enter or leave a computation.
2. **Guarantee** — what a mechanism actually enforces by construction.
3. **Evidence** — what testing has empirically shown about a particular configured system.
4. **Requirement** — what a particular use of that system needs.
5. **Policy** — what the runtime should do when results are rejected, uncertain, unavailable, or insufficient.

They should not silently substitute for one another.

A schema is not proof that a result is correct. A benchmark score is not a guarantee. A model instruction is not a runtime constraint.

### Hard constraints come from mechanisms, not promises

Telling a model to emit one of three values changes its behavior probabilistically.

Constraining the runtime so that only those three values can be produced is different.

Ars Modulus intends to make that difference visible.

### Authority-bearing values should not come directly from free model text

For effectful operations, generated text should not be able to manufacture permission.

Closed value domains, runtime-resolved references, capabilities, validation, approval, and other enforcing mechanisms belong outside the model-visible token stream.

### Evidence belongs to the configured system that was measured

A model does not simply “have 97% accuracy.”

Observed performance belongs to a particular configuration: model, instructions, examples, retrieval, constraints, runtime behavior, and evaluation conditions.

Change the system materially and the old evidence does not automatically describe the new one.

## Why Fork simpleaichat?

The original project deliberately favored a small implementation over a large framework. Its `AIChat` interface manages sessions with relatively little machinery, supports synchronous and asynchronous generation, streaming, structured data, and simple tool workflows.

That makes it a useful place to begin experimenting.

Ars Modulus intends to preserve the spirit of:

```python
ai = AIChat(...)
result = ai("Do something")
```

while asking whether the underlying abstraction should eventually become something closer to:

```python
@model
def transform(x: Input) -> Output:
    """Describe the intended learned transformation."""
```

The syntax above is illustrative only. It is not yet an Ars Modulus API.

## Inherited simpleaichat Baseline

At the time of the fork, the inherited code provides:

- chat sessions
- synchronous and asynchronous model calls
- response streaming
- session save/load
- Pydantic-based structured input/output support
- simple function/tool selection workflows
- a command-line interactive chat

The current implementation is still centered on the original `simpleaichat` package and its OpenAI-era API assumptions.

Until Ars Modulus begins changing that implementation, consult the upstream project for the behavior of the inherited code:

- [simpleaichat repository](https://github.com/minimaxir/simpleaichat)
- [simpleaichat on PyPI](https://pypi.org/project/simpleaichat/)

## Interface Direction

A future Textual interface is part of the project direction, not a completed feature.

The intended interface is not merely another chat window. It should eventually make model-aware computation inspectable: functions, context, provenance, runtime behavior, evaluations, model realizations, and execution history should all be visible from one environment.

The visual direction currently uses the [LACKING64](https://lospec.com/palette-list/lacking64) palette.

## Development Philosophy

Ars Modulus is deliberately starting from semantics rather than features.

The project will prefer:

- small, inspectable modules
- explicit state and control flow
- progressive disclosure rather than mandatory framework ceremony
- ordinary Python interoperability
- learned and deterministic computation as peers
- mechanisms that enforce guarantees instead of annotations that merely claim them
- measured evidence instead of assumed reliability
- primitives that can express many workflows instead of abstractions tied to fashionable use cases

The project is experimental. Names, APIs, syntax, and internal architecture may change as the model is worked out.

## Upstream

Ars Modulus is forked from **simpleaichat** by Max Woolf / [minimaxir](https://github.com/minimaxir).

The original project emphasized simple, transparent access to chat models and intentionally avoided much of the abstraction overhead common in larger AI frameworks. Ars Modulus retains that work as its starting point while pursuing a substantially different programming-model direction.

Upstream repository:

https://github.com/minimaxir/simpleaichat

## License

MIT

The original simpleaichat source is MIT licensed. Existing copyright and attribution notices should be preserved as the fork evolves.
