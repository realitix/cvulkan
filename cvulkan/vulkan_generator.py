from contextlib import contextmanager
import random
import requests
from subprocess import call
import xmltodict


VULKAN_PLATEFORM_URL = ('http://raw.githubusercontent.com/KhronosGroup/'
                        'Vulkan-Docs/1.0/src/vulkan/vk_platform.h')
VULKAN_H_URL = ('http://raw.githubusercontent.com/KhronosGroup/'
                'Vulkan-Docs/1.0/src/vulkan/vulkan.h')
VK_XML_URL = ('http://raw.githubusercontent.com/KhronosGroup/'
              'Vulkan-Docs/1.0/src/spec/vk.xml')
OUT_FILE = 'vulkanmodule.c'

DEFINE_HEADER = '''
#include <Python.h>
#include <dlfcn.h>

#define VK_NO_PROTOTYPES

#ifdef __unix__

#define LOAD_SDK() dlopen("libvulkan.so", RTLD_NOW);

#elif defined(_WIN32) || defined(WIN32)

#define LOAD_SDK() LoadLibrary("vulkan-1.dll");
#define dlsym GetProcAddress

#endif
'''

# Struct and command which need to be surrounded by #define
MAPPING_EXTENSION_DEFINE = {
    'VkAndroidSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_ANDROID_KHR',
    'VkMirSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_MIR_KHR',
    'VkWaylandSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_WAYLAND_KHR',
    'VkWin32SurfaceCreateInfoKHR': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkImportMemoryWin32HandleInfoNV': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkExportMemoryWin32HandleInfoNV': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkWin32KeyedMutexAcquireReleaseInfoNV': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkXcbSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_XCB_KHR',
    'VkXlibSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_XLIB_KHR',
    'VkRect3D': 'hackdefine',  # VkRect3D is not used
    'vkCreateAndroidSurfaceKHR': 'VK_USE_PLATFORM_ANDROID_KHR',
    'vkCreateMirSurfaceKHR': 'VK_USE_PLATFORM_MIR_KHR',
    'vkGetPhysicalDeviceMirPresentationSupportKHR': 'VK_USE_PLATFORM_MIR_KHR',
    'vkCreateWaylandSurfaceKHR': 'VK_USE_PLATFORM_WAYLAND_KHR',
    'vkGetPhysicalDeviceWaylandPresentationSupportKHR':
    'VK_USE_PLATFORM_WAYLAND_KHR',
    'vkCreateWin32SurfaceKHR': 'VK_USE_PLATFORM_WIN32_KHR',
    'vkCreateXcbSurfaceKHR': 'VK_USE_PLATFORM_XCB_KHR',
    'vkGetPhysicalDeviceXcbPresentationSupportKHR': 'VK_USE_PLATFORM_XCB_KHR',
    'vkGetMemoryWin32HandleNV': 'VK_USE_PLATFORM_WIN32_KHR',
    'vkGetPhysicalDeviceWin32PresentationSupportKHR':
    'VK_USE_PLATFORM_WIN32_KHR',
    'vkGetPhysicalDeviceXlibPresentationSupportKHR':
    'VK_USE_PLATFORM_XLIB_KHR',
    'vkCreateXlibSurfaceKHR': 'VK_USE_PLATFORM_XLIB_KHR'
}

CUSTOM_COMMANDS = ('vkGetInstanceProcAddr', 'vkGetDeviceProcAddr')

# Members which must always be null
NULL_MEMBERS = ('pNext', 'pAllocator')

# Used for extension enum value generation
extBase = 1000000000
extBlockSize = 1000

vulkan_plateform = None
vulkan_h = None
vk_xml = None
vk_extension_functions = None
vk_all_functions = None
return_structs = None
create_structs = None
structs = None
handles = None
unions = None
commands = None
enums = None
exceptions = None
out = None


def main():
    global vulkan_plateform
    global vulkan_h
    global vk_xml
    global vk_extension_functions
    global vk_all_functions
    global return_structs
    global create_structs
    global out
    global structs
    global handles
    global unions
    global enums
    global commands
    global exceptions

    vulkan_plateform = get_source(VULKAN_PLATEFORM_URL)
    vulkan_h = clean_vulkan_h(get_source(VULKAN_H_URL))
    vk_xml = xmltodict.parse(get_source(VK_XML_URL))
    vk_extension_functions = get_vk_extension_functions()
    vk_all_functions = get_all_vk_functions()
    exceptions = get_exceptions()
    structs = get_structs()
    return_structs = get_structs_returned_only()
    create_structs = get_create_structs()
    handles = get_handles()
    unions = get_unions()
    enums = get_enums()
    commands = get_commands()

    out = open(OUT_FILE, 'w')

    add_header()
    add_vk_plateform()
    add_vk_h()
    add_vk_exception_signatures()
    add_vulkan_function_prototypes()
    add_initsdk()
    add_pyhandles()
    add_pyobject()
    add_extension_functions()
    add_proc_addr_functions()
    add_macros_functions()
    add_pyvk_functions()
    add_pymethod()
    add_pymodule()
    add_pyinit()

    out.close()

    call(['astyle', OUT_FILE])
    call(['rm', OUT_FILE+'.orig'])


def get_source(url):
    mapping = {
        VULKAN_PLATEFORM_URL: 'cache_vk_plateform.h',
        VULKAN_H_URL: 'cache_vulkan.h',
        VK_XML_URL: 'cache_vk.xml'
    }
    try:
        with open(mapping[url]) as f:
            result = f.read()
    except FileNotFoundError:
        result = requests.get(url).text
        with open(mapping[url], 'w') as f:
            f.write(result)
    return result


def clean_vulkan_h(vulkan_h):
    cleaned = ""
    for line in vulkan_h.splitlines(True):
        if '#include "vk_platform.h"' in line:
            continue
        line = line.replace(' const ', ' ')
        line = line.replace('const* ', '*')
        cleaned += line

    return cleaned


