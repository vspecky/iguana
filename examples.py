from iguana import Parser as P, run

# Note: The '@' symbol will be used as a substitute for the Greek Epsilon.

def display_result(res):
    print("Success" if not res.error else "Failure")

"""
EXAMPLE 1: ab^m (m > 0)
This is a classic example, a single 'a' followed by one or more 'b's,
and representing this in the form of context free grammar is very simple too.

S -> aB
B -> bB | b

And now lets create a parser for this
"""
def example_1(inp):
    B = P()
    b = P.Char('b')
    B == ((b & B) | b)
    S = P.Char('a') & B

    display_result(run(S, inp))

example_1("ab")
example_1("bbb")
example_1("abbbbb")

def example_2(inp):
    parser = P.Many(P.Char('b'))

    print(parser(inp))
