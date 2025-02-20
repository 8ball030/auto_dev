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