def get_vk_extension_functions():
    names = set()
    for extension in vk_xml['registry']['extensions']['extension']:
        if 'command' not in extension['require']:
            continue
        if type(extension['require']['command']) is not list:
            extension['require']['command'] = [
                extension['require']['command']]

        for command in extension['require']['command']:
            names.add(command['@name'])

    return names


def get_all_vk_functions():
    return set([c['proto']['name']
               for c in vk_xml['registry']['commands']['command']])


def get_exceptions():
    vk_result = next(x for x in vk_xml['registry']['enums']
                     if x['@name'] == 'VkResult')
    mapping = {}
    for enum in vk_result['enum']:
        if enum['@name'] == 'VK_SUCCESS':
            continue

        camel_name = ''.join(x for x in enum['@name'].title()
                             if x != '_')
        mapping[camel_name] = enum['@value']
    return mapping


def get_structs():
    """Return structs

    Keep informations of xmltodict
    """
    return [s for s in vk_xml['registry']['types']['type']
            if s.get('@category', None) == 'struct']


def get_enums():
    enums = {e['@name'] for e in vk_xml['registry']['enums']}
    return enums


def get_handles():
    """Return set of name handles """
    return set([s['name'] for s in vk_xml['registry']['types']['type']
               if s.get('@category', None) == 'handle'])


def get_unions():
    return [u for u in vk_xml['registry']['types']['type']
            if u.get('@category', None) == 'union']


def get_commands():
    return [c for c in vk_xml['registry']['commands']['command']]


def get_structs_returned_only():
    return set([s['@name'] for s in structs
               if '@returnedonly' in s and s['@returnedonly'] == 'true'])


def get_create_structs():
    return set([s['@name'] for s in structs if 'Create' in s['@name']])


def add_header():
    header = DEFINE_HEADER
    header += '\n'
    out.write(header)


def add_vk_plateform():
    out.write("// BEGIN VULKAN PLATEFORM\n")
    out.write(vulkan_plateform)
    out.write("// END VULKAN PLATEFORM\n")


def add_vk_h():
    out.write("// BEGIN VULKAN H\n")
    out.write(vulkan_h)
    out.write("// END VULKAN H\n")


def add_vk_exception_signatures():
    out.write('\nstatic PyObject *VulkanError;')
    for exception in exceptions:
        out.write('\nstatic PyObject *%s;' % exception)

    # raise exception function
    out.write('\nint raise(int value) { switch(value) {\n')
    for key, value in exceptions.items():
        out.write('''
            case {}: PyErr_SetString({}, ""); return 1;
            '''.format(value, key))
    out.write('} return 0;}\n')


def add_pyinit():
    out.write("\n\nPyMODINIT_FUNC PyInit_vulkan(void) {\n")
    create_module()
    add_constants()
    add_object_in_init()
    add_exceptions_in_init()
    out.write('''
        if (!init_import_sdk()) return NULL;
        return module;
    }''')


def add_pyhandles():
    for handle in handles:
        out.write("""
            static PyObject* PyHandle_{0} (PyObject *self, PyObject *args) {{
                  {0}* handle = malloc(sizeof({0}));
                  PyObject* value = PyCapsule_New(handle, "{0}", NULL);
                  if (value == NULL) return NULL;
                  return value;
            }}
            """.format(handle))


def add_object_in_init():
    for struct in structs + unions:
        with check_extension(struct['@name']):
            out.write('''
                if (PyType_Ready(&Py{0}Type) < 0)
                    return NULL;
                Py_INCREF(&Py{0}Type);
                PyModule_AddObject(module, "{0}", (PyObject *)&Py{0}Type);
            '''.format(struct['@name']))

    for name in vk_extension_functions:
        with check_extension(name):
            out.write('''
                if (PyType_Ready(&Py{0}Type) < 0)
                    return NULL;
                Py_INCREF(&Py{0}Type);
                PyModule_AddObject(module, "{0}", (PyObject *)&Py{0}Type);
            '''.format(name))


def add_exceptions_in_init():
    out.write('''
        VulkanError = PyErr_NewException("vulkan.VulkanError", NULL, NULL);
        Py_INCREF(VulkanError);
        PyModule_AddObject(module, "VulkanError", VulkanError);
        ''')
    for exception in exceptions:
        out.write('''
            {0} = PyErr_NewException("vulkan.{0}", VulkanError, NULL);
            Py_INCREF({0});
            PyModule_AddObject(module, "{0}", {0});
            '''.format(exception))


def get_member_type_name(member):
    '''Member of a struct'''
    name = member['type']
    if '#text' in member:
        name += ' ' + member['#text']
    return name


def get_signatures():
    names = set()
    for s in structs:
        for m in s['member']:
            name = m['type']
            if '#text' in m:
                name += ' ' + m['#text']
            names.add(name)
    for f in vk_xml['registry']['commands']['command']:
        if type(f['param']) is not list:
            f['param'] = [f['param']]
        for p in f['param']:
            name = p['type']
            if '#text' in p:
                name += ' ' + p['#text']
            names.add(name)
    return names


