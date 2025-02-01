import os
import sys
import re
import argparse
from openai import OpenAI

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
        print(f"__init__.py already exists at {init_file_path}. Skipping creation.")
        return

    init_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------
'''
    with open(init_file_path, 'w') as f:
        f.write(init_content)
    print(f"__init__.py created at {init_file_path}")


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
        print(f"'customs' folder created at {customs_path}")
    else:
        print(f"'customs' folder already exists at {customs_path}")
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
        print(f"Tool folder '{tool_name}' created at {tool_folder_path}")
    else:
        print(f"Tool folder '{tool_name}' already exists at {tool_folder_path}")
    return tool_folder_path

def create_component_yaml(tools_folder_path, tool_name, author_name):
    yaml_path = os.path.join(tools_folder_path, 'component.yaml')
    if os.path.exists(yaml_path):
        print(f"component.yaml already exists at {yaml_path}. Skipping creation.")
        return

    component_yaml_content = f'''name: {tool_name}
author: {author_name}
version: 0.1.0
type: custom
description: Custom tool created using the CLI
license: Apache-2.0
aea_version: '>=1.0.0, <2.0.0'
fingerprint:
  __init__.py: bafybeidlhllgpf65xwk357wukpguuaz6hxhkyh7dwplv2xkxlrlk4b7zty
  {tool_name}.py: bafybeicytmdkgdehao6obnqoff6fpugr6gpbjw4ztxcsswn5ne76vhboqi
