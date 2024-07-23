from anthropic import Anthropic
from pathlib import Path
import tomllib
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import List
from jinja2 import Environment, PackageLoader
import re
import stat
import argparse
import sys
import textwrap


jinja_env = Environment(loader=PackageLoader("text_function_by_example"), autoescape=False, trim_blocks=True)
prompt_template = jinja_env.get_template("prompt.txt")
wrapper_script_template = jinja_env.get_template("wrapper_script.py")


@dataclass_json
@dataclass
class Example:
    input: str
    output: str


@dataclass_json
@dataclass
class FuncSpec:
    description: str | None = None
    examples: List[Example] = field(default_factory=list)


@dataclass
class GenerationResult:
    thinking: str | None = None
    code: str | None = None


def load_func_spec(path: Path) -> FuncSpec:
    return FuncSpec.from_dict(tomllib.loads(path.read_text("utf8")))


def build_prompt(funcspec: FuncSpec) -> str:
    return prompt_template.render(funcspec=funcspec)


def unescape_xml(text: str) -> str:
    return text.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')


def extract_tag(text: str, tag: str) -> str:
    regex = f"<{tag}>(.*?)</{tag}>"
    return re.search(regex, text, re.DOTALL).group(1)


def generate_code_anthropic(funcspec: FuncSpec, anthropic: Anthropic = None, messages_opts: dict | None = None) -> GenerationResult:
    if anthropic is None:
        anthropic = Anthropic()
    messages_opts = dict(messages_opts or {})
    if not messages_opts.get("model"):
        messages_opts['model'] = "claude-3-5-sonnet-20240620"
    if not messages_opts.get("max_tokens"):
        messages_opts["max_tokens"] = 4096
    prompt = build_prompt(funcspec)
    messages_opts["messages"] = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt}
            ]
        }
    ]
    message = anthropic.messages.create(**messages_opts)
    message_text = "".join(c.text for c in message.content if c.type == "text")
    return GenerationResult(
        thinking=unescape_xml(extract_tag(message_text, "thinking")),
        code=unescape_xml(extract_tag(message_text, "code"))
    )


@dataclass
class ValidationFailure:
    input: str
    expected: str
    actual: str | None = None
    error: Exception | None = None


def validate_code(funcspec: FuncSpec, code: str) -> List[ValidationFailure]:
    failures = []
    for example in funcspec.examples:
        ctx = {}
        try:
            exec(code, ctx)
            if "solve" not in ctx:
                raise ValueError("The code did not define a solve function.")
            actual = ctx["solve"](example.input)
            if actual != example.output:
                failures.append(ValidationFailure(input=example.input, expected=example.output, actual=actual))
        except Exception as ex:
            failures.append(ValidationFailure(input=example.input, expected=example.output, error=ex))
    return failures


def create_wrapper_script(path: Path, code: str) -> None:
    path.write_text(wrapper_script_template.render(code=code), "utf8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC) # https://stackoverflow.com/a/56049405


def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str, help="Path to function specification toml file.")
    parser.add_argument("--yolo", action="store_true", help="Run LLM-generated code without asking user to review it first.")
    args = parser.parse_args(argv[1:])
    toml_path = Path(args.path)
    funcspec = load_func_spec(toml_path)
    genresult = generate_code_anthropic(funcspec)
    print(f"GENERATED CODE:\n\n{genresult.code}\n")
    if not args.yolo:
        ok = input("RUN IT? Type 'trust' to continue: ")
        if ok != "trust":
            sys.exit(1)
    failures = validate_code(funcspec, genresult.code)
    if failures:
        print(f"{len(failures)} EXAMPLES FAILED!")
        for idx, failure in enumerate(failures):
            print(f"Failure {idx}:")
            print(f"\tInput:")
            print(textwrap.indent(failure.input, "\t\t"))
            print(f"\tExpected:")
            print(textwrap.indent(failure.expected, "\t\t"))
            if failure.actual:
                print(f"\tActual:")
                print(textwrap.indent(failure.actual, "\t\t"))
            if failure.error:
                print(f"\tError:")
                print(textwrap.indent(str(failure.error), "\t\t"))
        sys.exit(2)
    py_path = toml_path.parent.joinpath(f"{toml_path.stem}.py")
    create_wrapper_script(py_path, genresult.code)