def pyobject_to_val(force_array=False):
    def rand_name():
        return 'tmp' + str(random.randrange(99999999))

    arraychar_convert = '''
        if ({{member}} == Py_None) {{{{ {{member_struct}} = NULL; }}}}
        else {{{{
            PyObject * {0} = PyUnicode_AsASCIIString({{member}});
            char* {1} = PyBytes_AsString({0});
            char* {2} = strdup({1});
            {{member_struct}} = {2};
            Py_DECREF({0});
        }}}}
        '''.format(rand_name(), rand_name(), rand_name())

    listchar_convert = '''
        int {0} = PyList_Size({{member}});
        char** {1} = malloc(sizeof(char*)*{0} + 1);
        int {2};
        for ({2} = 0; {2} < {0}; {2}++) {{{{
            PyObject* item = PyList_GetItem({{member}}, {2});
            if (item == NULL) return -1;

            PyObject* ascii_str = PyUnicode_AsASCIIString(item);
            if (ascii_str == NULL) {{{{
                PyErr_SetString(PyExc_TypeError,
                "{{member}} must be a list of strings");
                return -1;
            }}}}

            char* tmp2 = PyBytes_AsString(ascii_str);
            {1}[{2}] = strdup(tmp2);
            Py_DECREF(ascii_str);
        }}}}
        {1}[{2}] = NULL; // sentinel
        {{member_struct}} = {1};
        '''.format(rand_name(), rand_name(), rand_name())

    listfloat_convert = '''
        int {0} = PyList_Size({{member}});
        int {1};
        for ({1} = 0; {1} < {0}; {1}++) {{{{
            float tmp = (float) PyFloat_AsDouble(
            PyList_GetItem({{member}}, {1}));
            ({{member_struct}})[{1}] = tmp;
        }}}}
        '''.format(rand_name(), rand_name())

    pointerfloat_convert = '''
        int {0} = PyList_Size({{member}});
        int {1};
        float* float_array = malloc(sizeof(float)*{0});
        for ({1} = 0; {1} < {0}; {1}++) {{{{
            float tmp = (float) PyFloat_AsDouble(
            PyList_GetItem({{member}}, {1}));
            float_array[{1}] = tmp;
        }}}}
        {{member_struct}} = float_array;
        '''.format(rand_name(), rand_name())

    listuint32_convert = (
        listfloat_convert
        .replace('float', 'uint32_t')
        .replace('PyFloat_AsDouble', 'PyLong_AsLong'))

    listuint8_convert = listuint32_convert.replace('uint32_t', 'uint8_t')

    pointeruint32_convert = (
        pointerfloat_convert
        .replace('float', 'uint32_t')
        .replace('PyFloat_AsDouble', 'PyLong_AsLong'))

    mapping = {
        'uint32_t':
        '{member_struct} = (uint32_t) PyLong_AsLong({member});',
        'float':
        '{member_struct} = (float) PyFloat_AsDouble({member});',
        'int32_t':
        '{member_struct} = (int32_t) PyLong_AsLong({member});',
        'char []': arraychar_convert,
        'char const *': arraychar_convert,
        'char const * const*': listchar_convert,
        'float [2]': listfloat_convert,
        'float [4]': listfloat_convert,
        'float const *': pointerfloat_convert,
        'size_t':
        '{member_struct} = (size_t) PyLong_AsLong({member});',
        'uint32_t [2]': listuint32_convert,
        'uint32_t [3]': listuint32_convert,
        'uint32_t const *': pointeruint32_convert,
        'uint64_t':
        '{member_struct} = (uint64_t) PyLong_AsLong({member});',
        'uint8_t []': listuint8_convert,
        'void const *': '{member_struct} = NULL;',
        'void *': '{member_struct} = NULL;',
        'Window':
        '{member_struct} = (XID) PyLong_AsLong({member});',
        'Display *':
        '{member_struct} = (Display *) PyLong_AsLong({member});'
    }

    signatures = [s for s in get_signatures() if s.startswith('Vk')]

    for signature in signatures:
        vkname = signature.split()[0]
        is_struct = vkname in [s['@name'] for s in structs]
        is_union = vkname in [s['@name'] for s in unions]
        is_handle = vkname in [s for s in handles]

        if is_struct or is_union:
            # pointer
            if signature.endswith('*'):
                if force_array:
                    mapping[signature] = '''
                        int {0} = PyList_Size({{member}});
                        int {1};
                        {2}* {2}_array = malloc(sizeof({2})*{0});
                        for ({1} = 0; {1} < {0}; {1}++) {{{{
                            {2}_array[{1}] =
                            *( ( (Py{2}*) PyList_GetItem({{member}}, {1}) )
                                ->base);
                        }}}}
                        {{member_struct}} = {2}_array;
                    '''.format(rand_name(), rand_name(), vkname)
                else:
                    mapping[signature] = '''
                        {member_struct} = (((Py%s*){member})->base);
                    ''' % vkname
            # array
            elif signature.endswith(']'):
                convert = '''
                    int {0} = PyList_Size({{member}});
                    int {1};
                    for ({1} = 0; {1} < {0}; {1}++) {{{{
                        PyObject* tmp = PyList_GetItem({{member}}, {1});
                        ({{member_struct}})[{1}] = *(((Py{2}*)tmp)->base);
                    }}}}
                    '''.format(rand_name(), rand_name(), vkname)
                mapping[signature] = convert
            # base
            else:
                mapping[signature] = '''
                    {member_struct} = *(((Py%s*){member})->base);
                ''' % vkname
        elif is_handle:
            mapping[signature] = '''
                {member_struct} = PyCapsule_GetPointer({member}, "%s");
            ''' % vkname
        # int type
        else:
            if signature.endswith('*'):
                mapping[signature] = '''
                    %s tmp = PyLong_AsLong({member});
                    {member_struct} = &tmp;
                ''' % vkname
            else:
                mapping[signature] = '''
                    {member_struct} = PyLong_AsLong({member});
                '''

    return mapping


