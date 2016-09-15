{% for s in model.structs %}
    {% call check_define(s.define) %}


    // ----------
    // New
    // ----------
    static PyObject * Py{{s.name}}_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
        Py{{s.name}} *self = (Py{{s.name}} *)type->tp_alloc(type, 0);
        if (self == NULL) return NULL;
        self->base = malloc(sizeof({{s.name}}));
        if (self->base == NULL) {
            PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory for {{s.name}}");
            return NULL;
        }

        return (PyObject *)self;
    }


    // ----------
    // Del
    // ---------
    static void Py{{s.name}}_del(Py{{s.name}}* self) {
        Py_TYPE(self)->tp_free((PyObject*)self);
    }


    // ----------
    // Init
    // ----------
    static int Py{{s.name}}_init(Py{{s.name}} *self, PyObject *args, PyObject *kwds) {
        {% if not s.return_only %}
            {{s.members|init_function_members}}
            {{s.members|kwlist}}
            {{s.members|parse_tuple_and_keywords}}

            {% for m in s.members %}
                {% set cname = 'c_' ~ m.name %}
                {% set jr = m|python_to_c(m.name, cname, '-1') %}
                {% if jr %}
                    {{jr}}
                    {{cname|copy_in_object(m)}}
                {% endif %}
            {% endfor %}
        {% endif %}

        return 0;
    }


    // ----------
    // Get
    // ----------
    {% for m in s.members %}
        static PyObject* Py{{s.name}}_get{{m.name}}(Py{{s.name}} *self, void *closure) {
            {% set jr = m|c_to_python('((self->base)->' ~ m.name ~ ')', 'pyvalue') %}
            {% if jr %}
                {{jr}}
                Py_INCREF(pyvalue);
                return pyvalue;
            {% else %}
                PyErr_SetString(PyExc_ImportError, "Not Implemented, ask to the maintener");
                return NULL;
            {% endif %}
        }
    {% endfor %}


    // ----------
    // PyGetSetDef
    // ----------
    static PyGetSetDef Py{{s.name}}_getsetters[] = {
        {% for m in s.members %}
            {"{{m.name}}", (getter)Py{{s.name}}_get{{m.name}}, NULL, "", NULL},
        {% endfor %}
        {NULL}
    };




    {% endcall %}
{% endfor %}

// PyType objects are declared in a function because there are
// initialized in the main function.
// All the pytype signatures are create before.
void init_pytype_objects(void) {
    {% for s in model.structs %}
        {% call check_define(s.define) %}
            Py{{s.name}}Type = (PyTypeObject) {
                PyVarObject_HEAD_INIT(NULL, 0)
                "vulkan.{{s.name}}", sizeof(Py{{s.name}}), 0,
                (destructor)Py{{s.name}}_del,
                0,0,0,0,0,0,0,0,0,0,0,0,0,0,Py_TPFLAGS_DEFAULT,
                "{{s.name}} object",0,0,0,0,0,0,0,0,
                Py{{s.name}}_getsetters,0,0,0,0,0,
                (initproc)Py{{s.name}}_init,0,Py{{s.name}}_new,
            };
        {% endcall %}
    {% endfor %}
}
