"""
compile_template

string_template

ListMarker

OptionMarker

MaxDepth
"""

# This file is licensed under the GNU Lesser General Public License v2.1.
# originally written for Mojo Nation by Bram Cohen, based on an earlier 
# version by Bryce Wilcox
# all subsequent changes are by Bram Cohen and are public domain

import types

def string_template(thing, verbose):
    if type(thing) != types.StringType:
        raise ValueError, "not a string"

st = string_template

def exact_length(l):
    def func(s, verbose, l = l):
        if type(s) != types.StringType:
            raise ValueError, 'should have been string'
        if len(s) != l:
            raise ValueError, 'wrong length, should have been ' + str(l) + ' was ' + str(len(s))
    return func

class MaxDepth:
    def __init__(self, max_depth, template = None):
        assert max_depth >= 0
        self.max_depth = max_depth
        self.template = template

    def get_real_template(self):
        assert self.template is not None, 'You forgot to set the template!'
        if self.max_depth == 0:
            return fail_too_deep
        self.max_depth = self.max_depth - 1
        try:
            return compile_inner(self.template)
        finally:
            self.max_depth = self.max_depth + 1

    def __repr__(self):
        if hasattr(self, 'p'):
            return '...'
        try:
            self.p = 1
            return 'MaxDepth(' + str(self.max_depth) + ', ' + `self.template` + ')'
        finally:
            del self.p

def fail_too_deep(thing, verbose):
    raise ValueError, 'recursed too deep'

class ListMarker:
    def __init__(self, template):
        self.template = template

    def get_real_template(self):
        return compile_list_template(self.template)

    def __repr__(self):
        return 'ListMarker(' + `self.template` + ')'

def compile_list_template(template):
    def func(thing, verbose, template = compile_inner(template)):
        if type(thing) not in (types.ListType, types.TupleType):
            raise ValueError, 'not a list'
        if verbose:
            try:
                for i in xrange(0, len(thing)):
                    template(thing[i], 1)
            except ValueError, e:
                reason = 'mismatch at index ' + str(i) + ': ' + str(e)
                raise ValueError, reason
        else:
            for i in thing:
                template(i, 0)
    return func

compilers = {}

def compile_string_template(template):
    assert type(template) is types.StringType
    def func(thing, verbose, template = template):
        if thing != template:
            raise ValueError, "didn't match string"
    return func

compilers[types.StringType] = compile_string_template

def int_template(thing, verbose):
    if type(thing) not in (types.IntType, types.LongType):
        raise ValueError, 'thing not of integer type'

def nonnegative_int_template(thing, verbose):
    if type(thing) not in (types.IntType, types.LongType):
        raise ValueError, 'thing not of integer type'
    if thing < 0:
        raise ValueError, 'thing less than zero'

def positive_int_template(thing, verbose):
    if type(thing) not in (types.IntType, types.LongType):
        raise ValueError, 'thing not of integer type'
    if thing <= 0:
        raise ValueError, 'thing less than or equal to zero'

def compile_int_template(s):
    assert s in (-1, 0, 1)
    if s == -1:
        return int_template
    elif s == 0:
        return nonnegative_int_template
    else:
        return positive_int_template

compilers[types.IntType] = compile_int_template
compilers[types.LongType] = compile_int_template

def compile_slice(template):
    assert type(template) is types.SliceType
    assert template.step is None
    assert template.stop is not None
    start = template.start
    if start is None:
        start = 0
    def func(thing, verbose, start = start, stop = template.stop):
        if type(thing) not in (types.IntType, types.LongType):
            raise ValueError, 'not an int'
        if thing < start:
            raise ValueError, 'thing too small'
        if thing >= stop:
            raise ValueError, 'thing too large'
    return func

compilers[types.SliceType] = compile_slice

class OptionMarker:
    def __init__(self, template):
        self.option_template = template

    def __repr__(self):
        return 'OptionMarker(' + `self.option_template` + ')'

def compile_dict_template(template):
    assert type(template) is types.DictType
    agroup = []
    bgroup = []
    cgroup = []
    optiongroup = []
    for key, value in template.items():
        if hasattr(value, 'option_template'):
            optiongroup.append((key, compile_inner(value.option_template)))
        elif type(value) is types.StringType:
            agroup.append((key, compile_inner(value)))
        elif type(value) in (types.IntType, types.LongType, types.SliceType):
            bgroup.append((key, compile_inner(value)))
        else:
            cgroup.append((key, compile_inner(value)))
    def func(thing, verbose, required = agroup + bgroup + cgroup, optional = optiongroup):
        if type(thing) is not types.DictType:
            raise ValueError, 'not a dict'
        try:
            for key, template in required:
                if not thing.has_key(key):
                    raise ValueError, 'key not present'
                template(thing[key], verbose)
            for key, template in optional:
                if thing.has_key(key):
                    template(thing[key], verbose)
        except ValueError, e:
            if verbose:
                reason = 'mismatch in key ' + `key` + ': ' + str(e)
                raise ValueError, reason
            else:
                raise
    return func

compilers[types.DictType] = compile_dict_template

def none_template(thing, verbose):
    if thing is not None:
        raise ValueError, 'thing was not None'

compilers[types.NoneType] = lambda template: none_template

