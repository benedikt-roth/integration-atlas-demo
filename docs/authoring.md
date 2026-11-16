# Authoring the atlas

[Start here](../README.md) · [Generated catalog](generated/index.md)

## Files and definitions

Use one JSON object per file under these folders:

| Folder | ID prefix | Required data |
| --- | --- | --- |
| `model/systems/` | `SYS-` | `id`, `name`, `description`, `boundary` (`internal` or `external`) |
| `model/components/` | `CMP-` | `id`, `name`, `description`, `systemId` |
| `model/interfaces/` | `IF-` | `id`, `name`, `description`, `owner`, `protocol`, `versions` |
| `model/data-contracts/` | `DC-` | `id`, `name`, `description`, `versions` |
| `model/views/` | `VIEW-` | `id`, `name`, `description`, `kind`, plus `steps` or `scenarios` |

The filename is `ID--descriptive-name.json`. Its ID must equal the object's ID.
Use stable IDs for references; the descriptive filename can change without
breaking references. Duplicate IDs, duplicate JSON keys, and unknown fields fail.
ID suffixes allow ASCII letters, digits, and hyphens. Names can contain normal
Unicode text. The schema is defined in [model.cue](../schemas/model.cue).

A system or component reference is an object such as
`{"kind": "component", "id": "CMP-001"}`. An interface reference is
`{"id": "IF-001", "version": "1.0.0"}`. Entity ownership and message direction
are separate: requests flow toward the interface owner; events flow from the
interface owner to the selected participant.

Interfaces and data contracts declare version maps. Each version has at least
one artifact with `label`, `kind`, and repository-root-relative `path`. Artifact
kinds are `openapi`, `xsd`, `markdown`, or `other`. OpenAPI `info.version` and XSD
`xs:schema/@version` must match the declared version key. Paths must exist; they
cannot leave the repository or be symlinks. These are identity/version checks,
not full OpenAPI or XML Schema semantic validation. Versioned artifacts stay in
[contracts](../contracts/) so historical contracts remain inspectable.

## Scenarios and annotations

Use a `scenario` view with ordered `steps`. Each request/event step has a stable
local `id`, `kind`, `participant`, `interface`, and `annotation`. Numbering follows
array order; no manually maintained number field exists.

A response has `kind: "response"`, `responseTo`, and `annotation`. It references
an earlier **request** step and inherits that request's interface/version and
route. It cannot select an unrelated reverse-direction interface. Use the
[seed view](../model/views/VIEW-001--example-request.json) as a complete example.

Annotations have plain `text` and an optional `links` list. Each link has a
`label` and `target`. Targets can be typed entity references (`system`,
`component`, `interface`, `dataContract`, `view`) or
`{"kind": "file", "path": "docs/notes/example.md"}`. Paths are relative to the
repository root. URLs, queries, heading fragments, and `..` path segments are
rejected in this minimal version.

Links are generated independently in flowchart connection labels, with underline
styling removed. The canonical interface and artifacts are linked automatically.
The same destinations appear in the generated Markdown table. Sequence messages
remain plain text because GitHub's Mermaid sequence renderer does not preserve
these embedded annotation links.

## Routed usages

Add a router as a normal component and its routing API as a normal interface.
Keep the target system/interface separate. The routing interface's version
declares supported envelope versions, for example:

```json
"envelopes": {"DC-001": ["2.0.0"]}
```

That is a capability declaration, not an actual usage. On a request/event step,
select the target interface normally and add transport metadata:

```json
"transport": {
  "viaInterface": {"id": "IF-ROUTE", "version": "3.0.0"},
  "envelope": {"id": "DC-001", "version": "2.0.0"},
  "envelopeScope": "router-leg"
}
```

The routing API, envelope, and target API version are independent references.
The router identity comes from the routing interface's owner. It must be distinct
from the logical endpoints. CUE rejects an envelope version that exists but is
not supported by the selected routing API version.

Choose `router-leg` when the envelope is carried between the sender and router,
or `end-to-end` when both physical hops carry it. The reverse response follows
the corresponding return hops. This makes envelope placement explicit and does
not invent an envelope requirement on an external system. In the initial schema,
a response inherits the request's envelope/version/scope; response-specific
overrides would need an explicit future schema extension.

One logical step generates hops `1a` and `1b`; a response in logical step 2
generates `2a` and `2b`. Each hop shows its interface/version and envelope where
applicable. The table also keeps the end-to-end target payload identity. The
router passes that payload through without a new contract or transformation.
Do not create a second maintained usage just to draw the forwarding hop.

There is no artificial target/envelope compatibility matrix. Add tighter
constraints only for real restrictions in your system. Component software
release versions are not inferred from API or envelope versions and are outside
this starter's deployment model.

## Overview views

An overview contains references to existing scenario views:

```json
{
  "id": "VIEW-OVERVIEW",
  "name": "Subdomain overview",
  "description": "Usages collected from selected scenarios.",
  "kind": "overview",
  "scenarios": ["VIEW-001"]
}
```

Its component diagram omits sequence numbering. Its table links to the source
scenario and retains that scenario's step numbers. Overview references must
point directly to scenarios, not other overviews; this keeps composition simple
and prevents recursive view dependencies.

## Generation and extension

Run `generate` after edits and commit its results. The generator owns
`docs/generated/` and removes obsolete files from that directory. Keep authored
notes outside it. Renaming a filename slug preserves entity-page URLs because
those use IDs. Deleting an entity fails if another object still references it.

To add a field, first update the appropriate closed CUE definition and its
constraints, then the Jinja template if it should be visible. Cross-reference and
compatibility rules belong in CUE. The Python adapter handles file loading,
artifact metadata extraction, model projection, and rendering. It does not
reimplement the domain validation rules.
