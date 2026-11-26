from dataclasses import dataclass
from pathlib import Path


from references import DEFAULT, REFERENCES


# What guarantees the expected result of a shared case:
# - language_spec: the Python language reference.
# - stdlib_spec: the standard library documentation for the reference version.
# - cpython_behavior: observed CPython behavior that the documentation does not promise.
# - optional_capability: an optional module, build feature or platform capability.
# - unclassified: nobody has checked the documentation yet.
CONTRACT_KINDS = ("language_spec", "stdlib_spec", "cpython_behavior", "optional_capability", "unclassified")


@dataclass(frozen=True)
class Probe:
    id: str
    api: str
    title: str
    expression: str
    expected: str
    # An upstream CPython test that checks the same behavior. Every case is
    # written for this dashboard; None means no upstream test checks it.
    upstream: str | None
    setup: str = ""

    @property
    def module(self):
        return self.api.split(".")[0]

    @property
    def contract(self):
        return CONTRACTS.get(self.id, ("unclassified", None))[0]

    def contract_source(self, reference=REFERENCES[DEFAULT]):
        """The paragraph of the reference version's documentation that states the expected result."""
        anchor = CONTRACTS.get(self.id, ("unclassified", None))[1]
        return reference.docs_root + anchor if anchor else None


PROBES = (
    Probe("json-empty", "json.loads", "Decode an empty object", "api('{}')",
          "dict: {}", "test.test_json.test_decode.TestPyDecode.test_empty_objects"),
    Probe("json-whitespace", "json.loads", "Allow whitespace around separators", "api('{  \"reponse\"  :  42  }')", "dict: {'reponse': 42}",
          "test.test_json.test_decode.TestPyDecode.test_decoder_optimizations"),
    Probe("json-extra-data", "json.loads", "Reject extra data after a value", "api('[1, 2]3')", "exception: json.JSONDecodeError",
          "test.test_json.test_decode.TestPyDecode.test_extra_data"),
    Probe("json-unicode", "json.loads", "Decode a character outside the Basic Multilingual Plane",
          r"ord(api('\"\\ud83d\\ude80\"'))", "int: 128640",
          "test.test_json.test_unicode.TestPyUnicode.test_big_unicode_decode"),
    Probe("json-parse-int", "json.loads", "Convert integers with parse_int", "api('7', parse_int=float)", "float: 7.0",
          "test.test_json.test_decode.TestPyDecode.test_float"),
    Probe("json-separators", "json.dumps", "Customize output separators", "api({'a': [1, 2]}, separators=(',', ':'))", "str: '{\"a\":[1,2]}'",
          "test.test_json.test_separators.TestPySeparators.test_separators"),
    Probe("struct-pack", "struct.pack", "Pack a big-endian integer", "api('>H', 0x1234)", "bytes: b'\\x124'", None),
    Probe("struct-unpack", "struct.unpack", "Unpack a signed little-endian integer",
          r"api('<h', b'\xfe\xff')", "tuple: (-2,)", None),
    Probe("struct-calcsize", "struct.calcsize", "Count padding bytes", "api('>B3xH')", "int: 6", None),
    Probe("struct-unpack-from", "struct.unpack_from", "Read from an offset", r"api('>H', b'x\x01\x02', 1)", "tuple: (258,)", "test.test_struct.StructTest.test_unpack_from"),
    Probe("struct-invalid-format", "struct.calcsize", "Reject an unknown format", "api('Z')", "exception: struct.error", "test.test_struct.StructTest.test_consistence"),
    Probe("struct-iter", "struct.iter_unpack", "Unpack multiple records", r"list(api('>H', b'\x00\x01\x00\x02'))", "list: [(1,), (2,)]",
          "test.test_struct.UnpackIteratorTest.test_module_func"),
    Probe("binascii-hex", "binascii.hexlify", "Encode bytes as hexadecimal", r"api(b'\x00\xff')", "bytes: b'00ff'", "test.test_binascii.BinASCIITest.test_hex"),
    Probe("binascii-unhex", "binascii.unhexlify", "Decode mixed-case hexadecimal", "api('00Ff')", "bytes: b'\\x00\\xff'", None),
    Probe("binascii-odd-hex", "binascii.unhexlify", "Reject a single hex digit", "api('a')", "exception: binascii.Error", "test.test_binascii.BinASCIITest.test_hex"),
    Probe("binascii-base64-decode", "binascii.a2b_base64", "Decode padded Base64", "api(b'YWI=')", "bytes: b'ab'", "test.test_binascii.BinASCIITest.test_base64valid"),
    Probe("binascii-base64-newline", "binascii.b2a_base64", "Omit the Base64 trailing newline",
          "api(b'ab', newline=False)", "bytes: b'YWI='", "test.test_binascii.BinASCIITest.test_b2a_base64_newline"),
    Probe("binascii-crc32", "binascii.crc32", "Compute an unsigned CRC-32", "api(b'123456789')", "int: 3421780262", "test.test_binascii.BinASCIITest.test_crc32"),
    Probe("binascii-crc-hqx", "binascii.crc_hqx", "Compute CRC-16 with an initial value",
          "api(b'123456789', 0xffff)", "int: 10673", "test.test_binascii.BinASCIITest.test_crc_hqx"),
    Probe("math-sqrt", "math.sqrt", "Compute an exact square root", "api(81)", "float: 9.0", "test.test_math.MathTests.testSqrt"),
    Probe("math-sqrt-negative", "math.sqrt", "Reject a negative argument to square root",
          "api(-1)", "exception: ValueError", "test.test_math.MathTests.testSqrt"),
    Probe("math-floor", "math.floor", "Round a negative number down", "api(-1.25)", "int: -2", "test.test_math.MathTests.testFloor"),
    Probe("math-nan", "math.isnan", "Identify a NaN", "api(float('nan'))", "bool: True", "test.test_math.MathTests.testIsnan"),
    Probe("math-isclose", "math.isclose", "Use absolute tolerance near zero", "api(0.0, 1e-10, abs_tol=1e-9)", "bool: True", "test.test_math.IsCloseTests.test_near_zero"),
    Probe("math-gcd", "math.gcd", "Compute the GCD with a negative argument", "api(-18, 24)", "int: 6", "test.test_math.MathTests.testGcd"),

    # Regular expressions cover Unicode, capture semantics and control of backtracking.
    Probe("re-atomic", "re.fullmatch", "Do not backtrack into an atomic group",
          "api('(?>ab|a)b', 'ab') is None", "bool: True", "test.test_re.ReTests.test_fullmatch_atomic_grouping"),
    Probe("re-possessive", "re.fullmatch", "Do not give characters back after a possessive quantifier",
          "api('a*+a', 'aaa') is None", "bool: True", "test.test_re.ReTests.test_fullmatch_possessive_quantifiers"),
    Probe("re-unicode-fold", "re.fullmatch", "Apply Unicode case folding to character ranges",
          "api('[A-Z]', 'K', module.IGNORECASE) is not None", "bool: True", "test.test_re.ReTests.test_ignore_case_range"),
    Probe("re-ascii-fold", "re.fullmatch", "Restrict case folding with the ASCII flag",
          "api('[A-Z]', 'K', module.IGNORECASE | module.ASCII) is None", "bool: True", "test.test_re.ReTests.test_ignore_case_range"),
    Probe("re-conditional", "re.fullmatch", "Use a named group in a conditional branch",
          "api('(?P<quote><)?x(?(quote)>|!)', '<x>').groupdict()", "dict: {'quote': '<'}",
          "test.test_re.ReTests.test_re_groupref_exists"),
    Probe("re-lookbehind", "re.compile", "Reject a variable-width lookbehind",
          "api('(?<=a+)b')", "exception: re.error", None),

    # Decimal equality alone would miss changes in exponent, flags and context.
    Probe("decimal-half-even", "decimal.Decimal.quantize", "Round ties to even digits",
          "(str(api(module.Decimal('2.5'), module.Decimal('1'), rounding=module.ROUND_HALF_EVEN)), "
          "str(api(module.Decimal('3.5'), module.Decimal('1'), rounding=module.ROUND_HALF_EVEN)))",
          "tuple: ('2', '4')", None),
    Probe("decimal-context", "decimal.localcontext", "Restore precision after leaving a local context",
          "(inside, module.getcontext().prec == original)", "tuple: ('0.333', True)",
          "test.test_decimal.PyContextWithStatement.test_local_context_kwargs_does_not_overwrite_existing_argument",
          setup="""
              original = module.getcontext().prec
              with api(prec=3):
                  inside = str(module.Decimal(1) / module.Decimal(3))
          """),
    Probe("decimal-trap", "decimal.Context.divide", "Raise an exception for a trapped inexact result",
          "api(context, module.Decimal(1), module.Decimal(3))", "exception: decimal.Inexact",
          None,
          setup="""
              context = module.Context(prec=3)
              context.traps[module.Inexact] = True
          """),
    Probe("decimal-flags", "decimal.Context.divide", "Set flags when division rounds the result",
          "(str(quotient), bool(context.flags[module.Inexact]), bool(context.flags[module.Rounded]))",
          "tuple: ('0.333', True, True)", None,
          setup="""
              context = module.Context(prec=3)
              quotient = api(context, module.Decimal(1), module.Decimal(3))
          """),

    # Validate decoded bytes and stream state, never the compressor's representation.
    Probe("zlib-eof", "zlib.decompressobj", "Detect an incomplete stream until the trailer arrives",
          "(before, decoder.eof, decoded == original)", "tuple: (False, True, True)",
          "test.test_zlib.CompressObjectTestCase.test_decompress_eof_incomplete_stream",
          setup="""
              original = b'python' * 16
              encoded = module.compress(original)
              decoder = api()
              decoded = decoder.decompress(encoded[:-2])
              before = decoder.eof
              decoded += decoder.decompress(encoded[-2:])
          """),
    Probe("zlib-unused", "zlib.decompressobj", "Preserve bytes after a compressed stream",
          "(decoder.decompress(module.compress(b'payload') + b'next'), decoder.unused_data)",
          "tuple: (b'payload', b'next')", "test.test_zlib.CompressObjectTestCase.test_decompress_unused_data",
          setup="decoder = api()"),
    Probe("zlib-max-length", "zlib.decompressobj", "Resume decoding after an output limit",
          "(first, had_tail, len(rest), decoder.eof)", "tuple: (b'ababa', True, 195, True)",
          "test.test_zlib.CompressObjectTestCase.test_decompressmaxlen",
          setup="""
              decoder = api()
              first = decoder.decompress(module.compress(b'ab' * 100), max_length=5)
              tail = decoder.unconsumed_tail
              had_tail = bool(tail)
              rest = decoder.decompress(tail)
          """),
    Probe("zlib-dictionary", "zlib.compressobj", "Decode a stream made with a preset dictionary",
          "(decoder.decompress(encoded), decoder.eof)", "tuple: (b'common prefix: blue', True)",
          "test.test_zlib.CompressObjectTestCase.test_dictionary",
          setup="""
              dictionary = b'common prefix: red and blue and green'
              encoder = api(zdict=dictionary)
              encoded = encoder.compress(b'common prefix: blue') + encoder.flush()
              decoder = module.decompressobj(zdict=dictionary)
          """),
    Probe("zlib-window", "zlib.compress", "Select a gzip wrapper using the window parameter",
          "(encoded[:2], module.decompress(encoded, wbits=31))", "tuple: (b'\\x1f\\x8b', b'output')",
          "test.test_zlib.CompressObjectTestCase.test_wbits",
          setup="encoded = api(b'output', wbits=31)"),

    # SQLite examples use local, in-memory databases.
    Probe("sqlite-rollback", "sqlite3.connect", "Roll back an insert after a commit",
          "(inside, connection.in_transaction, rows)", "tuple: (True, False, [(1,)])",
          "test.test_sqlite3.test_dbapi.ConnectionTests.test_in_transaction",
          setup="""
              connection = api(':memory:')
              connection.execute('create table example (value integer)')
              connection.execute('insert into example values (?)', (1,))
              connection.commit()
              connection.execute('insert into example values (?)', (2,))
              inside = connection.in_transaction
              connection.rollback()
              rows = connection.execute('select value from example').fetchall()
          """),
    Probe("sqlite-binding", "sqlite3.Connection.execute", "Bind named parameters with SQL punctuation in the value",
          "api(connection, 'select :item, :count', {'item': \"it's here\", 'count': 7}).fetchone()",
          "tuple: (\"it's here\", 7)", "test.test_sqlite3.test_dbapi.CursorTests.test_execute_dict_mapping",
          setup="connection = module.connect(':memory:')"),
    Probe("sqlite-row", "sqlite3.Row", "Look up result column names without matching case",
          "(row['label'], row['LABEL'], row[-1], row.keys())", "tuple: ('value', 'value', 4, ['Label', 'count'])",
          "test.test_sqlite3.test_factory.RowFactoryTests.test_sqlite_row_index",
          setup="""
              connection = module.connect(':memory:')
              connection.row_factory = module.Row
              row = connection.execute("select 'value' as Label, 4 as count").fetchone()
          """),
    Probe("sqlite-unique", "sqlite3.Connection.execute", "Raise IntegrityError on a duplicate key",
          "api(connection, 'insert into example values (1)')", "exception: sqlite3.IntegrityError",
          None,
          setup="""
              connection = module.connect(':memory:')
              connection.execute('create table example (value integer unique)')
              connection.execute('insert into example values (1)')
          """),
    Probe("sqlite-blob", "sqlite3.Connection.blobopen", "Write and read bytes at an offset in a blob",
          "raw", "bytes: b'\\x00xy\\x00'", "test.test_sqlite3.test_dbapi.BlobTests.test_blob_write_at_offset",
          setup="""
              connection = module.connect(':memory:')
              connection.execute('create table example (data blob)')
              connection.execute('insert into example values (zeroblob(4))')
              with api(connection, 'example', 'data', 1) as blob:
                  blob.seek(1)
                  blob.write(b'xy')
                  blob.seek(0)
                  raw = blob.read()
          """),
    Probe("sqlite-function", "sqlite3.Connection.create_function", "Register a deterministic SQL function",
          "connection.execute('select triple(4)').fetchone()", "tuple: (12,)",
          "test.test_sqlite3.test_userfunctions.FunctionTests.test_func_deterministic",
          setup="""
              connection = module.connect(':memory:')
              api(connection, 'triple', 1, lambda n: n * 3, deterministic=True)
          """),

    # SSL probes use buffers only and make no network connections.
    Probe("ssl-bio-pending", "ssl.MemoryBIO", "Track pending bytes after a partial read",
          "(bio.pending, bio.read(2), bio.pending, bio.read())", "tuple: (4, b'ab', 2, b'cd')",
          "test.test_ssl.MemoryBIOTests.test_pending", setup="bio = api()\nbio.write(b'abcd')"),
    Probe("ssl-bio-eof", "ssl.MemoryBIO", "Report EOF once read buffers are empty",
          "(bio.eof, bio.read(), bio.eof)", "tuple: (False, b'ab', True)",
          "test.test_ssl.MemoryBIOTests.test_eof",
          setup="bio = api()\nbio.write(b'ab')\nbio.write_eof()"),
    Probe("ssl-client-policy", "ssl.SSLContext", "Enable peer verification and hostname checks for TLS clients",
          "(context.verify_mode == module.CERT_REQUIRED, context.check_hostname)", "tuple: (True, True)",
          "test.test_ssl.ContextTests.test_context_client_server", setup="context = api(module.PROTOCOL_TLS_CLIENT)"),
    Probe("ssl-client-hostname", "ssl.SSLContext.wrap_bio", "Expose the configured hostname on an SSL object",
          "api(context, module.MemoryBIO(), module.MemoryBIO(), server_hostname='example.test').server_hostname",
          "str: 'example.test'", None,
          setup="context = module.SSLContext(module.PROTOCOL_TLS_CLIENT)"),

    Probe("mmap-overlap", "mmap.mmap", "Move overlapping ranges within a memory map",
          "region[:6]", "bytes: b'aabcdf'", "test.test_mmap.MmapTests.test_move",
          setup="region = api(-1, 6)\nregion[:] = b'abcdef'\nregion.move(1, 0, 4)"),
    Probe("mmap-memoryview", "mmap.mmap", "Reject closing a map with an active memory view",
          "region.close()", "exception: BufferError", None,
          setup="region = api(-1, 4)\nview = memoryview(region)"),
    Probe("mmap-slice", "mmap.mmap", "Assign to a strided memory map slice",
          "region[:]", "bytes: b'xbydzf'", "test.test_mmap.MmapTests.test_extended_set_del_slice",
          setup="region = api(-1, 6)\nregion[:] = b'abcdef'\nregion[::2] = b'xyz'"),
    Probe("mmap-seek", "mmap.mmap", "Seek backwards from the end before reading",
          "(region.tell(), region.read(2))", "tuple: (4, b'ef')", "test.test_mmap.MmapTests.test_basic",
          setup="region = api(-1, 6)\nregion[:] = b'abcdef'\nregion.seek(-2, 2)"),

    Probe("codecs-split-utf8", "codecs.getincrementaldecoder", "Decode a Unicode character split across chunks",
          r"(decoder.decode(b'\xe2\x82'), decoder.decode(b'\xac', final=True))", "tuple: ('', '€')",
          "test.test_codecs.UTF8Test.test_partial", setup="decoder = api('utf-8')()"),
    Probe("codecs-truncated-utf8", "codecs.getincrementaldecoder", "Reject a truncated UTF-8 sequence at EOF",
          "decoder.decode(b'', final=True)", "exception: UnicodeDecodeError", None,
          setup=r"""
              decoder = api('utf-8')()
              decoder.decode(b'\xe2\x82')
          """),
    Probe("codecs-surrogateescape", "codecs.decode", "Preserve invalid UTF-8 bytes with surrogateescape",
          r"ord(api(b'\xff', 'utf-8', 'surrogateescape'))", "int: 56575", "test.test_codecs.SurrogateEscapeTest.test_utf8"),
    Probe("codecs-bom", "codecs.getincrementaldecoder", "Consume a UTF-8 BOM split across chunks",
          r"(decoder.decode(b'\xef'), decoder.decode(b'\xbb\xbfA', final=True))", "tuple: ('', 'A')",
          "test.test_codecs.UTF8SigTest.test_partial", setup="decoder = api('utf-8-sig')()"),

    Probe("datetime-offset", "datetime.datetime.fromisoformat", "Preserve a non-hour UTC offset",
          "api('2024-02-29T12:30:15+05:45').isoformat()", "str: '2024-02-29T12:30:15+05:45'",
          "test.datetimetester.TestDateTime.test_fromisoformat_timezone"),
    Probe("datetime-utc", "datetime.datetime.fromisoformat", "Parse the ISO 8601 UTC suffix",
          "api('2024-02-29T12:30:15Z').isoformat()", "str: '2024-02-29T12:30:15+00:00'",
          "test.datetimetester.TestDateTime.test_fromisoformat_datetime_examples"),
    Probe("datetime-invalid-date", "datetime.date.fromisoformat", "Reject an impossible leap-day date",
          "api('2023-02-29')", "exception: ValueError", "test.datetimetester.TestDate.test_fromisoformat_fails"),
    Probe("zoneinfo-fold", "zoneinfo.ZoneInfo.from_file", "Disambiguate the repeated hour at a DST transition",
          "(earlier.isoformat(), later.isoformat(), int(later.timestamp() - earlier.timestamp()))",
          "tuple: ('2021-11-07T01:30:00-04:00', '2021-11-07T01:30:00-05:00', 3600)",
          "test.test_zoneinfo.test_zoneinfo.ZoneInfoTest.test_folds_and_gaps",
          setup=r"""
              from datetime import datetime
              from io import BytesIO
              from struct import pack

              header = b'TZif' + bytes(16) + pack('>6I', 0, 0, 0, 2, 2, 8)
              transitions = pack('>2i2B', 1615705200, 1636264800, 0, 1)
              offsets = pack('>iBBiBB', -14400, 1, 0, -18000, 0, 4)
              zone = api(BytesIO(header + transitions + offsets + b'EDT\0EST\0'), key='Example/Fold')
              earlier = datetime(2021, 11, 7, 1, 30, tzinfo=zone, fold=0)
              later = earlier.replace(fold=1)
          """),

    Probe("csv-multiline", "csv.reader", "Read a quoted field across physical lines",
          "list(api(['\"a\\n', 'b\",c\\n']))", "list: [['a\\nb', 'c']]",
          "test.test_csv.Test_Csv.test_roundtrip_quoteed_newlines"),
    Probe("csv-nul", "csv.reader", "Preserve an embedded null in a CSV field",
          r"list(api(['data\0field,2']))", "list: [['data\\x00field', '2']]", "test.test_csv.Test_Csv.test_read_nul"),
    Probe("csv-strict", "csv.reader", "Reject an unterminated quoted field in strict mode",
          "list(api(['\"unclosed'], strict=True))", "exception: csv.Error", "test.test_csv.Test_Csv.test_read_eof"),
    Probe("csv-restkey", "csv.DictReader", "Collect extra columns under the configured key",
          "list(api(['name', 'item,extra,more'], restkey='rest'))", "list: [{'name': 'item', 'rest': ['extra', 'more']}]",
          "test.test_csv.TestDictFields.test_read_long_with_rest"),

    Probe("itertools-pairwise", "itertools.pairwise", "Return overlapping pairs from a one-shot iterator",
          "list(api(iter([1, 2, 4, 8])))", "list: [(1, 2), (2, 4), (4, 8)]", "test.test_itertools.TestBasicOps.test_pairwise"),
    Probe("itertools-islice", "itertools.islice", "Advance the original iterator to the slice stop",
          "(list(api(items, 2, 7, 3)), next(items))", "tuple: ([2, 5], 7)",
          "test.test_itertools.TestBasicOps.test_islice", setup="items = iter(range(10))"),
    Probe("itertools-accumulate", "itertools.accumulate", "Include the initial value in an empty accumulation",
          "list(api([], initial=9))", "list: [9]", "test.test_itertools.TestBasicOps.test_accumulate"),
    Probe("itertools-groupby", "itertools.groupby", "Keep separate runs of the same group key",
          "[(key, ''.join(values)) for key, values in api('aabba')]", "list: [('a', 'aa'), ('b', 'bb'), ('a', 'a')]",
          "test.test_itertools.TestBasicOps.test_groupby"),

    # Threads must not lose updates, with or without a global lock.
    Probe("threading-append", "threading.Thread", "Append from several threads without losing items",
          "(len(items), sum(items))", "tuple: (40000, 199980000)",
          None,
          setup="""
              items = []

              def work():
                  for number in range(10000):
                      items.append(number)

              threads = [api(target=work) for _ in range(4)]
              for thread in threads:
                  thread.start()
              for thread in threads:
                  thread.join()
          """),
    Probe("threading-lock", "threading.Lock", "Protect a shared counter with a lock",
          "counter[0]", "int: 20000", None,
          setup="""
              lock = api()
              counter = [0]

              def work():
                  for _ in range(5000):
                      with lock:
                          counter[0] += 1

              threads = [module.Thread(target=work) for _ in range(4)]
              for thread in threads:
                  thread.start()
              for thread in threads:
                  thread.join()
          """),
    Probe("threading-local", "threading.local", "Keep thread-local values separate",
          "(state.value, seen)", "tuple: ('main', ['worker'])",
          None,
          setup="""
              state = api()
              state.value = 'main'
              seen = []

              def work():
                  state.value = 'worker'
                  seen.append(state.value)

              thread = module.Thread(target=work)
              thread.start()
              thread.join()
          """),

    Probe("asyncio-taskgroup", "asyncio.TaskGroup", "Wait for every child before leaving a task group",
          "module.run(main())", "tuple: (2, 8)", "test.test_asyncio.test_taskgroups.TestTaskGroup.test_taskgroup_01",
          setup="""
              async def double(n):
                  await module.sleep(0)
                  return n * 2

              async def main():
                  async with api() as tasks:
                      first = tasks.create_task(double(1))
                      second = tasks.create_task(double(4))
                  return first.result(), second.result()
          """),
    Probe("asyncio-cancel-sibling", "asyncio.TaskGroup", "Cancel a sibling when another child raises",
          "module.run(main())", "tuple: (True, True)", "test.test_asyncio.test_taskgroups.TestTaskGroup.test_cancel_children_on_child_error",
          setup="""
              async def main():
                  ready = module.Event()
                  cancelled = False
                  failed = False

                  async def sibling():
                      nonlocal cancelled
                      try:
                          ready.set()
                          await module.Event().wait()
                      finally:
                          cancelled = True

                  async def fail():
                      await ready.wait()
                      raise LookupError('child failed')

                  try:
                      async with api() as tasks:
                          tasks.create_task(sibling())
                          tasks.create_task(fail())
                  except* LookupError:
                      failed = True
                  return failed, cancelled
          """),
    Probe("asyncio-context", "asyncio.TaskGroup", "Pass an explicit context to a child task",
          "module.run(main())", "tuple: ('child', 'parent')",
          "test.test_asyncio.test_taskgroups.TestTaskGroup.test_taskgroup_task_context",
          setup="""
              from contextvars import Context, ContextVar
              label = ContextVar('label', default='parent')

              async def read():
                  return label.get()

              async def main():
                  context = Context()
                  context.run(label.set, 'child')
                  async with api() as tasks:
                      child = tasks.create_task(read(), context=context)
                  return child.result(), label.get()
          """),
)


