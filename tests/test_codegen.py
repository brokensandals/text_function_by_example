import unittest
from text_function_by_example.codegen import load_func_spec, FuncSpec, Example, build_prompt, unescape_xml, extract_tag, generate_code_anthropic, validate_code, ValidationFailure
from pathlib import Path
from textwrap import dedent


EXAMPLE_LOWERCASE_PATH = Path(__file__).parent.joinpath("example_lowercase.toml")


class TestCodegen(unittest.TestCase):
    maxDiff = None

    def test_load_func_spec(self):
        expected = FuncSpec(
            description="Convert the string to lowercase.",
            examples=[
                Example(input="Hello world!", output="hello world!"),
                Example(input="Only You Can Prevent Forest Fires", output="only you can prevent forest fires")
            ]
        )
        actual = load_func_spec(EXAMPLE_LOWERCASE_PATH)
        self.assertEqual(actual, expected)
    
    def test_build_prompt(self):
        expected = dedent('''
                             Your goal is to implement a particular function with Python code.
                             Here is a description of the function: <description>Convert the string to lowercase.</description>
                             The following examples show the correct output for various inputs:
                             <example>
                                 <input>Hello world!</input>
                                 <output>hello world!</output>
                             </example>
                             <example>
                                 <input>Only You Can Prevent Forest Fires</input>
                                 <output>only you can prevent forest fires</output>
                             </example>
                             Please make your best guess what the function is intended to do even if you do not have sufficient information.
                             Think step-by-step and put your thought process in a <thinking> tag.
                             Write the Python code in a <code> tag. Escape any '<', '>', or '&' characters in the code using '&lt;', '&gt;', and '&amp;' respectively.
                             The primary function in the Python code should be named 'solve', should take a single string parameter as input, and should return a string.
                             The Python code should only use built-in Python libraries.
                          ''').strip()
        actual = build_prompt(load_func_spec(EXAMPLE_LOWERCASE_PATH))
        self.assertEqual(actual, expected)
    
    def test_build_prompt_no_description(self):
        expected = dedent('''
                             Your goal is to implement a particular function with Python code.
                             The following examples show the correct output for various inputs:
                             <example>
                                 <input>Hello world!</input>
                                 <output>hello world!</output>
                             </example>
                             <example>
                                 <input>Only You Can Prevent Forest Fires</input>
                                 <output>only you can prevent forest fires</output>
                             </example>
                             Please make your best guess what the function is intended to do even if you do not have sufficient information.
                             Think step-by-step and put your thought process in a <thinking> tag.
                             Write the Python code in a <code> tag. Escape any '<', '>', or '&' characters in the code using '&lt;', '&gt;', and '&amp;' respectively.
                             The primary function in the Python code should be named 'solve', should take a single string parameter as input, and should return a string.
                             The Python code should only use built-in Python libraries.
                          ''').strip()
        funcspec = load_func_spec(EXAMPLE_LOWERCASE_PATH)
        funcspec.description = None
        actual = build_prompt(funcspec)
        self.assertEqual(actual, expected)
        
    def test_build_prompt_no_examples(self):
        expected = dedent('''
                             Your goal is to implement a particular function with Python code.
                             Here is a description of the function: <description>Convert the string to lowercase.</description>
                             Please make your best guess what the function is intended to do even if you do not have sufficient information.
                             Think step-by-step and put your thought process in a <thinking> tag.
                             Write the Python code in a <code> tag. Escape any '<', '>', or '&' characters in the code using '&lt;', '&gt;', and '&amp;' respectively.
                             The primary function in the Python code should be named 'solve', should take a single string parameter as input, and should return a string.
                             The Python code should only use built-in Python libraries.
                          ''').strip()
        funcspec = load_func_spec(EXAMPLE_LOWERCASE_PATH)
        funcspec.examples = []
        actual = build_prompt(funcspec)
        self.assertEqual(actual, expected)
    
    def test_unescape_xml(self):
        original = "&lt;foo&gt;&amp;"
        self.assertEqual(unescape_xml(original), "<foo>&")
    
    def test_extract_tag(self):
        text = dedent('''
                         <thinking>
                           Hmm, well, let's see.
                           I don't know so I'll just make something up.
                         </thinking>
                         <code>
                           if __name__ == "__main__":
                             print(True)
                         </code>
                      ''').strip()
        self.assertEqual(extract_tag(text, "thinking"), "\n  Hmm, well, let's see.\n  I don't know so I'll just make something up.\n")
        self.assertEqual(extract_tag(text, "code"), "\n  if __name__ == \"__main__\":\n    print(True)\n")
    
    @unittest.skip("this costs money and time")
    def test_generate_code_anthropic(self):
        result = generate_code_anthropic(load_func_spec(EXAMPLE_LOWERCASE_PATH))
        print("Chain of thought:")
        print(result.thinking)
        print("Code:")
        print(result.code)
        self.assertIn("def solve(", result.code)
    
    def test_validate_code_successful(self):
        code = "def solve(s):\n    return s.lower()"
        funcspec = load_func_spec(EXAMPLE_LOWERCASE_PATH)
        self.assertEqual(validate_code(funcspec, code), [])
    
    def test_validate_code_no_function(self):
        code = "a = 3 + 4"
        funcspec = load_func_spec(EXAMPLE_LOWERCASE_PATH)
        failures = validate_code(funcspec, code)
        self.assertEqual(str(failures[0].error), "The code did not define a solve function.")
    
    def test_validate_code_error(self):
        code = "def solve(s):\n    raise ValueError('no')"
        funcspec = load_func_spec(EXAMPLE_LOWERCASE_PATH)
        failures = validate_code(funcspec, code)
        self.assertEqual(str(failures[0].error), "no")
    
    def test_validate_code_failure(self):
        code = "def solve(s):\n    return s.lower()"
        funcspec = load_func_spec(EXAMPLE_LOWERCASE_PATH)
        expected = funcspec.examples[1].output
        funcspec.examples[1].output = "BOGUS"
        failures = validate_code(funcspec, code)
        self.assertEqual(failures[0], ValidationFailure(input=funcspec.examples[1].input, expected="BOGUS", actual=expected))


if __name__ == '__main__':
    unittest.main()