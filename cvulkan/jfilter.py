'''Module containing custom jinj2 filters

All the shit is here man! The rest is heaven compared to this garbage.
I have hiden the conversion functions here (c_to_py py_to_c) because
it can't be made beautiful.
Enjoy the pain!
'''

__all__ = ['join_comma', 'kwlist', 'parse_tuple_and_keywords',
           'c_to_python', 'init_function_members',
           'copy_in_object', 'format_fname', 'free_pyc']

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

    names = []
    for m in members[:without_n]:
        if m.get('null'):
            names.append('NULL')
        else:
            names.append(m['name'])

    return ','.join(names) + dot


def members_formated(members):
    return [m for m in members
            if not m.get('to_create') and not m.get('null')]


def init_member(member):
    def t(ct):
        if member['type'] == ct:
            return True
        return False

    def from_type(ctype):
        return '%s %s;\n' % (ctype, member['name'])

    # ----------------
    # NATIVE C TYPES
    # ----------------
    for ctype in ('uint32_t', 'uint64_t', 'int32_t', 'size_t', 'Window',
                  'Display *', 'float', 'void *', 'xcb_connection_t *',
                  'xcb_visualid_t', 'xcb_window_t', 'ANativeWindow *',
                  'MirConnection *', 'MirSurface *', 'HINSTANCE',
                  'HWND', 'HANDLE', 'SECURITY_ATTRIBUTES *', 'DWORD',
                  'MirConnection *', 'VisualID'):
        if t(ctype):
            return from_type(ctype)
    if t('char []') or t('char *'):
        return from_type('char*')
    if t('char * const*'):
        return from_type('char**')
    if t('float [2]') or t('float [4]') or t('float *'):
        return from_type('float*')
    if t('uint32_t [2]') or t('uint32_t [3]') or \
       t('uint32_t [4]') or t('uint32_t *'):
        return from_type('uint32_t*')
    if t('int32_t [4]'):
        return from_type('int32_t*')
    if t('uint64_t *'):
        return from_type('uint64_t*')
    if t('uint8_t []'):
        return from_type('uint8_t*')
    if t('wl_display struct *'):
        return from_type('struct wl_display*')
    if t('wl_surface struct *'):
        return from_type('struct wl_surface*')

    # ----------------
    # VULKAN TYPES
    # ----------------
    for signature in vulkan_signatures:
        raw_signature = signature['raw']
        vkname = signature['vkname']
        if not t(raw_signature):
            continue

        if signature['is_struct'] or signature['is_union']:
            if raw_signature.endswith('*') or raw_signature.endswith(']'):
                return from_type('%s*' % vkname)
            else:
                return from_type(vkname)
        elif signature['is_handle']:
            if member['type'].endswith('*'):
                return from_type('%s*' % vkname)
            else:
                return from_type(vkname)
        else:
            if raw_signature.endswith('*'):
                return from_type('%s*' % vkname)
            else:
                return from_type(vkname)
    return '//cant init member\n'


def init_function_members(members):
    result = ''
    for m in members_formated(members):
        result += init_member(m)

    return result


def kwlist(members):
    members = members_formated(members)
    if not members:
        return ''

    result = ','.join(['"%s"' % m['name'] for m in members])
    result += ',NULL'
    return "static char *kwlist[] = {%s};" % result


def format_fname(name):
    '''Well format function name'''
    return name.replace(' ', '_').replace('*', 'x')


