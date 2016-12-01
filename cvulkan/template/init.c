PyMODINIT_FUNC PyInit_vulkan(void) {
    PyObject* module = PyModule_Create(&vulkanmodule);
    if (module == NULL)
        return NULL;

    if (!init_import_sdk())
        return NULL;


    // ----------
    // CONSTANTS
    // ----------
    {% for constant in model.constants %}
        {% if constant.type == 'int' %}
            PyModule_AddIntConstant(module, "{{constant.name}}", {{constant.value}});
        {% elif constant.type == 'str' %}
            PyModule_AddStringConstant(module, "{{constant.name}}", {{constant.value}});
        {% endif %}
    {% endfor %}


    // ----------
    // MACROS
    // ----------
    {% for m in model.macro_properties %}
        {# Return 0 on success #}
        if(PyModule_AddIntMacro(module, {{m}}))
            return NULL;
    {% endfor %}


    // ----------
    // TYPES
    // ----------
    init_pytype_objects();
    {% for s in model.structs %}
    {% call check_define(s.define) %}
        if (PyType_Ready(&Py{{s.name}}Type) < 0)
            return NULL;
        Py_INCREF(&Py{{s.name}}Type);
        PyModule_AddObject(module, "{{s.name}}", (PyObject *)&Py{{s.name}}Type);
    {% endcall %}
    {% endfor %}


    // ----------
    // TYPES FOR CUSTOM STRUCTS
    // ----------
    {% for s in model.custom_structs %}
        if (PyType_Ready(&Py{{s}}Type) < 0)
            return NULL;
        Py_INCREF(&Py{{s}}Type);
        PyModule_AddObject(module, "{{s}}", (PyObject *)&Py{{s}}Type);
    {% endfor %}

    // ----------
    // TYPES FOR EXTENSION FUNCTIONS
    // ----------
    {% for f in model.extension_functions %}
    {% call check_define(f.define) %}
        if (PyType_Ready(&Py{{f.name}}Type) < 0)
            return NULL;
        Py_INCREF(&Py{{f.name}}Type);
    {% endcall %}
    {% endfor %}


    // ----------
    // EXCEPTIONS
    // ----------
    VulkanError = PyErr_NewException("vulkan.VulkanError", NULL, NULL);
    Py_INCREF(VulkanError);
    PyModule_AddObject(module, "VulkanError", VulkanError);

    {% for e in model.exceptions %}
        {{e}} = PyErr_NewException("vulkan.{{e}}", VulkanError, NULL);
        Py_INCREF({{e}});
        PyModule_AddObject(module, "{{e}}", {{e}});
    {% endfor %}


    return module;
}

