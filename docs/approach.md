# Repository structure and cross-reference choices

[Back to the landscape](../README.md)

**Agreed target design:** see the [solution architecture](solution-architecture.md)
for the two-layer model, per-entity JSON files, CUE validation, usages defined only
in views, and Mermaid publication in GitHub. The page below describes the current
POC implementation; migration to the target architecture has not been implemented.

```text
README.md                         Generated Mermaid overview and linked catalog
catalog/catalog.json              IDs, systems, connections, versions, notes
docs/landscape.mmd                Generated reusable Mermaid diagram source
docs/systems/<system-id>.md        Generated incoming/outgoing interface backlinks
docs/interfaces/IF-xxx.md          Generated stable interface detail pages
docs/views/<view-id>.md            Generated focused overview or scenario page
docs/notes/                       Authored pages referenced by annotations
contracts/<domain>/<versioned-file>  Versioned documentation artifacts
scripts/generate.py               Generator and reference checker
.github/workflows/docs.yml        Checks on pushes and pull requests
tests/test_generate.py            Reference, scenario, and drift checks
```

## Address the connection explicitly

Mermaid flowcharts provide `click` links on nodes. Each integration is therefore
represented as `source → interface node → target`. The yellow interface node is
a visual handle for a connection, not a deployed proxy or service. This also allows
two different interfaces between the same systems without ambiguous links.

Every interface has a stable ID and one canonical Markdown detail page. Its
source and target each link back to it through a generated system page. The
landscape table links to the same interface page and directly to its artifact.
An external-to-external connection follows exactly the same structure.

## Focused views and annotated scenarios

The catalog's optional `views` list defines reusable views of the same interface
definitions. Start with the [invoice creation scenario](views/invoice-creation.md)
or the [invoicing subdomain overview](views/invoicing-overview.md).

Each view has a unique lowercase slug `id`, a `kind`, a `title`, and a `summary`.
An `overview` selects `interface_ids`; its diagram and table contain exactly those
interfaces and their endpoints. It does not imply execution order or pull in
other connections attached to the selected systems.

A `scenario` instead defines an ordered `steps` list:

```json
{
  "id": "invoice-creation",
  "kind": "scenario",
  "title": "Invoice creation",
  "summary": "From an accepted order to a confirmed ERP invoice.",
  "steps": [
    {"interface_id": "IF-001", "annotation": {"text": "Order accepted"}},
    {
      "interface_id": "IF-003",
      "annotation": {
        "text": "Create invoice using the mapping rules",
        "target": "docs/notes/invoice-mapping.md"
      }
    },
    {
      "interface_id": "IF-003",
      "direction": "reverse",
      "annotation": {"text": "Return invoice ID"}
    }
  ]
}
```

Array order determines step numbers. `direction` defaults to `forward`, using the
interface's canonical source and target. `reverse` swaps those endpoints and
uses dashed arrows. It documents a response or reverse message on the same
interface, not another interface definition.

The generator derives the scenario's interface membership and systems from its
steps. Do not maintain an additional `interface_ids` list for a scenario. The same
interface can appear multiple times; each occurrence has its own number and
annotation, while all occurrences link to the same canonical interface page.

The same steps generate a component map, an automatically numbered sequence
diagram, and a step table. The map provides a clickable interface node per step.
Linked annotations have a separate destination: for example, step 2 opens the
authored [invoice mapping rules](notes/invoice-mapping.md). Names, selected
versions, protocols, and artifact paths always come from the shared interfaces.

Annotation `text` is plain text. Optional `target` is a repository-root-relative
Markdown page path, not relative to the view page. Targets may be authored or
generated pages. This first version accepts page paths without URL schemes,
queries, or heading fragments; paths with spaces are URL-encoded automatically.
Missing pages and paths outside the repository fail validation.

GitHub's current Mermaid renderer preserves hyperlinks embedded in flowchart
connection labels. Other viewers may disable them. Sequence message labels and
notes do not support these HTML annotation links, so they show plain annotation
text; the adjacent step table provides the same clickable annotation. The table
also links to canonical interface pages and their current contract artifacts.

The README lists every view. Interface and system pages generate "Used in views"
backlinks from view membership, counting a scenario once even if it uses an
interface repeatedly. All generated views, including their displayed metadata,
are regenerated together; only the catalog and authored reference pages need
maintenance. This version models linear scenarios, including explicit responses.

## Two link styles, for two contexts

Ordinary Markdown uses relative file links. GitHub can resolve these against the
current branch or commit, so the text navigation works when browsing a branch.

Mermaid `click` directives and annotation hyperlinks use full GitHub
`blob/main/...` URLs. `click` directives request target `_top`; GitHub may rewrite
navigation targets to `_parent`.
Mermaid may render in an iframe; a relative URL can otherwise resolve against
the diagram host. The `_top` target requests navigation outside that frame.
These diagram links intentionally point to the configured branch. A diagram
viewed in a historical commit or feature branch still opens that branch's current
pages; use the adjacent relative Markdown table when reviewing historical changes.
For release snapshots, configure a release tag as `branch` before generation.

Click support is controlled by the host's Mermaid version, sandbox, and security
settings. A host may render the diagram but disable interactions. This demo does
not attempt to override the host's security configuration. Test the diagram in
GitHub and in any editor you intend to use; the ordinary links cover every route
if interaction is unavailable. No hosted documentation site is required.

## Separate the selected version from the artifact

`deployed_version` describes the contract selected by this integration. The
artifact has the same explicit version in its filename and contents. A protocol
major version such as `/v2` is not a full contract version such as `2.1.0`.

When upgrading, add a new contract file, change the catalog's version and artifact
path, and regenerate. Preserve the previous artifact so historical documentation
stays inspectable through Git. The interface ID and detail-page path remain stable.
If two versions operate concurrently, document each deployment/binding explicitly;
this small demo models only one selected version per interface.

## Edit and validate

1. Change systems or interfaces in [the catalog](../catalog/catalog.json).
2. Add the versioned contract under [contracts](../contracts/).
3. Run `python3 scripts/generate.py`, then `python3 scripts/generate.py --check`.
4. Run `python3 -m unittest discover -s tests -v`.
5. Commit the catalog, contracts, authored reference pages, and generated Markdown together for review.

The check rejects duplicate IDs, unknown endpoints, missing artifacts, version
mismatches, invalid views or steps, missing annotation targets, stale generated
output, orphaned generated pages, and missing local Markdown destinations. It
uses the Python standard library. It does not make
network requests, check external links, inspect live deployed versions, or fully
validate OpenAPI/JSON Schema semantics.

Generated pages are marked at the top. Edit the catalog for their details; use
versioned contract Markdown for longer authored documentation. For a larger
landscape, split the catalog by domain and generate smaller per-domain diagrams.
Keep the interface IDs global so links stay stable across those views.

The demo includes no credentials or live endpoints. All API and schema hosts use
the reserved `.invalid` domain.