# Documentation that states each expected result, relative to the library documentation root. A case
# stays unclassified when the documentation is silent or ambiguous about it.
CONTRACTS = {
    "json-empty": ("stdlib_spec", "json.html#json-to-py-table"),
    "json-whitespace": ("stdlib_spec", "json.html#standard-compliance-and-interoperability"),
    "json-extra-data": ("stdlib_spec", "json.html#json.loads"),
    "json-unicode": ("stdlib_spec", "json.html#standard-compliance-and-interoperability"),
    "json-parse-int": ("stdlib_spec", "json.html#json.load"),
    "json-separators": ("stdlib_spec", "json.html#json.dump"),
    "struct-pack": ("stdlib_spec", "struct.html#byte-order-size-and-alignment"),
    "struct-unpack": ("stdlib_spec", "struct.html#byte-order-size-and-alignment"),
    "struct-calcsize": ("stdlib_spec", "struct.html#format-characters"),
    "struct-unpack-from": ("stdlib_spec", "struct.html#struct.unpack_from"),
    # struct.error is documented as raised "on various occasions", not for unknown codes.
    "struct-invalid-format": ("unclassified", None),
    "struct-iter": ("stdlib_spec", "struct.html#struct.iter_unpack"),
    "binascii-hex": ("stdlib_spec", "binascii.html#binascii.hexlify"),
    "binascii-unhex": ("stdlib_spec", "binascii.html#binascii.unhexlify"),
    "binascii-odd-hex": ("stdlib_spec", "binascii.html#binascii.unhexlify"),
    "binascii-base64-decode": ("stdlib_spec", "binascii.html#binascii.a2b_base64"),
    "binascii-base64-newline": ("stdlib_spec", "binascii.html#binascii.b2a_base64"),
    "binascii-crc32": ("stdlib_spec", "binascii.html#binascii.crc32"),
    "binascii-crc-hqx": ("stdlib_spec", "binascii.html#binascii.crc_hqx"),
    "math-sqrt": ("stdlib_spec", "math.html#math.sqrt"),
    "math-sqrt-negative": ("stdlib_spec", "math.html#special-functions"),
    "math-floor": ("stdlib_spec", "math.html#math.floor"),
    "math-nan": ("stdlib_spec", "math.html#math.isnan"),
    "math-isclose": ("stdlib_spec", "math.html#math.isclose"),
    "math-gcd": ("stdlib_spec", "math.html#math.gcd"),
    "re-atomic": ("stdlib_spec", "re.html#regular-expression-syntax"),
    "re-possessive": ("stdlib_spec", "re.html#regular-expression-syntax"),
    "re-unicode-fold": ("stdlib_spec", "re.html#re.IGNORECASE"),
    "re-ascii-fold": ("stdlib_spec", "re.html#re.IGNORECASE"),
    "re-conditional": ("stdlib_spec", "re.html#regular-expression-syntax"),
    "re-lookbehind": ("stdlib_spec", "re.html#regular-expression-syntax"),
    "decimal-half-even": ("stdlib_spec", "decimal.html#decimal.Decimal.quantize"),
    "decimal-context": ("stdlib_spec", "decimal.html#decimal.localcontext"),
    "decimal-trap": ("stdlib_spec", "decimal.html#signals"),
    "decimal-flags": ("stdlib_spec", "decimal.html#signals"),
    "zlib-eof": ("stdlib_spec", "zlib.html#zlib.Decompress.eof"),
    "zlib-unused": ("stdlib_spec", "zlib.html#zlib.Decompress.unused_data"),
    "zlib-max-length": ("stdlib_spec", "zlib.html#zlib.Decompress.decompress"),
    "zlib-dictionary": ("stdlib_spec", "zlib.html#zlib.compressobj"),
    "zlib-window": ("stdlib_spec", "zlib.html#zlib.compressobj"),
    "sqlite-rollback": ("stdlib_spec", "sqlite3.html#sqlite3.Connection.in_transaction"),
    "sqlite-binding": ("stdlib_spec", "sqlite3.html#sqlite3-placeholders"),
    "sqlite-row": ("stdlib_spec", "sqlite3.html#sqlite3.Row"),
    "sqlite-unique": ("stdlib_spec", "sqlite3.html#sqlite3.IntegrityError"),
    "sqlite-blob": ("stdlib_spec", "sqlite3.html#sqlite3.Connection.blobopen"),
    "sqlite-function": ("stdlib_spec", "sqlite3.html#sqlite3.Connection.create_function"),
    "ssl-bio-pending": ("stdlib_spec", "ssl.html#ssl.MemoryBIO.pending"),
    "ssl-bio-eof": ("stdlib_spec", "ssl.html#ssl.MemoryBIO.eof"),
    "ssl-client-policy": ("stdlib_spec", "ssl.html#ssl.PROTOCOL_TLS_CLIENT"),
    "ssl-client-hostname": ("stdlib_spec", "ssl.html#ssl.SSLObject"),
    # mmap.move() is documented as a copy, without saying how overlapping ranges behave.
    "mmap-overlap": ("cpython_behavior", None),
    # mmap.close() documents ValueError for later calls, not BufferError for exported buffers.
    "mmap-memoryview": ("cpython_behavior", None),
    "mmap-slice": ("stdlib_spec", "mmap.html#module-mmap"),
    "mmap-seek": ("stdlib_spec", "mmap.html#mmap.mmap.seek"),
    "codecs-split-utf8": ("stdlib_spec", "codecs.html#codecs.IncrementalDecoder.decode"),
    "codecs-truncated-utf8": ("stdlib_spec", "codecs.html#codecs.IncrementalDecoder.decode"),
    "codecs-surrogateescape": ("stdlib_spec", "codecs.html#error-handlers"),
    "codecs-bom": ("stdlib_spec", "codecs.html#encodings-and-unicode"),
    "datetime-offset": ("stdlib_spec", "datetime.html#datetime.datetime.fromisoformat"),
    "datetime-utc": ("stdlib_spec", "datetime.html#datetime.datetime.fromisoformat"),
    "datetime-invalid-date": ("stdlib_spec", "datetime.html#datetime.date.fromisoformat"),
    "zoneinfo-fold": ("stdlib_spec", "zoneinfo.html#using-zoneinfo"),
    "csv-multiline": ("stdlib_spec", "csv.html#csv.reader"),
    # The csv documentation does not mention NUL characters in fields.
    "csv-nul": ("unclassified", None),
    "csv-strict": ("stdlib_spec", "csv.html#csv.Dialect.strict"),
    "csv-restkey": ("stdlib_spec", "csv.html#csv.DictReader"),
    "itertools-pairwise": ("stdlib_spec", "itertools.html#itertools.pairwise"),
    # The documentation does not say how far islice() advances the source iterator.
    "itertools-islice": ("unclassified", None),
    "itertools-accumulate": ("stdlib_spec", "itertools.html#itertools.accumulate"),
    "itertools-groupby": ("stdlib_spec", "itertools.html#itertools.groupby"),
    # Python 3.12 documents no thread safety for list.append().
    "threading-append": ("cpython_behavior", None),
    "threading-lock": ("stdlib_spec", "threading.html#lock-objects"),
    "threading-local": ("stdlib_spec", "threading.html#thread-local-data"),
    "asyncio-taskgroup": ("stdlib_spec", "asyncio-task.html#task-groups"),
    "asyncio-cancel-sibling": ("stdlib_spec", "asyncio-task.html#task-groups"),
    "asyncio-context": ("stdlib_spec", "asyncio-task.html#asyncio.TaskGroup.create_task"),
}


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
    "re": (
        "test.test_re.ReTests.test_fullmatch_atomic_grouping",
        "test.test_re.ReTests.test_fullmatch_possessive_quantifiers",
        "test.test_re.ReTests.test_ignore_case_range",
        "test.test_re.ReTests.test_re_groupref_exists",
        "test.test_re.ReTests.test_lookbehind",
    ),
    "decimal": (
        "test.test_decimal.PyContextAPItests.test_quantize",
        "test.test_decimal.PyContextWithStatement.test_nested_with_statements",
        "test.test_decimal.PyContextWithStatement.test_local_context_kwargs_does_not_overwrite_existing_argument",
        "test.test_decimal.PyExplicitConstructionTest.test_explicit_from_float",
    ),
    "zlib": (
        "test.test_zlib.CompressObjectTestCase.test_decompress_eof_incomplete_stream",
        "test.test_zlib.CompressObjectTestCase.test_decompress_unused_data",
        "test.test_zlib.CompressObjectTestCase.test_decompressmaxlen",
        "test.test_zlib.CompressObjectTestCase.test_dictionary_streaming",
    ),
    "sqlite3": (
        "test.test_sqlite3.test_factory.RowFactoryTests.test_sqlite_row_as_dict",
        "test.test_sqlite3.test_factory.RowFactoryTests.test_sqlite_row_index_unicode",
        "test.test_sqlite3.test_factory.RowFactoryTests.test_sqlite_row_slice",
        "test.test_sqlite3.test_backup.BackupTests.test_simple",
        "test.test_sqlite3.test_backup.BackupTests.test_progress",
    ),
    "ssl": (
        "test.test_ssl.MemoryBIOTests.test_pending",
        "test.test_ssl.MemoryBIOTests.test_eof",
        "test.test_ssl.ContextTests.test_context_client_server",
        "test.test_ssl.MemoryBIOTests.test_buffer_types",
    ),
    "mmap": (
        "test.test_mmap.MmapTests.test_move",
        "test.test_mmap.MmapTests.test_extended_getslice",
        "test.test_mmap.MmapTests.test_extended_set_del_slice",
        "test.test_mmap.MmapTests.test_context_manager",
    ),
    "codecs": (
        "test.test_codecs.UTF8Test.test_partial",
        "test.test_codecs.UTF8Test.test_decode_error",
        "test.test_codecs.SurrogateEscapeTest.test_utf8",
        "test.test_codecs.UTF8SigTest.test_partial",
    ),
    "datetime": (
        "test.datetimetester.TestDateTime.test_fromisoformat_timezone",
        "test.datetimetester.TestDateTime.test_fromisoformat_utc",
        "test.datetimetester.TestDate.test_fromisoformat_fails",
    ),
    "csv": (
        "test.test_csv.Test_Csv.test_roundtrip_quoteed_newlines",
        "test.test_csv.Test_Csv.test_read_nul",
        "test.test_csv.Test_Csv.test_read_eof",
        "test.test_csv.TestDictFields.test_read_long_with_rest",
    ),
    "itertools": (
        "test.test_itertools.TestBasicOps.test_pairwise",
        "test.test_itertools.TestBasicOps.test_islice",
        "test.test_itertools.TestExamples.test_accumulate",
        "test.test_itertools.TestExamples.test_groupby",
    ),
    "asyncio": (
        "test.test_asyncio.test_taskgroups.TestTaskGroup.test_taskgroup_01",
        "test.test_asyncio.test_taskgroups.TestTaskGroup.test_cancel_children_on_child_error",
        "test.test_asyncio.test_taskgroups.TestTaskGroup.test_taskgroup_task_context",
    ),
}


def test_location(test_id):
    """Split a test id into the source file path, relative to Lib/, and the class and method names."""
    parts = test_id.split(".")
    return "/".join(parts[:-2]) + ".py", parts[-2], parts[-1]


def test_line(test_id, lib):
    """Line of the test method in an extracted Lib directory, following base classes
    defined in the same file. None when the method is defined elsewhere."""
    import ast
    path, cls, method = test_location(test_id)
    try:
        tree = ast.parse((Path(lib) / path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    classes = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    pending, seen = [cls], set()
    while pending:
        name = pending.pop(0)
        if name in seen or name not in classes:
            continue
        seen.add(name)
        for item in classes[name].body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method:
                return item.lineno
        pending.extend(base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
                       for base in classes[name].bases)
    return None


def source_url(test_id, lib=None, reference=REFERENCES[DEFAULT]):
    """Immutable link to an upstream test: the release tag, and the method line when known."""
    if test_id is None:
        return None
    path = test_location(test_id)[0]
    line = test_line(test_id, lib) if lib else None
    return reference.source_root + path + (f"#L{line}" if line else "")
