# Augmenting visualisation station with an OpenAPI Handler

The tools within the `openapi` subcommand are used to augment a customs component with handler methods based on an OpenAPI 3 specification. This process automates the creation of endpoints methods. 

## Prerequisites

1. An OpenAPI 3 specification file with paths, operationIds, and if augmenting with data access objects, schemas defined.
2. A `component.yaml` file in the current directory that references the OpenAPI specification using the `api_spec` field.
3. If augmenting with DAOs, DAOs for each schema in the OpenAPI specification (see dao docs for how to scaffold these).

## Steps to Augment a Handler (without data access objects)

### 1. Define an OpenAPI3 spec.

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

### 2. [Optional] Scaffold a repo and a customs component.

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


### 3. Create or update the `component.yaml` file to reference the OpenAPI specification.

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

### 4. Run the Handler augment command.

```bash
cd packages/xiuxiuxar/customs/new_handler
```

We automatically confirm all actions, though you can omit the `--auto-confirm` flag to see the actions that will be taken.

```bash
adev augment customs openapi3 --auto-confirm
```

### 5. Update the component and aea-config.yaml to run the new handler.

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

### 6. Run the agent.

```shell
adev run dev xiuxiuxar/agent --force
```

The augmenting process creates the following handler methods: For each path defined in the OpenAPI specification, a corresponding handler method is generated along with a general handler and resolver method.

## How It Works

The augmentation process involves several steps:

1. Loading and validating the OpenAPI specification.
2. Generating handler methods for each path.

For more details on the implementation, refer to:
`auto_dev/handler/scaffolder.py`

## Customization

The generated Handler methods use Jinja2 templates for customization. If you need to modify the structure of the generated classes, you can update the templates located in the `JINJA_TEMPLATE_FOLDER`.

## Next Steps

After augmenting your handler:

- Review the generated handler methods in the `handlers.py` file.

Remember to regenerate the handlers if you make changes to your OpenAPI specification to keep them in sync.

## Steps to Augment a Handler (with DAOs)

### 1. Perform steps 1-3 above. 

### 2. Run the DAO scaffold command.

[NOTE]
We automatically confirm all actions, though you can omit the `--auto-confirm` flag to see the actions that will be taken.


```shell
adev scaffold dao --auto-confirm
```

### 3. Run the handler augment command with DAO flag.  

We automatically confirm all actions, though you can omit the `--auto-confirm` flag to see the actions that will be taken.

```shell
adev augment customs openapi3 --use-daos --auto-confirm
```

### 4. Perform 5-6 above.