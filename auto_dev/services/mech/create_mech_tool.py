import os
from pathlib import Path
import sys
import re
import argparse
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI

from auto_dev import cli
from auto_dev.services.mech.constants.prompts import COMMENTS, INIT_CONTENT
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
    yaml_path = Path(tools_folder_path) / "component.yaml"
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


def generate_and_write_tool_file(tool_folder_path, tool_name, api_file, gpt_api_key, force=False):
    """Generates and writes the content for <tool_name>.py using GPT."""
    tool_py_path = Path(tool_folder_path) / f"{tool_name}.py"

    # Always overwrite unless force=False and user declines
    if os.path.exists(tool_py_path) and not force:
        user_input = input(f"The file {tool_py_path} already exists. Do you want to override it? (yes/no): ").strip().lower()
        if user_input != "yes":
            logger.info(f"Skipping file generation for {tool_py_path}")
            return False

    client = OpenAI(api_key=gpt_api_key)

    try:
        with open(api_file, 'r') as f:
            api_logic_content = f.read()
    except Exception as e:
        logger.error(f"Error reading API file: {e}")
        sys.exit(1)

    # Render the template
    templates_path = Path(__file__).resolve().parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_path)))
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
        logger.error(f"Error calling GPT: {e}")
        sys.exit(1)

    # Write to file
    if not gpt_response or gpt_response.strip() == "":
        logger.error("GPT response is empty! Aborting file write.")
        sys.exit(1)
    try:
        logger.info(f"Writing generated code to {tool_py_path}")
        with open(tool_py_path, 'w', encoding='utf-8') as f:
            f.write(gpt_response)
        logger.info(f"Generated content written to {tool_py_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing to {tool_py_path}: {e}")
        sys.exit(1)

def write_to_file(file_path, content, mode="a"):
    """Writes content to a file, ensuring safe append mode."""
    with open(file_path, mode, encoding="utf-8") as f:
        f.write(content)


def append_comments_to_tool_file(tool_file_path, comments):
    """
    Appends comments to the bottom of the specified tool file.
    Ensures existing content is not erased.
    """
    try:
        # ✅ Read existing file content before appending
        with open(tool_file_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

        # ✅ Append mode ensures content is not erased
        with open(tool_file_path, "a", encoding="utf-8") as f:
            f.write("\n\n# " + "\n# ".join(comments.splitlines()))

        # ✅ Read file after appending
        with open(tool_file_path, "r", encoding="utf-8") as f:
            new_content = f.read()

        logger.info(f"Comments successfully appended to {tool_file_path}")

    except Exception as e:
        logger.error(f"Error appending comments to {tool_file_path}: {e}")



def main(api_file, tool_name, author_name, gpt_key):

    GPT_KEY = gpt_key
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
    file_generated = generate_and_write_tool_file(tools_folder_path, tool_name, api_file, GPT_KEY)

    # Append instructions to tool_name.py file only if the file was generated
    if file_generated:
        tool_py_path = os.path.join(tool_base_path, 'customs', tool_name, f"{tool_name}.py")
        append_comments_to_tool_file(tool_py_path, COMMENTS)

    logger.info(f"Custom tool '{tool_name}' has been created successfully!")

if __name__ == "__main__":
    main()