def detect_py_to_c(member):
    def t(ct):
        if member['type'] == ct:
            return True
        return False

    # ----------------
    # NATIVE C TYPES
    # ----------------
    for ctype in ('uint32_t', 'uint64_t', 'int32_t', 'size_t', 'Window',
                  'Display *', 'xcb_connection_t *', 'float', 'void *',
                  'xcb_window_t', 'ANativeWindow *', 'MirConnection *',
                  'MirSurface *', 'HINSTANCE', 'HWND', 'HANDLE',
                  'SECURITY_ATTRIBUTES *', 'DWORD', 'MirConnection *',
                  'VisualID', 'xcb_visualid_t'):
        if t(ctype):
            return 'pyc_%s_converter' % format_fname(ctype)
    if t('char []') or t('char *'):
        return 'pyc_string_converter'
    if t('char * const*'):
        return 'pyc_array_string_converter'
    if t('float [2]') or t('float [4]') or t('float *'):
        return 'pyc_array_float_converter'
    if t('uint32_t [2]') or t('uint32_t [3]') or \
       t('uint32_t [4]') or t('uint32_t *'):
        return 'pyc_array_uint32_t_converter'
    if t('int32_t [4]'):
        return 'pyc_array_int32_t_converter'
    if t('uint8_t []'):
        return 'pyc_array_uint8_t_converter'
    if t('uint64_t *'):
        return 'pyc_array_uint64_t_converter'
    if t('wl_display struct *'):
        return 'pyc_wl_display_converter'
    if t('wl_surface struct *'):
        return 'pyc_wl_surface_converter'

    # ----------------
    # VULKAN TYPES
    # ----------------
    force_array = member.get('force_array')
    for signature in vulkan_signatures:
        raw_signature = signature['raw']
        vkname = signature['vkname']
        if not t(raw_signature):
            continue

        if signature['is_struct'] or signature['is_union']:
            if (raw_signature.endswith('*') and force_array) \
               or raw_signature.endswith(']'):
                return 'pyc_struct_array_%s_converter' % vkname
            elif raw_signature.endswith('*') and not force_array:
                return 'pyc_struct_pointer_%s_converter' % vkname
            else:
                return 'pyc_struct_base_%s_converter' % vkname
        elif signature['is_handle']:
            if force_array:
                return 'pyc_handle_array_%s_converter' % vkname
            elif member['type'].endswith('*'):
                return 'pyc_handle_pointer_%s_converter' % vkname
            else:
                return 'pyc_handle_base_%s_converter' % vkname
        else:
            if raw_signature.endswith('*') and member.get('len'):
                return 'pyc_flag_array_%s_converter' % vkname
            elif raw_signature.endswith('*'):
                return 'pyc_flag_pointer_%s_converter' % vkname
            else:
                return 'pyc_flag_base_%s_converter' % vkname

    return 'cant_detect_py_to_c'


def parse_tuple_and_keywords(members, optional=False, return_value='NULL'):
    '''Parse Python object to C type'''
    members = members_formated(members)
    if not members:
        return ''

    options = []
    var_names = []

    for member in members:
        name = detect_py_to_c(member)
        options += 'O&'
        var_names.append(name)
        var_names.append('&%s' % member['name'])

    options = ''.join(options)
    var_names = ','.join(var_names)
    return '''
    if( !PyArg_ParseTupleAndKeywords(args, kwds,
        "{optional}{o}", kwlist, {names}))
        return {return_value};
    '''.format(o=options, optional='|' if optional else '',
               names=var_names, return_value=return_value)


def free_pyc(members, disable=False):
    '''Call functions to free each member'''
    members = members_formated(members)
    if not members:
        return ''

    result = ''
    for m in members:
        fname = detect_py_to_c(m) + '_free'
        result += '%s(&%s, %s);\n' % (fname, m['name'], 1 if disable else 0)

    return result


