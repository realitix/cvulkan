{% macro check_called(name) %}
    {% if name in model.called_converters %}
        {{ caller() }}
    {% endif %}
{% endmacro %}

{% for t in ['uint32_t', 'uint64_t', 'int32_t', 'size_t', 'Window', 'Display *', 'xcb_connection_t *', 'xcb_visualid_t', 'xcb_window_t', 'ANativeWindow *', 'MirConnection *', 'MirSurface *', 'HINSTANCE', 'HWND', 'HANDLE', 'SECURITY_ATTRIBUTES *', 'DWORD', 'VisualID'] %}
    {% call check_define(model.MAPPING_EXTENSION_DEFINE.get(t.split()[0])) %}
    {% call check_called(t|format_fname ~ '_converter') %}
    static int {{t|format_fname}}_converter(PyObject* arg, {{t}}* val) {
        if (!PyLong_Check(arg)) {
            PyErr_SetString(PyExc_TypeError, "Argument must be an integer");
            return 0;
        }

        *val = ({{t}}) PyLong_AsLong(arg);

        if (PyErr_Occurred())
            return 0;

        return 1;
    }
    {% endcall %}
    {% endcall %}
{% endfor %}

static int float_converter(PyObject* arg, float* val) {
    // We accept int and we convert it to float
    if (!PyFloat_Check(arg) && !PyLong_Check(arg)) {
        PyErr_SetString(PyExc_TypeError, "Argument must be a float");
        return 0;
    }

    *val = (float) PyFloat_AsDouble(arg);

    if (PyErr_Occurred())
        return 0;

    return 1;
}

static int {{'void *'|format_fname}}_converter(PyObject* arg, void** val) {
    *val = NULL;
    return 1;
}


static int string_converter(PyObject* arg, char** val) {
    if (arg == Py_None) {
        *val = NULL;
        return 1;
    }

    PyObject* tmp0 = PyUnicode_AsASCIIString(arg);
    if (tmp0 == NULL) {
        PyErr_SetString(PyExc_TypeError, "Argument must be a string");
        return 0;
    }

    char* tmp1 = PyBytes_AsString(tmp0);
    *val = strdup(tmp1);
    Py_DECREF(tmp0);

    return 1;
}

static int array_string_converter(PyObject* arg, char*** val) {
    int size = PyList_Size(arg);
    *val = malloc(sizeof(char*) * size);
    int i;
    for (i=0; i < size; i++) {
        PyObject* item = PyList_GetItem(arg, i);

        if (item == NULL)
            return 0;

        PyObject* ascii_str = PyUnicode_AsASCIIString(item);

        if (ascii_str == NULL) {
            PyErr_SetString(PyExc_TypeError, "Argument must be a list of strings");
            return 0;
        }

        char* tmp = PyBytes_AsString(ascii_str);
        (*val)[i] = strdup(tmp);
        Py_DECREF(ascii_str);
    }

    return 1;
}

{% macro list_generic(ctype, pyfunction) %}
static int array_{{ctype}}_converter(PyObject* arg, {{ctype}}** val) {
    if (arg == Py_None) {
        *val = VK_NULL_HANDLE;
    }
    else if (PyBytes_CheckExact(arg)) {
        *val = ({{ctype}}*) PyBytes_AsString(arg);
    }
    else {
        int size = PyList_Size(arg);
        *val = malloc(sizeof({{ctype}}) * size);
        int i;
        for (i = 0; i < size; i++) {
            {{ctype}} r = ({{ctype}}) {{pyfunction}}(PyList_GetItem(arg, i));
            memcpy(*val + i, &r, sizeof({{ctype}}));
        }
    }

    return 1;
}
{% endmacro %}

