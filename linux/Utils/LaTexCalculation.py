#!/usr/bin/env python
import math

def solveLaTex(equation):
    """Takes in a string of latex with 'x' as the 
    variable and returns a single-argument function 
    that computes f(x)."""
    tokens = tokenize (equation)
    solve_trivial(tokens)
    return solve_recursive(tokens)

    
def solve_recursive(tokens):
    """Take in a list of latex tokens, and
    recursively solve sub-expressions to generate
    a single-argument function that computes the
    equation for 'x'"""
    if len(tokens) == 0:
        return (lambda x: x)
    tokens = list(tokens)
    while '(' in tokens:
        level = 1
        startIdx = tokens.index('(')
        curIdx = startIdx + 1
        subExpr = []
        tk = tokens.pop(startIdx)
        while level > 0:
            tk = tokens.pop(startIdx)
            subExpr.append(tk)
            if tk == ')':
                level -= 1
            elif tk == '(':
                level += 1
        subExpr.pop() #Remove the closing )
        tokens.insert(startIdx, solve_recursive(subExpr))
    return solve_basic(tokens)

def tokenize(eqn):
    """Take in a string of latex and return a list of tokens"""
    tokens = []
    i = j = 0
    while j <= len(eqn):
        j+= 1
        token = eqn[i:j].strip()
        if token in [r"\left(",
                     r"\left[",
                     r"\left{",
                     r"{",
                     r"(",
                     r"[" ]:
            tokens.append("(")
            i = j
        elif token in [r"\right)",
                     r"\right]",
                     r"\right}",
                     r"}",
                     r")",
                     r"]",]:
            tokens.append(")")
            i = j
        elif token in ['-','+','/','*','^']:
            tokens.append(token)
            i = j
        elif token.isdigit() and ( j+1 > len(eqn) or not eqn[i:j+1].isdigit()):
            tokens.append(int(token))
            i = j
        elif token.lower() == "x":
            tokens.append(token)
            i = j
        elif token == "\dfrac":
            tokens.append("div")
            i = j
        elif token == "\sqrt":
            tokens.append("sqrt")
            i = j
        elif token == "\cos":
            tokens.append("cos")
            i = j
        elif token == "\sin":
            tokens.append("sin")
            i = j
        elif token == r"\tan":
            tokens.append("tan")
            i = j
    if i != len(eqn):
        print i, len(eqn)
        print "Lexer failed to tokenize at {}.\nTokens so far:{}".format(eqn[i:], tokens)
        #return []
    return tokens


def solve_trivial(tokens):
    for i, tk in enumerate(tokens):
        if tk == 'x':
            tokens[i] = (lambda x: x)
        elif type(tk) == int:
            tokens[i] = (lambda x, num=tk: num)

def solve_basic(tokens):
    assert('(' not in tokens)
    assert(')' not in tokens)
    tokenList = list(tokens)
    while len(tokenList) > 1:
        #Take care of exponentiation
        while '^' in tokenList:
            opIdx = tokenList.index('^')
            binaryOp(tokenList, opIdx,
                     lambda lhs, rhs: math.pow(float(lhs), float(rhs)))
        while 'sqrt' in tokenList:
            opIdx = tokenList.index('sqrt')
            tokenList.pop(opIdx)
            arg = tokenList.pop(opIdx)
            assert callable(arg)
            tokenList.insert(opIdx, lambda x: math.sqrt(arg(x)))
        #insert mulitplication tokens
        while 'div' in tokenList:
            opIdx = tokenList.index('div')
            tokenList.pop(opIdx)
            tokenList.insert(opIdx+1, '/')
        while 'cos' in tokenList:
            opIdx = tokenList.index('cos')
            tokenList.pop(opIdx)
            arg = tokenList.pop(opIdx)
            assert callable(arg)
            tokenList.insert(opIdx, lambda x: math.cos(arg(x)))
        while 'tan' in tokenList:
            opIdx = tokenList.index('tan')
            tokenList.pop(opIdx)
            arg = tokenList.pop(opIdx)
            assert callable(arg)
            tokenList.insert(opIdx, lambda x: math.tan(arg(x)))
        while 'sin' in tokenList:
            opIdx = tokenList.index('sin')
            tokenList.pop(opIdx)
            arg = tokenList.pop(opIdx)
            assert callable(arg)
            tokenList.insert(opIdx, lambda x: math.sin(arg(x)))
        prev = None
        tokensCopy = []
        for tk in tokenList:
            if callable(prev) and callable(tk):
                tokensCopy.append('*')
                tokensCopy.append(tk)
            else:
                tokensCopy.append(tk)
            prev = tk
        tokenList = tokensCopy

        #Evaluate binary operators
        while '*' in tokenList:
            opIdx = tokenList.index('*')
            binaryOp(tokenList, opIdx,
                     lambda lhs, rhs: lhs * rhs)
        while '/' in tokenList:
            opIdx = tokenList.index('/')
            binaryOp(tokenList, opIdx,
                     lambda lhs, rhs: lhs / float(rhs))
        while '+' in tokenList:
            opIdx = tokenList.index('+')
            binaryOp(tokenList, opIdx,
                     lambda lhs, rhs: lhs + rhs)
        while '-' in tokenList:
            opIdx = tokenList.index('-')
            binaryOp(tokenList, opIdx,
                     lambda lhs, rhs: lhs - rhs)

    assert( callable(tokenList[0]))
    return tokenList[0]
            
def binaryOp(tokens, opIdx, func):
    """Replace three tokens with a function that takes
    two values (x,y) as arguments"""
    assert(opIdx < len(tokens)-1 and opIdx > 0)
    lhs = tokens.pop(opIdx-1)
    tokens.pop(opIdx-1)
    rhs = tokens.pop(opIdx-1)
    assert callable(lhs) and callable(rhs)
    tokens.insert(opIdx-1, 
                  lambda x: func(lhs(x), rhs(x)))
        


if __name__ == '__main__':
    import sys
    import pdb
    def main(args):
        if len(args) < 1:
            print "Usage: %s" % (args[0])
            exit(1)

        equation = raw_input("Equation: ")
        """
        tokens = tokenize (equation)
        print tokens
        solve_trivial(tokens)
        print solve_recursive(tokens)(2)
        """
        print solveLaTex(equation)(2)
    main(sys.argv)
