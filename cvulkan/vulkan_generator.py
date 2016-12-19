"""C Vulkan generator

# How it works?  C vulkan module is generated following these steps:
    - Download vk.xml or get it locally
    - Pass it to xmltodict to get a python dict from it
    - Generate a custom model for each part of the binding
    - Pass the model to the jinja2 template engine
    - Generate the final c module from within template

We import vulkan.h and vulkan_plateform.h instead of generate it.

# Data model
The model must allow template to generate structs, functions,
dynamic function, dynamic struct, callback functions, constants...
Model design will be described in followings sections.

## Constants
Constants are very basic and can be of type int or string.
model['constants'] = [{
    'name': 'name'
    'value': 'value',
    'type': 'int'
]

## Structs and Unions
There are several way to do it:

    - We could copy the Vulkan struct and for each one, create a python
wrapper struct containing a pointer to the the vulkan struct.

    - We could create only Python struct, which is good for memory allocation
and simplify the conversion C <> Python but we have a problem with this:
Vulkan functions wait for Vulkan C structs whereas Python structs contain
a Python Header. How can we pass Python structs to Vulkan functions...
The only way I can think of is to update the pointer reference.
We have to create a function which transform a Python struct into a
Vulkan struct. Basically, we create a pointer void onto the first Vulkan
property (sType for a create). We also have to update all pointers into
this Vulkan struct.

After thinking, this solution is a pain in the ass so I will stick with the
obvious first solution.

Here the struct model:
model['structs'] = [{
    'name': 'name',
    'define': 'DEFINE_MUST_EXIST',
    'union': False,
    'return_only': False,
    'members': [{
        'name': 'name',
        'type': 'type []',
        'raw_type': 'type' -> Type without #text
        'null': False,
        'enum': MAX_ARRAY -> Size of array with fixed length,
        'len': 'member', -> Name of the member for the array length
        'force_array': False -> Used when a pointer is an array of VK types
    }]
}]

## Functions
There are two types of function in cvulkan, dynamicly linked functions
into the SDK and extensions functions.
Functions vkGetInstanceProcAddr and vkGetDeviceProcAddr are custom so not here!
Here the model:
model['functions'] = [{
    'name': 'name',
    'define': 'DEFINE_MUST_EXIST',
    'arg': 'METH_VARARGS | METH_KEYWORDS', -> python parameter
    'custom': False, -> written directly in template
    'allocate': True, -> create one object
    'count': True, -> create several objects
    'return_type': 'type', -> type returned by the function
    'return_boolean': True, -> True if the function return a vkbool
    'return_member': {
        'name': 'name',
        'type': 'type without #text',
        'handle': False,
        'enum': False,
        'struct': True,
        'static_count': {
            'key': 'name', -> Name of the member if count is static
            'value': 'name' -> Name of the property if count is static
        }
    },
    'members': [{
        'name': 'name',
        'type': 'type', -> raw_type + #text
        'null': False,
        'force_array': False, -> This member is a list
        'to_create': False -> this value must be created(count or allocate)
    }]
}]

## Extension functions
Extension functions are loaded dynamically with vkGetInstanceProcAddr or
vkGetDeviceProcAddr.
To allow this, we create a new Type for each extension.
This types take a function pointer as argument (PyCapsule).
We make this type callable to be treated as a function although it's a type.
model['extension_functions'] = like model['function']


## Custom functions
Custom functions are written directly in C in the template.
We create an array in the model to declare them in python.
model['custom_functions'] = ['f1', 'f2']

## Custom structs
Custom functions are written directly in C in the template.
We create an array in the model to declare them in python.
model['custom_structs'] = ['f1', 'f2']

## Macro functions
Macros are just custom functions.
model['macro_functions'] = ['f1', 'f2']

## Exceptions
Exceptions are created based on the name in the VkResult enum:
model['exceptions'] = {
    'exceptionName': value
}

## Signatures
Signatures are used in converters.c to convert Python to Vulkan type
model['signatures']
"""
import jinja2
import os
import requests
import xmltodict

from cvulkan import jfilter

VULKAN_PLATEFORM_URL = ('http://raw.githubusercontent.com/KhronosGroup/'
                        'Vulkan-Docs/1.0/src/vulkan/vk_platform.h')
