
"""Module Docs"""

# ------------------------------------------------------------------------------

import io
import sys
import json
import time
import readline
from glob import glob

# ------------------------------------------------------------------------------

def getInput(env):
    code = ""
    while True:
        newInput = input("> "  if not code else "~ ")
        code += newInput + "\n"
        try:
            exec(code, {**env})
        except SyntaxError as err:
            if err.args[0] == "EOF while scanning triple-quoted string literal":
                continue
            if err.args[0] == "unexpected EOF while parsing":
                continue
            if err.args[0] == "expected an indented block":
                continue
            raise err
        else:
            if not newInput or len(code.splitlines()) == 1:
                return code

# ------------------------------------------------------------------------------

def preludeClosure():
    prelude = []

    def getPrelude():
        return prelude

    def getPreludeEnv(preludePath):
        if preludePath is None:
            useOldPrelude = bool(prelude)
            if not useOldPrelude:
                newPrelude()

        else:
            useOldPrelude = True
            loadPrelude(preludePath)

        return initPrelude(show=useOldPrelude)

    def loadPrelude(preludePath):
        nonlocal prelude
        with open(preludePath) as file:
            testObj = json.loads(file.read())
        prelude = testObj["prelude"]

    def initPrelude(show):
        if show:
            print("[replTest: using prelude]")

        env = {}
        for initStr in prelude:
            exec(initStr, env)
            if show: print(initStr, end="")
        return env

    def newPrelude():
        nonlocal prelude
        prelude.clear()
        print("[replTest: new prelude]")
        
        env = {}
        while True:
            try:
                newInput = getInput(env)

            except KeyboardInterrupt:
                return

            if newInput:
                try: exec(newInput, env)
                except Exception as err: print(repr(err))
                else: prelude.append(newInput)

    return getPrelude, getPreludeEnv, newPrelude

getPrelude, getPreludeEnv, newPrelude = preludeClosure()


def replTest(preludePath=None):
    print("[replTest: help(replTest) for info]")

    try:
        env = getPreludeEnv(preludePath)
    except EOFError:
        print("[replTest: prelude discarded]")
        return

    inputs = []; outputs = [];

    print("[replTest: new test]")
    while True:
        try:
            newInput = getInput(env)

        except EOFError:
            print("[replTest: test discarded]")
            break

        except KeyboardInterrupt:
            saveTest(inputs, outputs)
            break

        if newInput:
            inputs.append(newInput)
            outputs.append(processInput(newInput, env))
            if outputs[-1]:
                print(outputs[-1], end="")


def runTests(path="./test/"):
    start = time.time()    
    results = testDir(path)
    end = time.time()

    print("-" * 40)
    for result in results:
        print("[{} pass, {} fail] {}".format(*result))
    print("{} seconds".format(round(end - start, 4)))

def testDir(path):
    results = []
    for subDir in glob(path.strip("/") + "/*/"):
        results += testDir(subDir)

    numPass = numFail = 0
    files = glob(path.strip("/") + "/*.json")
    for file in files:
        with open(file) as testFile:
            testObj = json.loads(testFile.read())
            result = doTest(testObj)
            if not result:
                numPass += 1
                print("[PASS] {}".format(file))
            else:
                numFail += 1
                print("[FAIL] {}".format(file))
                print("-" * 40)
                print(result, end="")
                print("-" * 40)

    results.append((numPass, numFail, path))
    return results


def doTest(testObj):
    err = ""
    env = {}
    for initStr in testObj["prelude"]:
        exec(initStr, env)
        err += "> " + initStr

    for inputStr, outputStr in zip(testObj["inputs"], testObj["outputs"]):    
        result = processInput(inputStr, env)
        err += "> " + inputStr + result

        if result != outputStr:
            err += "-" * 40 + "\n"
            err += "Expected: " + outputStr
            return err


def processInput(newInput, env):
    stream = io.StringIO("")
    sys.stdout = stream
    try:
        result = repr(eval(newInput, env))

    except SyntaxError as err:
        exec(newInput, env)
        result = None

    except NameError as err:
        result = repr(err) + "\n"
        result += ("[replTest: missing definition in prelude?]")

    except Exception as err:
        result = repr(err)

    finally:
        sys.stdout = sys.__stdout__

    newOut = stream.getvalue()
    return str(newOut) + (result + "\n") if result else ""


def saveTest(inputs, outputs):
    try:
        timeStr = time.strftime("%Y-%m-%d-%H:%M:%S")
        fileName = input("[replTest: test name]: ") or timeStr

    except (EOFError, KeyboardInterrupt):
        print("[replTest: test discarded]")
        return

    if not fileName.endswith(".json"): fileName += ".json"
    testObj = {"prelude": getPrelude(), "inputs": inputs, "outputs": outputs}
    err = doTest(testObj)

    if err:
        sep = "-" * 40
        print("[replTest: error verifying test]\n{}".format(sep))
        print("In file '{}'\n{}".format(fileName, sep))
        print("{}{}".format(err, sep))

    else:
        with open(fileName, "w") as file:
            file.write(json.dumps(testObj) + "\n")
        print("[replTest: saved '{}']".format(fileName))