def val_to_pyobject(member):
    listchar_convert = '''
        if ({0}[0] == NULL) return PyList_New(0);;
        PyObject* value = PyList_New(0);
        int i = 0;
        while ({0}[i] != NULL) {{{{
            PyObject* py_tmp = PyUnicode_FromString((const char *) {0}[i]);
            PyList_Append(value, py_tmp);
            i++;
        }}}}
        '''

    listfloat_convert = '''
        PyObject* value = PyList_New(0);
        int nb = sizeof({0}) / sizeof({0}[0]);
        int i = 0;
        for (i = 0; i < nb; i++) {{{{
            PyObject* py_tmp = PyFloat_FromDouble((double) {0}[i]);
            PyList_Append(value, py_tmp);
        }}}}
        '''

    listuint32_convert = (
        listfloat_convert
        .replace('double', 'long')
        .replace('PyFloat_FromDouble', 'PyLong_FromLong'))

    listuint8_convert = listuint32_convert

    mapping = {
        'uint32_t':
        'PyObject* value = PyLong_FromLong((long) {});',
        'float':
        'PyObject* value = PyFloat_FromDouble((double) {});',
        'int32_t':
        'PyObject* value = PyLong_FromLong((long) {});',
        'char []':
        'PyObject* value = PyUnicode_FromString((const char *) {});',
        'char const *':
        'PyObject* value = PyUnicode_FromString((const char *) {});',
        'char const * const*': listchar_convert,
        'float [2]': listfloat_convert,
        'float [4]': listfloat_convert,
        'float const *':
        'PyObject* value = PyFloat_FromDouble((double) (*({})));',
        'size_t':
        'PyObject* value = PyLong_FromLong((long) {});',
        'uint32_t [2]': listuint32_convert,
        'uint32_t [3]': listuint32_convert,
        'uint32_t const *':
        'PyObject* value = PyLong_FromLong((long) (*({})));',
        'uint64_t':
        'PyObject* value = PyLong_FromLong((long) {});',
        'uint8_t []': listuint8_convert,
        'void const *': 'Py_INCREF(Py_None);PyObject* value = Py_None;',
        'void *': 'Py_INCREF(Py_None);PyObject* value = Py_None;',
        'Window':
        'PyObject* value = PyLong_FromLong((long) {});',
        'Display *': 'Py_INCREF(Py_None);PyObject* value = Py_None;',
    }

    signatures = [s for s in get_signatures() if s.startswith('Vk')]

    for signature in signatures:
        vkname = signature.split()[0]
        is_struct = vkname in [s['@name'] for s in structs]
        is_union = vkname in [s['@name'] for s in unions]
        is_handle = vkname in [s for s in handles]

        if is_struct:
            if signature.endswith('*') or signature.endswith('[]'):
                mapping[signature] = '''
                    PyObject* value = _PyObject_New(&Py{0}Type);
                    if(!value) return NULL;
                    ((Py{0}*)value)->base = {{}};
                '''.format(vkname)
            else:
                mapping[signature] = '''
                    PyObject* value = _PyObject_New(&Py{0}Type);
                    if(!value) return NULL;
                    ((Py{0}*)value)->base = &({{}});
                '''.format(vkname)
        elif is_union:
            pass
        elif is_handle:
            pass
        else:
            if signature.endswith('*'):
                mapping[signature] = '''
                    PyObject* value = PyLong_FromLong(*{});
                '''
            else:
                mapping[signature] = '''
                    PyObject* value = PyLong_FromLong({});
                '''

    name = get_member_type_name(member)
    value = mapping.get(name, None)
    if value:
        return value.format('(self->base)->{1}')
    return None


def extracts_vars(members, return_error='-1'):
    ''' This function extract all arguments to python objects

    members must be a list of member's name
    '''
    members = [m for m in members
               if m not in NULL_MEMBERS]

    if not members:
        return ''

    final_result = ''
    result = []
    for member in members:
        result.append('PyObject* %s = NULL;' % member)

    final_result += '\n'.join(result) + '\n'

    result = 'static char *kwlist[] = {'
    for member in members:
        result += '"{}",'.format(member)
    result += 'NULL};'

    final_result += result + '\n'

    result = 'PyArg_ParseTupleAndKeywords(args, kwds, "'
    result += 'O' * len(members)

    result += '", kwlist'
    for member in members:
        result += ', &{}'.format(member)
    result += ')'

    final_result += 'if(!%s) return %s;' % (result, return_error) + '\n'
    return final_result


def get_debug_create_init():
    return '''
        static PyObject *python_debug_callback = NULL;
        static VKAPI_ATTR VkBool32 VKAPI_CALL debug_callback(
            VkDebugReportFlagsEXT flags,
            VkDebugReportObjectTypeEXT objType,
            uint64_t obj,
            size_t location,
            int32_t code,
            const char* layerPrefix,
            const char* msg,
            void* userData) {
                PyObject_CallFunction(python_debug_callback, "iiKIisss", flags,
                objType, obj, location, code, layerPrefix, msg, NULL);
            return VK_FALSE;
        }

        static int
         PyVkDebugReportCallbackCreateInfoEXT_init(
         PyVkDebugReportCallbackCreateInfoEXT *self, PyObject *args,
         PyObject *kwds) {
             int sType;
             int flags;
             PyObject* tmp = NULL;
             static char *kwlist[] = {"sType", "flags","pfnCallback",NULL};
             if(!PyArg_ParseTupleAndKeywords(args, kwds, "iiO", kwlist,
                                             &sType, &flags, &tmp))
                 return -1;

             if (!PyCallable_Check(tmp)) {
                 PyErr_SetString(PyExc_TypeError,
                                 "pfnCallback must be callable");
                 return -1;
             }
             // Renew callback
             Py_INCREF(tmp);
             Py_XDECREF(python_debug_callback);
             python_debug_callback = tmp;

             (self->base)->sType = sType;
             (self->base)->pNext = NULL;
             (self->base)->pUserData = NULL;
             (self->base)->flags = flags;
             (self->base)->pfnCallback =
                 (PFN_vkDebugReportCallbackEXT)(&debug_callback);

             return 0;
         }
    '''


