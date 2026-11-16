# Interface Atlas starter

A small, forkable interface-documentation repository: **individual JSON files →
CUE validation → Jinja templates → Markdown and Mermaid rendered by GitHub**.

[Browse the generated atlas](docs/generated/index.md) ·
[Authoring guide](docs/authoring.md) ·
[Solution architecture](docs/solution-architecture.md)

## Start your project

1. Fork the repository with **Copy the main branch only** disabled, then make
   `feat/model-starter` your fork's default branch. This implementation remains
   separate from the upstream `main` branch. The original POCs are preserved by
   the `poc-done` tag in the upstream repository.
2. Install Python 3.11+, Git, and [CUE v0.17.1](https://github.com/cue-lang/cue/releases/tag/v0.17.1).
3. Create a Python environment and install the two pinned dependencies:

   ```sh
   python3 -m venv .venv
   . .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

4. Replace the five example objects under [model](model/), keeping references
   consistent. Each file is one object, named `ID--descriptive-name.json`.
5. Generate and check your documentation:

   ```sh
   python scripts/atlas.py generate
   python scripts/atlas.py check
   python -m unittest discover -s tests -v
   ```

6. Commit the model, artifacts, authored notes, and generated files together.
   GitHub renders the diagrams when you open the Markdown pages.

Run `generate` once immediately after forking to update diagram hyperlinks to
your repository and current branch. The repository and revision are inferred
from Git's `origin` and current branch, or from GitHub Actions. Explicit overrides
are available when building outside a checkout:

```sh
python scripts/atlas.py generate --repository YOUR-ORG/YOUR-REPO --ref main
```

The generated `.context.json` records the hyperlink destination, so `check`
reproduces the committed documentation even in a detached CI checkout. After
changing your default branch or preparing a release snapshot, regenerate with
the intended `--ref`. Markdown table links remain relative to the page's branch;
Mermaid links point at the recorded repository/revision because GitHub renders
diagrams in a separate frame.

## What is included

There is exactly **one system, component, interface, data contract, and view**.
The example component calls its parent platform's API and receives a response.
The envelope demonstrates an independently versioned reusable schema; the seed
view is a direct call and does not claim to use a router.

Routing is supported by the schema and renderer. To document a real routed
interaction, add your routing component/interface and target system/interface,
then select them through the view's `transport` field. See the
[routed example](docs/authoring.md#routed-usages). The test suite exercises that
path without adding more seed entities to your repository.

- Systems and components own interfaces; interfaces declare available versions.
- Only views define actual usage, selected versions, annotations, and routes.
- CUE enforces schemas, typed references, versions, supported envelopes, and
  request/response associations.
- Component maps provide numbered connections with multiple clickable links.
- Sequence diagrams use the same steps, with a generated link table underneath.
- Overview views project existing scenarios without copying maintained usages.
- Generated entity pages contain derived backlinks to their actual usages.

## Commands and CI

| Command | Purpose |
| --- | --- |
| `python scripts/atlas.py validate` | Load all entity files and validate with CUE |
| `python scripts/atlas.py generate` | Validate, generate pages, remove obsolete generated pages, and check local Markdown links |
| `python scripts/atlas.py check` | Validate and reject stale/orphaned output or broken local Markdown links |
| `python -m unittest discover -s tests -v` | Exercise the real CUE rules and rendering behavior |

Set `CUE=/path/to/cue` if the binary is not on your PATH. CI installs the pinned
CUE and Python dependencies, checks generated-file consistency, and runs tests.
The **Update generated documentation** workflow action can regenerate and commit
pages on the branch you select in GitHub's Actions UI. Ordinary pushes and pull
requests validate the committed output; they do not silently rewrite it.

No HTML site, npm dependency, diagram server, or paid license is required. This
starter is MIT licensed; CUE is Apache-2.0, and Jinja/MarkupSafe are BSD licensed.

Generated pages belong to the generator. Edit the model and `docs/notes/` rather
than the generated directory. CUE validates declared documentation consistency;
it does not inspect running systems, infer API compatibility, or validate XML
instances against XSDs. External annotation URLs and heading-fragment targets
are intentionally outside this minimal schema.
