from compiler_utils import *
from data           import Token

USELESS_CHARS = [' ']

PUNCTUATION = [
  '(',
  ')',
  '[',
  ']',
  '{',
  '}',
  '<',
  '>',
  '=',
  '!',
  ';',
  '+',
  '-',
  '*',
  '/',
  '#',
  ',',
  '.',
]

DOUBLE_PUNCTUATION = [
  '<=',
  '>=',
  '==',
  '!='
]

KEYWORDS = [
  'signed',
  'unsigned',
  'struct',
  'char',
  'short',
  'int',
  'long',
  'unsigned',
  'return',
]

class Lexer(CompilerComponent):
  def __init__(self, src_info):
    super().__init__(src_info)

    self.idx = 0
    self.row = 1
    self.col_start_idx = 0
    self.end_idx_of_last_token = 0
    self.is_on_new_line = False

  @property
  def src(self):
    return self.src_info.filecontent

  @property
  def bck(self):
    try:
      return Option(self.src[self.idx - 1])
    except IndexError:
      return Option(None)

  @property
  def cur(self):
    try:
      return self.src[self.idx]
    except IndexError:
      self.report('unexpected eof', self.cur_pos)
      return '\0'

  @property
  def nxt(self):
    try:
      return Option(self.src[self.idx + 1])
    except IndexError:
      return Option(None)

  def eof(self):
    return self.idx >= len(self.src)

  def get_col(self):
    return self.idx - self.col_start_idx + 1

  @property
  def cur_pos(self):
    _len = range_to_len(self.idx, self.idx + 1)
    is_on_new_line = self.get_is_on_new_line()

    return SourcePosition(
      self.src_info,
      self.row,
      self.get_col(),
      _len,
      self.get_spacing(_len, is_on_new_line),
      is_on_new_line
    )

  def get_spacing(self, _len, is_on_new_line):
    spacing = self.idx - self.end_idx_of_last_token - _len

    return 0 if spacing < 0 or is_on_new_line else spacing

  def match_comment_pattern(self):
    return Out(
      self.cur == '/' and self.nxt.is_some_with_any(['/', '*']),
      skipper=lambda _: self.skip_comment(self.nxt.is_some_with('/'))
    )

  def eat_comment(self):
    will_eat_comment = self.match_comment_pattern()

    if will_eat_comment.unwrap():
      will_eat_comment.skipper(self)

    return will_eat_comment.unwrap()

  def eat_whitespace(self):
    match self.cur:
      case '\n':
        self.idx += 1
        self.col_start_idx = self.idx
        self.row += 1
        self.is_on_new_line = True

      case '\r' | '\t':
        self.idx += 1
        self.report("'\\r' and '\\t' are not allowed", self.cur_pos)

      case _:
        if self.cur not in USELESS_CHARS:
          return False

        self.idx += 1

    return True

  def eat_useless_chars(self):
    ate_whitespace_or_comment = True

    while not self.eof() and ate_whitespace_or_comment:
      ate_whitespace_or_comment = self.eat_whitespace() or self.eat_comment()

  def get_is_on_new_line(self):
    is_on_new_line, self.is_on_new_line = self.is_on_new_line, False

    return is_on_new_line

  def collect_seq_until(self, until, is_collecting_string):
    start_pos = self.idx
    col = self.get_col()
    seq = ''

    while not self.eof() and until(self.bck, self.cur, self.nxt):
      seq += self.collect_escaped_char() if is_collecting_string and self.cur == '\\' else self.cur
      self.idx += 1

    self.idx -= 1

    _len = range_to_len(start_pos, self.idx + 1)
    is_on_new_line = self.get_is_on_new_line()
    return (seq, SourcePosition(self.src_info, self.row, col, _len, self.get_spacing(_len, is_on_new_line), is_on_new_line))

  def collect_id(self):
    (id, pos) = self.collect_seq_until(lambda bck, cur, nxt: cur.isalnum() or cur == '_', False)

    return Token('id', id, pos)

  def convert_to_keyword_or_id(self, id):
    if id.value in KEYWORDS:
      id.kind = id.value

    return id

  def check_digit(self, digit, pos):
    chars = str(digit)

    for (i, c) in enumerate(chars):
      if c.isalpha() or (c == '_' and i == len(chars) - 1):
        self.report('invalid digit', pos)

  def collect_digit(self):
    (digit, pos) = self.collect_seq_until(lambda bck, cur, nxt: cur.isalnum() or cur == '_', False)

    self.check_digit(digit, pos)

    return Token('digit', digit.replace('_', ''), pos)

  def collect_string(self):
    # skipping first '"'
    self.idx += 1

    (value, pos) = self.collect_seq_until(lambda bck, cur, nxt: cur != '"' or bck.is_some_with('\\'), True)

    # skipping last character of string
    self.idx += 1

    return Token('str', value, pos)

  def collect_char(self):
    # skipping first '\''
    self.idx += 1

    (value, pos) = self.collect_seq_until(lambda bck, cur, nxt: cur != '\'' or bck.is_some_with('\\'), True)

    # skipping last character of char
    self.idx += 1

    return Token('chr', value, pos)

  def collect_punctuation_or_bad(self):
    result = Token('bad', self.cur, self.cur_pos)

    if self.cur + self.nxt.unwrap_or_default('') in DOUBLE_PUNCTUATION:
      result.kind = self.cur + self.nxt.unwrap()
    elif self.cur in PUNCTUATION:
      result.kind = self.cur
    else:
      self.report('unknown char', self.cur_pos)

    return result

  def next_token(self):
    token = None

    for matches in plugin_call('match_next_token', self.next_token):
      if matches.unwrap():
        token = matches.collector(self)
    
    if token is None:
      pass
    elif self.cur.isalpha() or self.cur == '_':
      token = self.convert_to_keyword_or_id(self.collect_id())
    elif self.cur.isdigit():
      token = self.collect_digit()
    elif self.cur == '"':
      token = self.collect_string()
    elif self.cur == '\'':
      token = self.collect_char()
    else:
      token = self.collect_punctuation_or_bad()

    self.idx += 1
    return token

  def gen(self):
    self.output = []

    while True:
      self.eat_useless_chars()

      if self.eof():
        break

      token = self.next_token()
      self.end_idx_of_last_token = self.idx - 1

      plugin_call('on_token_append_to_lexer_output', self.gen)

      self.output.append(token)

      plugin_call('on_token_appended_to_lexer_output', self.gen)

    return CompilerResult(self.errors_bag, self.output)