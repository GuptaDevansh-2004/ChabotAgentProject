import re
from dataclasses import dataclass
from typing import List, Tuple, Union, Dict, Set, Any


class TextProcessor:
    """Provide utilities tools for operations related to text"""
    
    @staticmethod
    def normalize_content(content: str) -> str:
        """
        Normalize content by:
        1. Collapsing multiple spaces or tabs into a single space
        2. Stripping leading/trailing spaces on each line
        3. Removing empty lines
        """
        # Collapse multiple spaces or tabs into one
        content = re.sub(r"[ \t]+", " ", content)
        # Strip leading/trailing spaces on each line, preserving newline
        content = re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE)
        content = re.sub(r"^[ \t]+", "", content, flags=re.MULTILINE)
        # Replace multiple consecutive newlines with a single newline
        content = re.sub(r"\n{2,}", "\n", content)
        return content


class JSONDataProcessor:
    """Provide utils to convert raw data in JSON-Object"""

    # Define custom types for clarity
    JSONValue = Union[Dict, List, Tuple, Set, str, int, float, bool, None]
    JSONTop = Union[Dict, List, Tuple, Set]


    @dataclass(frozen=True)
    class ParseOptions:
        """
        Configuration options for parsing JSON-like strings.

        Attributes:
            parse_quoted_structures (bool): If True, attempts to recursively parse
                content found within quoted strings if they resemble JSON structures.
            tolerant (bool): If True, applies preprocessing heuristics to fix common
                malformed input issues, such as unescaped inner quotes.
            extract_multiple (bool): If True, `parse_json_data` will extract and return
                all found JSON-like structures. If False, it returns only the first.
            strict_json (bool): If True, only extracts and parses standard JSON
                structures (dictionaries `{}` and lists `[]`), excluding tuples `()`.
        """
        parse_quoted_structures: bool = True
        tolerant: bool = True
        extract_multiple: bool = True
        strict_json: bool = False

    @classmethod
    def parse_json(cls, text: str, options: ParseOptions = ParseOptions()) -> Union[JSONTop, List[JSONTop], None]:
        """
        Extracts and parses JSON-like structures from a given text string,
        handling surrounding noise and common malformations.

        This is the main entry point for the JSON-like data processor. It attempts
        to find and parse structured data embedded within a larger text.
        """
        if not isinstance(text, str):
            # Ensure input is a string for consistent behavior.
            # Attempt to convert to string if not None, otherwise return None.
            try:
                text = str(text)
            except Exception:
                return None

        # Step 1: Extract all balanced JSON-like structures from the text.
        extracted_structures = cls._extract_json_structures(text, options)

        if not extracted_structures:
            # If no explicit structures are found, try parsing the whole text
            # as a single JSON-like entity, after cleaning.
            try:
                cleaned_text = cls._clean_text(text)
                return cls._parse_json_like_safe(cleaned_text, options)
            except ValueError as e:
                # If the whole text can't be parsed, return None.
                raise ValueError(f"Value must be JSON-like string, recieved: {e}.")

        # Step 2: Parse each extracted structure.
        parsed_results = []
        for structure in extracted_structures:
            try:
                # Attempt to parse the extracted structure directly.
                parsed = cls._parse_json_like_safe(structure, options)
                parsed_results.append(parsed)
            except ValueError:
                # If direct parsing fails, clean the structure and try again.
                cleaned_structure = cls._clean_text(structure)
                try:
                    parsed = cls._parse_json_like_safe(cleaned_structure, options)
                    parsed_results.append(parsed)
                except ValueError:
                    # If still fails after cleaning, append the raw string.
                    parsed_results.append(structure)

        # Step 3: Return based on `extract_multiple` option.
        if not options.extract_multiple and parsed_results:
            return parsed_results[0]
        return parsed_results if parsed_results else None

    @classmethod
    def _extract_json_structures(cls, text: str, options: ParseOptions) -> List[str]:
        """
        Extracts all top-level, balanced JSON-like structures (objects, arrays, tuples)
        from a given text. This function is tolerant of surrounding non-JSON text.
        """
        structures = []
        i = 0
        n = len(text)

        # Define valid opening characters based on strict_json flag.
        # If strict_json is True, only '{' and '[' are considered.
        # Otherwise, '(' is also included for tuples.
        openers = ['{', '[']
        if not options.strict_json:
            openers.append('(')

        while i < n:
            if text[i] in openers:
                start = i
                end = -1
                if text[i] == '{':
                    end = cls._find_closing_bracket(text, i, '{', '}')
                elif text[i] == '[':
                    end = cls._find_closing_bracket(text, i, '[', ']')
                elif text[i] == '(':
                    # Only attempt to find closing parenthesis if not in strict JSON mode
                    end = cls._find_closing_bracket(text, i, '(', ')')

                if end != -1 and end >= start:
                    structure = text[start:end+1]
                    structures.append(structure)
                    i = end + 1  # Move past the extracted structure
                    if not options.extract_multiple:
                        # If only one structure is needed, stop after the first.
                        break
                else:
                    i += 1  # If no closing bracket found, move to the next character
            else:
                i += 1  # Move to the next character if no opener found

        return structures

    @classmethod
    def _find_closing_bracket(cls, text: str, start: int, open_char: str, close_char: str) -> int:
        """
        Finds the index of the matching closing bracket for a given opening bracket,
        correctly handling nested structures and quoted strings.
        This function is optimized to use `str.find()` for performance.
        """
        count = 0
        i = start
        n = len(text)
        in_string = False

        while i < n:
            char = text[i]

            # Handle escaped characters within strings
            if char == '\\' and i + 1 < n:
                i += 2  # Skip escaped character
                continue

            if char == '"':
                in_string = not in_string
            elif not in_string:
                if char == open_char:
                    count += 1
                elif char == close_char:
                    count -= 1
                    if count == 0:
                        return i  # Found the matching closing bracket
            i += 1
        return -1

    @classmethod
    def _clean_text(cls, text: str) -> str:
        """
        Cleans common JSON-like formatting issues in a string using regular expressions.
        This includes:
        - Removing BOM (Byte Order Mark) markers.
        - Replacing single quotes with double quotes (basic heuristic).
        - Removing trailing commas before closing brackets.
        - Replacing 'undefined'/'NaN' with 'null'.
        """
        # Remove BOM
        if text.startswith('\ufeff'):
            text = text[1:]

        # Use a single regex pass for multiple common cleanup tasks:
        # 1. Replace single quotes with double quotes, but be careful not to double-escape
        #    already escaped double quotes or single quotes within content that *should* be single-quoted.
        #    This is a simple heuristic and might not cover all edge cases, but it's a common issue.
        # 2. Remove trailing commas before closing braces/brackets/parentheses.
        # 3. Replace 'undefined' and 'NaN' with 'null'.
        cleaned = re.sub(
            r"'(?![^{\[]*?[:,])([^']*)'|,\s*([}\]])|\bundefined\b|\bNaN\b",
            lambda match: '"' + match.group(1).replace('"', '\\"') + '"' if match.group(1) else (
                match.group(2) if match.group(2) else 'null'
            ),
            text
        )

        return cleaned

    @classmethod
    def _parse_json_like_safe(cls, s: str, options: ParseOptions) -> JSONTop:
        """
        The core recursive parser for JSON-like strings.
        Converts a JSON-like string into Python dict, list, tuple, or primitive types.
        Handles nested structures, strings, numbers, booleans, unicode, and nulls safely.
        """
        s = s.strip()
        if not s:
            # For an empty string, default to an empty dictionary, which is often a valid
            # representation of an empty JSON object.
            return {}

        # Apply preprocessing for unescaped inner quotes if tolerant mode is enabled.
        if options.tolerant:
            s = cls._preprocess_escape_inner_quotes(s)

        # Determine the top-level structure type and delegate parsing.
        if s.startswith('{'):
            # Objects (dict) or Sets
            _next_idx, content = cls._extract_braces(s, 0, '{', '}', options)
            inner = content[1:-1].strip()
            if cls._is_set_like(inner, options) and not options.strict_json:
                return cls._parse_set_safe(inner, options)
            else:
                return cls._parse_object_safe(inner, options)
        elif s.startswith('['):
            # Arrays (list)
            _next_idx, content = cls._extract_braces(s, 0, '[', ']', options)
            return cls._parse_array_safe(content[1:-1], options)
        elif s.startswith('(') and not options.strict_json:
            # Tuples (if not in strict JSON mode)
            _next_idx, content = cls._extract_parens(s, 0, options)
            return cls._parse_tuple_safe(content, options)
        else:
            # If it's not a recognized top-level structure, it's an invalid input
            # for this parser. Raise a ValueError.
            raise ValueError(f"Invalid JSON-like string received: {s}")

    @classmethod
    def _preprocess_escape_inner_quotes(cls, s: str) -> str:
        """
        Escapes inner (unescaped) quotes within quoted strings in JSON-like content,
        especially useful for tolerant parsing. For example, transforms
        '{"a":"(\\"A\\",\\"B\\")"}' to '{"a":"(\\"A\\",\\"B\\")"}' effectively.

        This function attempts to handle cases where a string contains a nested
        JSON-like structure that is itself quoted, but the inner quotes are not
        properly escaped for the outer string.
        """
        out = []
        i = 0
        n = len(s)

        while i < n:
            char = s[i]
            if char != '"':
                # If not a quote, just append the character and move on.
                out.append(char)
                i += 1
                continue

            # Encountered a double quote, start of a potential string.
            out.append('"')
            i += 1

            nested_depth = 0  # Track depth of nested structures ({, [, ()})
            while i < n:
                current_char = s[i]

                # Handle already escaped characters
                if current_char == '\\' and i + 1 < n:
                    out.append(current_char)
                    out.append(s[i+1])
                    i += 2
                    continue

                # Track nested structure depth (e.g., inside "a(b)")
                if current_char in '({[':
                    nested_depth += 1
                    out.append(current_char)
                elif current_char in ')}]':
                    nested_depth -= 1
                    out.append(current_char)
                elif current_char == '"':
                    # If it's a quote within a string:
                    if nested_depth > 0:
                        # If we are inside a nested structure within the string,
                        # this quote should be escaped.
                        out.append('\\"')
                    else:
                        # If not inside a nested structure, this is the closing quote
                        # for the current string.
                        out.append('"')
                        i += 1  # Move past the closing quote
                        break  # Exit inner while loop, string parsing complete
                else:
                    out.append(current_char)
                i += 1  # Move to the next character within the string

        return ''.join(out)

    @classmethod
    def _is_set_like(cls, s: str, options: ParseOptions) -> bool:
        """
        Detects if the content within braces `{}` looks like a set rather than a dictionary.
        A set is characterized by comma-separated values without colons (`:` key-value pairs).
        This function carefully skips over quoted strings and nested structures to avoid
        misinterpreting colons inside them.
        """
        i = 0
        length = len(s)

        while i < length:
            ch = s[i]

            # Skip quoted strings safely
            if ch == '"':
                # Find the end of the string. _parse_string_safe returns (value, next_index)
                # We only need the next_index here.
                try:
                    _, next_i = cls._parse_string_safe(s, i, options)
                    i = next_i
                    continue
                except ValueError:
                    # If string parsing fails, treat the rest of the content as part of
                    # the current element and assume it's not a set (since it's malformed).
                    return False

            # Skip nested structures (objects, arrays, tuples) safely
            if ch == '{':
                i, _ = cls._extract_braces(s, i, '{', '}', options)
                continue
            if ch == '[':
                i, _ = cls._extract_braces(s, i, '[', ']', options)
                continue
            if ch == '(':
                i, _ = cls._extract_parens(s, i, options)
                continue

            # Check for a colon outside of strings and nested structures.
            # If a colon is found, it indicates a key-value pair, so it's a dictionary.
            if ch == ':':
                return False

            i += 1
        return True  # No colon found outside of strings/structures, so it's likely a set.

    @classmethod
    def _parse_set_safe(cls, s: str, options: ParseOptions) -> Set[Any]:
        """
        Parses a set-like structure, e.g., '{element1, element2, ...}'.
        Ensures elements are hashable for set inclusion; unhashable types are
        converted to their string representation.
        """
        elements = set()  # Use a set directly to handle uniqueness
        i = 0
        length = len(s)

        while i < length:
            # Skip leading whitespace and commas
            if s[i].isspace() or s[i] == ',':
                i += 1
                continue

            # If we've reached the end of the string, break.
            if i >= length:
                break

            # Parse the next value in the set.
            try:
                val, i = cls._parse_next_value_safe(s, i, options)
                if val is not None:
                    processed_val = cls._process_nested_value(val, options)
                    # Convert unhashable types (dict, list, set) to string for set inclusion.
                    # Tuples are hashable, so they can be added directly.
                    if isinstance(processed_val, (dict, list, set)):
                        elements.add(str(processed_val))
                    else:
                        elements.add(processed_val)
            except ValueError:
                # If parsing a value fails, try to extract the raw string up to the next comma.
                start = i
                depth = 0
                while i < length:
                    if s[i] == '"':
                        try:
                            _, i_temp = cls._parse_string_safe(s, i, options)
                            i = i_temp
                            continue
                        except ValueError:
                            i += 1 # move past malformed string
                    elif s[i] in '{[(':
                        depth += 1
                    elif s[i] in ')]}':
                        depth -= 1
                    elif s[i] == ',' and depth == 0:
                        break # End of current element
                    i += 1
                raw_value = s[start:i].strip()
                if raw_value:
                    elements.add(raw_value)
            except Exception:
                # Catch any other unexpected errors during parsing of a single element
                # and move past it. This makes the parser more robust.
                i += 1
                continue
        return elements

    @classmethod
    def _process_nested_value(cls, v: Any, options: ParseOptions) -> Any:
        """
        Recursively processes nested dictionaries, lists, tuples, and sets.
        For string values, it optionally attempts to parse them as further JSON-like structures
        if `parse_quoted_structures` is enabled.
        """
        if isinstance(v, dict):
            return {k: cls._process_nested_value(val, options) for k, val in v.items()}
        if isinstance(v, list):
            return [cls._process_nested_value(item, options) for item in v]
        if isinstance(v, tuple):
            return tuple(cls._process_nested_value(item, options) for item in v)
        if isinstance(v, set):
            return {cls._process_nested_value(item, options) for item in v}
        if isinstance(v, str) and options.parse_quoted_structures:
            # Attempt to parse inner JSON-like structures within strings.
            parsed = cls._try_parse_quoted_content(v, options)
            if parsed != v:
                # If parsing was successful, recursively process the newly parsed structure.
                return cls._process_nested_value(parsed, options)
        return v

    @classmethod
    def _try_parse_quoted_content(cls, text: str, options: ParseOptions) -> Any:
        """
        Attempts to parse a string that might contain a JSON-like structure
        (e.g., "{...}", "[...]", "(...)"). If parsing fails, the original
        string is returned.
        """
        text = text.strip()
        # Check if the string starts with a known JSON-like structure opener.
        if text.startswith(('{', '[', '(')):
            try:
                # Create new options with tolerant=False for the inner parse to avoid
                # redundant preprocessing. The outer parse already handled tolerance.
                inner_parse_options = cls.ParseOptions(
                    parse_quoted_structures=options.parse_quoted_structures,
                    tolerant=False,
                    extract_multiple=False, # We are parsing a single block here.
                    strict_json=options.strict_json
                )
                # Attempt to parse the content.
                return cls._parse_json_like_safe(text, inner_parse_options)
            except ValueError:
                # If parsing fails (e.g., malformed inner structure), return the original text.
                return text
        return text # Not a structure, return as-is.

    @classmethod
    def _parse_object_safe(cls, s: str, options: ParseOptions) -> Dict[str, Any]:
        """
        Parses a dictionary-like structure, e.g., 'key1:value1, key2:value2'.
        This function is robust to unquoted keys and tries to handle malformed values.
        """
        result = {}
        i = 0
        length = len(s)

        while i < length:
            # Skip leading whitespace and commas
            if s[i].isspace() or s[i] == ',':
                i += 1
                continue

            # Parse key
            key_start = i
            key = None
            if s[i] == '"':
                # Key is a quoted string
                try:
                    key, i = cls._parse_string_safe(s, i, options)
                except ValueError:
                    # If quoted string parsing fails, treat the rest as a raw key.
                    key = s[key_start:].split(':', 1)[0].strip() # Take up to first colon or end
                    i = length # Assume rest of string is part of this malformed key
            else:
                # Key is an unquoted identifier
                # Find the end of the unquoted key (up to ':', ',' or '}')
                key_end = i
                depth = 0 # To handle nested structures within unquoted keys (unlikely but robust)
                while key_end < length:
                    if s[key_end] == '"':
                        try:
                            _, temp_key_end = cls._parse_string_safe(s, key_end, options)
                            key_end = temp_key_end
                            continue
                        except ValueError:
                            key_end += 1 # Move past malformed string
                    elif s[key_end] in '{[(':
                        depth += 1
                    elif s[key_end] in ')]}':
                        depth -= 1
                    elif s[key_end] == ':' and depth == 0:
                        break # Found the colon separator for the key
                    elif s[key_end] == ',' and depth == 0:
                        # If a comma is found before a colon, this key has no value
                        break
                    key_end += 1
                key = s[key_start:key_end].strip()
                i = key_end # Update global index

            if not key:
                # If key is empty or unparsable, break to avoid infinite loop.
                break

            # Skip whitespace after key
            while i < length and s[i].isspace():
                i += 1

            # Look for colon separator for the value
            if i < length and s[i] == ':':
                i += 1 # Move past colon

                # Parse value
                try:
                    val, i = cls._parse_next_value_safe(s, i, options)
                    result[key] = cls._process_nested_value(val, options)
                except ValueError:
                    # If value parsing fails, try to capture the raw value until the next comma or end of object.
                    value_start = i
                    depth = 0
                    while i < length:
                        if s[i] == '"':
                            try:
                                _, temp_i = cls._parse_string_safe(s, i, options)
                                i = temp_i
                                continue
                            except ValueError:
                                i += 1
                        elif s[i] in '{[(':
                            depth += 1
                        elif s[i] in '}])':
                            if depth == 0 and s[i] == '}': # End of current object
                                break
                            depth -= 1
                        elif s[i] == ',' and depth == 0:
                            break # End of current key-value pair
                        i += 1
                    raw_value = s[value_start:i].strip()
                    result[key] = raw_value if raw_value else None # Store raw value or None
            else:
                # No colon found for the key, treat as key with a None value.
                result[key] = None

        return result

    @classmethod
    def _parse_array_safe(cls, s: str, options: ParseOptions) -> List[Any]:
        """
        Parses an array-like structure, e.g., '[element1, element2, ...]'.
        """
        arr = []
        i = 0
        length = len(s)

        while i < length:
            # Skip leading whitespace and commas
            if s[i].isspace() or s[i] == ',':
                i += 1
                continue

            # If we've reached the end of the string, break.
            if i >= length:
                break

            # Parse the next value in the array.
            try:
                val, i = cls._parse_next_value_safe(s, i, options)
                if val is not None:
                    arr.append(cls._process_nested_value(val, options))
            except ValueError:
                # If parsing a value fails, extract the raw string up to the next comma
                # or closing bracket.
                start = i
                depth = 0
                while i < length:
                    if s[i] == '"':
                        try:
                            _, temp_i = cls._parse_string_safe(s, i, options)
                            i = temp_i
                            continue
                        except ValueError:
                            i += 1
                    elif s[i] in '{[(':
                        depth += 1
                    elif s[i] in '}])':
                        if depth == 0 and s[i] == ']': # End of current array
                            break
                        depth -= 1
                    elif s[i] == ',' and depth == 0:
                        break # End of current element
                    i += 1
                raw_value = s[start:i].strip()
                if raw_value:
                    arr.append(raw_value)
        return arr

    @classmethod
    def _parse_tuple_safe(cls, s: str, options: ParseOptions) -> Tuple[Any, ...]:
        """
        Parses a tuple-like structure, e.g., '(element1, element2, ...)'.
        """
        # Remove outer parentheses if present for consistent inner string.
        inner = s
        if s.startswith('(') and s.endswith(')'):
            inner = s[1:-1]

        elements = []
        i = 0
        length = len(inner)

        while i < length:
            # Skip leading whitespace and commas
            if inner[i].isspace() or inner[i] == ',':
                i += 1
                continue

            # If we've reached the end of the string, break.
            if i >= length:
                break

            # Parse the next value in the tuple.
            try:
                val, i = cls._parse_next_value_safe(inner, i, options)
                if val is not None:
                    elements.append(cls._process_nested_value(val, options))
            except ValueError:
                # Fallback for unparsable content: extract raw string until next comma or end.
                start = i
                depth = 0
                while i < length:
                    if inner[i] == '"':
                        try:
                            _, temp_i = cls._parse_string_safe(inner, i, options)
                            i = temp_i
                            continue
                        except ValueError:
                            i += 1
                    elif inner[i] in '{[(':
                        depth += 1
                    elif inner[i] in ')]}':
                        if depth == 0 and inner[i] == ')': # End of current tuple
                            break
                        depth -= 1
                    elif inner[i] == ',' and depth == 0:
                        break # End of current element
                    i += 1
                raw_value = inner[start:i].strip()
                if raw_value:
                    elements.append(raw_value)
        return tuple(elements)

    @classmethod
    def _parse_next_value_safe(cls, s: str, i: int, options: ParseOptions) -> Tuple[Any, int]:
        """
        Parses the next value (primitive, string, object, array, or tuple)
        from the given string starting at index `i`.
        """
        # Skip leading whitespace
        while i < len(s) and s[i].isspace():
            i += 1

        length = len(s)
        if i >= length:
            raise ValueError(f"No more characters to parse at index {i}")

        ch = s[i]
        if ch == '"':
            return cls._parse_string_safe(s, i, options)
        if ch == '{':
            _next_idx, content = cls._extract_braces(s, i, '{', '}', options)
            inner = content[1:-1].strip()
            # Differentiate between set and dict within braces
            if cls._is_set_like(inner, options) and not options.strict_json:
                return cls._parse_set_safe(inner, options), _next_idx
            else:
                return cls._parse_object_safe(inner, options), _next_idx
        if ch == '[':
            _next_idx, content = cls._extract_braces(s, i, '[', ']', options)
            return cls._parse_array_safe(content[1:-1], options), _next_idx
        if ch == '(' and not options.strict_json:
            _next_idx, content = cls._extract_parens(s, i, options)
            return cls._parse_tuple_safe(content, options), _next_idx

        # If it's not a known structure, try to parse as a primitive value.
        start = i
        # Find the end of the primitive value (until a comma, closing brace/bracket/paren)
        depth = 0
        while i < length:
            if s[i] == '"':
                try:
                    _, temp_i = cls._parse_string_safe(s, i, options)
                    i = temp_i
                    continue
                except ValueError:
                    i += 1
            elif s[i] in '{[(':
                depth += 1
            elif s[i] in '}])':
                if depth == 0: # If at top level and find a closing character, this is the end of the primitive.
                    break
                depth -= 1
            elif s[i] == ',' and depth == 0:
                break
            i += 1
        raw_value = s[start:i].strip()

        # Attempt to convert the raw string to a Python primitive type.
        parsed = cls._parse_primitive_safe(raw_value, options)
        return parsed, i

    @classmethod
    def _parse_string_safe(cls, s: str, i: int, options: ParseOptions) -> Tuple[str, int]:
        """
        Parses a double-quoted string, handling escape sequences (e.g., \\", \\n, \\t, \\uXXXX).
        """
        if i >= len(s) or s[i] != '"':
            raise ValueError(f"Expected opening double quote at position {i} for string parsing.")

        i += 1  # Move past the opening quote
        parts = []
        length = len(s)

        while i < length:
            ch = s[i]
            if ch == '\\':
                # Handle escape sequences
                if i + 1 < length:
                    next_ch = s[i+1]
                    if next_ch == '"':
                        parts.append('"')
                    elif next_ch == '\\':
                        parts.append('\\')
                    elif next_ch == '/':
                        parts.append('/') # JSON allows escaping '/', Python does not need it.
                    elif next_ch == 'b':
                        parts.append('\b')
                    elif next_ch == 'f':
                        parts.append('\f')
                    elif next_ch == 'n':
                        parts.append('\n')
                    elif next_ch == 'r':
                        parts.append('\r')
                    elif next_ch == 't':
                        parts.append('\t')
                    elif next_ch == 'u' and i + 5 < length:
                        # Unicode escape sequence (\uXXXX)
                        try:
                            hex_code = s[i+2:i+6]
                            code = int(hex_code, 16)
                            parts.append(chr(code))
                            i += 6 # Move past \uXXXX
                            continue
                        except ValueError:
                            # If unicode sequence is malformed, treat as literal '\u'
                            parts.append('\\u')
                            i += 2 # Move past \u and continue to next characters
                            continue
                    else:
                        # For unknown escape sequences, append the escaped character directly
                        parts.append(next_ch)
                    i += 2 # Move past '\\' and next_ch
                    continue
                else:
                    # Trailing backslash, malformed string
                    raise ValueError(f"Incomplete escape sequence at end of string at index {i}.")
            elif ch == '"':
                # Found the closing double quote
                i += 1
                break
            else:
                # Regular character
                parts.append(ch)
            i += 1
        else:
            # Reached end of string without finding closing quote
            raise ValueError(f"Unterminated string starting at index {i}.")

        return ''.join(parts), i

    @classmethod
    def _extract_braces(cls, s: str, i: int, open_brace: str, close_brace: str, options: ParseOptions) -> Tuple[int, str]:
        """
        Extracts a balanced section of a string enclosed by specified braces (e.g., {}, []).
        Handles nested braces and quoted strings correctly.
        """
        start = i
        count = 0
        length = len(s)

        while i < length:
            ch = s[i]
            if ch == '"':
                # If inside a string, skip to its end.
                try:
                    _, string_end_idx = cls._parse_string_safe(s, i, options)
                    i = string_end_idx
                    continue
                except ValueError as e:
                    # If the string itself is malformed, raise an error.
                    raise ValueError(f"Malformed string within braces: {e}")
            
            if ch == open_brace:
                count += 1
            elif ch == close_brace:
                count -= 1
                if count == 0:
                    # Found the matching closing brace.
                    return i + 1, s[start:i+1]
            i += 1
        
        # If loop finishes and count is not zero, braces are unbalanced.
        raise ValueError(f"Unbalanced braces in string starting at index {start}. Expected '{close_brace}'")
    
    @classmethod
    def _extract_parens(cls, s: str, i: int, options: ParseOptions) -> Tuple[int, str]:
        """
        Extracts a balanced section of a string enclosed by parentheses ().
        Handles nested parentheses and quoted strings correctly.
        """
        start = i
        count = 0
        length = len(s)

        while i < length:
            ch = s[i]
            if ch == '"':
                # If inside a string, skip to its end.
                try:
                    _, string_end_idx = cls._parse_string_safe(s, i, options)
                    i = string_end_idx
                    continue
                except ValueError as e:
                    # If the string itself is malformed, raise an error.
                    raise ValueError(f"Malformed string within parentheses: {e}")

            if ch == '(':
                count += 1
            elif ch == ')':
                count -= 1
                if count == 0:
                    # Found the matching closing parenthesis.
                    return i + 1, s[start:i+1]
            i += 1
        
        # If loop finishes and count is not zero, parentheses are unbalanced.
        raise ValueError(f"Unbalanced parentheses in string starting at index {start}. Expected ')'")
    
    @classmethod
    def _parse_primitive_safe(cls, val: str, options: ParseOptions) -> JSONValue:
        """
        Attempts to parse a string value into a Python primitive type (None, bool, int, float).
        If it cannot be parsed as a primitive, the original string is returned.
        """
        if not val:
            return None

        low_val = val.lower()
        if low_val == 'null' or low_val == 'none':
            return None
        if low_val == 'true':
            return True
        if low_val == 'false':
            return False

        # Try to parse as number (float before int to handle decimals)
        try:
            # Check for float characteristics: decimal point or exponent notation.
            if '.' in val or 'e' in low_val:
                return float(val)
            return int(val)
        except ValueError:
            # Not a valid number, return as a string.
            return val