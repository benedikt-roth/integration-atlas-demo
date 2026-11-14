# Repository structure and cross-reference choices

[Back to the landscape](../README.md)

```text
README.md                         Generated Mermaid overview and linked catalog
catalog/catalog.json              IDs, systems, connections, versions, notes
docs/landscape.mmd                Generated reusable Mermaid diagram source
docs/systems/<system-id>.md        Generated incoming/outgoing interface backlinks
docs/interfaces/IF-xxx.md          Generated stable interface detail pages
contracts/<domain>/<versioned-file>  Versioned documentation artifacts
scripts/generate.py               Generator and reference checker
.github/workflows/docs.yml        Checks on pushes and pull requests
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

## Two link styles, for two contexts

Ordinary Markdown uses relative file links. GitHub can resolve these against the
current branch or commit, so the text navigation works when browsing a branch.

Mermaid `click` directives use full GitHub `blob/main/...` URLs and target `_top`.
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
4. Commit the catalog, contracts, and generated Markdown together for review.

The check rejects duplicate IDs, unknown endpoints, missing artifacts, version
mismatches, stale generated output, orphaned generated pages, and missing local
Markdown destinations. It uses the Python standard library. It does not make
network requests, check external links, inspect live deployed versions, or fully
validate OpenAPI/JSON Schema semantics.

Generated pages are marked at the top. Edit the catalog for their details; use
versioned contract Markdown for longer authored documentation. For a larger
landscape, split the catalog by domain and generate smaller per-domain diagrams.
Keep the interface IDs global so links stay stable across those views.

The demo includes no credentials or live endpoints. All API and schema hosts use
the reserved `.invalid` domain.