fingerprint_ignore_patterns: []
entry_point: {tool_name}.py
callable: run
dependencies: {{}}
'''

    with open(os.path.join(tools_folder_path, 'component.yaml'), 'w') as f:
        f.write(component_yaml_content)

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
    tool_py_path = os.path.join(tool_folder_path, f"{tool_name}.py")
    if os.path.exists(tool_py_path):
        user_input = input(f"The file {tool_py_path} already exists. Do you want to override it? (yes/no): ").strip().lower()
        if user_input != "yes":
            print(f"Skipping file generation for {tool_py_path}")
            return False
    client = OpenAI(api_key=gpt_api_key)
    try:
        # Read the content of the API logic file
        with open(api_file, 'r') as f:
            api_logic_content = f.read()
    except Exception as e:
        print(f"Error reading the API file: {e}")
        sys.exit(1)

     # Define the prompt for GPT to adjust the API logic
    prompt = f"""
    # -*- coding: utf-8 -*-
    # ------------------------------------------------------------------------------
    #
    #   Copyright 2023-2024 Valory AG
    #
    #   Licensed under the Apache License, Version 2.0 (the "License");
    #   you may not use this file except in compliance with the License.
    #   You may obtain a copy of the License at
    #
    #       http://www.apache.org/licenses/LICENSE-2.0
    #
    #   Unless required by applicable law or agreed to in writing, software
    #   distributed under the License is distributed on an "AS IS" BASIS,
    #   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    #   See the License for the specific language governing permissions and
    #   limitations under the License.
    #
    # ------------------------------------------------------------------------------
    \"\"\"Contains the job definitions\"\"\"
    import requests
    from typing import Any, Dict, Optional, Tuple
    DEFAULT_PERPLEXITY_SETTINGS = {{
        "max_": 1,
        "stop_sequences": None,
        "max_output_tokens": 500,
        "temperature": 0.7,
    }}
    PREFIX = "llama-"
    ENGINES = {{
        "chat": ["3.1-sonar-small-128k-online", "3.1-sonar-large-128k-online", "3.1-sonar-huge-128k-online"],
    }}
    ALLOWED_TOOLS = [PREFIX + value for value in ENGINES["chat"]]
    url = "https://api.perplexity.ai/chat/completions"
    # def count_tokens(text: str) -> int:
    #     \"\"\"Count the number of tokens in a text using the Gemini model's tokenizer.\"\"\"
    #     return genai.count_message_tokens(prompt=text)
    def run(**kwargs) -> Tuple[Optional[str], Optional[Dict[str, Any]], Any, Any]:
        \"\"\"Run the task\"\"\"
        api_key = kwargs["api_keys"]["perplexity"]
        tool = kwargs["tool"]
        prompt = kwargs["prompt"]
        if tool not in ALLOWED_TOOLS:
            return (
                f"Model {{tool}} is not in the list of supported models.",
                None,
                None,
                None,
            )
        max_tokens = kwargs.get("candidate_count")
        stop_sequences = kwargs.get(
            "stop_sequences", DEFAULT_GEMINI_SETTINGS["stop_sequences"]
        )
        max_output_tokens = kwargs.get(
            "max_output_tokens", DEFAULT_GEMINI_SETTINGS["max_output_tokens"]
        )
        temperature = kwargs.get("temperature", DEFAULT_GEMINI_SETTINGS["temperature"])
        counter_callback = kwargs.get("counter_callback", None)
        genai.configure(api_key=api_key)
        engine = genai.GenerativeModel(tool)
        try:
            response = engine.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=candidate_count,
                    stop_sequences=stop_sequences,
                    max_output_tokens=max_output_tokens,
                    temperature=temperature,
                ),
            )
            # Ensure response has a .text attribute
            response_text = getattr(response, "text", None)
        except Exception as e:
            return f"An error occurred: {{str(e)}}", None, None, None
        return response.text, prompt, None, counter_callback
        ....Edit this to work for the code I about to give you for {tool_name} based on the documentation and only give the code.
        Output only code, no words. This is being put directly in a Python file. Do not put the coding quotation formatting for python files.
        Also give me a commented out main function to run this code at the bottom of the file for testing.
        .....
        {api_logic_content}
    """


    # Call GPT to generate the content
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract GPT's response
        gpt_response = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling GPT: {e}")
        sys.exit(1)

    # Write the generated content into the <tool_name>.py file
    tool_py_path = os.path.join(tool_folder_path, f"{tool_name}.py")
    try:
        with open(tool_py_path, 'w') as f:
            f.write(gpt_response)
        print(f"Generated content written to {tool_py_path}")
        return True
    except Exception as e:
        print(f"Error writing to {tool_py_path}: {e}")
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
        with open(tool_file_path, 'a') as f:
            f.write("\n\n# " + "\n# ".join(comments.splitlines()))
        print(f"Comments successfully appended to {tool_file_path}")
    except Exception as e:
        print(f"Error appending comments to {tool_file_path}: {e}")

def main():
    #TODO: Input your GPT KEY HERE
    parser = argparse.ArgumentParser(description="CLI tool to create a custom Mech tool")
    parser.add_argument("gpt_key", help="Your OpenAi API Key")
    parser.add_argument("api_file", help="Python file implementing the API logic")
    parser.add_argument("tool_name", help="The name for the new tool")
    parser.add_argument("author_name", help="The name of the author")
    

    comments= """
    1. The main() function should only be used for testing purposes. Do NOT push this.
    2. Once main() works as expected run 'autonomy packages lock && autonomy push-all'
    3. Add to API_KEY list in .example.env and adhere to the current structure. Only do this if the API_KEY doesn't already exist for your key.
    4. Next, add all new models to FILE_HASH_TO_TOOLS and use the new hash from packages/packages.json for your tool.
    Check this PR for reference. https://github.com/valory-xyz/mech/pull/228/files
    """

    args = parser.parse_args()
    GPT_KEY = args.gpt_key
    base_path = os.path.abspath(os.path.join(os.getcwd(), *[".."] * 4))

    print("The base path is")
    print(base_path)

    # Create the tool's directory structure and necessary files
    tool_base_path = create_directory_structure(base_path, args.author_name)
    # Create the init file within the author's folder
    generate_init_file(tool_base_path)



    # Create the customs folder
    customs_path = create_customs_folder(tool_base_path)

    # Create the tool folder
    tools_folder_path = create_tool_folder(customs_path, args.tool_name)

    # Create the init file within the tool_name folder
    generate_init_file(tools_folder_path)

    # Create the component.yaml file
    create_component_yaml(tools_folder_path, args.tool_name, args.author_name)

    # Create the `<tool_name>.py` file
    file_generated = generate_and_write_tool_file(tools_folder_path, args.tool_name, args.api_file, GPT_KEY)

    # Append instructions to tool_name.py file only if the file was generated
    if file_generated:
        tool_py_path = os.path.join(tool_base_path, 'customs', args.tool_name, f"{args.tool_name}.py")
        append_comments_to_tool_file(tool_py_path, comments)

    print(f"Custom tool '{args.tool_name}' has been created successfully!")

if __name__ == "__main__":
    main()