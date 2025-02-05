GENERATE_MECH_TOOL = f"""
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


COMPONENT_YAML_CONTENT = f'''name: {tool_name}
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


COMMENTS = """
1. The main() function should only be used for testing purposes. Do NOT push this.
2. Once main() works as expected run 'autonomy packages lock && autonomy push-all'
3. Add to API_KEY list in .example.env and adhere to the current structure. Only do this if the API_KEY doesn't already exist for your key.
4. Next, add all new models to FILE_HASH_TO_TOOLS and use the new hash from packages/packages.json for your tool.
Check this PR for reference. https://github.com/valory-xyz/mech/pull/228/files
"""

INIT_CONTENT = '''#!/usr/bin/env python3
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