# text_function_by_example

This is a small utility to generate text-transformation scripts from examples.

## Setup

1. Install via `pip install text_function_by_example`
2. Make sure you have an [Anthropic API key](https://docs.anthropic.com/en/api/getting-started).
3. Make sure the `ANTHROPIC_API_KEY` environment variable is set before running the tool; for example, you could run `export ANTHROPIC_API_KEY=your-key-here` in the terminal first.

## Usage

Create a toml file containing examples of the text transformation and, optionally, a description.
For example, the following `example_change_citation.toml` illustrates transforming from one citation syntax to another:

```toml
# This is optional - you can just supply examples and no description, and let Claude figure it out.
description = "Replace parenthetical citations with Markdown footnotes."

[[examples]]
input = "A very smart person said (p. 13) something I agree with"
output = "A very smart person said ^[p. 13] something I agree with"

[[examples]]
input = "A not-so-smart person argued (p. 45) for the opposing view"
output = "A not-so-smart person argued ^[p. 45] for the opposing view"
```

Now you can run the tool like this:

`python -m text_function_by_example example_change_citation.toml`

Which will generate output like this:

```
GENERATED CODE:


import re

def solve(input_string):
    # Define the pattern for parenthetical citations
    pattern = r'\(p\. \d+\)'
    
    # Function to replace each match with Markdown footnote
    def replace_citation(match):
        return '^[' + match.group()[1:-1] + ']'
    
    # Use re.sub to find and replace all occurrences
    output_string = re.sub(pattern, replace_citation, input_string)
    
    return output_string


RUN IT? Type 'trust' to continue:
```

If you type "trust" and hit enter, it will then test the generated code against all your examples, and report any cases where it does not give the expected output.

If all examples succeed, a python script named after the toml file (`example_change_citation.py` in this case) will be created containing the function.
When run, the script will read all input from stdin, invoke the function, and print the result to stdout.

If some examples fail, the script will report the problems to Claude and ask it to fix it.
You'll have to type "trust" again after each iteration (unless you use the `--yolo` argument).
It will give up after 10 retries (use the `--max-fix-attempts` argument to override this.)

## Why?

I also wrote a [Hammerspoon plugin](https://github.com/brokensandals/ClipTransform.spoon/) for executing a script against the contents of the clipboard.
In conjunction, these enable you to quickly create scripts for commonly-performed text manipulations, and use them with the following workflow:

1. Copy input text to clipboard
2. Press hotkey that ClipTransform.spoon is bound to
3. Choose script from fuzzy finder
4. Paste transformed text

## License

This is available as open source under the terms of the [MIT License](https://opensource.org/licenses/MIT).