VULKAN_H_URL = ('http://raw.githubusercontent.com/KhronosGroup/'
                'Vulkan-Docs/1.0/src/vulkan/vulkan.h')
VK_XML_URL = ('http://raw.githubusercontent.com/KhronosGroup/'
              'Vulkan-Docs/1.0/src/spec/vk.xml')
PATH = os.path.dirname(os.path.abspath(__file__))
PATH_TEMPLATE = os.path.join(PATH, 'template')
DEFAULT_OUT_FILE = os.path.join(PATH, 'vulkanmodule.c')
OUT_VULKAN_H = os.path.join(PATH, 'cache_vulkan.h')
OUT_VULKAN_PLATEFORM = os.path.join(PATH, 'cache_vk_plateform.h')

CACHE_MAPPING = {
    VULKAN_PLATEFORM_URL: 'cache_vk_plateform.h',
    VULKAN_H_URL: 'cache_vulkan.h',
    VK_XML_URL: 'cache_vk.xml'
}

MAPPING_EXTENSION_DEFINE = {
    'VkAndroidSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_ANDROID_KHR',
    'VkMirSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_MIR_KHR',
    'VkMirSurfaceCreateFlagsKHR': 'VK_USE_PLATFORM_MIR_KHR',
    'MirConnection': 'VK_USE_PLATFORM_MIR_KHR',
    'MirSurface': 'VK_USE_PLATFORM_MIR_KHR',
    'VkWaylandSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_WAYLAND_KHR',
    'HANDLE': 'VK_USE_PLATFORM_WIN32_KHR',
    'HWND': 'VK_USE_PLATFORM_WIN32_KHR',
    'HINSTANCE': 'VK_USE_PLATFORM_WIN32_KHR',
    'SECURITY_ATTRIBUTES': 'VK_USE_PLATFORM_WIN32_KHR',
    'DWORD': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkWin32SurfaceCreateInfoKHR': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkWin32SurfaceCreateFlagsKHR': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkImportMemoryWin32HandleInfoNV': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkExportMemoryWin32HandleInfoNV': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkWin32KeyedMutexAcquireReleaseInfoNV': 'VK_USE_PLATFORM_WIN32_KHR',
    'VkXcbSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_XCB_KHR',
    'VkXlibSurfaceCreateInfoKHR': 'VK_USE_PLATFORM_XLIB_KHR',
    'VkRect3D': 'hackdefine',  # VkRect3D is not used
    'vkCreateAndroidSurfaceKHR': 'VK_USE_PLATFORM_ANDROID_KHR',
    'VkAndroidSurfaceCreateFlagsKHR': 'VK_USE_PLATFORM_ANDROID_KHR',
    'ANativeWindow': 'VK_USE_PLATFORM_ANDROID_KHR',
    'vkCreateMirSurfaceKHR': 'VK_USE_PLATFORM_MIR_KHR',
    'vkGetPhysicalDeviceMirPresentationSupportKHR': 'VK_USE_PLATFORM_MIR_KHR',
    'vkCreateWaylandSurfaceKHR': 'VK_USE_PLATFORM_WAYLAND_KHR',
    'vkGetPhysicalDeviceWaylandPresentationSupportKHR':
    'VK_USE_PLATFORM_WAYLAND_KHR',
    'vkCreateWin32SurfaceKHR': 'VK_USE_PLATFORM_WIN32_KHR',
    'vkCreateXcbSurfaceKHR': 'VK_USE_PLATFORM_XCB_KHR',
    'xcb_connection_t': 'VK_USE_PLATFORM_XCB_KHR',
    'xcb_visualid_t': 'VK_USE_PLATFORM_XCB_KHR',
    'xcb_window_t': 'VK_USE_PLATFORM_XCB_KHR',
    'VisualID': 'VK_USE_PLATFORM_XCB_KHR',
    'vkGetPhysicalDeviceXcbPresentationSupportKHR': 'VK_USE_PLATFORM_XCB_KHR',
    'vkGetMemoryWin32HandleNV': 'VK_USE_PLATFORM_WIN32_KHR',
    'vkGetPhysicalDeviceWin32PresentationSupportKHR':
    'VK_USE_PLATFORM_WIN32_KHR',
    'vkGetPhysicalDeviceXlibPresentationSupportKHR':
    'VK_USE_PLATFORM_XLIB_KHR',
    'Window': 'VK_USE_PLATFORM_XLIB_KHR',
    'Display': 'VK_USE_PLATFORM_XLIB_KHR',
    'vkCreateXlibSurfaceKHR': 'VK_USE_PLATFORM_XLIB_KHR',
    'VkWaylandSurfaceCreateFlagsKHR': 'VK_USE_PLATFORM_WAYLAND_KHR'
}

