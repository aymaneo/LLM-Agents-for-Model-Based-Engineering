# Usage Guide

## 1. Initialize a Session with Your Metamodel

First, create a new session by uploading your EMF metamodel (.ecore file):

```bash
curl -X POST -F "file=@/path/to/your/metamodel.ecore" \
  http://localhost:8095/metamodel/start
```

This will return a response with a sessionId used by subsequent requests:

```json
{
  "sessionId": "428e82e8-ab61-4e11-a6fc-b5f76e78ebb8",
  "routes": { /* OpenAPI-like summary of endpoints */ }
}
```

## 2. Create a Model Instance

To create a new instance of a class in your metamodel:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "attribute1": "value1",
    "attribute2": "value2",
    "reference1": { "nestedAttribute": "nestedValue" },
    "multiReference": [
      {"nestedAttribute": "item1"},
      {"nestedAttribute": "item2"}
    ]
  }' \
  http://localhost:8095/metamodel/YOUR_SESSION_ID/YourClassName
```

Note: With the stateless routes, the POST body is optional; an empty instance is created if omitted.

## 3. Stateless API (fixed routes)

The server exposes a fixed set of routes that work for any uploaded metamodel. Generic path params let you operate on any class and feature.

Available routes

- POST /metamodel/start — upload a .ecore and start a session (multipart/form-data "file")
- POST /metamodel/{sessionId}/{eClassName} — create a new instance of the EClass
- PUT /metamodel/{sessionId}/{eClassName}/{id}/{featureName} — set/update an attribute/reference value
  - Body: application/json { "value": <scalar | id | [ids]> }
- DELETE /metamodel/{sessionId}/{eClassName}/{id}/{featureName} — clear a feature value
- DELETE /metamodel/{sessionId}/{eClassName}/{id} — delete an instance

Example: using uploads/Class.ecore

1. Start a session

```bash
curl -s -F file=@uploads/Class.ecore \
  http://localhost:8095/metamodel/start | tee /tmp/start.json
SESSION_ID=$(sed -n 's/.*"sessionId"[[:space:]]*:[[:space:]]*"\([^\"]*\)".*/\1/p' /tmp/start.json)
echo SESSION_ID=$SESSION_ID
```

1. Create a Class instance

```bash
curl -s -X POST \
  http://localhost:8095/metamodel/$SESSION_ID/Class | tee /tmp/class_create.json
CLASS_ID=$(sed -n 's/.*"id"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' /tmp/class_create.json)
echo CLASS_ID=$CLASS_ID
```

1. Update a feature (e.g., name)

```bash
curl -i -s -X PUT -H "Content-Type: application/json" \
  -d '{"value":"MyClass"}' \
  http://localhost:8095/metamodel/$SESSION_ID/Class/$CLASS_ID/name
```

1. Clear the feature

```bash
curl -i -s -X DELETE \
  http://localhost:8095/metamodel/$SESSION_ID/Class/$CLASS_ID/name
```

1. Delete the instance

```bash
curl -i -s -X DELETE \
  http://localhost:8095/metamodel/$SESSION_ID/Class/$CLASS_ID
```

Notes

- IDs are Java hashCodes of EObjects and are not stable across restarts.
- Models are saved per session under uploads/model_{sessionId}.xmi.
- For references, pass the target object's id as value, or a JSON array of ids for multi-valued refs.

## 2.1 Example: Creating a Family

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "lastName": "Smith",
    "father": {"firstName": "John"},
    "mother": {"firstName": "Jane"},
    "sons": [{"firstName": "Jimmy"}, {"firstName": "Johnny"}],
    "daughters": [{"firstName": "Sally"}]
  }' \
  http://localhost:8095/metamodel/428e82e8-ab61-4e11-a6fc-b5f76e78ebb8/Family
```
