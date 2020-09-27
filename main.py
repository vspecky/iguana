class PTypes:
    Char   = 0
    String = 1
    Seq    = 2
    Or     = 3
    Many   = 4

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
        self.idx += len(expr)

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
        self.__type = None
        self.__include = True

    def map(self, map_fn):
        self.__map_fn = map_fn
        return self

    def name(self, name):
        self.__name = name
        return self

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

    def parse(self, trckr):
        return self.__parse_fn(self, trckr)

    def __parse_char(self, trckr):
        res = ParseResult(self.__include)
        if trckr.match(self.__to_parse):
            node = Node(self.__to_parse, self.__name, trckr.lin, trckr.col)
            trckr.consume(self.__to_parse)
            return res.success(self.__map_fn(node))

        return res.fail(f"{self.__name} Parsing Error: Expected {self.__to_parse}")

    def __parse_string(self, trckr):
        res = ParseResult(self.__include)
        if trckr.match(self.__to_parse):
            node = Node(self.__to_parse, self.__name, trckr.lin, trckr.col)
            trckr.consume(self.__to_parse)
            return res.success(self.__map_fn(node))

        return res.fail(f"{self.__name} Parsing Error: Expected {self.__to_parse}")

    def __parse_many(self, trckr):
        res = ParseResult(self.__include)

        lin = trckr.lin
        col = trckr.col

        nodes = []
        p_res = self.__to_parse.parse(trckr)
        not_even_one = p_res.error
        while not p_res.error:
            if p_res.include:
                nodes.append(p_res.node)
            p_res = self.__to_parse.parse(trckr)

        if not_even_one:
            return res.fail(f"{self.__name} Parsing Error: Expected {self.__to_parse.__name}")

        return res.success(self.__map_fn(Node(nodes, self.__name, lin, col)))

def run(parser, code):
    if not isinstance(parser, Parser):
        raise Exception("Expected a Parser")

    if not isinstance(code, str):
        raise Exception("Expected code in string format")

    trckr = StringTracker(code)
    return parser.parse(trckr)
