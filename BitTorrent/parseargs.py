# Written by Bram Cohen
# this file is public domain

from getopt import getopt
from types import *
import sys
import string
from cStringIO import StringIO

def longLineForm(longDescription):
    if longDescription[-1:] == '=':
        return '--' + longDescription[0:-1]
    else:
        return '--' + longDescription

def shortLineForm(shortDescription):
    return '-' + shortDescription[:1]

def takesArgument(aDescription):
    if aDescription[-1:] in [':', '=']:
        return 1
    else:
        return 0

def combinedLineForm(longDescription, shortDescription):
    s = ""
    if longDescription:
        s = longLineForm(longDescription)
    if shortDescription:
        if len(s): s = s + "/" + shortLineForm(shortDescription)
        else: s = shortLineForm(shortDescription)

    if takesArgument(longDescription):
        s = s + " <arg>"

    return s

def formatDefinitions(optionDefinitions, COLS):
    s = StringIO()
    outArray = []
    for i in optionDefinitions:
        garbage, longDescription, shortDescription, default, doc = i

        lineForm = combinedLineForm(longDescription, shortDescription)
        if default is not None:
            doc += ' defaults to ' + `default`
        outArray.append( (lineForm, doc) )

    bodyLineString = " " * 10
    targetBodyWidth = COLS - 11

    if targetBodyWidth < 15:
        targetBodyWidth = COLS - 2
        bodyLineString = " "

    for head, body in outArray:
        s.write(head + '\n')
        splitBody = string.split(body)
        outAmount = 0
        for aWord in splitBody:
            if outAmount == 0:
                s.write(bodyLineString + aWord)
                outAmount = len(aWord)
            elif outAmount + len(aWord) >= targetBodyWidth:
                s.write("\n" + bodyLineString + aWord)
                outAmount = len(aWord)
            else:
                s.write(' ' + aWord)
                outAmount += len(aWord) + 1
        s.write("\n\n")
    return s.getvalue()

def usage(str):
    raise ValueError(str)

def checkOpt(config, commandLineOptionValue, shortOptDictionary, longOptDictionary):
    key, value = commandLineOptionValue

    if shortOptDictionary.has_key(key):
        configName, longDescription, shortDescription, defaultValue, usageText = shortOptDictionary[key]
    elif longOptDictionary.has_key(key):
        configName, longDescription, shortDescription, defaultValue, usageText = longOptDictionary[key]
    else:
        assert 0

    try:
        t = type(config.get(configName))
        if t is NoneType or t is StringType:
            config[configName] = value
        elif t is IntType or t is LongType:
            config[configName] = long(value)
        elif t is FloatType:
            config[configName] = float(value)
        else:
            assert 0
    except ValueError, e:
        usage('wrong format of %s - %s' % (key, str(e)))

def parseargs(argv, optionDefinitions, minimumArgs, maximumArgs):
    config = {}
    reqDict = {}

    ## generate getopt style argument descriptions and argument processing dictionaries
    shortGetOptString = ""
    longGetOptArray = []
    shortOptDictionary = {}
    longOptDictionary = {}
    for optionDescription in optionDefinitions:
        configName, longDescription, shortDescription, defaultValue, usageText = optionDescription
        if shortDescription:
            shortGetOptString = shortGetOptString + shortDescription
            shortOptDictionary[shortLineForm(shortDescription)] = optionDescription

        if longDescription:
            longGetOptArray.append(longDescription)
            longOptDictionary[longLineForm(longDescription)] = optionDescription

        if defaultValue is None:
            reqDict[configName] = optionDescription
        else:
            config[configName] = defaultValue
            
    ## parse arguments
    try:
        optionList, bareArgs = getopt(argv, shortGetOptString, longGetOptArray)
    except:
        usage(sys.exc_info()[1])

    ## process args and set defaults
    for anOpt in optionList:
        checkOpt(config, anOpt, shortOptDictionary, longOptDictionary)

    for requiredKey in reqDict.keys():
        if not config.has_key(requiredKey):
            configName, longDescription, shortDescription, defaultValue, usageText = reqDict[requiredKey]
            s = None
            if longDescription:
                s = longLineForm(longDescription)
            if shortDescription:
                if s:
                    s += "/" + shortLineForm(shortDescription)
                else:
                    s = shortLineForm(shortDescription)
            usage("Option %s is required." % s)

    ## verify arg quantities
    if len(bareArgs) < minimumArgs:
        usage("Must supply at least %d args." % minimumArgs)
    if len(bareArgs) > maximumArgs:
        usage("Too many args;  %d max, encountered %d." % (maximumArgs, len(bareArgs)))

    return (config, bareArgs)