{{list_generic('float', 'PyFloat_AsDouble')}}
{{list_generic('uint32_t', 'PyLong_AsLong')}}
{# {{list_generic('int32_t', 'PyLong_AsLong')}}
{{list_generic('uint8_t', 'PyLong_AsLong')}}
{{list_generic('uint64_t', 'PyLong_AsLong')}} #}

static int wl_display_converter(PyObject* arg, struct wl_display** val) {
    *val = (struct wl_display*) PyLong_AsLong(arg);
    return 1;
}

static int wl_surface_converter(PyObject* arg, struct wl_surface** val) {
   *val = (struct wl_surface*) PyLong_AsLong(arg);
   return 1;
}


{% for signature in model.signatures %}
    {% set vkname = signature.vkname %}

    {% call check_define(signature.define) %}

    {% if signature.is_struct or signature.is_union %}

        {% call check_called('struct_array_'~ vkname ~'_converter') %}
        static int struct_array_{{vkname}}_converter(PyObject* arg, {{vkname}}** val) {
            if (arg == Py_None) {
                *val = NULL;
                return 1;
            }

            int size = PyList_Size(arg);
            *val = malloc(size * sizeof({{vkname}}));
            int i;
            for (i = 0; i < size; i++) {
                (*val)[i] = *(((Py{{vkname}}*) PyList_GetItem(arg, i))->base);
            }

            return 1;
        }
        {% endcall %}

        {% call check_called('struct_pointer_'~ vkname ~'_converter') %}
        static int struct_pointer_{{vkname}}_converter(PyObject* arg, {{vkname}}** val) {
            if (arg == Py_None) {
                *val = NULL;
                return 1;
            }

            *val = ((Py{{vkname}}*)arg)->base;
            return 1;
        }
        {% endcall %}

        {% call check_called('struct_base_'~ vkname ~'_converter') %}
        static int struct_base_{{vkname}}_converter(PyObject* arg, {{vkname}}* val) {
            *val = *(((Py{{vkname}}*)arg)->base);
            return 1;
        }
        {% endcall %}

    {% elif signature.is_handle %}

        {% call check_called('handle_array_'~ vkname ~'_converter') %}
        // Specific ugly case
        // handle_array_VkDeviceMemory_converter is used only by Windows
        {% if vkname == 'VkDeviceMemory' %}
            #ifdef VK_USE_PLATFORM_WIN32_KHR
        {% endif %}
        static int handle_array_{{vkname}}_converter(PyObject* arg, {{vkname}}** val) {
            if (arg == Py_None) {
                *val = VK_NULL_HANDLE;
                return 1;
            }

            int size = PyList_Size(arg);
            *val = malloc(size * sizeof({{vkname}}));
            int i;

            for (i = 0; i < size; i++) {
                {{vkname}}* handle_pointer = PyCapsule_GetPointer(PyList_GetItem(arg, i), "{{vkname}}");
                (*val)[i] = *handle_pointer;
            }

            return 1;
        }
        {% if vkname == 'VkDeviceMemory' %}
            #endif
        {% endif %}
        {% endcall %}

        {% call check_called('handle_pointer_'~ vkname ~'_converter') %}
        static int handle_pointer_{{vkname}}_converter(PyObject* arg, {{vkname}}** val) {
            if (arg == Py_None) {
                *val = VK_NULL_HANDLE;
                return 1;
            }

            {{vkname}}* handle_pointer = PyCapsule_GetPointer(arg, "{{vkname}}");
            *val = handle_pointer;
            return 1;
        }
        {% endcall %}

        {% call check_called('handle_base_'~ vkname ~'_converter') %}
        static int handle_base_{{vkname}}_converter(PyObject* arg, {{vkname}}* val) {
            if (arg == Py_None) {
                *val = VK_NULL_HANDLE;
                return 1;
            }

            {{vkname}}* handle_pointer = PyCapsule_GetPointer(arg, "{{vkname}}");
            *val = *handle_pointer;
            return 1;
        }
        {% endcall %}

    {% else %}

        {% call check_called('flag_array_'~ vkname ~'_converter') %}
        static int flag_array_{{vkname}}_converter(PyObject* arg, {{vkname}}** val) {
            if (arg == Py_None) {
                *val = NULL;
                return 1;
            }

            int size = PyList_Size(arg);
            *val = malloc(size * sizeof({{vkname}}));
            int i;
            for (i = 0; i < size; i++) {
                {{vkname}} tmp = ({{vkname}}) PyLong_AsLong(PyList_GetItem(arg, i));
                (*val)[i] = tmp;
            }
            return 1;
        }
        {% endcall %}

        {% call check_called('flag_pointer_'~ vkname ~'_converter') %}
        static int flag_pointer_{{vkname}}_converter(PyObject* arg, {{vkname}}** val) {
            if (arg == Py_None) {
                *val = NULL;
                return 1;
            }

            *val = malloc(sizeof({{vkname}}));
            {{vkname}} tmp = ({{vkname}}) PyLong_AsLong(arg);
            memcpy(*val, &tmp, sizeof({{vkname}}));
            return 1;
        }
        {% endcall %}

        {% call check_called('flag_base_'~ vkname ~'_converter') %}
        static int flag_base_{{vkname}}_converter(PyObject* arg, {{vkname}}* val) {
            *val = ({{vkname}}) PyLong_AsLong(arg);
            return 1;
        }
        {% endcall %}

    {% endif %}

    {% endcall %}

{% endfor %}
