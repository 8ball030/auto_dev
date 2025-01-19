# Scaffolding a new DAO

The tools within the `dao` subcommand are used to scaffold a new DAO (Data Access Object) based on an OpenAPI 3 specification. This process automates the creation of DAO classes, dummy data, and test scripts.

## Prerequisites

1. An OpenAPI 3 specification file with components/schema models defined.
2. A `component.yaml` file in the current directory that references the OpenAPI specification using the `api_spec` field.

## Steps to Scaffold a DAO

1. Ensure you have the OpenAPI 3 specification file. You can view its contents using:

```bash
cat auto_dev/data/openapi/openapi_specification.yaml
```

2. Create or update the `component.yaml` file to reference the OpenAPI specification using the `api_spec` field.

```yaml
api_spec: <path_to_openapi_specification.yaml>
```

3. Run the DAO scaffolding command:

```bash
adev scaffold dao
```

The scaffolding process creates the following:

1. DAO Classes: For each model defined in the OpenAPI specification, a corresponding DAO class is generated.
2. Dummy Data: 
   - Aggregated dummy data for all models
   - Individual dummy data instances for testing
3. Test Script: A test script to validate the generated DAO classes

To identify the persistent schemas, the scaffolder uses the following logic:

1. It checks whether custom x-persistent field is set to true for a schema. If it is, the schema is identified as a persistent schema.

   ```yaml
   components:
      schemas:
         User:
            x-persistent: true  # Marking the schema as persistent
            type: object
            properties:
               name:
                  type: string
                  ...
   ```

2. If no x-persistent tags are found, it then attempts to identify all the schemas in the OpenAPI specification by checking if they are used in any request or response.
3. If the schema is used in a request and is used in multiple contexts (request or response), it is identified as a persistent schema.

## Generated File Structure

After running the scaffold command, you'll find the following structure in your project:

```
generated/
├── dao/
│ ├── <model_name_1>dao.py
│ ├── <model_name_2>dao.py
│ └── ...
├── aggregated_data.json
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

The scaffolding process includes comprehensive error handling to catch issues such as:
- Missing or invalid OpenAPI specification
- YAML or JSON parsing errors
- File I/O errors

If any errors occur during the scaffolding process, detailed error messages will be logged to help with troubleshooting.

## Next Steps

After scaffolding your DAO:

1. Review the generated DAO classes in the `generated/dao/` directory.
2. Examine the `aggregated_data.json` file for the structure of the dummy data.
3. Run the `test_dao.py` script to ensure the basic functionality of your DAOs.
4. Customize the generated classes as needed for your specific use case.

Remember to regenerate the DAOs if you make changes to your OpenAPI specification to keep them in sync.