def add_pyobject():

    def add_struct(s):
        definition = '''
            typedef struct {{ PyObject_HEAD {0} *base; }}
            Py{0};
            '''
        out.write(definition.format(s['@name']))

    def add_del(s):
        definition = '''
            static void Py{0}_del(Py{0}* self) {{
                Py_TYPE(self)->tp_free((PyObject*)self); }}
            '''
        out.write(definition.format(s['@name']))

    def add_new(s):
        definition = '''
            static PyObject *
            Py{0}_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
            {{
                Py{0} *self;
                self = (Py{0} *)type->tp_alloc(type, 0);
                if ( self != NULL) {{
                    self->base = malloc(sizeof({0}));
                    if (self->base == NULL) {{
                        PyErr_SetString(PyExc_MemoryError,
                            "Cannot allocate memory for {0}");
                        return NULL;
                    }}
                }}

                return (PyObject *)self;
            }}
            '''
        out.write(definition.format(s['@name']))

    def add_init(s):
        if 'VkDebugReportCallbackCreateInfoEXT' == s['@name']:
            out.write(get_debug_create_init())
            return

        is_union = s['@name'] in [u['@name'] for u in unions]

        definition = '''
            static int
            Py{0}_init(Py{0} *self, PyObject *args, PyObject *kwds) {{
            '''.format(s['@name'])

        if s['@name'] not in return_structs:
            members = s['member']

            definition += extracts_vars([m['name'] for m in members])
            if is_union:
                definition += add_init_check_union(members) + '\n'
            definition += add_init_py_to_val(members) + '\n'

        definition += 'return 0; }'

        out.write(definition)

    def add_init_check_union(members):
        result = '\nint nb_union_arg = 0;\n'
        for member in members:
            result += '''
                if ({0} != NULL && {0} != Py_None) nb_union_arg++;
                '''.format(member['name'])
        result += '''
            if (nb_union_arg > 1) {
                PyErr_SetString(PyExc_TypeError, "Only one argument allowed");
                return -1;
            }'''
        return result

    def add_init_py_to_val(members):
        result = ''
        for member in members:
            if member['name'] in NULL_MEMBERS:
                result += '\n(self->base)->%s = NULL;\n' % member['name']
                continue

            name = get_member_type_name(member)
            force_array = True if '@len' in member else False
            val = pyobject_to_val(force_array).get(name, None)
            if not val:
                continue
            result += '''
                if ({0} != NULL && {0} != Py_None) {{
                '''.format(member['name'])
            result += val.format(
                member=member['name'],
                member_struct='(self->base)->%s' % member['name'])
            result += '\n } \n'
        return result

    def add_getters(s):
        def add_getter(member):
            definition = '''
            static PyObject * Py{0}_get{1}(Py{0} *self, void *closure){{
            '''

            convert = val_to_pyobject(member)
            if convert:
                definition += convert
            else:
                return

            definition += '''
                Py_INCREF(value);
                return value;
            }}
            '''
            out.write(definition.format(s['@name'], member['name']))

        def add_getter_setter(s):
            out.write('''
                static PyGetSetDef Py{}_getsetters[] = {{
                '''.format(s['@name']))

            for member in s['member']:
                if not val_to_pyobject(member):
                    continue
                sname = s['@name']
                mname = member['name']
                getter = '(getter)Py{0}_get{1}'.format(sname, mname)
                setter = 'NULL'

                out.write('''
                    {{ "{}", {}, {}, "", NULL}},
                '''.format(mname, getter, setter))

            out.write('{NULL}};\n')

        for member in s['member']:
            add_getter(member)
        add_getter_setter(s)

    def add_type(s):
        out.write('''
            static PyTypeObject Py{0}Type = {{
                PyVarObject_HEAD_INIT(NULL, 0)
                "vulkan.{0}", sizeof(Py{0}), 0,
                (destructor)Py{0}_del,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,Py_TPFLAGS_DEFAULT,
                "{0} object",0,0,0,0,0,0,0,0,
                Py{0}_getsetters,0,0,0,0,0,(initproc)Py{0}_init,0,Py{0}_new,}};
        '''.format(s['@name']))

    for struct in structs + unions:
        with check_extension(struct['@name']):
            add_struct(struct)

    for struct in structs + unions:
        with check_extension(struct['@name']):
            for fun in (add_del, add_new, add_getters,
                        add_init, add_type):
                fun(struct)


@contextmanager
def check_extension(name):
    mapping = MAPPING_EXTENSION_DEFINE
    try:
        if name in mapping:
            out.write('\n#ifdef {}\n'
                      .format(mapping[name]))
        yield
    finally:
        if name in mapping:
            out.write('\n#endif\n')


def add_pymodule():
    name = '"vulkan"'
    doc = '"Vulkan module"'
    out.write('''
        static struct PyModuleDef vulkanmodule = {{
            PyModuleDef_HEAD_INIT, {}, {}, -1, VulkanMethods}};
        '''.format(name, doc))


def create_module():
    out.write('''
        PyObject* module;
        module = PyModule_Create(&vulkanmodule);
        if (module == NULL) return NULL;
    ''')


def add_vulkan_function_prototypes():
    commands = [c for c in vk_all_functions if c not in vk_extension_functions]
    for name in commands:
        name_pfn = 'PFN_{}'.format(name)
        with check_extension(name):
            out.write('''
                static {} {};
            '''.format(name_pfn, name))


