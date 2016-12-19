{% macro check_called(name) %}
    {% if name in model.called_converters %}
        {{ caller() }}
    {% endif %}
{% endmacro %}

{% for t in ['uint32_t', 'uint64_t', 'int32_t', 'size_t', 'Window', 'Display *', 'xcb_connection_t *', 'xcb_visualid_t', 'xcb_window_t', 'ANativeWindow *', 'MirConnection *', 'MirSurface *', 'HINSTANCE', 'HWND', 'HANDLE', 'SECURITY_ATTRIBUTES *', 'DWORD', 'VisualID'] %}
    {% call check_define(model.MAPPING_EXTENSION_DEFINE.get(t.split()[0])) %}
    {% call check_called('pyc_' ~ t|format_fname ~ '_converter') %}
    static int pyc_{{t|format_fname}}_converter(PyObject* arg, {{t}}* val) {
        if (!PyLong_Check(arg)) {
            PyErr_SetString(PyExc_TypeError, "Argument must be an integer");
            return 0;
        }

        *val = ({{t}}) PyLong_AsLong(arg);

        if (PyErr_Occurred())
            return 0;

        return 1;
    }

    static void pyc_{{t|format_fname}}_converter_free({{t}}* val, int disable) { }
    {% endcall %}
    {% endcall %}
{% endfor %}

static int pyc_float_converter(PyObject* arg, float* val) {
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

static void pyc_float_converter_free(float* val, int disable) {}

static int pyc_{{'void *'|format_fname}}_converter(PyObject* arg, void** val) {
    *val = NULL;
    return 1;
}

static void pyc_{{'void *'|format_fname}}_converter_free(void** val, int disable) {}

static int pyc_string_converter(PyObject* arg, char** val) {
    if (arg == Py_None) {
        *val = NULL;
        return 1;
    }

    if (!PyUnicode_Check(arg)) {
        PyErr_SetString(PyExc_TypeError, "Argument must be a string");
        return 0;
    }

    PyObject* tmp0 = PyUnicode_AsASCIIString(arg);
    if (tmp0 == NULL) {
        // Exception is raised by PyUnicode_AsASCIIString
        return 0;
    }

    char* tmp1 = PyBytes_AsString(tmp0);
    if (tmp1 == NULL) {
        // Exception is raised by PyUnicode_AsString
        Py_DECREF(tmp0);
        return 0;
    }

    *val = strdup(tmp1);
    if (*val == NULL) {
        Py_DECREF(tmp0);
        PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
        return 0;
    }

    Py_DECREF(tmp0);

    return 1;
}

static void pyc_string_converter_free(char** val, int disable) {
    if (disable)
        return;

    if (*val != NULL) {
        free(*val);
    }
}

static int pyc_array_string_converter(PyObject* arg, char*** val) {
    if (!PyList_Check(arg)) {
        PyErr_SetString(PyExc_TypeError, "Argument must be a list");
        return 0;
    }

    int size = PyList_Size(arg);

    // Array ends with NULL (needed for free part)
    *val = malloc(sizeof(char*) * (size + 1));
    if (*val == NULL) {
        PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
        return 0;
    }

    int i;
    for (i = 0; i < size; i++) {
        // item is a borrowed reference, so no Py_DECREF
        PyObject* item = PyList_GetItem(arg, i);
        if (item == NULL) {
            free(*val);
            // free previous string in array
            int j; for (j = 0; j < i; j++) free((*val)[j]);
            return 0;
        }

        if (!PyUnicode_Check(item)) {
            free(*val);
            // free previous string in array
            int j; for (j = 0; j < i; j++) free((*val)[j]);
            PyErr_SetString(PyExc_TypeError, "Argument must be a list of string");
            return 0;
        }

        PyObject* ascii_str = PyUnicode_AsASCIIString(item);
        if (ascii_str == NULL) {
            free(*val);
            // free previous string in array
            int j; for (j = 0; j < i; j++) free((*val)[j]);
            PyErr_SetString(PyExc_TypeError, "Argument must be a list of strings");
            return 0;
        }

        char* tmp = PyBytes_AsString(ascii_str);
        if (tmp == NULL) {
            // Exception is raised by PyUnicode_AsString
            free(*val);
            // free previous string in array
            int j; for (j = 0; j < i; j++) free((*val)[j]);
            Py_DECREF(ascii_str);
            return 0;
        }

        (*val)[i] = strdup(tmp);
        if ((*val)[i] == NULL) {
            free(*val);
            // free previous string in array
            int j; for (j = 0; j < i; j++) free((*val)[j]);
            Py_DECREF(ascii_str);
            PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
            return 0;
        }

        Py_DECREF(ascii_str);
    }

    (*val)[i] = NULL;

    return 1;
}

static void pyc_array_string_converter_free(char*** val, int disable) {
    if (disable)
        return;

    char** tmp = *val;

    while (tmp != NULL) {
        free(*tmp);
        tmp++;
    }

    free(*val);
}

{% macro list_generic(ctype, pyfunction) %}
static int pyc_array_{{ctype}}_converter(PyObject* arg, {{ctype}}** val) {
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
            PyObject* item = PyList_GetItem(arg, i);
            if (item == NULL) {
                return 0;
            }

            {{ctype}} r = ({{ctype}}) {{pyfunction}}(item);

            if (PyErr_Occurred())
                return 0;

            memcpy(*val + i, &r, sizeof({{ctype}}));
        }
    }

    return 1;
}

