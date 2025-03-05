# Data Access Object (DAO) Scaffolding

This guide explains how to scaffold Data Access Objects based on an OpenAPI 3 specification, automating the creation of database interaction classes.

## Prerequisites

- An OpenAPI 3 specification file with defined components/schema models
- A `component.yaml` file referencing the OpenAPI specification via the `api_spec` field

## Quick Start

### 1. Define an OpenAPI 3 specification

Your specification should include schema definitions:

```
cat auto_dev/data/openapi/openapi_specification.yaml
```

Output:

```yaml
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
  description: A simple API for testing the OpenAPI Handler Generator
paths:
  /api/users:
    get:
      summary: List users
      responses:
        '200':
          description: Successful response
          content:
            application/json:    
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'
    post:
      summary: Create a user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/User'
      responses:
        '201':
          description: Created
          content:
            application/json:    
              schema:
                $ref: '#/components/schemas/User'
  /api/users/{userId}:
    get:
      summary: Get a user
      parameters:
        - name: userId
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: Successful response
          content:
            application/json:    
              schema:
                $ref: '#/components/schemas/User'
components:
  schemas:
    User:
      type: object
      required:
        - id
        - name
      properties:
        id:
          type: integer
        name:
          type: string
        email:
          type: string
```

### 2. Set Up Your Project Structure

!!! note "Optional Step"
    Skip this if you already have a project structure set up.

Initialize aea:
```bash
aea init --remote --author xiuxiuxar --ipfs --reset 
```

Create a new repo:
```bash
adev repo scaffold -t autonomy new_station
```

```bash
cd new_station
```

Scaffold a customs component:
```bash
aea scaffold -tlr custom simple_dao
```

### 3. Configure Your Component

```bash
cp ../auto_dev/data/openapi/openapi_specification.yaml packages/xiuxiuxar/customs/simple_dao/
```

```bash
yq e '.api_spec = "openapi_specification.yaml"' -i packages/xiuxiuxar/customs/simple_dao/component.yaml
```

```bash
cat packages/xiuxiuxar/customs/simple_dao/component.yaml
```

Output:

```yaml
name: simple_dao
author: xiuxiuxar
version: 0.1.0
type: custom
description: The custom component package.
license: Apache-2.0
aea_version: '>=1.0.0, <2.0.0'
fingerprint:
  __init__.py: bafybeigjt2jaxismyp3hspvqefjrcp33mmen3pnmnkm4rhesh74io3vikm
fingerprint_ignore_patterns: []
dependencies: {}
api_spec: openapi_specification.yaml
```

### 4. Generate DAOs

```bash
cd packages/xiuxiuxar/customs/simple_dao
```

!!! tip
    We automatically confirm all actions, though you can omit the `--auto-confirm` flag to see the actions that will be taken.

```bash
adev scaffold dao --auto-confirm
```

## Generated Structure

The scaffolding process creates the following files:

```
daos/
├── __init__.py
├── base_dao.py              # Base Data Access Object class
├── <model_name_1>_dao.py    # Model-specific Data Access Object
├── <model_name_2>_dao.py    # Model-specific Data Access Object
├── aggregated_data.json     # Sample test data
└── test_dao.py              # Test script
```

## Understanding the Generated Code

### Base DAO

The `base_dao.py` file contains:

- Common CRUD operations (Create, Read, Update, Delete)
- Transaction handling
- Error management

### Model-Specific DAOs

Each model gets its own DAO class with:

- Model-specific validation
- Custom query methods
- Type hints for your schema

### Test Data

The `aggregated_data.json` file contains:

- Sample data for each model
- Valid test cases for CRUD operations

## Customization

!!! tip "Template Customization"
    The generated DAOs use Jinja2 templates. To customize:
    
    1. Locate templates in `auto_dev/data/templates/dao`
    2. Modify them to suit your requirements
    3. Re-run the scaffolding command

## Best Practices

### Error Handling

The scaffolding process validates:

- Component configuration
- OpenAPI specification format
- Schema definitions

!!! warning "Schema Requirements"
    Ensure your OpenAPI spec includes proper schema definitions with required fields and property types.

### Keeping DAOs in Sync

!!! success "Regenerate After Changes"
    Always regenerate your DAOs after modifying your OpenAPI specification to maintain consistency.

## Testing Your DAOs

Run the generated test script to verify functionality:

```bash
python -m packages.your_author.customs.simple_dao.daos.test_dao
```

## Integration with Handlers

DAOs work seamlessly with OpenAPI handlers. See the [OpenAPI Handler Integration](openapi.md) guide for details on connecting your DAOs to API endpoints.