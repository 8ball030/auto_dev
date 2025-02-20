"""This module provides utilities for generating Mech tools using OpenAI's GPT API.

It creates directory structures, initializes tool files, and integrates Jinja templates.
"""

import os
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from openai import OpenAI

from auto_dev.utils import get_logger
from auto_dev.services.mech.constants.prompts import COMMENTS, INIT_CONTENT


logger = get_logger()


def create_directory_structure(base_path, author_name):
    """Create the directory structure for the tool under the author's namespace.

    Args:
    ----
        base_path (Path): The base path where the tool directory should be created.
        author_name (str): The name of the author.

    Returns:
    -------
        str: The path to the created tool directory.

    """
    tool_path = os.path.join(base_path, "packages", author_name)
    if Path.exists(tool_path):
        return tool_path
    Path(tool_path).mkdir(parents=True, exist_ok=True)

    return tool_path


def generate_init_file(tool_path):
    """Generates an __init__.py file with predefined content in the specified tool path
    if it does not already exist.

    Args:
    ----
        tool_path (str): The path where the __init__.py file will be created.

    Returns:
    -------
        None.

    """
    init_file_path = os.path.join(tool_path, "__init__.py")
    if Path.exists(init_file_path):
        logger.info(f"__init__.py already exists at {init_file_path}. Skipping creation.")
        return

    write_to_file(init_file_path, INIT_CONTENT)
    logger.info(f"__init__.py created at {init_file_path}")


def create_customs_folder(tool_path):
    """Creates a 'customs' folder within the given tool directory.

    Args:
    ----
        tool_path (str): The path to the tool directory.

    Returns:
    -------
        str: The path to the created 'customs' folder.

    """
    customs_path = os.path.join(tool_path, "customs")
    if not Path.exists(customs_path):
        Path(customs_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"'customs' folder created at {customs_path}")
    else:
        logger.info(f"'customs' folder already exists at {customs_path}")
    return customs_path


def create_tool_folder(customs_path, tool_name):
    """Creates a folder inside the customs folder with the name of the tool.

    Args:
    ----
        customs_path (str): The path to the customs folder.
        tool_name (str): The name of the tool.

    Returns:
    -------
        str: The path to the created tool folder.

    """
    tool_folder_path = os.path.join(customs_path, tool_name)
    if not Path.exists(tool_folder_path):
        Path(tool_folder_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Tool folder '{tool_name}' created at {tool_folder_path}")
    else:
        logger.info(f"Tool folder '{tool_name}' already exists at {tool_folder_path}")
    return tool_folder_path


def create_component_yaml(tools_folder_path, tool_name, author_name):
    """Create a `component.yaml` file for the specified tool.

    This function generates a `component.yaml` file inside the given tools folder
    using a Jinja2 template. If the file already exists, it logs a message and skips creation.

    Args:
    ----
        tools_folder_path (str | Path): The path to the folder where `component.yaml` should be created.
        tool_name (str): The name of the tool.
        author_name (str): The name of the author.

    Returns:
    -------
        None

    """
    yaml_path = Path(tools_folder_path) / "component.yaml"
    if yaml_path.exists():
        logger.info(f"component.yaml already exists at {yaml_path}. Skipping creation.")
        return

    script_dir = Path(__file__).resolve().parent

    templates_path = script_dir / "templates"

    # Load the Jinja environment and template
    env = Environment(loader=FileSystemLoader(str(templates_path)), autoescape=True)
    template = env.get_template("component.yaml.j2")

    # Render the template with collected variables
    component_yaml_content = template.render(tool_name=tool_name, author_name=author_name)

    # Write output to component.yaml
    write_to_file(yaml_path, component_yaml_content)
    logger.info(f"component.yaml created at {yaml_path}")


def generate_and_write_tool_file(tool_folder_path, tool_name, api_file, gpt_api_key, force=False):
    """Generates and writes the content for <tool_name>.py using GPT."""
    tool_py_path = Path(tool_folder_path) / f"{tool_name}.py"

    # Always overwrite unless force=False and user declines
    if Path.exists(tool_py_path) and not force:
        user_input = input(
            f"The file {tool_py_path} already exists. Do you want to override it? (yes/no): "
            ).strip().lower()
        if user_input != "yes":
            logger.info(f"Skipping file generation for {tool_py_path}")
            return False

    client = OpenAI(api_key=gpt_api_key)

    try:
        with open(api_file, encoding="utf-8") as f:
            api_logic_content = f.read()
    except Exception as e:
        logger.exception(f"Error reading API file: {e}")
        sys.exit(1)

    # Render the template
    templates_path = Path(__file__).resolve().parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_path)),
        autoescape=select_autoescape(["html", "xml", "j2"])  # Autoescapes HTML, XML, and Jinja2 templates
    )
    template = env.get_template("generate_mech_tool.py.j2")
    generated_code_prompt = template.render(tool_name=tool_name, api_logic_content=api_logic_content)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": generated_code_prompt}]
        )
        gpt_response = response.choices[0].message.content.strip()

        # Remove unwanted triple backticks from GPT response
        if gpt_response.startswith("```python"):
            gpt_response = gpt_response[9:]  # Remove first 9 characters (` ```python `)
        if gpt_response.endswith("```"):
            gpt_response = gpt_response[:-3]  # Remove last 3 characters (` ``` `)

    except Exception as e:
        logger.exception(f"Error calling GPT: {e}")
        sys.exit(1)

    # Write to file
    if not gpt_response or gpt_response.strip() == "":
        logger.error("GPT response is empty! Aborting file write.")
        sys.exit(1)
    try:
        logger.info(f"Writing generated code to {tool_py_path}")
        with open(tool_py_path, "w", encoding="utf-8") as f:
            f.write(gpt_response)
        logger.info(f"Generated content written to {tool_py_path}")
        return True
    except Exception as e:
        logger.exception(f"Error writing to {tool_py_path}: {e}")
        sys.exit(1)


