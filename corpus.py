from dataclasses import dataclass


CPYTHON_VERSION = "3.11.17"
SOURCE_ROOT = f"https://github.com/python/cpython/blob/v{CPYTHON_VERSION}/Lib/"


@dataclass(frozen=True)
class Probe:
    id: str
    api: str
    title: str
    expression: str
    expected: str
    upstream: str

    @property
    def module(self):
        return self.api.split(".")[0]


PROBES = (
    Probe("json-empty", "json.loads", "Décoder un objet vide", "api('{}')",
          "dict: {}", "test.test_json.test_decode.TestPyDecode.test_empty_objects"),
    Probe("json-whitespace", "json.loads", "Accepter les espaces autour des séparateurs",
          "api('{  \"reponse\"  :  42  }')", "dict: {'reponse': 42}",
          "test.test_json.test_decode.TestPyDecode.test_decoder_optimizations"),
    Probe("json-extra-data", "json.loads", "Rejeter les données après une valeur",
          "api('[1, 2]3')", "exception: json.JSONDecodeError",
          "test.test_json.test_decode.TestPyDecode.test_extra_data"),
    Probe("json-unicode", "json.loads", "Décoder un caractère hors du plan multilingue de base",
          r"ord(api('\"\\ud83d\\ude80\"'))", "int: 128640",
          "test.test_json.test_unicode.TestPyUnicode.test_big_unicode_decode"),
    Probe("json-parse-int", "json.loads", "Convertir les entiers avec parse_int",
          "api('7', parse_int=float)", "float: 7.0",
          "test.test_json.test_decode.TestPyDecode.test_float"),
    Probe("json-separators", "json.dumps", "Choisir les séparateurs de sortie",
          "api({'a': [1, 2]}, separators=(',', ':'))", "str: '{\"a\":[1,2]}'",
          "test.test_json.test_separators.TestPySeparators.test_separators"),
    Probe("struct-pack", "struct.pack", "Encoder un entier en ordre gros-boutiste",
          "api('>H', 0x1234)", "bytes: b'\\x124'", "test.test_struct.StructTest.test_transitiveness"),
    Probe("struct-unpack", "struct.unpack", "Décoder un entier signé en ordre petit-boutiste",
          r"api('<h', b'\xfe\xff')", "tuple: (-2,)", "test.test_struct.StructTest.test_transitiveness"),
    Probe("struct-calcsize", "struct.calcsize", "Compter les octets de remplissage",
          "api('>B3xH')", "int: 6", "test.test_struct.StructTest.test_calcsize"),
    Probe("struct-unpack-from", "struct.unpack_from", "Lire à partir d’un décalage",
          r"api('>H', b'x\x01\x02', 1)", "tuple: (258,)", "test.test_struct.StructTest.test_unpack_from"),
    Probe("struct-invalid-format", "struct.calcsize", "Rejeter un format inconnu",
          "api('Z')", "exception: struct.error", "test.test_struct.StructTest.test_consistence"),
    Probe("struct-iter", "struct.iter_unpack", "Décoder plusieurs enregistrements",
          r"list(api('>H', b'\x00\x01\x00\x02'))", "list: [(1,), (2,)]",
          "test.test_struct.UnpackIteratorTest.test_module_func"),
    Probe("binascii-hex", "binascii.hexlify", "Encoder des octets en hexadécimal",
          r"api(b'\x00\xff')", "bytes: b'00ff'", "test.test_binascii.BinASCIITest.test_hex"),
    Probe("binascii-unhex", "binascii.unhexlify", "Décoder de l’hexadécimal mixte",
          "api('00Ff')", "bytes: b'\\x00\\xff'", "test.test_binascii.BinASCIITest.test_hex"),
    Probe("binascii-odd-hex", "binascii.unhexlify", "Rejeter un chiffre hexadécimal isolé",
          "api('a')", "exception: binascii.Error", "test.test_binascii.BinASCIITest.test_hex"),
    Probe("binascii-base64-decode", "binascii.a2b_base64", "Décoder du Base64 avec remplissage",
          "api(b'YWI=')", "bytes: b'ab'", "test.test_binascii.BinASCIITest.test_base64valid"),
    Probe("binascii-base64-newline", "binascii.b2a_base64", "Désactiver le retour à la ligne en Base64",
          "api(b'ab', newline=False)", "bytes: b'YWI='", "test.test_binascii.BinASCIITest.test_b2a_base64_newline"),
    Probe("binascii-crc32", "binascii.crc32", "Calculer un CRC-32 non signé",
          "api(b'123456789')", "int: 3421780262", "test.test_binascii.BinASCIITest.test_crc32"),
    Probe("binascii-crc-hqx", "binascii.crc_hqx", "Calculer un CRC-16 avec valeur initiale",
          "api(b'123456789', 0xffff)", "int: 10673", "test.test_binascii.BinASCIITest.test_crc_hqx"),
    Probe("math-sqrt", "math.sqrt", "Calculer une racine carrée exacte",
          "api(81)", "float: 9.0", "test.test_math.MathTests.testSqrt"),
    Probe("math-sqrt-negative", "math.sqrt", "Rejeter une racine carrée réelle hors domaine",
          "api(-1)", "exception: ValueError", "test.test_math.MathTests.testSqrt"),
    Probe("math-floor", "math.floor", "Arrondir vers le bas un nombre négatif",
          "api(-1.25)", "int: -2", "test.test_math.MathTests.testFloor"),
    Probe("math-nan", "math.isnan", "Reconnaître un NaN",
          "api(float('nan'))", "bool: True", "test.test_math.MathTests.testIsnan"),
    Probe("math-isclose", "math.isclose", "Utiliser une tolérance absolue près de zéro",
          "api(0.0, 1e-10, abs_tol=1e-9)", "bool: True", "test.test_math.IsCloseTests.test_near_zero"),
    Probe("math-gcd", "math.gcd", "Calculer le PGCD avec un argument négatif",
          "api(-18, 24)", "int: 6", "test.test_math.MathTests.testGcd"),
)


