# Written by Bram Cohen
# this file is public domain

from getopt import getopt
import sys

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

def usage(usageHeading, optionDefintions, msg, exitCode=1):
    if msg:
        sys.stderr.write('error: %s\n' % msg)
    sys.stdout.write('%s\n' % usageHeading)
    for configName, longDescription, shortDescription, defaultValue, usageText in optionDefintions:
        argDescript = ""
        if longDescription:
            if takesArgument(longDescription):
                sys.stdout.write(longLineForm(longDescription) + " <value>\n")
            else:
                sys.stdout.write(longLineForm(longDescription) + "\n")

        if shortDescription:
            if takesArgument(shortDescription):
                sys.stdout.write(shortLineForm(shortDescription) + '<value>\n')
            else:
                sys.stdout.write(shortLineForm(shortDescription) + '\n')

        if defaultValue: sys.stdout.write("\tdefault value: %s" % defaultValue)
        sys.stdout.write("\t%s\n\n" % usageText)

    sys.exit(exitCode)


def checkOpt( configurationDictionary, commandLineOptionValue, shortOptDictionary, longOptDictionary, setValue = None):
    key, value = commandLineOptionValue

    if key and shortOptDictionary.has_key(key):
        configName, longDescription, shortDescription, defaultValue, usageText = shortOptDictionary[key]
    elif key and longOptDictionary.has_key(key):
        configName, longDescription, shortDescription, defaultValue, usageText = longOptDictionary[key]
    else:
        usage("Encountered key '%s' that passed getopt() but was not in opt dict.  Very confused. Dieing!" % key)

    if configName == None:
        usage(None)

    if (value == '') and setValue and configurationDictionary.has_key(configName):
        configurationDictionary[configName] = setValue
    else:
        configurationDictionary[configName] = value

def getKeyOrNone(d, k):
    try: return d[k]
    except: return None

def parseargs(argv, usageHeading, optionDefinitions, minimumArgs, maximumArgs, requiredConfig=[]):
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

        if defaultValue:
            config[configName] = defaultValue

        if configName in requiredConfig:
            reqDict[configName] = optionDescription
            
    ## parse arguments
    try:
        optionList, bareArgs = getopt(argv, shortGetOptString, longGetOptArray)
    except:
        exc_value = sys.exc_info()[1]
        usage(usageHeading, optionDefinitions, exc_value)

    ## process args and set defaults
    for anOpt in optionList:
        checkOpt( config, anOpt, shortOptDictionary, longOptDictionary )

    if requiredConfig:
        for requiredKey in requiredConfig:
            if not config.has_key(requiredKey):
                configName, longDescription, shortDescription, defaultValue, usageText = reqDict[requiredKey]
                s = None
                if longDescription:
                    s = longLineForm(longDescription)
                if shortDescription:
                    if s: s = s + "/" + shortLineForm(shortDescription)
                    else: s = shortLineForm(shortDescription)
                usage(usageHeading, optionDefinitions, "Option %s is required." % s)

    ## verify arg quantities
    if len(bareArgs) < minimumArgs:
        usage(usageHeading, optionDefinitions, "Must supply at least %d args." % minimumArgs)
    if len(bareArgs) > maximumArgs:
        usage(usageHeading, optionDefinitions, "Too many args;  %d max, encountered %d." % (maximumArgs, len(bareArgs)))

    return (config, bareArgs)
