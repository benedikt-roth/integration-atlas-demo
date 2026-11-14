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

These results support the interface-node approach. Mermaid renderer versions and
host security settings can change. The relative Markdown link table provides the
same destinations independently of diagram interactions.