static void pyc_array_{{ctype}}_converter_free({{ctype}}** val, int disable) {
    if (disable)
        return;

    free(*val);
}
{% endmacro %}

{{list_generic('float', 'PyFloat_AsDouble')}}
{{list_generic('uint32_t', 'PyLong_AsLong')}}

{# We don't need that for now
{{list_generic('int32_t', 'PyLong_AsLong')}}
{{list_generic('uint8_t', 'PyLong_AsLong')}}
{{list_generic('uint64_t', 'PyLong_AsLong')}}
#}

static int pyc_wl_display_converter(PyObject* arg, struct wl_display** val) {
    *val = (struct wl_display*) PyLong_AsLong(arg);
    return 1;
}

static void pyc_wl_display_converter_free(struct wl_display** val, int disable) {}

static int pyc_wl_surface_converter(PyObject* arg, struct wl_surface** val) {
   *val = (struct wl_surface*) PyLong_AsLong(arg);
   return 1;
}

static void pyc_wl_surface_converter_free(struct wl_surface** val, int disable) {}

{% for signature in model.signatures %}
    {% set vkname = signature.vkname %}

    {% call check_define(signature.define) %}

    {% if signature.is_struct or signature.is_union %}

        {% call check_called('pyc_struct_array_'~ vkname ~'_converter') %}
        static int pyc_struct_array_{{vkname}}_converter(PyObject* arg, {{vkname}}** val) {
            if (arg == Py_None) {
                *val = NULL;
                return 1;
            }

            if (!PyList_Check(arg)) {
                PyErr_SetString(PyExc_TypeError, "Argument must be a list");
                return 0;
            }

            int size = PyList_Size(arg);
            *val = malloc(size * sizeof({{vkname}}));
            if (*val == NULL) {
                PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
                return 0;
            }

            int i;
            for (i = 0; i < size; i++) {
                PyObject* item = PyList_GetItem(arg, i);
                if (item == NULL) {
                    free(*val);
                    return 0;
                }

                if (!PyObject_TypeCheck(item, &Py{{vkname}}Type)) {
                    free(*val);
                    PyErr_SetString(PyExc_TypeError, "Argument must be a list of {{vkname}}");
                    return 0;
                }

                (*val)[i] = *(((Py{{vkname}}*) item)->base);
            }

            return 1;
        }

        static void pyc_struct_array_{{vkname}}_converter_free({{vkname}}** val, int disable) {
            if (disable)
                return;

            free(*val);
        }
        {% endcall %}

        {% call check_called('pyc_struct_pointer_'~ vkname ~'_converter') %}
        static int pyc_struct_pointer_{{vkname}}_converter(PyObject* arg, {{vkname}}** val) {
            if (arg == Py_None) {
                *val = NULL;
                return 1;
            }

            if (!PyObject_TypeCheck(arg, &Py{{vkname}}Type)) {
                PyErr_SetString(PyExc_TypeError, "Argument must be a {{vkname}}");
                return 0;
            }

            *val = ((Py{{vkname}}*)arg)->base;
            return 1;
        }
        static void pyc_struct_pointer_{{vkname}}_converter_free({{vkname}}** val, int disable) {}
        {% endcall %}

        {% call check_called('pyc_struct_base_'~ vkname ~'_converter') %}
        static int pyc_struct_base_{{vkname}}_converter(PyObject* arg, {{vkname}}* val) {
            if (!PyObject_TypeCheck(arg, &Py{{vkname}}Type)) {
                PyErr_SetString(PyExc_TypeError, "Argument must be a {{vkname}}");
                return 0;
            }

            *val = *(((Py{{vkname}}*)arg)->base);
            return 1;
        }
        static void pyc_struct_base_{{vkname}}_converter_free({{vkname}}* val, int disable) {}
        {% endcall %}

    {% elif signature.is_handle %}

        {% call check_called('pyc_handle_array_'~ vkname ~'_converter') %}
        // Specific ugly case
        // handle_array_VkDeviceMemory_converter is used only by Windows
        {% if vkname == 'VkDeviceMemory' %}
            #ifdef VK_USE_PLATFORM_WIN32_KHR
        {% endif %}
        static int pyc_handle_array_{{vkname}}_converter(PyObject* arg, {{vkname}}** val) {
            if (arg == Py_None) {
                *val = VK_NULL_HANDLE;
                return 1;
            }

            if (!PyList_Check(arg)) {
                PyErr_SetString(PyExc_TypeError, "Argument must be a list of {{vkname}}");
                return 0;
            }

            int size = PyList_Size(arg);
            *val = malloc(size * sizeof({{vkname}}));
            if (*val == NULL) {
                PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
                return 0;
            }

            int i;
            for (i = 0; i < size; i++) {
                PyObject* item = PyList_GetItem(arg, i);
                if (item == NULL) {
                    free(*val);
                    return 0;
                }

                {{vkname}}* handle_pointer = PyCapsule_GetPointer(PyList_GetItem(arg, i), "{{vkname}}");
                if (handle_pointer == NULL) {
                    free(*val);
                    return 0;
                }

                (*val)[i] = *handle_pointer;
            }

            return 1;
        }
        static void pyc_handle_array_{{vkname}}_converter_free({{vkname}}** val, int disable) {
            if (disable)
                return;

            free(*val);
        }
        {% if vkname == 'VkDeviceMemory' %}
            #endif
        {% endif %}
        {% endcall %}

        {% call check_called('pyc_handle_pointer_'~ vkname ~'_converter') %}
        static int pyc_handle_pointer_{{vkname}}_converter(PyObject* arg, {{vkname}}** val) {
            if (arg == Py_None) {
                *val = VK_NULL_HANDLE;
                return 1;
            }

            {{vkname}}* handle_pointer = PyCapsule_GetPointer(arg, "{{vkname}}");
            if (handle_pointer == NULL) {
                return 0;
            }

            *val = handle_pointer;
            return 1;
        }
        static void pyc_handle_pointer_{{vkname}}_converter_free({{vkname}}** val, int disable) {}
        {% endcall %}

        {% call check_called('pyc_handle_base_'~ vkname ~'_converter') %}
        static int pyc_handle_base_{{vkname}}_converter(PyObject* arg, {{vkname}}* val) {
            if (arg == Py_None) {
                *val = VK_NULL_HANDLE;
                return 1;
            }

            {{vkname}}* handle_pointer = PyCapsule_GetPointer(arg, "{{vkname}}");
            if (handle_pointer == NULL) {
                return 0;
            }

            *val = *handle_pointer;
            return 1;
        }
        static void pyc_handle_base_{{vkname}}_converter_free({{vkname}}* val, int disable) {}
        {% endcall %}

    {% else %}

        {% call check_called('pyc_flag_array_'~ vkname ~'_converter') %}
        static int pyc_flag_array_{{vkname}}_converter(PyObject* arg, {{vkname}}** val) {
            if (arg == Py_None) {
                *val = NULL;
                return 1;
            }

            if (!PyList_Check(arg)) {
                PyErr_SetString(PyExc_TypeError, "Argument must be a list of {{vkname}}");
                return 0;
            }

            int size = PyList_Size(arg);
            *val = malloc(size * sizeof({{vkname}}));
            if (*val == NULL) {
                PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
                return 0;
            }

            int i;
            for (i = 0; i < size; i++) {
                PyObject* item = PyList_GetItem(arg, i);
                if (item == NULL) {
                    free(*val);
                    return 0;
                }

                if (!PyLong_Check(item)) {
                    free(*val);
                    PyErr_SetString(PyExc_TypeError, "Argument must be a list of {{vkname}} or integer");
                    return 0;
                }

                {{vkname}} tmp = ({{vkname}}) PyLong_AsLong(item);
                if (PyErr_Occurred()) {
                    free(*val);
                    return 0;
                }

                (*val)[i] = tmp;
            }
            return 1;
        }
        static void pyc_flag_array_{{vkname}}_converter_free({{vkname}}** val, int disable) {
            if (disable)
                return;

            free(*val);
        }
        {% endcall %}

        {% call check_called('pyc_flag_pointer_'~ vkname ~'_converter') %}
        static int pyc_flag_pointer_{{vkname}}_converter(PyObject* arg, {{vkname}}** val) {
            if (arg == Py_None) {
                *val = NULL;
                return 1;
            }

            if (!PyLong_Check(arg)) {
                PyErr_SetString(PyExc_TypeError, "Argument must be a {{vkname}} or integer");
                return 0;
            }

            {{vkname}} tmp = ({{vkname}}) PyLong_AsLong(arg);

            if (PyErr_Occurred()) {
                return 0;
            }

            *val = malloc(sizeof({{vkname}}));
            if (*val == NULL) {
                PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory");
                return 0;
            }

            memcpy(*val, &tmp, sizeof({{vkname}}));
            return 1;
        }
        static void pyc_flag_pointer_{{vkname}}_converter_free({{vkname}}** val, int disable) {}
        {% endcall %}

        {% call check_called('pyc_flag_base_'~ vkname ~'_converter') %}
        static int pyc_flag_base_{{vkname}}_converter(PyObject* arg, {{vkname}}* val) {
            if (!PyLong_Check(arg)) {
                PyErr_SetString(PyExc_TypeError, "Argument must be a {{vkname}} or integer");
                return 0;
            }

            *val = ({{vkname}}) PyLong_AsLong(arg);
            if (PyErr_Occurred()) {
                return 0;
            }

            return 1;
        }
        static void pyc_flag_base_{{vkname}}_converter_free({{vkname}}* val, int disable) {}
        {% endcall %}

    {% endif %}

    {% endcall %}

{% endfor %}