def add_constants():
    result = []

    def add_result(name, value, string_constant = False):
        if not string_constant:
            result.append('PyModule_AddIntConstant(module, "{}", {})'.format(
                name, value))
        else:
            result.append('PyModule_AddStringConstant(module, "{}", {})'.format(
                name, value))

    # List enums
    for enum in vk_xml['registry']['enums']:
        name = ""
        value = ""

        # List constant in enum
        if type(enum['enum']) is not list:
            enum['enum'] = [enum['enum']]

        for constant in enum['enum']:
            if '@bitpos' in constant:
                value = constant['@bitpos']
                numVal = int(value, 0)
                numVal = 1 << numVal
                value = '0x%08x' % numVal
                constant['@value'] = value
            name = constant["@name"]
            value = constant["@value"]
            add_result(name, value)

    # List extension enums
    for extension in vk_xml['registry']['extensions']['extension']:
        extnumber = int(extension['@number'])

        if type(extension['require']['enum']) is not list:
            extension['require']['enum'] = [extension['require']['enum']]

        for enum in extension['require']['enum']:
            name = enum['@name']
            string_constant = False
            if '@value' in enum:
                value = enum['@value']
                if value.startswith('"'):
                    string_constant = True
            if '@bitpos' in enum:
                value = enum['@bitpos']
                numVal = int(value, 0)
                numVal = 1 << numVal
                value = '0x%08x' % numVal
            if '@offset' in enum:
                value = extBase + (extnumber - 1) * extBlockSize + int(enum['@offset'])
            add_result(name, value, string_constant)

    # Custom constants
    add_result('VK_API_VERSION_1_0', 'VK_API_VERSION_1_0')

    text = '\n\n'
    text += ';\n'.join(result)
    text += ';\n'
    out.write(text)


def add_initsdk():
    functions = []
    for command in vk_all_functions - vk_extension_functions:
        name = command
        name_pfn = 'PFN_{}'.format(name)
        functions.append('''
                         {0} = ({1})dlsym(vk_sdk, "{0}");
                         if( {0} == NULL ) {{
                             PyErr_SetString(PyExc_ImportError,
                                             "Can't load {0} in sdk");
                             return 0;
                         }}
                         '''
                         .format(name, name_pfn))

    out.write('''
        static int init_import_sdk(void) {
            void* vk_sdk = LOAD_SDK();
            if (vk_sdk == NULL) {
                PyErr_SetString(PyExc_ImportError,
                                "Can't find vulkan sdk");
                return 0;
            }

            '''+'\n'.join(functions)+'''

            return 1;
        }
    ''')


def add_pyvk_functions():
    for command in commands:
        cname = command['proto']['name']
        if cname in CUSTOM_COMMANDS or cname in vk_extension_functions:
            continue
        cname = command['proto']['name']
        add_pyvk_function(command)


