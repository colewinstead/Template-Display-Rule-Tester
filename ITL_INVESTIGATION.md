# Included ITL investigation

The original [`rwd.itl`](rwd.itl) was inspected read-only. No development step writes to, renames, or replaces this file.

## Format and identity

- Size: 6,318,687 bytes
- SHA-256: `93EEE35AF190F4A1323EF77EAAE5C4C7B5EEB949CB765DCF62282C068E9DE26F`
- Format: well-formed, uncompressed XML without an XML declaration
- Root: `InRoads`
- File metadata: `productVersion="4.0"`, imperial linear units, degree angular units
- The `TemplateLibrary` metadata records a historical Bentley source path. The tester preserves it only as read metadata.

## Structures actually exposed

| XML element | Count | Currently extracted |
|---|---:|---|
| `Template` | 216 | category path, name, description, OID, raw attributes |
| `Point` | 5,889 | name, X/Y, feature/style, null-point indicators, raw attributes |
| `Constraint` | 11,778 | type, value, parent(s), equation, raw attributes |
| `Component` | 2,921 | name, material, type, vertices, display expression, raw attributes |
| `DisplayRule` | 1,027 | name, description, type, point/object references, test, value, raw attributes |
| `Category` | 32 | nested template folder hierarchy |

Also present are `Vertex`, `ClassificationProperties`, `RolloverValueSet`, `EndConditionTarget`, `PointList`, and `Preferences`. Unknown attributes and unsupported children are tolerated. Useful original attributes are retained on parsed objects; the program does not pretend unsupported sections have been interpreted.

## Display-rule representation

Atomic rules are attributes, not free-form comparison text. Types found in this file are:

- Slope (331)
- Vertical Difference (295)
- Horizontal Difference (201)
- Component Is Displayed (108)
- Absolute Horizontal Difference (79)
- Absolute Vertical Difference (13)

Component `displayExpression` values combine atomic rule names with `AND`, `OR`, `NOT`, and parentheses. The parser resolves those names against rules in the same template and builds rule-to-component associations.

Some component expressions in the source are incomplete, including values equivalent to `NOT ` and `AND `. These are reported as source diagnostics. The program does not invent missing names.

## Tester interpretation and limits

For interactive testing, atomic rules are rendered transparently using safe helper calls such as `HDIFF(P1.X, P2.X) < 0`, `VDIFF(...)`, `AHDIFF(...)`, `AVDIFF(...)`, and `SLOPE(P1.X, P1.Y, P2.X, P2.Y)`. The original Bentley attributes remain visible beside the tester expression.

The XML names the operation but does not fully specify every Bentley runtime detail: point-control resolution, component availability order, tolerance policy, or behavior for a vertical/zero-run slope. The tester uses ordinary numeric difference, absolute difference, and rise-over-run calculations and clearly labels this as an interpretation. Critical production behavior should still be confirmed in OpenRoads Designer.
