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

## Focused views and annotated flows

- [ ] Open [Invoice creation](views/invoice-creation.md) from the README's view index. Both diagrams and the table show three numbered steps.
- [ ] Step 2 sends an invoice request from Billing Worker to ERP. Step 3 returns the invoice ID from ERP to Billing Worker using dashed arrows.
- [ ] Both IF-003 step nodes open [the same interface page](interfaces/IF-003.md); there is no second response interface definition.
- [ ] Click step 2's connection annotation in the component map. It opens [the authored invoice mapping rules](notes/invoice-mapping.md).
- [ ] Click that same annotation in the step table. It opens the same page. The sequence diagram shows plain annotation text without HTML markup.
- [ ] Follow "Used in views" from IF-003 or Billing Worker back to the scenario; each view appears once.
- [ ] Open [Invoicing subdomain](views/invoicing-overview.md). It includes IF-001, IF-003, and IF-004 without sequence numbering, and excludes CRM lookup and customer export.
- [ ] Run `python3 -m unittest discover -s tests -v` and `python3 scripts/generate.py --check`.

To test drift detection locally, change IF-003's `deployed_version` to `2.2.0`
without adding a matching artifact. `python3 scripts/generate.py --check` must fail.
Restore the catalog afterward. This check validates documentation consistency;
it does not query a running ERP deployment.

If direct edge clicking is mandatory, this pattern does not satisfy that exact
interaction: users click the named interface node on the connection. If this
small visual addition is acceptable, it provides one stable link per connection
using Mermaid plus ordinary repository Markdown.
