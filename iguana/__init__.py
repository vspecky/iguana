class PTypes:
    Char     = 0
    String   = 1
    And      = 2
    Or       = 3
    Many     = 4
    Closure  = 5
    Repeat   = 6
    Range    = 7
    MoreThan = 8
    LessThan = 9

class Code(object):
    def __init__(self, code):
        self.code = code

    def __len__(self):
        return len(self.code)

    def __getitem__(self, idx):
        return self.code[idx]

    def startswith(self, expr, start_idx, end_idx):
        return self.code.startswith(expr, start_idx, end_idx)

class StringTracker(object):
    def __init__(self, code):
        self.code = code
        self.idx = 0
        self.lin = 1
        self.col = 1

    def skip_whitespace(self):
        strlen = len(self.code)
        while self.idx < strlen:
            ch = self.code[self.idx]
            if ch not in "\r\n\t ":
                break

            if ch == '\n':
                self.lin += 1
                self.col = 1
            else:
                self.col += 1

            self.idx += 1

    def match(self, expr):
        self.skip_whitespace()

        return self.code.startswith(expr, self.idx, self.idx + len(expr))

    def consume(self, expr):
        l = len(expr)
        self.idx += l
        self.col += l

    def copy(self):
        new = StringTracker(self.code)
        new.idx = self.idx
        new.lin = self.lin
        new.col = self.col

        return new

class ParseResult(object):
    def __init__(self, include):
        self.include = include
        self.node = None
        self.error = False
        self.error_msg = ''

    def success(self, node):
        self.node = node
        return self

    def fail(self, msg):
        self.error = True
        self.error_msg = msg
        return self

    def __str__(self):
        if self.error:
            return f"Error: {self.error_msg}"

        return f"Success: {self.node}"

class Node(object):
    def __init__(self, node, name, lin, col):
        self.node = node
        self.name = name
        self.lin = lin
        self.col = col

    def __str__(self):
        return f"Node({self.name}, {self.node}, ({self.lin}, {self.col}))"

    def __repr__(self):
        return self.__str__()

