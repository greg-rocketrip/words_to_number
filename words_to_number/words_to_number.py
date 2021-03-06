import logging
import re
import sys
from operator import mul

logger = logging.getLogger('words_to_number.words_to_number')
# logger.addHandler(logging.StreamHandler())
logger.addHandler(logging.NullHandler())
def log_exception(exc_type, exc_value, exc_traceback):
    # http://stackoverflow.com/a/16993115/2954547
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    raise exc_type(exc_value).with_traceback(exc_traceback)
sys.excepthook = log_exception
# logger.setLevel(logging.DEBUG)
# logger.setLevel(logging.ERROR)

# import inflect
# UNITS = tuple(inflect.unit + inflect.teen)
# TENS = tuple(inflect.ten)
# MILLS = tuple(map(str.strip, inflect.mill))
UNITS = ('', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
         'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen')
TENS = ('', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety')
HUNDRED = ('hundred',)
MILLS = ('', 'thousand', 'million', 'billion', 'trillion', 'quadrillion', 'quintillion', 'sextillion', 'septillion', 'octillion', 'nonillion', 'decillion')
STARTING_NUMBERS = UNITS + TENS
SEPARATORS = HUNDRED + MILLS
ALL_NUMBERS = UNITS + TENS + HUNDRED + MILLS
AND = ['and']
SPLIT_REGEX = re.compile(r'\s+|-')

def split_text(string):
    tokens = SPLIT_REGEX.split(string)
    return [token for token in tokens if token]

def contains_number(string):
    for number in ALL_NUMBERS:
        if number in string:
            return True
    return False

def is_number(string):
    for number in ALL_NUMBERS:
        if number == string:
            return True
    return False

def get_type(string):
    if is_number(string):
        if string in UNITS[:10]:
            return 'ones'
        if string in UNITS[10:]:
            return 'teens'
        if string in TENS:
            return 'tens'
        if string in HUNDRED:
            return 'hundred'
        if string in MILLS:
            return 'mills'
        if "-" in string:
            ten, unit = string.split("-")
            if (ten in TENS) and (unit in UNITS[:10]):
                return 'compound'
        return 'unrecognized'
    return 'unrecognized'

# def is_valid_next_type(types_so_far, next_token):
#     """
#     Valid overall sequence:
#         [ ... [ hundreds_chunk mill ] ] [ hundreds_chunk ]
#     Valid hundreds chunks:
#         [tens_chunk [hundred] ] [ tens_chunk ]
#     """
#     next_type = get_type(next_token)
#     return None

def split_list(items, value):
    if not items:
        return None
    items = tuple(items)
    try:
        index = items.index(value)
    except ValueError:
        return (items,)
    # return items[:index], split_list(items[(index + 1):] or None, value)
    return items[:index], items[(index + 1):] or None

def parse_chunk(tokens):
    """Parse hundreds"""
    if not tokens:
        return 0
    split_tokens = split_list(tokens, 'hundred')
    if len(split_tokens) == 2:
        pre_hundred, post_hundred = split_tokens
        return 100 * parse_chunk(pre_hundred) + parse_chunk(post_hundred)
    else:
        tokens = split_tokens[0]
        if len(tokens) == 2:
            first, second = tokens
            first_type, second_type = get_type(first), get_type(second)
            logger.debug("\t\tReceived chunk: '{}' ({}), '{}' ({})".format(first, first_type, second, second_type))
            if first_type == 'tens' and second_type == 'ones':  # "sixty five"
                first_value = TENS.index(first) * 10
                second_value = UNITS.index(second) * 1
            elif first_type in 'tens' and second_type == 'tens':  # "twenty eighty"
                first_value = TENS.index(first) * 100
                second_value = TENS.index(second) * 10
            elif first_type in ('ones', 'teens') and second_type == 'tens':  # "one eighty" / "sixteen fifty"  ... note, I haven't gotten to "sixteen fifty-five" yet...                first_value = UNITS.index(first) * 100
                first_value = UNITS.index(first) * 100
                second_value = TENS.index(second) * 10
            elif first_type == 'ones' and second_type == 'teens':  # "one sixteen"
                first_value = UNITS.index(first) * 100
                second_value = UNITS.index(second) * 1
            else:
                raise ValueError("Unrecognized sequence {}".format(tokens))
            result = first_value + second_value
            logger.debug("\t\tValue: {} + {} = {}".format(first_value, second_value, result))
            return result
        if len(tokens) == 1:
            token = tokens[0]
            logger.debug("\t\tReceived singleton: '{}'".format(token))
            if "-" in token:
                return parse_chunk(token.split("-"))
            try:
                return 10 * TENS.index(token)
            except ValueError:
                try:
                    return UNITS.index(token)
                except ValueError:
                    raise ValueError("Unrecognized number: {}".format(token))
        else:
            raise ValueError("Unrecognized format: {}".format(tokens))

def parse_tokens(tokens):
    """Break at separators and parse each chunk as a hundred"""
    if 'point' in tokens:
        raise ValueError("Decimals not implemented")
    # positions_types = list(zip(*((i, get_type(token)) for i, token in enumerate(tokens))))
    positions_tokens_types = list(zip(*((i, token, get_type(token)) for i, token in enumerate(tokens))))
    positions_mills = list(zip(*((i, token) for i, token, ttype in zip(*positions_tokens_types) if ttype == 'mills')))
    n_separators = 0
    if positions_mills:
        positions, mills = positions_mills
        logger.debug("\tFound {} separators at {} of mills {}".format(len(positions), positions, mills))
        powers = [10 ** (3 * MILLS.index(t)) for t in mills]
        positions = positions + (len(tokens),)
        powers.append(1)
        start = 0
        parsed_chunks = []
        for stop in positions:
            chunk = tokens[start:stop]
            logger.debug("\tBefore separator, parsing chunk from {} until {}: {}".format(start, stop, chunk))
            try:
                parsed_chunk = parse_chunk(chunk)
            except (ValueError, NotImplementedError):
                # Bail out immediately if parsing fails, so we can return the
                # problem back up to find_numbers, so it can start its search
                # over again
                return None
            parsed_chunks.append(parsed_chunk)
            start = stop + 1
        return sum(map(mul, powers, parsed_chunks))
    else:
        logger.debug("\tBy itself, parsing chunk: {}".format(tokens))
        try:
            return parse_chunk(tokens)
        except (ValueError, NotImplementedError):
            # Bail out immediately if parsing fails, so we can return the
            # problem back up to find_numbers, so it can start its search
            # over again
            return None

def find_numbers(text):
    """Extract numbers from text, tokenizing on whitespace"""
    if isinstance(text, str):
        tokens = split_text(text.lower())
    else:
        tokens = list(map(str.lower, text))
    results, starts, lengths = [], [], []
    prev_type = None
    attempting = False
    attempt_number = -1
    logger.debug("Parsing sequence of length {}:\n\t{}".format(len(tokens), tokens))
    for i, token in enumerate(tokens):
        logger.debug("Checking token {}".format(token))
        if not attempting:
            if token in STARTING_NUMBERS:
                # Move into the "attempting match" state
                attempting = True
                attempt_number += 1
                logger.debug("Start attempt {} at {}".format(attempt_number, i))
                start = i
                length = 0
                and_offset = 0
                stop = start + length + 1 + and_offset
                result = parse_tokens(tokens[start:stop])
                logger.debug("First result: {}".format(result))
                # initialize placeholders for the values we're going to save
                starts.append(None)
                lengths.append(None)
                results.append(None)
        if attempting:
            # Continue in the "attempting match" state
            logger.debug("Continuing attempt {} at {} (length of previous result: {})".format(attempt_number, i, length))
            if token in AND:
                # we want to skip "and" but not cause it to trigger a failure
                continue
            if token in ALL_NUMBERS:
                logger.debug("Match successful")
                stop = start + length + 1 + and_offset
                to_be_parsed = tokens[start:stop]
                # remove all the and's before continuing
                for and_word in AND:
                    logger.debug("Looking for 'and's to remove")
                    try:
                        to_be_parsed.remove(and_word)
                    except ValueError:
                        pass
                    else:
                        logger.debug("Removed an 'and'")
                        and_offset += 1
                    break
                result = parse_tokens(to_be_parsed)
                if result:
                    # We got a result, so bank what we got and keep going
                    length += 1
                    logger.debug("Longest result so far: {} at length {}".format(result, length))
                    logger.debug("Banking results so far: {},  {} until {}".format(result, start, start + length))
                    starts[attempt_number] = start
                    lengths[attempt_number] = stop - start
                    results[attempt_number] = result
                else:
                    # Drop out of the "attempting match" state
                    logger.debug("Attempt of length {} terminated on parse failure with result {}".format(length, result))
                    attempting = False
            else:
                # Drop out of the "attempting match" state
                logger.debug("Attempt of length {} terminated on non-match with result {}".format(length, result))
                attempting = False
    # Save the latest results, knowing that if they are never
    # overwritten then we never found anything better
    logger.debug("Final starts: {}".format(starts))
    logger.debug("Final lengths: {}".format(lengths))
    logger.debug("Final results: {}".format(results))
    if results:
        return {result: (start, length) for result, start, length in zip(results, starts, lengths)}
    else:
        return None

def replace_numbers(text, formatstr=None):
    # TODO in the distant future: save the whitespace and return it as it was
    # input
    tokens = split_text(text.lower())
    results = find_numbers(tokens)
    if not results:
        return text
    for replacement, (start, length) in results.items():
        if formatstr:
            tokens[start] = formatstr % replacement
        else:
            tokens[start] = str(replacement)
        for i in range(start + 1, start+length):
            tokens[i] = None
    return ' '.join(token for token in tokens if token)

