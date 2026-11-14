# Invoice mapping rules

[Invoice creation scenario](../views/invoice-creation.md) · [Full landscape](../../README.md)

This authored page documents the scenario's mapping between an accepted order and
the ERP invoice request. The scenario's invoice-request annotation links here from its
component map and step table.

## Order event to invoice request

Use the payload from [IF-001](../interfaces/IF-001.md) to build the request for
[IF-003](../interfaces/IF-003.md):

| Order event field | Invoice request field | Mapping |
| --- | --- | --- |
| `orderId` | `orderId` | Copy unchanged |
| `customerId` | `customerId` | Copy unchanged; this demo assumes shared customer identifiers |
| `totalMinor` | `totalMinor` | Copy unchanged; preserve integer minor units |
| `currency` | `currency` | Copy unchanged; do not perform currency conversion |

After ERP accepts the request, use the returned invoice identifier to correlate
the order with the new ERP invoice. The scenario documents that response using
the reverse direction of IF-003, without defining another interface.

The linked canonical interface pages provide the selected contract versions,
schemas, authentication, and failure-handling details. This page owns the mapping
rules; it does not independently maintain those contract details.