class Parser(object):
    def __init__(self):
        self.__to_parse = None
        self.__name = ""
        self.__parse_fn = None
        self.__map_fn = lambda x: x
        self.__type = -1
        self.__include = True

    def map(self, map_fn):
        self.__map_fn = map_fn
        return self

    def name(self, name):
        self.__name = name
        return self

    def include(self):
        self.__include = True
        return self

    def dont_include(self):
        self.__include = False
        return self

    def wrap(self):
        if self.__type not in [PTypes.And, PTypes.Or]:
            raise Exception("Only 'And' and 'Or' combinators can be wrapped")

        P = Parser()
        P.__set_params([self], "Anonymous", self.__parse_fn, self.__type, self.__include)

        return P

    def __set_params(self, parse, name, fn, p_type, include):
        self.__to_parse = parse
        self.__name = name
        self.__parse_fn = fn
        self.__type = p_type
        self.__include = include

    @staticmethod
    def _get_params(args):
        name    = args.pop('name', "Anonymous")
        include = args.pop('include', True)

        if not isinstance(name, str):
            raise Exception("Parser name must be a string")

        if not isinstance(include, bool):
            raise Exception(f"The 'include' key must be a boolean, at parser {name}")

        return name, include

    @staticmethod
    def Char(char, **kwargs):
        if not isinstance(char, str) or len(char) != 1:
            raise Exception("Expected a character")

        name, include = Parser._get_params(kwargs)

        P = Parser()
        P.__set_params(char, name, Parser.__parse_char, PTypes.Char, include)

        return P

    @staticmethod
    def String(string, **kwargs):
        if not isinstance(string, str) or len(string) < 1:
            raise Exception("Expected a non-empty string")

        name, include = Parser._get_params(kwargs)

        P = Parser()
        P.__set_params(string, name, Parser.__parse_string, PTypes.String, include)

        return P

    @staticmethod
    def Many(parser, **kwargs):
        if not isinstance(parser, Parser):
            raise Exception("The 'Many' constructor takes an instance of Parser as the argument")

        name, include = Parser._get_params(kwargs)

        P = Parser()
        P.__set_params(parser, name, Parser.__parse_many, PTypes.Many, include)

        return P

    @staticmethod
    def Closure(parser, **kwargs):
        if not isinstance(parser, Parser):
            raise Exception("The 'Closure' constructor takes an instance of Parser as the argument")

        name, include = Parser._get_params(kwargs)

        P = Parser()
        P.__set_params(parser, name, Parser.__parse_closure, PTypes.Closure, include)

        return P

    @staticmethod
    def Repeat(parser, times, **kwargs):
        if not isinstance(parser, Parser):
            raise Exception("The 'Repeat' constructor takes an instance of Parser as an argument")

        if not isinstance(times, int):
            raise Exception("The 'times' argument in the 'Repeat' constructor must be an integer")

        if not times > 0:
            raise Exception("The 'times' argument in the 'Repeat' constructor must be positive")

        name, include = Parser._get_params(kwargs)
        P = Parser()
        P.__set_params(parser, name, Parser.__parse_repeat, PTypes.Repeat, include)
        P.__amt = times

        return P

    @staticmethod
    def Range(parser, low, high, **kwargs):
        if not isinstance(parser, Parser):
            raise Exception("The 'Range' constructor takes an instance of Parser as an argument")

        if not isinstance(low, int) or not isinstance(high, int):
            raise Exception("The 'low' and 'high' values in the 'Range' constructor must be integers")

        if high < low:
            raise Exception("The 'high' argument in the 'Range' constructor must be larger than the 'low' argument")

        name, include = Parser._get_params(kwargs)

        P = Parser()
        P.__set_params(parser, name, Parser.__parse_range, PTypes.Range, include)
        P.__low = low
        P.__high = high

        return P

    @staticmethod
    def MoreThan(parser, amt, **kwargs):
        if not isinstance(parser, Parser):
            raise Exception("The 'MoreThan' constructor takes an instance of Parser as an argument")

        if not isinstance(amt, int):
            raise Exception("The amount argument in the 'MoreThan' constructor must be an integer")

        if amt < 0:
            raise Exception("The amount in the 'MoreThan' constructor must be non-negative")

        name, include = Parser._get_params(kwargs)

        P = Parser()
        P.__set_params(parser, name, Parser.__parse_greater, PTypes.MoreThan, include)
        P.__amt = amt

        return P

    @staticmethod
    def LessThan(parser, amt, **kwargs):
        if not isinstance(parser, Parser):
            raise Exception("The 'LessThan' constructor takes an instance of Parser as an argument")

        if not isinstance(amt, int):
            raise Exception("The amount argument in the 'LessThan' constructor must be an integer")

        if amt <= 0:
            raise Exception("The amount in the 'LessThan' constructor must be positive")

        name, include = Parser._get_params(kwargs)

        P = Parser()
        P.__set_params(parser, name, Parser.__parse_smaller, PTypes.LessThan, include)
        P.__amt = amt

        return P


    def __or__(self, other):
        if not isinstance(other, Parser):
            raise Exception(f"Expected an instance of Parser, got {type(other)}")

        if self.__type != PTypes.Or:
            P = Parser()
            P.__set_params([self, other], "Anonymous", Parser.__parse_or, PTypes.Or, True)
            return P

        self.__to_parse.append(other)
        return self

    def __and__(self, other):
        if not isinstance(other, Parser):
            raise Exception(f"Expected an instance of Parser, got {type(other)}")

        if self.__type != PTypes.And:
            P = Parser()
            P.__set_params([self, other], "Anonymous", Parser.__parse_and, PTypes.And, True)
            return P

        self.__to_parse.append(other)
        return self

    def __eq__(self, other):
        if not isinstance(other, Parser):
            raise Exception("Cannot assign a non-parser object to a parser")

        self.__set_params(other.__to_parse, other.__name, other.__parse_fn, other.__type, other.__include)

    def __call__(self, code_string):
        if not isinstance(code_string, str):
            raise Exception("Expected code in string format")

        code = Code(code_string)
        trckr = StringTracker(code)

        return self.__parse_fn(self, trckr)


    def parse(self, trckr):
        if self.__type == -1:
            raise Exception("Found uninitialized Parser")

        return self.__parse_fn(self, trckr)

    def __parse_char(self, trckr):
        res = ParseResult(self.__include)
        if trckr.match(self.__to_parse):
            node = Node(self.__to_parse, self.__name, trckr.lin, trckr.col)
            trckr.consume(self.__to_parse)
            return res.success(self.__map_fn(node))

        return res.fail(f"{self.__name} Parsing Error: Expected {self.__to_parse} ({trckr.lin}:{trckr.col})")

    def __parse_string(self, trckr):
        res = ParseResult(self.__include)
        if trckr.match(self.__to_parse):
            node = Node(self.__to_parse, self.__name, trckr.lin, trckr.col)
            trckr.consume(self.__to_parse)
            return res.success(self.__map_fn(node))

        return res.fail(f"{self.__name} Parsing Error: Expected {self.__to_parse} ({trckr.lin}:{trckr.col})")

    def __parse_many(self, trckr):
        res = ParseResult(self.__include)

        lin = trckr.lin
        col = trckr.col

        nodes = []
        p_res = self.__to_parse.parse(trckr)
        not_even_one = p_res.error
        while not p_res.error:
            nodes.append(p_res.node)
            p_res = self.__to_parse.__parse_fn(self.__to_parse, trckr)

        if not_even_one:
            return res.fail(f"{self.__name} Parsing Error: Expected {self.__to_parse.__name} ({lin}:{col})")

        return res.success(self.__map_fn(Node(nodes, self.__name, lin, col)))

    def __parse_closure(self, trckr):
        res = ParseResult(self.__include)

        lin = trckr.lin
        col = trckr.col

        many_res = self.__parse_many(trckr)

        return res.success(self.__map_fn(Node(many_res.node, self.__name, lin, col)))

    def __parse_or(self, trckr):
        res = ParseResult(self.__include)

        lin = trckr.lin
        col = trckr.col

        down_res = None
        for parser in self.__to_parse:
            trck_copy = trckr.copy()
            p_res = parser.__parse_fn(parser, trck_copy)

            if not p_res.error:
                down_res = p_res
                trckr.lin = trck_copy.lin
                trckr.col = trck_copy.col
                break

        if down_res == None:
            return res.fail(f"{self.__name} Parsing Error: Expected one of {', '.join([p.__name for p in self.__to_parse])} ({lin}:{col})")

        return res.success(self.__map_fn(Node(down_res.node, self.__name, lin, col)))

    def __parse_and(self, trckr):
        res = ParseResult(self.__include)

        lin = trckr.lin
        col = trckr.col

        nodes = []
        trckr_cpy = trckr.copy()

        for parser in self.__to_parse:
            p_res = parser.__parse_fn(parser, trckr_cpy)

            if p_res.error:
                return res.fail(f"{self.__name} Parsing Error: ({p_res.error_msg}) ({lin}:{col})")
            
            nodes.append(p_res.node)

        trckr.lin = trckr_cpy.lin
        trckr.col = trckr_cpy.col

        return res.success(self.__map_fn(Node(nodes, self.__name, lin, col)))

    def __parse_repeat(self, trckr):
        res = ParseResult(self.__include)

        lin = trckr.lin
        col = trckr.col

        many_res = self.__parse_many(trckr)

        if len(many_res.node) != self.__amt:
            return res.fail(f"{self.__name} Parsing Error: Expected exactly {self.__amt} of {self.__to_parse.__name} ({lin}:{col})")

        return res.success(self.__map_fn(Node(many_res.node, self.__name, lin, col)))

    def __parse_range(self, trckr):
        res = ParseResult(self.__include)

        lin = trckr.lin
        col = trckr.col

        many_res = self.__parse_many(trckr)

        l = len(many_res.node)
        if l > self.__high or l < self.__low:
            return res.fail(f"{self.__name} Parsing Error: Expected {self.__low}-{self.__high} of {self.__to_parse.__name}")

        return res.success(self.__map_fn(Node(many_res.node, self.__name, lin, col)))

    def __parse_greater(self, trckr):
        res = ParseResult(self.__include)

        lin = trckr.lin
        col = trckr.col

        many_res = self.__parse_many(trckr)

        if len(many_res.node) <= self.__amt:
            return res.fail(f"{self.__name} Parsing Error: Expected more than {self.__amt} of {self.__to_parse.__name} ({lin}:{col})")

        return res.success(self.__map_fn(Node(many_res.node, self.__name, lin, col)))

    def __parse_smaller(self, trckr):
        res = ParseResult(self.__include)

        lin = trckr.lin
        col = trckr.col

        many_res = self.__parse_many(trckr)

        if len(many_res.node) >= self.__amt:
            return res.fail(f"{self.__name} Parsing Error: Expected less than {self.__amt} of {self.__to_parse.__name} ({lin}:{col})")

        return res.success(self.__map_fn(Node(many_res.node, self.__name, lin, col)))

def run(parser, code):
    if not isinstance(parser, Parser):
        raise Exception("Expected a Parser")

    if not isinstance(code, str):
        raise Exception("Expected code in string format")

    trckr = StringTracker(code)
    return parser.parse(trckr)
