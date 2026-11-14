# Proof-of-concept verification

[Back to the landscape](../README.md)

Checks performed on 2026-11-14:

- Generation and `python3 scripts/generate.py --check` pass for four systems and five interfaces.
- All generated interface pages have landscape links, source/target links, selected versions, and contract links.
- Both endpoints' system pages link back to each interface.
- The checker rejects unknown endpoints, duplicate interface IDs, and mismatched selected versions/artifact paths.
- Mermaid 11.17.2 renders nine nodes and nine navigation links in a local Chromium test with interactions enabled.
- GitHub's current production Mermaid renderer bundle was fetched from its public Viewscreen endpoint using verified HTTPS and exercised in a local Chromium fixture. It rendered all nine nodes, retained all nine links after its sanitization, and reported no browser errors. GitHub's renderer rewrote link targets to `_parent`.

The GitHub renderer smoke test used the bundle
`mermaidMarkdown-5b99bd9a2037271fa4cf.js` served from
`viewscreen.githubusercontent.com`. This checks rendering and sanitized link
generation; it is not an end-to-end test of clicks in the hosted private repository.
Use the [review checklist](review-checklist.md) for that final assessment.

## Focused views and linked annotations

The extension adds an invoice-creation scenario and an invoicing subdomain
overview, generated from references to the existing interfaces.

- `python3 -m unittest discover -s tests -v` passes 13 behavior tests, including repeated interface references, explicit reverse responses, independent annotation destinations, shared metadata propagation, invalid references, and stale or orphaned pages.
- Generation and the consistency check pass for four systems, five interfaces, two views, and 13 generated files.
- The current GitHub Mermaid renderer bundle and its stylesheet were exercised in a local Chromium fixture. The invoice map renders six nodes and seven hyperlinks: three system links, three interface links, and the separate annotation link.
- Both request and response IF-003 nodes retain the same canonical interface destination. Clicking the request annotation navigates to the expected mapping-page URL; the fixture serves the actual authored mapping document there for this check.
- The sequence diagram renders numbers 1, 2, and 3 with an explicit reverse response and plain annotation text. Its links remain in the adjacent step table.
- The overview renders only its three selected interfaces and three endpoint systems, with six navigation links and no scenario numbering.
- Additional map and sequence fixtures preserve annotation text containing quotes, angle brackets, pipes, semicolons, and a hash. Mermaid entity escaping survives GitHub's HTML-decoding stage.

These are renderer and local navigation checks, not an end-to-end authenticated
browser test of the hosted private repository. No browser dependencies are
required by the generator or CI; the committed checks use Python's standard library.

These results support the interface-node approach. Mermaid renderer versions and
host security settings can change. The relative Markdown link table provides the
same destinations independently of diagram interactions.
