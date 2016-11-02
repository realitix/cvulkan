{% from 'macros.c' import content_function %}

{% for f in model.extension_functions %}
    {% call check_define(f.define) %}

    typedef struct { PyObject_HEAD PFN_{{f.name}} pfn; } Py{{f.name}};

    static PyObject* Py{{f.name}}_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
        Py{{f.name}} *self;
        self = (Py{{f.name}} *)type->tp_alloc(type, 0);
        return (PyObject *)self;
    }

    static void Py{{f.name}}_del(Py{{f.name}}* self) {
        Py_TYPE(self)->tp_free((PyObject*)self);
    }

    static int Py{{f.name}}_init(Py{{f.name}} *self, PyObject *args, PyObject *kwds) {
        PyObject* capsule;
        if (!PyArg_ParseTuple(args, "O", &capsule))
            return -1;
        self->pfn = (PFN_{{f.name}}) PyCapsule_GetPointer(capsule, NULL);
        if (self->pfn == NULL)
            return -1;
        return 0;
    }


    static PyObject* Py{{f.name}}_call(PyObject *self, PyObject *args, PyObject *kwds) {
        {{content_function(f, '(*(((Py'~ f.name ~'*)self)->pfn))')}}
    }

    static PyTypeObject Py{{f.name}}Type = {
        PyVarObject_HEAD_INIT(NULL, 0) "vulkan.{{f.name}}", sizeof(Py{{f.name}}), 0,
        (destructor)Py{{f.name}}_del, 0,0,0,0,0,0,0,0,0,(ternaryfunc)Py{{f.name}}_call,
        0,0,0,0,Py_TPFLAGS_DEFAULT, "{{f.name}} object",0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,(initproc)Py{{f.name}}_init,0,Py{{f.name}}_new,
    };
    {% endcall %}
{% endfor %}