def write_to_file(file_path, content, mode="a"):
    """Writes content to a file, ensuring safe append mode."""
    with open(file_path, mode, encoding="utf-8") as f:
        f.write(content)


def append_comments_to_tool_file(tool_file_path, comments):
    """Appends comments to the bottom of the specified tool file.
    Ensures existing content is not erased.
    """
    try:
        # ✅ Read existing file content before appending
        with open(tool_file_path, encoding="utf-8") as f:
            f.read()

        # ✅ Append mode ensures content is not erased
        with open(tool_file_path, "a", encoding="utf-8") as f:
            f.write("\n\n# " + "\n# ".join(comments.splitlines()))

        # ✅ Read file after appending
        with open(tool_file_path, encoding="utf-8") as f:
            f.read()

        logger.info(f"Comments successfully appended to {tool_file_path}")

    except Exception as e:
        logger.exception(f"Error appending comments to {tool_file_path}: {e}")


def main(api_file, tool_name, author_name, gpt_key):
    """Main function to scaffold a custom Mech tool.

    This function creates the necessary directory structure and files for a Mech tool,
    including initialization files, a `component.yaml` configuration file, and the
    main tool Python file. It also generates the tool's logic using OpenAI's GPT API.

    Args:
    ----
        api_file (str | Path): Path to the API definition file used for tool generation.
        tool_name (str): Name of the tool to be created.
        author_name (str): Name of the author or organization creating the tool.
        gpt_key (str): API key for OpenAI GPT, used to generate the tool's code.

    Returns:
    -------
        None

    Side Effects:
        - Creates necessary directories and initialization files.
        - Generates a `component.yaml` file using Jinja templates.
        - Uses GPT to generate and save the tool's Python script.
        - Appends documentation comments to the generated file.

    """
    base_path = Path.cwd()
    # Create the tool's directory structure and necessary files
    tool_base_path = create_directory_structure(base_path, author_name)
    # Create the init file within the author's folder
    generate_init_file(tool_base_path)

    # Create the customs folder
    customs_path = create_customs_folder(tool_base_path)

    # Create the tool folder
    tools_folder_path = create_tool_folder(customs_path, tool_name)

    # Create the init file within the tool_name folder
    generate_init_file(tools_folder_path)

    # Create the component.yaml file
    create_component_yaml(tools_folder_path, tool_name, author_name)

    # Create the `<tool_name>.py` file
    file_generated = generate_and_write_tool_file(tools_folder_path, tool_name, api_file, gpt_key)

    # Append instructions to tool_name.py file only if the file was generated
    if file_generated:
        tool_py_path = os.path.join(tool_base_path, "customs", tool_name, f"{tool_name}.py")
        append_comments_to_tool_file(tool_py_path, COMMENTS)

    logger.info(f"Custom tool '{tool_name}' has been created successfully!")


if __name__ == "__main__":
    main()
