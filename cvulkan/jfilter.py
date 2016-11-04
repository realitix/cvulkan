'''Module containing custom jinj2 filters

All the shit is here man! The rest is heaven compared to this garbage.
I have hiden the conversion functions here (c_to_py py_to_c) because
it can't be made beautiful.
Enjoy the pain!
'''

__all__ = ['join_comma', 'kwlist', 'parse_tuple_and_keywords',
           'python_to_c', 'c_to_python', 'init_function_members',
           'copy_in_object']

# Vulkan signatures with this data model
# signatures = [{
#    'raw': 'signature',
#    'vkname': 'vkname',
#    'is_struct': True,
#    'is_union': False,
#    'is_handle': False}]
vulkan_signatures = None


def join_comma(members, without_n=0, prefix=''):
    dot = ','
    if not without_n:
        without_n = None
        dot = ''
    else:
        without_n = -without_n

    if not members[:without_n]:
        return ''

    return ','.join([prefix + m['name'] for m in members[:without_n]]) + dot


def members_formated(members):
    return [m for m in members
            if not m.get('to_create') and not m.get('null')]


def init_function_members(members):
    result = ''
    for m in members_formated(members):
        result += 'PyObject* %s = NULL;\n' % m['name']

    return result


def kwlist(members):
    members = members_formated(members)
    if not members:
        return ''

    result = ','.join(['"%s"' % m['name'] for m in members])
    result += ',NULL'
    return "static char *kwlist[] = {%s};" % result


def parse_tuple_and_keywords(members):
    members = members_formated(members)
    if not members:
        return ''

    var_names = ','.join(["&"+m['name'] for m in members_formated(members)])
    o = 'O' * len(members)
    return '''
    if( !PyArg_ParseTupleAndKeywords(args, kwds, "{o}", kwlist, {names}))
        return 0;
    '''.format(o=o, names=var_names)


def copy_in_object(cname, member):
    '''Insert c value named cname into member
    Depending on the type, the way to do it can change
    '''
    mname = member['name']
    if member['type'] == 'char []':
        return 'strcpy((self->base)->{mname}, {cname});'.format(
            cname=cname, mname=mname)
    if member['type'].endswith('[2]'):
        return '''
        memcpy((self->base)->{mname}, {cname}, 2 * sizeof({mtype}));
        '''.format(mname=mname, cname=cname, mtype=member['raw_type'])
    if member['type'].endswith('[4]'):
        return '''
        memcpy((self->base)->{mname}, {cname}, 4 * sizeof({mtype}));
        '''.format(mname=mname, cname=cname, mtype=member['raw_type'])
    if member['enum']:
        return '''
        memcpy((self->base)->{mname}, {cname}, {enum} * sizeof({mtype}));
        '''.format(mname=mname, cname=cname, mtype=member['raw_type'],
                   enum=member['enum'])
    return '(self->base)->{mname} = {cname};'.format(
            cname=cname, mname=mname)


