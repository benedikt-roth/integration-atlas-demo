# Customer export contract

Contract version: **3.0.0**

Fictional immutable contract artifact. [Interface details](../../docs/interfaces/IF-005.md).

The CRM vendor uploads one full snapshot per day to ERP over SFTP. Filename:
`customers-YYYYMMDD.csv` (UTC business date). Encoding: UTF-8 without BOM;
delimiter: comma; line ending: LF. First row is the header, in this order.
Quote fields using standard CSV double-quote escaping. Empty optional fields are empty strings.

| Column | Type | Required | Meaning |
| --- | --- | --- | --- |
| customer_id | string | Yes | Stable CRM customer identifier; unique within file |
| display_name | string | Yes | Customer display name |
| country_code | ISO 3166-1 alpha-2 | No | Two uppercase letters |

Example:

```csv
customer_id,display_name,country_code
C-100,Example Company,DE
```

Publish atomically by renaming the completed temporary upload. ERP rejects the full
file if required columns are absent or customer identifiers repeat. ERP writes
`customers-YYYYMMDD.csv.done` after successful import. The sender retains the
original for reconciliation. Empty snapshots need explicit operational approval.