def add_pyvk_function(command, pyfunction=None, null_return='NULL',
                      call_name=''):
    def normalize_param(command):
        if not isinstance(command['param'], list):
            command['param'] = [command['param']]
        return command

    def get_count_param(command):
        for param in command['param']:
            if param['type'] + param.get('#text', '') == 'uint32_t*':
                return param
        return None

    def add_return_struct(members):
        """Create a struct inside the function

        The struct handle values converted from PyObject
        """
        if not members:
            return ''

        result = '\nstruct {\n'
        for m in members:
            pointer = ''
            if m.get('#text', False) or m['type'] in handles:
                pointer = '*'
            if 'struct' in m.get('#text', ''):
                m['type'] = 'struct ' + m['type']

            result += '\n{}{} {};\n'.format(
                m['type'], pointer, m['name'])
        result += '\n} return_struct = {};\n'
        return result

    def add_py_to_val(members):
        result = ''

        if not members:
            return result

        for member in members:
            if member['name'] in NULL_MEMBERS:
                result += '\nreturn_struct.%s = NULL;\n' % member['name']
                continue
            name = get_member_type_name(member)
            val = pyobject_to_val().get(name, None)
            if not val:
                continue
            result += val.format(
                member=member['name'],
                member_struct='return_struct.%s' % member['name'])
        return result

    def get_param(p):
        if p['type'] in handles and not p.get('#text'):
            return '*(return_struct.%s)' % p['name']
        return 'return_struct.' + p['name']

    allocate_prefix = ('vkCreate', 'vkGet', 'vkEnumerate', 'vkAllocate',
                       'vkMap')
    allocate_exception = ('vkGetFenceStatus', 'vkGetEventStatus',
                          'vkGetQueryPoolResults',
                          'vkGetPhysicalDeviceXlibPresentationSupportKHR')

    cname = command['proto']['name']
    ctype = command['proto']['type']
    call_name = call_name if call_name else cname

    command = normalize_param(command)
    count_param = get_count_param(command)

    is_allocate = any([cname.startswith(a) for a in allocate_prefix])
    is_count = is_allocate and count_param is not None

    if cname in allocate_exception or ctype == 'VkBool32':
        is_allocate = is_count = False

    num_param = None
    if is_allocate:
        num_param = -1
    if is_count:
        num_param = -2

    definition = ('''
        static PyObject* Py%s(PyObject *self, PyObject *args,
                              PyObject *kwds) {
        ''' % (pyfunction if pyfunction else cname))
    extract_params = [p['name'] for p in command['param']][:num_param]
    definition += extracts_vars(extract_params, return_error='NULL')
    definition += add_return_struct(command['param'][:num_param])
    definition += add_py_to_val(command['param'][:num_param])

    if cname == 'vkMapMemory':
        definition += '''
            void* value;
            if (raise(
            vkMapMemory(*(return_struct.device), *(return_struct.memory),
                        return_struct.offset, return_struct.size,
                        return_struct.flags, &value)
            )) return NULL;
            PyObject* return_value = PyMemoryView_FromMemory(value,
                return_struct.size, PyBUF_WRITE);
        '''
    elif cname == 'vkGetPipelineCacheData':
        definition += '''
            void* value = NULL;
            size_t* data_size = NULL;
            if (raise(
            vkGetPipelineCacheData(
                *(return_struct.device), *(return_struct.pipelineCache),
                data_size, value)
            )) return NULL;
            PyObject* return_value = PyMemoryView_FromMemory(value,
                *data_size, PyBUF_WRITE);
        '''
    elif is_count:
        return_object = command['param'][-1]
        param_func = [get_param(p) for p in command['param'][:-2]]
        # param_func = ['return_struct.' + p['name']
        #              for p in command['param'][:-2]]

        # first call which count
        definition += '\nuint32_t count;'
        func_str_call = '\n%s(' % call_name
        func_str_call += ','.join(param_func) + ',' if param_func else ''
        func_str_call += '&count, NULL)'
        if ctype == 'VkResult':
            definition += 'if (raise(%s)) return NULL;' % func_str_call
        else:
            definition += func_str_call + ';'

        # create array of object
        definition += '''
            {0} *values = malloc(count*sizeof({0}));
            '''.format(return_object['type'])

        # call with array
        func_str_call = '\n%s(' % call_name
        func_str_call += ','.join(param_func) + ',' if param_func else ''
        func_str_call += '&count, values)'
        if ctype == 'VkResult':
            definition += 'if (raise(%s)) return NULL;' % func_str_call
        else:
            definition += func_str_call + ';'

        definition += '''
            PyObject* return_value = PyList_New(0);
            uint32_t i;
            for (i=0; i<count; i++) {{
                {0}* value = malloc(sizeof({0}));
                memcpy(value, values + i, sizeof({0}));
            '''.format(return_object['type'])

        if return_object['type'] in handles:
            definition += '''
                PyObject* pyreturn = PyCapsule_New(value
                , "{0}", NULL);
            '''.format(return_object['type'])
        elif return_object['type'] in enums:
            definition += '''
                PyObject* pyreturn =
                PyLong_FromLong((long) *value);
            '''.format(return_object['type'])
        else:
            definition += '''
                PyObject* pyreturn = _PyObject_New(&Py{0}Type);
                if(!pyreturn) return NULL;
                ((Py{0}*)pyreturn)->base = value;

                /*PyObject* pyreturn = PyObject_Call((PyObject *)&Py{0}Type,
                                                   NULL, NULL);
                memcpy(((Py{0}*)pyreturn)->base,
                       values + i, sizeof({0}));*/
            '''.format(return_object['type'])

        definition += '''
                PyList_Append(return_value, pyreturn);
            }
            free(values);
        '''

    elif is_allocate:
        return_object = command['param'][-1]
        param_func = [get_param(p) for p in command['param'][:-1]]

        # create object
        definition += '\n{0} *value = malloc(sizeof({0}));\n'.format(
            return_object['type'])
        # call
        func_str_call = '\n%s(' % call_name
        func_str_call += ','.join(param_func) + ',' if param_func else ''
        func_str_call += 'value)'
        if ctype == 'VkResult':
            definition += 'if (raise(%s)) return NULL;' % func_str_call
        else:
            definition += func_str_call + ';'

        if return_object['type'] in handles:
            definition += '''
                PyObject* return_value = PyCapsule_New(value, "{}", NULL);
            '''.format(return_object['type'])
        elif return_object['type'] in [s['@name'] for s in structs]:
            definition += '''
                PyObject* return_value = _PyObject_New(&Py{0}Type);
                if (return_value == NULL) return NULL;
                ((Py{0}*)return_value)->base = value;
            '''.format(return_object['type'])
        else:
            definition += '''
                PyObject* return_value = PyLong_FromLong(*value);
                '''
    else:
        param_func = [get_param(p) for p in command['param']]
        param_func = ','.join(param_func)

        if ctype == 'VkBool32':
            definition += '''
                PyObject* return_value = PyBool_FromLong(
            '''

        definition += '\n%s(' % call_name
        definition += param_func

        if ctype == 'VkBool32':
            definition += ')'

        definition += ');\n'

        if ctype != 'VkBool32':
            definition += 'PyObject* return_value = Py_None;\n'

    definition += '''
        return return_value; }
        '''

    with check_extension(cname):
        out.write(definition)


def add_proc_addr_functions():
    infos = [{'name': 'vkGetInstanceProcAddr',
              'arg': 'instance',
              'type': 'VkInstance'},
             {'name': 'vkGetDeviceProcAddr',
              'arg': 'device',
              'type': 'VkDevice'}]

    for info in infos:
        out.write('''
            static PyObject* Py{0}(
                PyObject *self, PyObject *args, PyObject *kwds) {{

                PyObject* instance = NULL;
                PyObject* pName = NULL;
                static char *kwlist[] = {{"{1}", "pName", NULL}};

                if(!PyArg_ParseTupleAndKeywords(args, kwds, "OO", kwlist,
                                                &instance, &pName))
                      return NULL;

                {2}* arg0 = PyCapsule_GetPointer(instance, "{2}");
                if(arg0 == NULL) return NULL;

                PyObject* tmp = PyUnicode_AsASCIIString(pName);
                if(tmp == NULL) return NULL;

                char* arg1 = PyBytes_AsString(tmp);
                if(arg1 == NULL) return NULL;
                Py_DECREF(tmp);

                PFN_vkVoidFunction fun = {0}(*arg0, arg1);
                if (fun == NULL) {{
                      PyErr_SetString(PyExc_ImportError,
                      "Can't get address of extension function");
                      return NULL;
                }}
                PyObject* pointer = PyCapsule_New(fun, NULL, NULL);
                if (pointer == NULL) return NULL;

                PyObject* call_args = Py_BuildValue("(O)", pointer);
                if (call_args == NULL) return NULL;

                PyObject* pyreturn = NULL;
        '''.format(info['name'], info['arg'], info['type']))

        for name in vk_extension_functions:
            with check_extension(name):
                out.write('''
                    if (strcmp(arg1, "{0}") == 0) {{
                        pyreturn = PyObject_Call((PyObject *)&Py{0}Type,
                            call_args, NULL);
                        if (pyreturn == NULL) return NULL;
                    }}
                '''.format(name))

        out.write('''
                Py_INCREF(pyreturn);
                return pyreturn;
            }
        ''')


