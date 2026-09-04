# rels

A small persistent relationship store for content IDs.

rels stores relationships of the form:

```
a → b
```
and provides a minimal Python interface:
```
rels.put(a, b)
rels.get(a)
rels.members(b)
rels.build()
rels.close()
```

## Example
```python
import rels

rels.put(observation_id, abstraction_id)

rels.build()

abstraction_id = rels.get(observation_id)

for observation_id in rels.members(abstraction_id):
    print(observation_id)
```

The intended relationship is many-to-one:

```
O1 ─┐
O2 ─┼──→ A
O3 ─┘
```

So:
```
rels.get(O2)
# A

list(rels.members(A))
# [O1, O2, O3]
```

## Relation stores
rels doesn't know what the identifiers represent. A consuming application
can maintain separate stores for different relationships:
```
url/
company/
country/
industry/
city/
```

The same API is used for each store.
```
rels.put(observation_id, company_id, rels_root=company_root)
```

## Batch workflow
Relationships are appended during ingestion and made queryable with `build()`:

```
for a, b in relationships:
    rels.put(a, b)
rels.build()
```

`build()` handles the sorting and merging required to produce the persistent
queryable store.

## Installation
`rels` is designed to be used directly as a Git submodule:

```
git submodule add git@github.com:4d30/rels.git rels
```

Then:
```
import rels
```
See docs/verbose.md for the storage model and design details.
