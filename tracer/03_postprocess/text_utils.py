import traceback
import re


def get_real_text(val, lang, verbose=False, return_new_i=False):
    opener = "{"
    closer = "}"
    items = val
    try:
        if val.startswith(opener):
            items = []
            if val.startswith('"'):
                i = 2
            else:
                i = 1
            item = None
            item_start = i
            ignore_next_character = False
            inside_string = False
            while True:
                if val[i] == "\\":
                    ignore_next_character = True
                    i += 1
                    continue
                if ignore_next_character:
                    ignore_next_character = False
                    continue

                if val[i] == ",":
                    if item is None:
                        items.append(val[item_start:i])
                    else:
                        items.append(item)
                        item = None
                    i += 1
                    while val[i].isspace():
                        i += 1
                    item_start = i
                elif val[i] == '"':
                    inside_string = not inside_string
                    i += 1
                elif val[i] == "=" and not inside_string:
                    # we are in a dict object - return the original string
                    return val
                elif val[i] == opener and not inside_string:
                    child_val, new_i = get_real_text(
                        val[i:], lang, verbose=verbose, return_new_i=True
                    )
                    if child_val in ("malformed", "error"):
                        return child_val
                    else:
                        i += new_i
                        item = child_val
                elif val[i] == closer and not inside_string:
                    if item is None:
                        if item_start != i:
                            items.append(val[item_start:i])
                    else:
                        items.append(item)
                    i += 1
                    break
                else:
                    i += 1
    except IndexError:
        if return_new_i:
            return "malformed", i
        else:
            return "malformed"
    except Exception:
        if verbose:
            traceback.print_exc()
        if return_new_i:
            return "error", i
        else:
            return "error"
    if return_new_i:
        return items, i
    else:
        return items


def test_get_real_text():
    print(get_real_text("foo", "c", True))
    print(get_real_text("foo{, , }", "c", True))
    print(get_real_text("{}", "c", True))
    print(get_real_text("{1, 2}", "c", True))
    print(get_real_text('{"foo", "boo"}', "c", True))
    print(get_real_text('{"foo", "boo"', "c", True))
    print(get_real_text('{"foo", ""boo"}', "c", True))
    print(get_real_text('{"foo", {"boo", "goo"}}', "c", True))
    print(get_real_text('{"printed\\n", 2}', "c", True))
    print(get_real_text("[0, 0, 0]", "java", True))
    print(get_real_text('"[[0, 2], [1]]"', "java", True))
    print(get_real_text('{"x = 0"}', "cpp", True))
    print(get_real_text("{x = 0}", "cpp", True))


def get_delta(name, old_value, new_value):
    if not isinstance(old_value, list) and isinstance(new_value, list):
        return None
    statements = []
    for i in range(max(len(old_value), len(new_value))):
        if i >= len(old_value):
            # TODO: New var?
            statements.append((f"{name}[{i}]", new_value[i]))
            continue
        if i >= len(new_value):
            statements.append((f"{name}[{i}]", "deleted"))
            continue

        if old_value[i] != new_value[i]:
            statements.append((f"{name}[{i}]", new_value[i]))
    return statements


def test_get_delta():
    print("* modify A[1]")
    print(get_delta("A", ['"foo"', '"goo"'], ['"foo"', '"boo"']))
    print("* add A[1]")
    print(get_delta("A", ['"foo"'], ['"foo"', '"moo"']))
    print("* delete A[1]")
    print(get_delta("A", ['"foo"', '"hoo"'], ['"foo"']))
    print("* modify A[0] AND delete A[1]")
    print(get_delta("A", ['"boo"', '"hoo"'], ['"moo"']))


def get_str_repr(val, max_str_len=250):
    # May have to truncate
    print_text = "{"
    last_was_opener = True
    i = 0
    while i < len(val):
        v = val[i]
        if i > 0:
            if (isinstance(v, list) or v not in "{}") and not last_was_opener:
                print_text += ", "
        last_was_opener = v == "{"
        if isinstance(v, list):
            val = val[:i] + ["{"] + v + ["}"] + val[i + 1 :]
            continue
        else:
            if len(print_text) + len(v) > max_str_len:
                print_text += f"<{len(val) - i} truncated>"
                break
            else:
                print_text += v
        i += 1
    print_text += "}"
    print_text = str(print_text)
    return print_text


def test_get_str_repr():
    print(get_str_repr([]))
    print(get_str_repr(["1", "2"]))
    print(get_str_repr(["1", "2", "3"], max_str_len=3))
    print(get_str_repr(['"foo"', '"boo"']))
    print(get_str_repr(['"foo"', ['"boo"', '"goo"']]))
    print(get_str_repr(['"printed\\n"', "2"]))
    print(get_str_repr(["0", "0", "0"]))
    print(get_str_repr([["0", "2"], ["1"]]))


def convert_proxy(matchobj):
    """https://stackoverflow.com/a/60343277/8999671"""
    innertext = matchobj.group(1)
    innertext = innertext.replace("&", "&amp;")
    innertext = innertext.replace("<", "&lt;")
    innertext = innertext.replace(">", "&gt;")
    innertext = innertext.replace("'", "&apos;")
    innertext = innertext.replace('"', "&quot;")
    return f'proxy="{innertext}"'


def convert_all_proxy(text):
    return re.sub(r'proxy="([^"]+)"', convert_proxy, text)


def convert_all_disallowedunicode(text):
    """
    https://www.w3.org/TR/xml/#charsets
    Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    """
    return re.sub(
        r"[^\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\u10000-\u10FFFF]", "", text
    )


def convert_all(text):
    text = convert_all_proxy(text)
    text = convert_all_disallowedunicode(text)
    return text


def test_convert_all_proxy():
    print(convert_all_proxy("foo"))
    print(convert_all_proxy('proxy="foo"'))
    print(convert_all_proxy('proxy="<foo&>"'))
    print(
        convert_all(
            """<variable name="h" age="new" proxy="std::string">""</variable>"""
        )
    )
    print(
        convert_all(
            """<variable name="s3" age="new" proxy="std::string">"
    @"</variable>"""
        )
    )