def add_macros_functions():
    out.write('''
        static PyObject *
        PyVK_MAKE_VERSION(PyObject *self, PyObject *args) {
            const int major, minor, patch;
            if (!PyArg_ParseTuple(args, "iii", &major, &minor, &patch))
                return NULL;
            return PyLong_FromLong(
                (((major) << 22) | ((minor) << 12) | (patch)));
        }

        static PyObject *
        PyVK_VERSION_MAJOR(PyObject *self, PyObject *args) {
            const int version;
            if (!PyArg_ParseTuple(args, "i", &version))
                return NULL;
            return PyLong_FromLong(((uint32_t)(version) >> 22));
        }

        static PyObject *
        PyVK_VERSION_MINOR(PyObject *self, PyObject *args) {
            const int version;
            if (!PyArg_ParseTuple(args, "i", &version))
                return NULL;
            return PyLong_FromLong((((uint32_t)(version) >> 12) & 0x3ff));
        }

        static PyObject *
        PyVK_VERSION_PATCH(PyObject *self, PyObject *args) {
            const int version;
            if (!PyArg_ParseTuple(args, "i", &version))
                return NULL;
            return PyLong_FromLong(((uint32_t)(version) & 0xfff));
        }
        ''')


def add_extension_functions():
    """Extension functions

    Extension functions are loaded dynamically with
    vkGetInstanceProcAddr or vkGetDeviceProcAddr.
    To allow this, we create a new Type for each extension.
    This types take a function pointer as argument (PyCapsule).
    We make this type callable to be treated as a function although
    it's a type.
    """
    def add_struct(command):
        name = command['proto']['name']
        definition = '''
            typedef struct {{ PyObject_HEAD PFN_{0} pfn; }}
            Py{0};
            '''
        out.write(definition.format(name))

    def add_del(command):
        name = command['proto']['name']
        definition = '''
            static void Py{0}_del(Py{0}* self) {{
                Py_TYPE(self)->tp_free((PyObject*)self); }}
            '''
        out.write(definition.format(name))

    def add_new(command):
        name = command['proto']['name']
        definition = '''
            static PyObject *
            Py{0}_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
            {{
                Py{0} *self;
                self = (Py{0} *)type->tp_alloc(type, 0);
                return (PyObject *)self;
            }}
            '''
        out.write(definition.format(name))

    def add_init(command):
        name = command['proto']['name']
        definition = '''
            static int
            Py{0}_init(Py{0} *self, PyObject *args, PyObject *kwds) {{
                PyObject* capsule;
                if (!PyArg_ParseTuple(args, "O", &capsule))
                    return -1;
                self->pfn = (PFN_{0}) PyCapsule_GetPointer(capsule, NULL);
                if (self->pfn == NULL) return -1;
                return 0;
            }}
        '''.format(name)
        out.write(definition)

    def add_call(command):
        name = command['proto']['name']
        add_pyvk_function(
            command,
            pyfunction=name + '_call',
            call_name='(*(((Py%s*)self)->pfn))' % name)

    def add_type(command):
        name = command['proto']['name']
        out.write('''
            static PyTypeObject Py{0}Type = {{
                PyVarObject_HEAD_INIT(NULL, 0)
                "vulkan.{0}", sizeof(Py{0}), 0,
                (destructor)Py{0}_del,
                0,0,0,0,0,0,0,0,0,(ternaryfunc)Py{0}_call,
                0,0,0,0,Py_TPFLAGS_DEFAULT,
                "{0} object",0,0,0,0,0,0,0,0,
                0,0,0,0,0,0,(initproc)Py{0}_init,0,Py{0}_new,}};
        '''.format(name))

    extension_commands = [c for c in commands
                          if c['proto']['name'] in vk_extension_functions]
    for c in extension_commands:
        with check_extension(c['proto']['name']):
            add_struct(c)

    for c in extension_commands:
        with check_extension(c['proto']['name']):
            for fun in (add_del, add_new, add_call,
                        add_init, add_type):
                fun(c)


def add_pymethod():
    """Add methods saw from python
    """
    functions = []

    # Add getProcAddr functions
    for name in ('vkGetInstanceProcAddr', 'vkGetDeviceProcAddr'):
        functions.append({'name': name,
                          'value': '(PyCFunction)Py%s' % name,
                          'arg': 'METH_VARARGS',
                          'doc': '""'})

    # Add macros
    for name in ('VK_MAKE_VERSION', 'VK_VERSION_MAJOR', 'VK_VERSION_MINOR',
                 'VK_VERSION_PATCH'):
        functions.append({'name': name,
                          'value': '(PyCFunction)Py%s' % name,
                          'arg': 'METH_VARARGS',
                          'doc': '""'})

    # Add handle functions
    for handle in handles:
        functions.append({'name': handle,
                          'value': 'PyHandle_' + handle,
                          'arg': 'METH_NOARGS',
                          'doc': '"Handle"'})

    # Add vk command
    for command in commands:
        cname = command['proto']['name']
        if cname in CUSTOM_COMMANDS or cname in vk_extension_functions:
            continue
        functions.append({'name': command['proto']['name'],
                          'value': ('(PyCFunction) Py' +
                                    command['proto']['name']),
                          'arg': 'METH_VARARGS | METH_KEYWORDS',
                          'doc': '""'})

    out.write('\nstatic PyMethodDef VulkanMethods[] = {\n')

    for fun in functions:
        with check_extension(fun['name']):
            out.write('{{"{}", {}, {}, {}}},\n'.format(
                fun['name'], fun['value'], fun['arg'], fun['doc']))

    out.write('\n{NULL, NULL, 0, NULL} };\n')


if __name__ == '__main__':
    main()