def python_to_c(member, pyname, cname, return_value='NULL',
                force_array=False):
    '''Convert python object to C value

    member: member to convert
    pyname: name of python variable to convert
    cname : name of resulting c variable
    This function is huge because there is lot of types to compare'''
    global vulkan_signatures

    if member.get('to_create'):
        return ''

    if member.get('null'):
        return '{} {} = NULL;'.format(member['type'], cname)

    def t(ct):
        if member['type'] == ct:
            return True
        return False

    def list_generic(ctype, py_function):
        '''Convert a python list to array

        ctype: type in c
        py_function: function used to convert py object
        '''
        return '''
        {ctype}* {cname} = NULL;
        {{
            int size = PyList_Size({pyname});
            {cname} = malloc(sizeof({ctype}) * size);
            int i;
            for (i = 0; i < size; i++) {{
                {ctype} r = ({ctype}) {py_function}(
                    PyList_GetItem({pyname}, i));
                memcpy({cname} + i, &r, sizeof({ctype}));
            }}
        }}'''.format(ctype=ctype, cname=cname,
                     pyname=pyname, py_function=py_function)

    def basic_generic(ctype, py_function):
        return '''
            {ctype} {cname} = ({ctype}) {py_function}({pyname});
        '''.format(ctype=ctype, cname=cname,
                   pyname=pyname, py_function=py_function)

    # ----------------
    # NATIVE C TYPES
    # ----------------
    for ctype in ('uint32_t', 'uint64_t', 'int32_t', 'size_t',
                  'Window', 'Display *'):
        if t(ctype):
            return basic_generic(ctype, 'PyLong_AsLong')
    if t('float'):
        return basic_generic('float', 'PyFloat_AsDouble')
    if t('void *'):
        return 'void* {cname} = NULL;'.format(cname=cname)
    if t('char []') or t('char *'):
        return '''
        char* {cname} = NULL;
        if ({pyname} != Py_None)
        {{
            PyObject* tmp0 = PyUnicode_AsASCIIString({pyname});
            if (tmp0 == NULL) {{
                PyErr_SetString(PyExc_TypeError, "{pyname} must be a string");
                return {return_value};
            }}
            char* tmp1 = PyBytes_AsString(tmp0);
            {cname} = strdup(tmp1);
            Py_DECREF(tmp0);
        }}'''.format(pyname=pyname, cname=cname, return_value=return_value)
    if t('char * const*'):
        return '''
        char** {cname} = NULL;
        {{
            int size = PyList_Size({pyname});
            {cname} = malloc(sizeof(char*) * size);
            int i;
            for (i = 0; i < size; i++) {{
                PyObject* item = PyList_GetItem({pyname}, i);
                if (item == NULL) return {return_value};

                PyObject* ascii_str = PyUnicode_AsASCIIString(item);
                if (ascii_str == NULL) {{
                    PyErr_SetString(PyExc_TypeError,
                    "{pyname} must be a list of strings");
                    return {return_value};
                }}

                char* tmp = PyBytes_AsString(ascii_str);
                {cname}[i] = strdup(tmp);
                Py_DECREF(ascii_str);
            }}
        }}'''.format(cname=cname, pyname=pyname, return_value=return_value)
    if t('float [2]') or t('float [4]') or t('float *'):
        return list_generic('float', 'PyFloat_AsDouble')
    if t('uint32_t [2]') or t('uint32_t [3]') or \
       t('uint32_t [4]') or t('uint32_t const *'):
        return list_generic('uint32_t', 'PyLong_AsLong')
    if t('int32_t [4]'):
        return list_generic('int32_t', 'PyLong_AsLong')
    if t('uint8_t []'):
        return list_generic('uint8_t', 'PyLong_AsLong')
    if t('wl_display struct *'):
        return '''
        struct wl_display* {cname} =
        (struct wl_display*) PyLong_AsLong({pyname});
        '''.format(cname=cname, pyname=pyname)
    if t('wl_surface struct *'):
        return '''
        struct wl_surface* {cname} =
        (struct wl_surface*) PyLong_AsLong({pyname});
        '''.format(cname=cname, pyname=pyname)
    if t('xcb_connection_t *'):
        return basic_generic('xcb_connection_t *', 'PyLong_AsLong')

    # ----------------
    # VULKAN TYPES
    # ----------------
    for signature in vulkan_signatures:
        raw_signature = signature['raw']
        vkname = signature['vkname']
        if not t(raw_signature):
            continue

        if signature['is_struct'] or signature['is_union']:
            # pointer
            if (raw_signature.endswith('*') and force_array) \
               or raw_signature.endswith(']'):
                return '''
                {vkname}* {cname} = NULL;
                {{
                    int size = PyList_Size({pyname});
                    {cname} = malloc(sizeof({vkname}));
                    int i;
                    for (i = 0; i < size; i++) {{
                        {cname}[i] = *( (
                            (Py{vkname}*) PyList_GetItem({pyname}, i) )->base);
                    }}
                }}
                '''.format(cname=cname, pyname=pyname, vkname=vkname)
            elif raw_signature.endswith('*') and not force_array:
                return '''
                {vkname}* {cname} = ((Py{vkname}*){pyname})->base;
                '''.format(cname=cname, pyname=pyname, vkname=vkname)
            else:
                return '''
                {vkname} {cname} = *(((Py{vkname}*){pyname})->base);
                '''.format(vkname=vkname, cname=cname, pyname=pyname)
        elif signature['is_handle']:
            deference = '' if member['type'].endswith('*') else '*'
            inv_deference = '*' if not deference else ''
            return '''
            {vkname}{inv_deference} {cname} = NULL;
            {{
                {vkname}* handle_pointer = PyCapsule_GetPointer(
                    {pyname}, "{vkname}");
                {cname} = {deference}handle_pointer;
            }}
            '''.format(vkname=vkname, cname=cname, pyname=pyname,
                       deference=deference, inv_deference=inv_deference)
        # int type
        else:
            if raw_signature.endswith('*'):
                return '''
                    {vkname}* {cname} = malloc(sizeof({vkname}));
                    {{
                        {vkname} tmp = ({vkname}) PyLong_AsLong({pyname});
                        memcpy({cname}, &tmp, sizeof({vkname}));
                    }}
                '''.format(vkname=vkname, cname=cname, pyname=pyname)
            else:
                return '''
                    {vkname} {cname} = ({vkname}) PyLong_AsLong({pyname});
                    '''.format(vkname=vkname, cname=cname, pyname=pyname)
    return None