def copy_in_object(member):
    '''Insert c value named cname into member
    Depending on the type, the way to do it can change
    '''
    mname = member['name']

    if member.get('null'):
        return '(self->base)->{mname} = NULL;'.format(mname=mname)
    if member['type'] == 'char []':
        return 'strcpy((self->base)->{mname}, {mname});'.format(mname=mname)
    if member['type'].endswith('[2]'):
        return '''
        memcpy((self->base)->{mname}, {mname}, 2 * sizeof({mtype}));
        '''.format(mname=mname, mtype=member['raw_type'])
    if member['type'].endswith('[4]'):
        return '''
        memcpy((self->base)->{mname}, {mname}, 4 * sizeof({mtype}));
        '''.format(mname=mname, mtype=member['raw_type'])
    if member['enum']:
        return '''
        memcpy((self->base)->{mname}, {mname}, {enum} * sizeof({mtype}));
        '''.format(mname=mname, mtype=member['raw_type'],
                   enum=member['enum'])
    return '(self->base)->{mname} = {mname};'.format(mname=mname)


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
        if ({pyname} == Py_None) {{
            {cname} = VK_NULL_HANDLE;
        }}
        else if (PyBytes_CheckExact({pyname})) {{
            {cname} = ({ctype}*) PyBytes_AsString({pyname});
        }}
        else {{
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
    for ctype in (
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
       t('uint32_t [4]') or t('uint32_t *'):
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
                if ({pyname} != Py_None) {{
                    int size = PyList_Size({pyname});
                    {cname} = malloc(size * sizeof({vkname}));
                    int i;
                    for (i = 0; i < size; i++) {{
                        {cname}[i] = *( (
                            (Py{vkname}*) PyList_GetItem({pyname}, i) )->base);
                    }}
                }}
                '''.format(cname=cname, pyname=pyname, vkname=vkname)
            elif raw_signature.endswith('*') and not force_array:
                return '''
                {vkname}* {cname} = NULL;
                if ({pyname} != Py_None) {{
                    {cname} = ((Py{vkname}*){pyname})->base;
                }}
                '''.format(cname=cname, pyname=pyname, vkname=vkname)
            else:
                return '''
                {vkname} {cname} = *(((Py{vkname}*){pyname})->base);
                '''.format(vkname=vkname, cname=cname, pyname=pyname)
        elif signature['is_handle'] and force_array:
            return '''
                {vkname}* {cname} = VK_NULL_HANDLE;
                if ({pyname} != Py_None)  {{
                    int size = PyList_Size({pyname});
                    {cname} = malloc(size * sizeof({vkname}));
                    int i;
                    for (i = 0; i < size; i++) {{
                        {vkname}* handle_pointer = PyCapsule_GetPointer(
                        PyList_GetItem({pyname}, i), "{vkname}");
                        {cname}[i] = *handle_pointer;
                    }}
                }}
            '''.format(vkname=vkname, cname=cname, pyname=pyname)
        elif signature['is_handle'] and not force_array:
            deference = '' if member['type'].endswith('*') else '*'
            inv_deference = '*' if not deference else ''
            return '''
                {vkname}{inv_deference} {cname} = VK_NULL_HANDLE;
                if ({pyname} != Py_None)  {{
                    {vkname}* handle_pointer = PyCapsule_GetPointer(
                        {pyname}, "{vkname}");
                    {cname} = {deference}handle_pointer;
                }}
            '''.format(vkname=vkname, cname=cname, pyname=pyname,
                       deference=deference, inv_deference=inv_deference)
        # int type
        else:
            if raw_signature.endswith('*') and member.get('len'):
                return '''
                    {vkname}* {cname} = NULL;
                    if ({pyname} != Py_None) {{
                        int size = PyList_Size({pyname});
                        {cname} = malloc(size * sizeof({vkname}));
                        int i;
                        for (i = 0; i < size; i++) {{
                            {vkname} tmp = ({vkname}) PyLong_AsLong(
                                PyList_GetItem({pyname}, i));
                            {cname}[i] = tmp;
                        }}
                    }}
                '''.format(vkname=vkname, cname=cname, pyname=pyname)
            elif raw_signature.endswith('*'):
                return '''
                    {vkname}* {cname} = NULL;
                    if ({pyname} != Py_None) {{
                        {cname} = malloc(sizeof({vkname}));
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