CUSTOM_FUNCTIONS = ('vkGetInstanceProcAddr', 'vkGetDeviceProcAddr',
                    'vkMapMemory', 'vkGetPipelineCacheData')
CUSTOM_STRUCTS = ('VkDebugReportCallbackCreateInfoEXT',)
CUSTOM_CONSTANTS = {'VK_NULL_HANDLE': 0}
MACRO_FUNCTIONS = ('VK_MAKE_VERSION', 'VK_VERSION_MAJOR',
                   'VK_VERSION_MINOR', 'VK_VERSION_PATCH')
MACRO_PROPERTIES = ('VK_NULL_HANDLE', 'UINT64_MAX')
NULL_MEMBERS = ('pNext', 'pAllocator', 'pUserData')


def get_source(url):
    filename = os.path.join(PATH, CACHE_MAPPING[url])
    try:
        with open(filename) as f:
            result = f.read()
    except FileNotFoundError:
        result = requests.get(url).text
        with open(filename, 'w') as f:
            f.write(result)
    return result


def init():
    """Init create cache files and return vkxml dict"""
    def clean(content):
        cleaned = ""
        for line in content.splitlines(True):
            if '#include "vk_platform.h"' in line:
                continue
            line = line.replace(' const ', ' ')
            line = line.replace('const* ', '*')
            cleaned += line
        return cleaned

    def write_template(filename, content):
        with open(os.path.join(PATH_TEMPLATE, filename), 'w') as f:
            f.write(content)

    write_template('vk_plateform.h', get_source(VULKAN_PLATEFORM_URL))
    write_template('vulkan.h', clean(get_source(VULKAN_H_URL)))
    return xmltodict.parse(get_source(VK_XML_URL))


def get_enum_names(vk):
    return {e['@name'] for e in vk['registry']['enums']}


def get_handle_names(vk):
    return {s['name'] for s in vk['registry']['types']['type']
            if s.get('@category', None) == 'handle'}


def get_struct_names(vk):
    return {s['@name'] for s in vk['registry']['types']['type']
            if s.get('@category', None) == 'struct'}


def get_union_names(vk):
    return {s['name'] for s in vk['registry']['types']['type']
            if s.get('@category', None) == 'union'}


def model_constants(vk, model):
    model['constants'] = []

    def add_constant(constant, ext_number=0):
        if '@bitpos' in constant:
            value = constant['@bitpos']
            num_val = int(value, 0)
            num_val = 1 << num_val
            value = '0x%08x' % num_val
            model['constants'].append({
                'name': constant['@name'],
                'value': value,
                'type': 'int'})
        elif '@value' in constant:
            value = constant['@value']
            value_type = 'str'
            if not constant['@value'].startswith('"'):
                value = constant['@value']
                value_type = 'int'
            model['constants'].append({
                'name': constant['@name'],
                'value': value,
                'type': value_type})
        elif '@offset' in constant:
            ext_base = 1000000000
            ext_block_size = 1000
            value = ext_base + (ext_number - 1) * ext_block_size
            value += int(constant['@offset'])
            model['constants'].append({
                'name': constant['@name'],
                'value': value,
                'type': 'int'})

    for enum in vk['registry']['enums']:
        # uniform
        if type(enum['enum']) is not list:
            enum['enum'] = [enum['enum']]
        for constant in enum['enum']:
            add_constant(constant)

    for extension in vk['registry']['extensions']['extension']:
        if type(extension['require']['enum']) is not list:
            extension['require']['enum'] = [extension['require']['enum']]
        for constant in extension['require']['enum']:
            add_constant(constant, int(extension['@number']))

    add_constant({'@name': 'VK_API_VERSION_1_0',
                  '@value': 'VK_API_VERSION_1_0'})


