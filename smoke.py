"""Small functional checks run after a package imports.

Importing a package proves little about native code: a wheel can import and still
fail on its first real call. Each check exercises the package's core feature with
fixed inputs and asserts the result. Checks use no network, no credentials and no
files outside memory or a temporary directory, and they must hold for the release
pinned in every ranking. A package without a check is reported as import-only.
"""

SMOKE = {
    # Native extensions first: their import says the least.
    "numpy": """
import numpy as np
matrix = np.arange(6, dtype=np.float64).reshape(2, 3)
assert (matrix @ matrix.T).tolist() == [[5.0, 14.0], [14.0, 50.0]]
assert np.linalg.solve([[3.0, 1.0], [1.0, 2.0]], [9.0, 8.0]).round(9).tolist() == [2.0, 3.0]
""",
    "pandas": """
import pandas as pd
frame = pd.DataFrame({"team": ["a", "b", "a"], "score": [1, 2, 3]})
assert frame.groupby("team")["score"].sum().to_dict() == {"a": 4, "b": 2}
assert frame.sort_values("score", ascending=False)["team"].tolist() == ["a", "b", "a"]
""",
    "cryptography": """
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
key = Fernet.generate_key()
assert Fernet(key).decrypt(Fernet(key).encrypt(b"conformity")) == b"conformity"
digest = hashes.Hash(hashes.SHA256())
digest.update(b"abc")
assert digest.finalize().hex() == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
""",
    "pyyaml": """
import yaml
loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
assert yaml.load("a: [1, 2]\\nb: {c: true}", Loader=loader) == {"a": [1, 2], "b": {"c": True}}
assert yaml.safe_dump({"x": [1, "y"]}) == "x:\\n- 1\\n- y\\n"
""",
    "cffi": """
import cffi
ffi = cffi.FFI()
numbers = ffi.new("int[]", [1, 2, 3])
assert sum(numbers) == 6
assert ffi.sizeof("int32_t") == 4
assert ffi.string(ffi.new("char[]", b"conformity")) == b"conformity"
""",
    "pydantic-core": """
from pydantic_core import SchemaValidator, ValidationError, core_schema
validator = SchemaValidator(core_schema.int_schema())
assert validator.validate_python("5") == 5
try:
    validator.validate_python("five")
except ValidationError:
    pass
else:
    raise AssertionError("invalid input accepted")
""",
    "pydantic": """
from pydantic import BaseModel, ValidationError

class Item(BaseModel):
    name: str
    count: int

assert Item(name="a", count="3").count == 3
try:
    Item(name="a", count="three")
except ValidationError as error:
    assert error.errors()[0]["loc"] == ("count",)
else:
    raise AssertionError("invalid input accepted")
""",
    "markupsafe": """
from markupsafe import Markup, escape
assert str(escape("<a href='x'>&</a>")) == "&lt;a href=&#39;x&#39;&gt;&amp;&lt;/a&gt;"
assert str(Markup("<b>%s</b>") % "<i>") == "<b>&lt;i&gt;</b>"
""",
    "pillow": """
from io import BytesIO
from PIL import Image
image = Image.new("RGB", (4, 3), (255, 0, 0))
buffer = BytesIO()
image.save(buffer, "PNG")
again = Image.open(BytesIO(buffer.getvalue()))
assert again.size == (4, 3)
assert again.convert("RGB").getpixel((1, 1)) == (255, 0, 0)
""",
    "rpds-py": """
from rpds import HashTrieMap, List
mapping = HashTrieMap({"a": 1}).insert("b", 2)
assert mapping["b"] == 2 and len(mapping) == 2 and "b" not in HashTrieMap({"a": 1})
assert list(List([1, 2]).push_front(0)) == [0, 1, 2]
""",
    "charset-normalizer": """
from charset_normalizer import from_bytes
text = "Les élèves étaient très contents de déjeuner à côté de la forêt."
best = from_bytes(text.encode("utf_8")).best()
assert best is not None and str(best) == text
""",
    "protobuf": """
from google.protobuf import struct_pb2
message = struct_pb2.Struct()
message.update({"name": "conformity", "ratio": 1.5})
again = struct_pb2.Struct.FromString(message.SerializeToString())
assert again["name"] == "conformity" and again["ratio"] == 1.5
""",
    # Pure-Python packages with a core feature worth checking.
    "jinja2": """
from jinja2 import Environment
template = Environment(autoescape=True).from_string("{% for x in items %}{{ x }};{% endfor %}")
assert template.render(items=["<b>", 2]) == "&lt;b&gt;;2;"
""",
    "requests": """
import requests
prepared = requests.Request("GET", "https://example.test/a", params={"q": "x y"}).prepare()
assert prepared.url == "https://example.test/a?q=x+y"
""",
    "urllib3": """
from urllib3.util import parse_url
url = parse_url("https://user@host.test:8443/path?q=1")
assert (url.host, url.port, url.path, url.query) == ("host.test", 8443, "/path", "q=1")
""",
    "idna": """
import idna
assert idna.encode("bücher.example") == b"xn--bcher-kva.example"
assert idna.decode(b"xn--bcher-kva.example") == "bücher.example"
""",
    "certifi": """
import certifi
with open(certifi.where(), encoding="ascii") as bundle:
    assert bundle.read().count("BEGIN CERTIFICATE") > 50
""",
    "packaging": """
from packaging.specifiers import SpecifierSet
from packaging.version import Version
assert Version("1.10") > Version("1.9")
assert "1.4" in SpecifierSet(">=1.2,<2") and "2.0" not in SpecifierSet(">=1.2,<2")
""",
    "python-dateutil": """
from datetime import date
from dateutil.relativedelta import relativedelta
assert date(2024, 1, 31) + relativedelta(months=1) == date(2024, 2, 29)
""",
    "click": """
import click
from click.testing import CliRunner

@click.command()
@click.option("--count", type=int)
def double(count):
    click.echo(count * 2)

assert CliRunner().invoke(double, ["--count", "21"]).output == "42\\n"
""",
    "attrs": """
import attrs

@attrs.define
class Point:
    x: int
    y: int = 0

assert Point(1) == Point(1, 0) and attrs.asdict(Point(2, 3)) == {"x": 2, "y": 3}
""",
    "pyjwt": """
import jwt
secret = "a-secret-key-long-enough-for-hs256!!"
token = jwt.encode({"sub": "conformity"}, secret, algorithm="HS256")
assert jwt.decode(token, secret, algorithms=["HS256"]) == {"sub": "conformity"}
""",
    "pygments": """
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer
assert '<span class="k">def</span>' in highlight("def f(): pass", PythonLexer(), HtmlFormatter())
""",
    "pycparser": """
from pycparser import c_parser
tree = c_parser.CParser().parse("int add(int a, int b) { return a + b; }")
assert tree.ext[0].decl.name == "add"
""",
    "jsonschema": """
import jsonschema
schema = {"type": "object", "properties": {"count": {"type": "integer"}}, "required": ["count"]}
jsonschema.validate({"count": 1}, schema)
try:
    jsonschema.validate({"count": "one"}, schema)
except jsonschema.ValidationError:
    pass
else:
    raise AssertionError("invalid document accepted")
""",
    "h11": """
import h11
connection = h11.Connection(h11.CLIENT)
data = connection.send(h11.Request(method="GET", target="/", headers=[("Host", "example.test")]))
assert data.startswith(b"GET / HTTP/1.1\\r\\n")
""",
    "anyio": """
import anyio

async def main():
    await anyio.sleep(0)
    return 7

assert anyio.run(main) == 7
""",
    "httpx": """
import httpx
transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"path": request.url.path}))
with httpx.Client(transport=transport) as client:
    assert client.get("https://example.test/x").json() == {"path": "/x"}
""",
    "python-dotenv": """
from io import StringIO
from dotenv import dotenv_values
assert dotenv_values(stream=StringIO("A=1\\nB='x y'\\n")) == {"A": "1", "B": "x y"}
""",
    "pathspec": """
import pathspec
spec = pathspec.PathSpec.from_lines("gitwildmatch", ["*.py", "!keep.py"])
assert spec.match_file("a/b.py") and not spec.match_file("keep.py") and not spec.match_file("a.txt")
""",
    "filelock": """
import os
import tempfile
from filelock import FileLock
path = os.path.join(tempfile.mkdtemp(), "conformity.lock")
with FileLock(path) as lock:
    assert lock.is_locked
assert not lock.is_locked
""",
    "tzdata": """
from importlib.resources import files
assert (files("tzdata") / "zoneinfo" / "Europe" / "Paris").read_bytes().startswith(b"TZif")
""",
}
