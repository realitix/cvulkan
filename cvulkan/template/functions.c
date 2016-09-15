{% for f in model['functions'] %}
   {% call check_define(f.define) %}

    static PyObject* Py{{f.name}}(PyObject *self, PyObject *args, PyObject *kwds) {
        {{f.members|init_function_members}}
        {{f.members|kwlist}}
        {{f.members|parse_tuple_and_keywords}}

        {% set prefix = 'c_' %}
        {% for m in f.members %}
            {{m|python_to_c(m.name, prefix ~ m.name, 'NULL')}}
        {% endfor %}

        {% set rt = f.return_member.type %}

        {% if f.count %}
            uint32_t count;

            {% set call_function = f.name ~ '(' ~ f.members|join_comma(2, prefix) ~ '&count, NULL)' %}
            {% if f.return_result %}
                if (raise({{call_function}}))
                    return NULL;
            {% else %}
                {{call_function}};
            {% endif %}

            {{rt}} *values = malloc(count * sizeof({{rt}}));

            {% set call_function = f.name ~ '(' ~ f.members|join_comma(2, prefix) ~ '&count, values)' %}
            {% if f.return_result %}
                if (raise({{call_function}}))
                    return NULL;
            {% else %}
                {{call_function}};
            {% endif %}

            PyObject* return_value = PyList_New(0);
            uint32_t i;
            for (i = 0; i < count; i++) {
                {{rt}}* value = malloc(sizeof({{rt}}));
                memcpy(value, values + i, sizeof({{rt}}));

                {% if f.return_member.handle %}
                    PyObject* pyreturn = PyCapsule_New(value, "{{rt}}", NULL);
                {% elif f.return_member.enum %}
                    PyObject* pyreturn = PyLong_FromLong((long) *value);
                {% elif f.return_member.struct %}
                    PyObject* pyreturn = _PyObject_New(&Py{{rt}}Type);
                    if (!pyreturn)
                        return NULL;
                    ((Py{{rt}}*)pyreturn)->base = value;
                {% else %}
                    PyObject* pyreturn = PyLong_FromLong((long) *value);
                {% endif %}
                PyList_Append(return_value, pyreturn);
            }
            free(values);

        {% elif f.allocate %}
            {{rt}} *value = malloc(sizeof({{rt}}));
            {% set call_function = f.name ~ '(' ~ f.members|join_comma(1, prefix) ~ 'value)' %}
            {% if f.return_result %}
                if (raise({{call_function}}))
                    return NULL;
            {% else %}
                {{call_function}};
            {% endif %}

            {% if f.return_member.handle %}
                PyObject* return_value = PyCapsule_New(value, "{{rt}}", NULL);
            {% elif f.return_member.enum %}
                PyObject* return_value = PyLong_FromLong((long) *value);
            {% elif f.return_member.struct %}
                PyObject* return_value = _PyObject_New(&Py{{rt}}Type);
                if (!return_value)
                    return NULL;
                ((Py{{rt}}*)return_value)->base = value;
            {% else %}
                PyObject* return_value = PyLong_FromLong((long) *value);
            {% endif %}

        {% else %}
            {% set call_function = f.name ~ '(' ~ f.members|join_comma(0, prefix) ~ ')' %}

            {% if f.return_boolean %}
                PyObject* return_value = PyBool_FromLong({{call_function}});
            {% else %}
                {{call_function}};
                PyObject* return_value = Py_None;
            {% endif %}
        {% endif %}

        return return_value;
    }

    {% endcall %}
{% endfor %}