def model_structs(vk, model):
    model['structs'] = []
    structs = [s for s in vk['registry']['types']['type']
               if s.get('@category', None) == 'struct']
    unions = [u for u in vk['registry']['types']['type']
              if u.get('@category', None) == 'union']
    FORCE_RETURN_ONLY = ('VkAllocationCallbacks',)
    for struct in structs + unions:
        sname = struct['@name']
        if sname in CUSTOM_STRUCTS:
            continue

        members = []
        for member in struct['member']:
            type_name = member['type']
            if '#text' in member:
                text = member['#text'].replace('const ', '').strip()
                type_name += ' ' + text

            l = member['@len'] if '@len' in member else None

            members.append({
                'name': member['name'],
                'type': type_name,
                'raw_type': member['type'],
                'enum': member.get('enum'),
                'null': True if member['name'] in NULL_MEMBERS else False,
                'len': l,
                'force_array': True if '@len' in member else False
            })

        return_only = False
        if struct.get('@returnedonly') or sname in FORCE_RETURN_ONLY:
            return_only = True

        model['structs'].append({
            'name': sname,
            'define': MAPPING_EXTENSION_DEFINE.get(struct['@name']),
            'members': members,
            'return_only': return_only,
            'union': True if struct in unions else False
        })

    model['custom_structs'] = CUSTOM_STRUCTS


def model_functions(vk, model):
    def get_vk_extension_functions():
        names = set()
        for extension in vk['registry']['extensions']['extension']:
            if 'command' not in extension['require']:
                continue
            if type(extension['require']['command']) is not list:
                extension['require']['command'] = [
                    extension['require']['command']]

            for command in extension['require']['command']:
                names.add(command['@name'])
        return names

    def get_count_param(command):
        for param in command['param']:
            if param['type'] + param.get('#text', '') == 'uint32_t*':
                return param
        return None

    def format_member(member):
        type_name = member['type']
        if '#text' in member:
            text = member['#text'].replace('const ', '').strip()
            type_name += ' ' + text
        return {'name': member['name'],
                'type': type_name,
                'null': member['name'] in NULL_MEMBERS,
                'force_array': True if '@len' in member else False,
                'to_create': False}

    def format_return_member(member):
        t = member['type']

        static_count = None
        if '@len' in member and '::' in member['@len']:
            lens = member['@len'].split('::')
            static_count = {'key': lens[0], 'value': lens[1]}

        is_handle = t in get_handle_names(vk)
        is_enum = t in get_enum_names(vk)
        is_struct = t in get_struct_names(vk)
        return {'name': member['name'],
                'type': t,
                'handle': is_handle,
                'enum': is_enum,
                'struct': is_struct,
                'static_count': static_count}

    ALLOCATE_PREFIX = ('vkCreate', 'vkGet', 'vkEnumerate', 'vkAllocate',
                       'vkMap', 'vkAcquire')
    ALLOCATE_EXCEPTION = ('vkGetFenceStatus', 'vkGetEventStatus',
                          'vkGetQueryPoolResults',
                          'vkGetPhysicalDeviceXlibPresentationSupportKHR')
    COUNT_EXCEPTION = ('vkAcquireNextImageKHR',)

    model['functions'] = []
    model['extension_functions'] = []
    functions = [f for f in vk['registry']['commands']['command']]
    extension_function_names = get_vk_extension_functions()

    for function in functions:
        fname = function['proto']['name']
        ftype = function['proto']['type']

        if fname in CUSTOM_FUNCTIONS:
            continue

        if type(function['param']) is not list:
            function['param'] = [function['param']]

        count_param = get_count_param(function)
        if fname in COUNT_EXCEPTION:
            count_param = None
        is_allocate = any([fname.startswith(a) for a in ALLOCATE_PREFIX])
        is_count = is_allocate and count_param is not None

        if fname in ALLOCATE_EXCEPTION or ftype == 'VkBool32':
            is_allocate = is_count = False

        members = []
        for member in function['param']:
            members.append(format_member(member))

        return_member = None
        if is_allocate:
            return_member = format_return_member(function['param'][-1])
            members[-1]['to_create'] = True
        if is_count:
            members[-2]['to_create'] = True

        f = {
            'name': fname,
            'define': MAPPING_EXTENSION_DEFINE.get(fname),
            'members': members,
            'arg': 'METH_VARARGS | METH_KEYWORDS',
            'custom': fname in CUSTOM_FUNCTIONS,
            'allocate': is_allocate,
            'count': is_count,
            'return_boolean': True if ftype == 'VkBool32' else False,
            'return_result': True if ftype == 'VkResult' else False,
            'return_member': return_member
        }

        if fname not in extension_function_names:
            model['functions'].append(f)
        else:
            model['extension_functions'].append(f)

    # Add custom functions
    model['custom_functions'] = CUSTOM_FUNCTIONS


