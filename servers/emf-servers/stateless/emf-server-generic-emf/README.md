# EMF Server - Stateless API Usage Guide

This guide covers how to use the EMF Server's stateless API. The stateless API doesn't require sessions - you simply provide the paths to your metamodel and model files with each request.

## API Overview

All stateless API endpoints follow this pattern:
- Base URL: `/model/`
- Required query parameters: 
  - `metamodelPath` - absolute path to your `.ecore` metamodel file
  - `modelPath` - absolute path to your `.xmi` model file

## API Examples

### 1. List Instances of a Class

```bash
curl "http://localhost:8080/model/Class?metamodelPath=/path/to/your/metamodel.ecore&modelPath=/path/to/your/model.xmi"
```

Response:

```json
[{"id":"1622539165"}, {"id":"1225694146"}]
```

### 2. Get a Specific Instance by ID

```bash
curl "http://localhost:8080/model/Class/1622539165?metamodelPath=/path/to/your/metamodel.ecore&modelPath=/path/to/your/model.xmi"
```

Response:

```json
{"eClass":"Class","id":"1622539165"}
```

### 3. Create a New Instance

```bash
curl -X POST "http://localhost:8080/model/Class?metamodelPath=/path/to/your/metamodel.ecore&modelPath=/path/to/your/model.xmi" \
-H "Content-Type: application/json" \
-d '{"name": "Employee", "isAbstract": false}'
```

Response:

```json
{"id":"919026017"}
```

### 4. Update an Instance

```bash
curl -X PUT "http://localhost:8080/model/Class/919026017?metamodelPath=/path/to/your/metamodel.ecore&modelPath=/path/to/your/model.xmi" \
-H "Content-Type: application/json" \
-d '{"name": "UpdatedEmployee"}'
```

Response:

```json
{"status":"updated"}
```

### 5. Delete an Instance

```bash
curl -X DELETE "http://localhost:8080/model/Class/919026017?metamodelPath=/path/to/your/metamodel.ecore&modelPath=/path/to/your/model.xmi"
```

Response:

```json
{"status":"deleted"}
```

### 6. Working with Other Types

You can work with any type defined in your metamodel:

```bash
curl -X POST "http://localhost:8080/model/DataType?metamodelPath=/path/to/your/metamodel.ecore&modelPath=/path/to/your/model.xmi" \
-H "Content-Type: application/json" \
-d '{"name": "Date"}'
```

Response:

```json
{"id":"1317876112"}
```

### 7. Update a Specific Feature

You can update a specific feature of an object:

```bash
curl -X PUT "http://localhost:8080/model/Class/1622539165/name?metamodelPath=/path/to/your/metamodel.ecore&modelPath=/path/to/your/model.xmi" \
-H "Content-Type: application/json" \
-d '{"value": "NewClassName"}'
```

Response:

```json
{"status":"updated"}
```

### 8. Clear a Feature Value

You can clear/delete a feature value:

```bash
curl -X DELETE "http://localhost:8080/model/Class/1622539165/attr?metamodelPath=/path/to/your/metamodel.ecore&modelPath=/path/to/your/model.xmi"
```

Response:

```json
{"status":"cleared"}
```