def compile_or_template(template):
    assert type(template) in (types.ListType, types.TupleType)
    def func(thing, verbose, templ = [compile_inner(x) for x in template]):
        if verbose:
            failure_reason = 'did not match any of the ' + str(len(templ)) + ' possible templates;'
            for i in xrange(len(templ)):
                try:
                    templ[i](thing, 1)
                    return
                except ValueError, reason:
                    failure_reason = failure_reason + ' failed template at index ' + str(i) + ' because (' + str(reason) + ')'
            raise ValueError, failure_reason
        else:
            for i in templ:
                try:
                    i(thing, 0)
                    return
                except ValueError:
                    pass
            raise ValueError, "did not match any possible templates"
    return func

compilers[types.ListType] = compile_or_template
compilers[types.TupleType] = compile_or_template

def compile_inner(template):
    while hasattr(template, 'get_real_template'):
        template = template.get_real_template()
    if callable(template):
        return template
    return compilers[type(template)](template)

def compile_template(template):
    def func(thing, t = compile_inner(template), s = `template`):
        try:
            t(thing, 0)
        except ValueError:
            try:
                t(thing, 1)
                assert 0
            except ValueError, reason:
                raise ValueError, 'failed template check because: (' + str(reason) + ') target was:(' + `thing` + ') template was: (' + s + ')'
    return func

def test_slice():
    f = compile_template(slice(4))
    f(0)
    f(3L)
    try:
        f(-1)
        assert 0
    except ValueError:
        pass
    try:
        f(4L)
        assert 0
    except ValueError:
        pass
    try:
        f('a')
        assert 0
    except ValueError:
        pass

    f = compile_template(slice(-2, 3))
    f(-2L)
    f(2)
    try:
        f(-3L)
        assert 0
    except ValueError:
        pass
    try:
        f(3)
        assert 0
    except ValueError:
        pass
    try:
        f('a')
        assert 0
    except ValueError:
        pass

def test_int():
    f = compile_template(0)
    f(0)
    f(1L)
    try:
        f(-1)
        assert 0
    except ValueError:
        pass
    try:
        f('a')
        assert 0
    except ValueError:
        pass

    f = compile_template(-1)
    f(0)
    f(1)
    f(-1L)
    try:
        f('a')
        assert 0
    except ValueError:
        pass

    f = compile_template(1)
    try:
        f(0)
        assert 0
    except ValueError:
        pass
    f(1)
    try:
        f(-1)
        assert 0
    except ValueError:
        pass
    try:
        f('a')
        assert 0
    except ValueError:
        pass

def test_none():
    f = compile_template(None)
    f(None)
    try:
        f(0)
        assert 0
    except ValueError:
        pass

def test_string():
    f = compile_template('a')
    f('a')
    try:
        f('b')
        assert 0
    except ValueError:
        pass
    try:
        f(0)
        assert 0
    except ValueError:
        pass

def test_generic_string():
    f = compile_template(st)
    f('a')
    try:
        f(0)
        assert 0
    except ValueError:
        pass

def test_list():
    f = compile_template(ListMarker(['a']))
    f(['a'])
    f(('a', 'a'))
    try:
        f(('a', 'b'))
        assert 0
    except ValueError:
        pass
    try:
        f(('b', 'a'))
        assert 0
    except ValueError:
        pass
    try:
        f('a')
        assert 0
    except ValueError:
        pass

def test_or():
    f = compile_template(['a', 'b'])
    f('a')
    f('b')
    try:
        f('c')
        assert 0
    except ValueError:
        pass

    f = compile_template(('a', 'b'))
    f('a')
    f('b')
    try:
        f('c')
        assert 0
    except ValueError:
        pass

def test_dict():
    f = compile_template({'a': 'b', 'c': OptionMarker('d')})
    try:
        f({})
        assert 0
    except ValueError:
        pass
    f({'a': 'b'})
    try:
        f({'a': 'e'})
        assert 0
    except ValueError:
        pass
    try:
        f({'c': 'd'})
        assert 0
    except ValueError:
        pass
    f({'a': 'b', 'c': 'd'})
    try:
        f({'a': 'e', 'c': 'd'})
        assert 0
    except ValueError:
        pass
    try:
        f({'c': 'f'})
        assert 0
    except ValueError:
        pass
    try:
        f({'a': 'b', 'c': 'f'})
        assert 0
    except ValueError:
        pass
    try:
        f({'a': 'e', 'c': 'f'})
        assert 0
    except ValueError:
        pass
    try:
        f(None)
        assert 0
    except ValueError:
        pass

def test_other_func():
    def check3(thing, verbose):
        if thing != 3:
            raise ValueError
    f = compile_template(check3)
    f(3)
    try:
        f(4)
        assert 0
    except ValueError:
        pass

def test_max_depth():
    md = MaxDepth(2)
    t = {'a': OptionMarker(ListMarker(md))}
    md.template = t
    f = compile_template(md)
    f({'a': [{'a': []}]})
    f({'a': [{'a': []}]})
    try:
        f({'a': [{'a': [{}]}]})
        assert 0
    except ValueError:
        pass
    try:
        f({'a': [{'a': [{}]}]})
        assert 0
    except ValueError:
        pass
    f({'a': [{'a': []}]})
    try:
        f({'a': [{'a': [{}]}]})
        assert 0
    except ValueError:
        pass