def model_macros(model):
    model['macro_functions'] = MACRO_FUNCTIONS
    model['macro_properties'] = MACRO_PROPERTIES


def get_signatures(vk):
    '''Return formatted signatures used in filters

    signatures = [{'raw':X, 'vkname':X, 'is_struct':X,
                   'is_union':X, 'is_handle':X}]
    '''
    names = set()
    structs = [s for s in vk['registry']['types']['type']
               if s.get('@category', None) == 'struct']
    unions = [u for u in vk['registry']['types']['type']
              if u.get('@category', None) == 'union']
    handles = set([s['name'] for s in vk['registry']['types']['type']
                  if s.get('@category', None) == 'handle'])
    for s in structs + unions:
        for m in s['member']:
            name = m['type']
            if '#text' in m:
                text = m['#text'].replace('const ', '').strip()
                name += ' ' + text
            names.add(name)
    for f in vk['registry']['commands']['command']:
        if type(f['param']) is not list:
            f['param'] = [f['param']]
        for p in f['param']:
            name = p['type']
            if '#text' in p:
                text = p['#text'].replace('const ', '').strip()
                name += ' ' + text
            names.add(name)

    result = []
    for name in names:
        if name.startswith('PFN'):
            continue
        if not name.startswith('Vk'):
            continue

        vkname = name.split()[0]
        is_struct = vkname in [s['@name'] for s in structs]
        is_union = vkname in [s['@name'] for s in unions]
        is_handle = vkname in handles
        result.append({
            'raw': name,
            'vkname': vkname,
            'is_struct': is_struct,
            'is_union': is_union,
            'is_handle': is_handle
        })

    return result


def converters_signatures(signatures):
    '''return array used in converters
    '''
    cache_vknames = set()
    result = []
    for s in signatures:
        if s['vkname'] in cache_vknames:
            continue
        cache_vknames.add(s['vkname'])
        result.append({
            'vkname': s['vkname'],
            'is_struct': s['is_struct'],
            'is_union': s['is_union'],
            'is_handle': s['is_handle'],
            'define': MAPPING_EXTENSION_DEFINE.get(s['vkname'])
        })
    return result


def model_exceptions(vk, model):
    model['exceptions'] = {}
    vk_result = next(x for x in vk['registry']['enums']
                     if x['@name'] == 'VkResult')

    for enum in vk_result['enum']:
        if enum['@name'] == 'VK_SUCCESS':
            continue

        camel_name = ''.join(x for x in enum['@name'].title()
                             if x != '_')
        model['exceptions'][camel_name] = enum['@value']


def get_called_converters(model):
    '''Create a list with all called converters

    That allow to write only used converters
    in converters.c
    '''
    called_converters = set()

    def go(s):
        if s.get('return_only'):
            return

        members = jfilter.members_formated(s['members'])
        for m in members:
            called_converters.add(jfilter.detect_py_to_c(m))

    for f in (model['functions'] + model['extension_functions'] +
              model['structs']):
        if f.get('union'):
            continue
        go(f)

    return called_converters


def main():
    model = {}
    vk = init()
    model_constants(vk, model)
    model_structs(vk, model)
    model_functions(vk, model)
    model_exceptions(vk, model)
    model_macros(model)

    env = jinja2.Environment(
        autoescape=False,
        # trim_blocks=True,
        # lstrip_blocks=True,
        loader=jinja2.FileSystemLoader(os.path.join(PATH, 'template')))

    # jfilter needs signatures
    signatures = get_signatures(vk)
    jfilter.vulkan_signatures = signatures
    model['signatures'] = converters_signatures(signatures)
    model['MAPPING_EXTENSION_DEFINE'] = MAPPING_EXTENSION_DEFINE
    model['called_converters'] = get_called_converters(model)

    env.filters.update({f: getattr(jfilter, f) for f in jfilter.__all__})

    with open(DEFAULT_OUT_FILE, 'w') as out:
        out.write(env.get_template('main.c').render(model=model))


if __name__ == '__main__':
    main()
