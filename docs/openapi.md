# OpenAPI Handler Integration

This guide explains how to augment components with handler methods based on an OpenAPI 3.

## Prerequisites

- An OpenAPI 3 specification file with defined paths and operationIds
- A `component.yaml` file referencing the OpenAPI specification via the `api_spec` field.
- For DAO integration: Data Access Objects for each schema in the specification. See [Data Access Object](dao.md).

## Basic Handler Augmentation

### 1. Define an OpenAPI 3 Specification.

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

Initialise aea:

```bash
aea init --remote --author xiuxiuxar --ipfs --reset 
```

Create a new repo:

```bash
adev repo scaffold --no-install -t autonomy new_station
```

```bash
cd new_station
```

Create a new agent based on the frontend_agent template:

```bash
adev create xiuxiuxar/agent -t eightballer/frontend_agent --no-clean-up --force
```

```bash
cd agent
```

Eject a custom component to use as a base handler template:

```bash
adev eject custom eightballer/simple_html xiuxiuxar/new_handler
```

Push to the local packages directory:

```bash
adev publish xiuxiuxar/agent --force
```

```bash
cd ..
```


### 3. Configure Your Component

Add your OpenAPI specification to the component:

```bash
cp ../auto_dev/data/openapi/openapi_specification.yaml packages/xiuxiuxar/customs/new_handler/openapi3_spec.yaml
```

```bash
yq e '.api_spec = "openapi3_spec.yaml"' -i packages/xiuxiuxar/customs/new_handler/component.yaml
```

```bash
cat packages/xiuxiuxar/customs/new_handler/component.yaml
```

Output:

```yaml
version: 0.1.0
type: custom
description: Simple HTML frontend to act as a template for the frontend ABCI loader.
license: Apache-2.0
aea_version: '>=1.0.0, <2.0.0'
fingerprint:
  __init__.py: bafybeidwwtpfuhelmwdkgh2ayk6hls62xpxns33f27qsryzd4vh2kw6hxq
  behaviours.py: bafybeiadbbujl23thcggr55up7t7jo5nxjk5qty7uqf75xgw57nzrq3dwy
  build/index.html: bafybeigyjfv75r7fnd7mw63vbidusohzopzyz47c5nmc3tiak5yh22gbfi
  handlers.py: bafybeibnco7jqjsfwamcek64cvltcr3wvvw73bs74wzbbhwqggy4p4hlsi
  openapi3_spec.yaml: bafybeibdvlfbr4ghin75dyqjyd3zbusq45uekmuoftmj74k4cvnq2rapci
  tests/__init__.py: bafybeiayjxaqrjpu7poz56eozqbi4ln7uene4r27bnq5qeely3ambcmggm
  tests/test_simple_html.py: bafybeiaqu3mw6kq5yq7blk5vjrd5mtw5ej55vs32ftxdf225k3semjyn4u
fingerprint_ignore_patterns: []
dependencies: {}
api_spec: openapi3_spec.yaml
frontend_dir: build
behaviours:
- class_name: LogReadingBehaviour
  args: {}
handlers:
- class_name: HttpHandler
  args: {}
```

### 4. Run the Augmentation Command

```bash
cd packages/xiuxiuxar/customs/new_handler
```

We automatically confirm all actions, though you can omit the `--auto-confirm` flag to see the actions that will be taken.

```bash
adev augment customs openapi3 --auto-confirm
```

### 5. Update Configuration

```bash
cd ../../../..
```

We ensure the component yaml references the handler class:

```bash
yq e '.handlers[].class_name = "ApiHttpHandler"' -i packages/xiuxiuxar/customs/new_handler/component.yaml
```

Modify the agent to load the new custom handler method:

```bash
yq e '(select(.public_id == "eightballer/trader_abci:0.1.0") | .models.params.args.user_interface.custom_component) = "xiuxiuxar/new_handler"' -i packages/xiuxiuxar/agents/agent/aea-config.yaml
```

```bash
autonomy packages lock
```

### 6. Run Your Agent

```shell
adev run dev xiuxiuxar/agent --force
```

## Advanced: Integration with Data Access Objects (DAOs)

### 1. Complete Basic Setup

Follow steps 1-3 from the basic handler augmentation.

### 2. Scaffold DAOs

!!! tip
    We automatically confirm all actions, though you can omit the `--auto-confirm` flag to see the actions that will be taken.


```shell
adev scaffold dao --auto-confirm
```

### 3. Augment with DAO Integration

!!! tip
    We automatically confirm all actions, though you can omit the `--auto-confirm` flag to see the actions that will be taken.

```shell
adev augment customs openapi3 --use-daos --auto-confirm
```

### 4. Complete Configuration

Follow steps 5-6 from the basic handler augmentation.

## How It Works

The augmentation process:

1. Loads and validates the OpenAPI specification
2. Generates handler methods for each defined path
3. Creates resolver methods to handle requests
4. When using DAOs, connects endpoints to database operations

!!! tip "Implementation Details"
    For more details on the implementation, see `auto_dev/handler/scaffolder.py`

## Customization

The generated handlers use Jinja2 templates. To customize the structure:

1. Locate the templates in the `JINJA_TEMPLATE_FOLDER`
2. Modify them to suit your specific requirements
3. Re-run the augmentation command

## Best Practices

!!! warning "Keep in Sync"
    Always regenerate handlers after modifying your OpenAPI specification to maintain consistency.

!!! success "Review Generated Code"
    After augmentation, review the generated code in `handlers.py` to ensure it meets your requirements.
