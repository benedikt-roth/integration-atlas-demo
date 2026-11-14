# Evaluate this proof of concept

[Back to the landscape](../README.md)

Use GitHub's rendered README on a desktop browser for this check.

- [ ] The Mermaid block renders a landscape with two internal components and two external systems.
- [ ] Clicking the yellow IF-003 node opens [its interface page](interfaces/IF-003.md).
- [ ] That page displays deployed version 2.1.0 and links to [the matching OpenAPI contract](../contracts/erp/invoices-2.1.0.openapi.json).
- [ ] Clicking its Billing Worker link opens [the system page](systems/billing-worker.md), with incoming and outgoing interfaces.
- [ ] IF-005 shows [the CRM → ERP connection](interfaces/IF-005.md) and [its CSV data dictionary](../contracts/customer-export/customer-export-3.0.0.md).
- [ ] The link table below the diagram provides the same paths if diagram interaction is disabled.
- [ ] Repeat the navigation in your normal editor to check that viewer's Mermaid support.

To test drift detection locally, change IF-003's `deployed_version` to `2.2.0`
without adding a matching artifact. `python3 scripts/generate.py --check` must fail.
Restore the catalog afterward. This check validates documentation consistency;
it does not query a running ERP deployment.

If direct edge clicking is mandatory, this pattern does not satisfy that exact
interaction: users click the named interface node on the connection. If this
small visual addition is acceptable, it provides one stable link per connection
using Mermaid plus ordinary repository Markdown.
