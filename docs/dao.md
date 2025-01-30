# Scaffolding a new DAO

The tools within the `dao` subcommand are used to scaffold a new customs component DAO (Data Access Object) based on an OpenAPI 3 specification. This process automates the creation of DAO classes, dummy data, and test scripts.

## Prerequisites

1. An OpenAPI 3 specification file with components/schema models defined.
2. A `component.yaml` file in the current directory that references the OpenAPI specification using the `api_spec` field.

## Steps to Scaffold a DAO

1. Ensure you have the OpenAPI 3 specification file. You can view its contents using:

```bash
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
  /users:
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
  /users/{userId}:
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

2. If not already done, scaffold a repo and a customs component.

Create a new repo.
```bash
adev repo scaffold -t autonomy new_station
```

```bash
cd new_station
```

Scaffold a customs component.
```bash
aea scaffold -tlr custom simple_dao
```


3. Create or update the `component.yaml` file to reference the OpenAPI specification using the `api_spec` field.

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

4. Run the DAO scaffolding command from the customs component directory:

```bash
cd packages/xiuxiuxar/customs/simple_dao
```

We automatically confirm all actions, though you can omit the `--auto-confirm` flag to see the actions that will be taken.

```bash
adev scaffold dao --auto-confirm
```

The scaffolding process creates the following:

1. DAO Classes: For each model defined in the OpenAPI specification, a corresponding DAO class is generated.
2. Dummy Data: 
   - Aggregated dummy data for all models
   - Individual dummy data instances for testing
3. Test Script: A test script to validate the generated DAO classes

To identify the persistent schemas, the scaffolder uses the following logic:

- It first checks for explicit `x-persistent` tags in schemas:

   ```yaml
   components:
      schemas:
         User:
            x-persistent: true  # Marking the User schema as persistent
            type: object
            properties:
               name:
                  type: string
                  ...
   ```

- If no `x-persistent` tags are found, it identifies schemas as persistent if they are:
  - Used in a responses
  - Used as nested objects in requests

The scaffolder will show the identified schemas and prompt for confirmation (unless `--auto-confirm` is used).

## Generated File Structure

After running the scaffold command, you'll find the following structure in your custom component:

```
daos/
├── __init__.py
├── base_dao.py
├── <model_name_1>_dao.py
├── <model_name_2>_dao.py
├── ...
└── aggregated_data.json
tests/
└── test_dao.py
```

## How It Works

The scaffolding process involves several steps:

1. Loading and validating the OpenAPI specification (checking for required fields, etc.)
2. Generating DAO classes for each model
3. Creating dummy data for testing
4. Generating a test script

For more details on the implementation, refer to:
`auto_dev/dao/scaffolder.py`

## Customization

The generated DAO classes use Jinja2 templates for customization. If you need to modify the structure of the generated classes, you can update the templates located in the `auto_dev/data/templates/dao` directory.

## Error Handling

The scaffolding process validates:
- `component.yaml` exists and has `api_spec` field
- OpenAPI spec file exits and is valid YAML
- OpenAPI spec contains components/schemas
- OpenAPI spec follows OpenAPI 3.0 format

Detailed error messages are logged for troubleshooting.

## Next Steps

After scaffolding your DAO:

1. Review the generated DAO classes in the `daos/` directory.
2. Examine the `aggregated_data.json` file for the structure of the dummy data.
3. Run the `test_dao.py` script to ensure the basic functionality of your DAOs.
4. Customize the generated classes as needed for your specific use case.

Remember to regenerate the DAOs if you make changes to your OpenAPI specification to keep them in sync.