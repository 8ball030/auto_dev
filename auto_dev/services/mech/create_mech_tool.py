import os
from pathlib import Path
import sys
import re
import argparse
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI

from auto_dev import cli
from auto_dev.services.mech.constants.prompts import COMMENTS, GENERATE_MECH_TOOL, INIT_CONTENT
from auto_dev.utils import get_logger, write_to_file

logger = get_logger()

def create_directory_structure(base_path, author_name):
    # Create the directory structure for the tool
    tool_path = os.path.join(base_path, 'packages', author_name)
    if os.path.exists(tool_path):
        print(f"Directory for author '{author_name}' already exists. Skipping creation.")
        return tool_path
    os.makedirs(tool_path, exist_ok=True)

    return tool_path

def generate_init_file(tool_path):
    """
    Generates an __init__.py file with predefined content in the specified tool path
    if it does not already exist.
    Args:
        tool_path (str): The path where the __init__.py file will be created.
    Returns:
        None
    """
    init_file_path = os.path.join(tool_path, '__init__.py')
    if os.path.exists(init_file_path):
        logger.info(f"__init__.py already exists at {init_file_path}. Skipping creation.")
        return

    write_to_file(init_file_path, INIT_CONTENT)
    logger.info(f"__init__.py created at {init_file_path}")


def create_customs_folder(tool_path):
    """
    Creates a 'customs' folder within the given tool directory.
    Args:
        tool_path (str): The path to the tool directory.
    Returns:
        str: The path to the created 'customs' folder.
    """
    customs_path = os.path.join(tool_path, 'customs')
    if not os.path.exists(customs_path):
        os.makedirs(customs_path, exist_ok=True)
        logger.info(f"'customs' folder created at {customs_path}")
    else:
        logger.info(f"'customs' folder already exists at {customs_path}")
    return customs_path

def create_tool_folder(customs_path, tool_name):
    """
    Creates a folder inside the customs folder with the name of the tool.
    Args:
        customs_path (str): The path to the customs folder.
        tool_name (str): The name of the tool.
    Returns:
        str: The path to the created tool folder.
    """
    tool_folder_path = os.path.join(customs_path, tool_name)
    if not os.path.exists(tool_folder_path):
        os.makedirs(tool_folder_path, exist_ok=True)
        logger.info(f"Tool folder '{tool_name}' created at {tool_folder_path}")
    else:
        logger.info(f"Tool folder '{tool_name}' already exists at {tool_folder_path}")
    return tool_folder_path

def create_component_yaml(tools_folder_path, tool_name, author_name):
    yaml_path = tools_folder_path / "component.yaml"
    if yaml_path.exists():
        logger.info(f"component.yaml already exists at {yaml_path}. Skipping creation.")
        return
    
    script_dir = Path(__file__).resolve().parent

    templates_path = script_dir / "templates"

    # Load the Jinja environment and template
    env = Environment(loader=FileSystemLoader(str(templates_path)))
    template = env.get_template("component.yaml.j2")

    # Render the template with collected variables
    component_yaml_content = template.render(tool_name=tool_name, author_name=author_name)

    # Write output to component.yaml
    write_to_file(yaml_path, component_yaml_content)
    logger.info(f"component.yaml created at {yaml_path}")


def generate_and_write_tool_file(tool_folder_path, tool_name, api_file, gpt_api_key):
    """
    Generates and writes the content for <tool_name>.py using GPT.
    Args:
        tool_path (str): The path where the tool files are stored.
        tool_name (str): The name of the tool.
        api_file (str): The path to the file containing API logic.
        gpt_api_key (str): The API key for OpenAI GPT.
    Returns:
        None
    """
    tool_py_path = Path(tool_folder_path) / f"{tool_name}.py"
    if os.path.exists(tool_py_path):
        user_input = input(f"The file {tool_py_path} already exists. Do you want to override it? (yes/no): ").strip().lower()
        if user_input != "yes":
            logger.info(f"Skipping file generation for {tool_py_path}")
            return False
    client = OpenAI(api_key=gpt_api_key)
    try:
        # Read the content of the API logic file
        with open(api_file, 'r') as f:
            api_logic_content = f.read()
    except Exception as e:
        logger.error(f"Error reading the API file: {e}")
        sys.exit(1)
    # Call GPT to generate the content

        # Use Jinja to load and render the template
    templates_path = Path(__file__).resolve().parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_path)))
    template = env.get_template("generate_mech_tool.py.j2")

    # Render the template with collected variables
    generated_code_prompt = template.render(tool_name=tool_name, api_logic_content=api_logic_content)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": generated_code_prompt}
            ]
        )

        # Extract GPT's response
        gpt_response = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error calling GPT: {e}")
        sys.exit(1)

    # Write the generated content into the <tool_name>.py file
    tool_py_path = Path(tool_folder_path) / f"{tool_name}.py"
    try:
        with open(tool_py_path, 'w') as f:
            f.write(gpt_response)
        logger.info(f"Generated content written to {tool_py_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing to {tool_py_path}: {e}")
        sys.exit(1)

def append_comments_to_tool_file(tool_file_path, comments):
    """
    Appends comments to the bottom of the specified tool file.
    Args:
        tool_file_path (str): The path to the tool file.
        comments (str): The comments to append.
    Returns:
        None
    """
    try:
        write_to_file(tool_file_path, "\n\n# " + "\n# ".join(comments.splitlines()), mode="a")
        logger.info(f"Comments successfully appended to {tool_file_path}")
    except Exception as e:
        logger.error(f"Error appending comments to {tool_file_path}: {e}")

@cli.group()
def main(api_file, tool_name, author_name, gpt_key):

    GPT_KEY = gpt_key
    base_path = Path.cwd().parents[3]  # Equivalent to going up 4 directories

    logger.info("The base path is" + base_path)
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
    file_generated = generate_and_write_tool_file(tools_folder_path, tool_name, api_file, GPT_KEY)

    # Append instructions to tool_name.py file only if the file was generated
    if file_generated:
        tool_py_path = os.path.join(tool_base_path, 'customs', tool_name, f"{tool_name}.py")
        append_comments_to_tool_file(tool_py_path, COMMENTS)

    logger.info(f"Custom tool '{tool_name}' has been created successfully!")

if __name__ == "__main__":
    main()
