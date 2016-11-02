{% from 'macros.c' import check_define %}
{% include 'header.c' %}


// ---------------
// DECLARE EXCEPTION FUNCTION
// ---------------
static PyObject *VulkanError;
{% for e in model.exceptions %}
    static PyObject *{{e}};
{% endfor %}

int raise(int value) {
    switch(value) {
        {% for key, value in model.exceptions.items() %}
            case {{value}}: PyErr_SetString({{key}}, "");
                return 1;
        {% endfor %}
       }
    return 0;
}

// ---------------
// DECLARE FUNCTIONS PROTOTYPE
// ---------------
{% for f in model.functions %}
    {% call check_define(f.define) %}
        static PFN_{{f.name}} {{f.name}};
    {% endcall %}
{% endfor %}

{% for f in model.custom_functions %}
    static PFN_{{f}} {{f}};
{% endfor %}


// ---------------
// DECLARE PYTHON STRUCTS
// ---------------
{% for s in model.structs %}
    {% call check_define(s.define) %}
        typedef struct { PyObject_HEAD {{s.name}} *base; } Py{{s.name}};
        static PyTypeObject Py{{s.name}}Type;
    {% endcall %}
{% endfor %}


// ---------------
// CREATE SDK LOADER FUNCTION
// ---------------
static int init_import_sdk(void) {
    void* vk_sdk = LOAD_SDK();
    if (vk_sdk == NULL) {
        PyErr_SetString(PyExc_ImportError, "Can't find vulkan sdk");
        return 0;
    }

    {% for f in model.functions %}
        {{f.name}} = (PFN_{{f.name}})dlsym(vk_sdk, "{{f.name}}");
        if ({{f.name}} == NULL) {
            PyErr_SetString(PyExc_ImportError, "Can't load {{f.name}} in sdk");
            return 0;
        }
    {% endfor %}

    return 1;
}


// ---------------
// CREATE PYTHON OBJECTS
// ---------------
{% include 'objects.c' %}


// ---------------
// CREATE PYTHON FUNCTIONS
// ---------------
{% include 'functions.c' %}
{% include 'extension_functions.c' %}


// ---------------
// CREATE PYTHON CUSTOM FUNCTIONS
// ---------------
{% include 'custom_functions.c' %}


// ---------------
// REGISTER VULKAN METHOD
// ---------------
static PyMethodDef VulkanMethods[] = {
    {% for f in model.functions %}
        {% call check_define(f.define) %}
            {"{{f.name}}", (PyCFunction)Py{{f.name}}, {{f.arg}}, ""},
        {% endcall %}
    {% endfor %}

    {% for f in model.custom_functions %}
        {"{{f}}", (PyCFunction)Py{{f}}, METH_VARARGS, ""},
    {% endfor %}

    {% for f in model.macros %}
        {"{{f}}", (PyCFunction)Py{{f}}, METH_VARARGS, ""},
    {% endfor %}

    {NULL, NULL, 0, NULL}
};


// ---------------
// CREATE PYTHON MODULE
// ---------------
static struct PyModuleDef vulkanmodule = {
    PyModuleDef_HEAD_INIT, "vulkan", "Vulkan Module", -1, VulkanMethods
};


// ---------------
// PYTHON ENTRY POINT
// ---------------
{% include 'init.c' %}