def c_to_python(member, cname, pyname):
    global vulkan_signatures

    def t(ct):
        if member['type'] == ct:
            return True
        return False

    def basic_generic(pyctype, pyfunction):
        return '''
            PyObject* {pyname} = {pyfunction}(({pyctype}) {cname});
        '''.format(cname=cname, pyname=pyname, pyctype=pyctype,
                   pyfunction=pyfunction)

    def list_convert(pyctype, pyfunction):
        return '''
        PyObject* {pyname} = PyList_New(0);
        int nb = sizeof({cname}) / sizeof({cname}[0]);
        int i = 0;
        for (i = 0; i < nb; i++) {{
            PyObject* tmp = {pyfunction}(({pyctype}) {cname}[i]);
            PyList_Append({pyname}, tmp);
        }}
        '''.format(pyname=pyname, cname=cname, pyctype=pyctype,
                   pyfunction=pyfunction)

    # ----------------
    # NATIVE C TYPES
    # ----------------
    for ctype in ('uint32_t', 'int32_t', 'size_t', 'uint64_t'):
        if t(ctype):
            return basic_generic('long', 'PyLong_FromLong')
    if t('float'):
        return basic_generic('double', 'PyFloat_FromDouble')
    if t('char []') or t('char *'):
        return '''
        PyObject* {pyname} = PyUnicode_FromString((const char *) {cname});
        '''.format(pyname=pyname, cname=cname)
    if t('char * const*'):
        return '''
        if ({cname}[0] == NULL)
            return PyList_New(0);
        PyObject* {pyname} = PyList_New(0);
        int i = 0;
        while ({cname}[i] != NULL) {{
            PyObject* tmp = PyUnicode_FromString((const char *) {cname}[i]);
            PyList_Append({pyname}, tmp);
            i++;
        }}
        '''.format(pyname=pyname, cname=cname)
    if t('float [2]') or t('float [4]'):
        return list_convert('double', 'PyFloat_FromDouble')
    if t('uint32_t [2]') or t('uint32_t [3]') or t('uint8_t []') or \
       t('int32_t [4]') or t('uint32_t [4]'):
        return list_convert('long', 'PyLong_FromLong')
    if t('float *'):
        return '''
        PyObject* {pyname} = PyFloat_FromDouble((double) (*({cname})));
        '''.format(pyname=pyname, cname=cname)
    if t('uint32_t *'):
        return '''
        PyObject* {pyname} = PyLong_FromLong((long) (*({cname})));
        '''.format(pyname=pyname, cname=cname)
    if t('void *') or t('Window') or t('Display *') or \
       t('wl_display struct *') or t('wl_surface struct *') or \
       t('xcb_connection_t *'):
        return '''
        Py_INCREF(Py_None);
        PyObject* {pyname} = Py_None;
        '''.format(pyname=pyname)

    # ----------------
    # VULKAN TYPES
    # ----------------
    for signature in vulkan_signatures:
        raw_signature = signature['raw']
        vkname = signature['vkname']
        if not t(raw_signature):
            continue

        if signature['is_struct'] or signature['is_union']:
            if raw_signature.endswith(']'):
                return '''
                PyObject* {pyname} = PyList_New(0);
                int nb = sizeof({cname}) / sizeof({cname}[0]);
                int i = 0;
                for (i = 0; i < nb; i++) {{
                    PyObject* tmp = _PyObject_New(&Py{vkname}Type);
                    if (!tmp)
                        return NULL;
                    ((Py{vkname}*) tmp)->base = {cname};
                    PyList_Append({pyname}, tmp);
                }}
                '''.format(cname=cname, vkname=vkname, pyname=pyname)

            star = '&'
            if raw_signature.endswith('*'):
                star = ''

            return '''
            PyObject* {pyname} = _PyObject_New(&Py{vkname}Type);
            if (!{pyname})
                return NULL;
            ((Py{vkname}*) {pyname})->base = {star}{cname};
            '''.format(pyname=pyname, vkname=vkname, cname=cname, star=star)
        elif signature['is_handle']:
            pass
        else:
            star = ''
            if raw_signature.endswith('*'):
                star = '*'

            return '''
            PyObject* {pyname} = PyLong_FromLong({star}{cname});
            '''.format(pyname=pyname, cname=cname, star=star)

    return None