# These individual upstream methods exercise public behavior. JSON's upstream
# fixtures explicitly use the pure-Python backend. The portable probes use the
# default module on every runtime, with no forced backend.
UPSTREAM = {
    "json": (
        "test.test_json.test_decode.TestPyDecode.test_empty_objects",
        "test.test_json.test_decode.TestPyDecode.test_float",
        "test.test_json.test_decode.TestPyDecode.test_object_pairs_hook",
        "test.test_json.test_unicode.TestPyUnicode.test_big_unicode_decode",
        "test.test_json.test_separators.TestPySeparators.test_separators",
    ),
    "struct": (
        "test.test_struct.StructTest.test_calcsize",
        "test.test_struct.StructTest.test_transitiveness",
        "test.test_struct.StructTest.test_unpack_from",
        "test.test_struct.StructTest.test_pack_into",
        "test.test_struct.UnpackIteratorTest.test_module_func",
    ),
    "binascii": (
        "test.test_binascii.BinASCIITest.test_base64valid",
        "test.test_binascii.BinASCIITest.test_hex",
        "test.test_binascii.BinASCIITest.test_crc32",
        "test.test_binascii.BinASCIITest.test_crc_hqx",
        "test.test_binascii.BinASCIITest.test_b2a_base64_newline",
    ),
    "math": (
        "test.test_math.MathTests.testSqrt",
        "test.test_math.MathTests.testFloor",
        "test.test_math.MathTests.testIsnan",
        "test.test_math.MathTests.testGcd",
        "test.test_math.IsCloseTests.test_near_zero",
    ),
}


def source_url(test_id):
    return SOURCE_ROOT + "/".join(test_id.split(".")[:-2]) + ".py"
