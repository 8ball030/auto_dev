# Scaffolding a new API Handler agent.

The tools within the `handler` subcommand are used to scaffold a new agent.

We start with a simple openapi;

```bash
cat auto_dev/data/openapi/openapi_specification.yaml
```

We now scaffold the agent and cd in.

```bash
aea create new_agent && cd new_agent
```

This creates a new agent without any real skills.

Once we have a new agent, we can now use the cli to scaffold the skill using the CORE autonomy libraries and the OpenAPI specification.

This reduces the amount of code we need to write to get a skill up and means that we have no need to write any code to re-implement the wheel.

## Scaffolding a new skill

Use the --new-skill flag to scaffold a new skill.

```bash
adev scaffold handler ../auto_dev/data/openapi/openapi_specification.yaml --output my_api_skill --new-skill
```

The skill will be created in the skills directory.  The user will be prompted whether to rename MyModel.py to strategy.py, and whether to remove the dialogues.py file. THe scaffolding step will also install the http protocol, and fingerprint the skill.  At the completion, the user can now run the agent.

```bash
aea run
```

## Augmenting with an OpenAPI Handler

The tools within the `openapi` subcommand are used to augment a customs component with a new handler based on an OpenAPI 3 specification. This process automates the creation of endpoints methods. 

## Prerequisites

1. An OpenAPI 3 specification file with paths, operationIds, and if augmenting with DAOs, schemas defined.
2. A `component.yaml` file in the current directory that references the OpenAPI specification using the `api_spec` field.
3. If augmenting with DAOs, DAOs for each schema in the OpenAPI specification (see dao docs for how to scaffold these).

## Steps to Augment a Handler

1. Ensure you have the OpenAPI 3 specification file. You can view its contents using:

```bash
cat auto_dev/data/openapi/openapi_specification.yaml
```

2. Create or update the `component.yaml` file to reference the OpenAPI specification using the `api_spec` field.

```yaml
api_spec: <path_to_openapi_specification.yaml>
```

3. Run the Handler augmenting command, optionally with the `--use-daos` flag if you are augmenting with DAOs:

```bash
adev augment customs openapi3 --use-daos
```

The augmenting process creates the following: 

1. Handler methods: For each path defined in the OpenAPI specification, a corresponding handler method is generated, along with a general handler and resolver method.
2. Dialogues.py: A boilerplate dialogues file is generated.

## How It Works

The augmentation process involves several steps:

1. Loading and validating the OpenAPI specification
2. Generating Handler methods for each path

For more details on the implementation, refer to:
`auto_dev/handler/scaffolder.py`

## Customization

The generated Handler methods use Jinja2 templates for customization. If you need to modify the structure of the generated classes, you can update the templates located in the `JINJA_TEMPLATE_FOLDER`.

## Next Steps

After augmenting your handler:

- Review the generated handler methods in the `handlers.py` file.

Remember to regenerate the Handlers if you make changes to your OpenAPI specification to keep them in sync.