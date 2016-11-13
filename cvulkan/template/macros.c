{% macro check_define(define) %}
    {% if define %} #ifdef {{define}} {% endif %}
        {{ caller() }}
    {% if define %} #endif {% endif %}
{% endmacro %}

{% macro content_function(f, call_name=None, return_value='NULL') %}
    {% set cname = f.name %}
    {% if call_name %}
        {% set cname = call_name %}
    {% endif %}

    {{f.members|init_function_members}}
    {{f.members|kwlist}}
    {{f.members|parse_tuple_and_keywords(return_value=return_value)}}

    {% set rt = f.return_member.type %}

    {% if f.count %}
        uint32_t count;

        {% set call_function = cname ~ '(' ~ f.members|join_comma(2, '') ~ '&count, NULL)' %}
        {% if f.return_result %}
            if (raise({{call_function}}))
                return NULL;
        {% else %}
            {{call_function}};
        {% endif %}

        {{rt}} *values = malloc(count * sizeof({{rt}}));

        {% set call_function = cname ~ '(' ~ f.members|join_comma(2, '') ~ '&count, values)' %}
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
        int allocate_size = 1;

        {% if f.return_member.static_count %}
            allocate_size = (int) {{f.return_member.static_count.key}}->{{f.return_member.static_count.value}};
        {% endif %}

        {{rt}} *value = malloc(allocate_size * sizeof({{rt}}));
        {% set call_function = cname ~ '(' ~ f.members|join_comma(1, '') ~ 'value)' %}
        {% if f.return_result %}
            if (raise({{call_function}}))
                return NULL;
        {% else %}
            {{call_function}};
        {% endif %}


        {% if f.return_member.static_count %}
            PyObject* return_value = PyList_New(0);
            int i = 0;
            for (i = 0; i < allocate_size; i++) {
                {{rt}}* val = malloc(sizeof({{rt}}));
                memcpy(val, value + i, sizeof({{rt}}));

                {% if f.return_member.handle %}
                    PyObject* tmp = PyCapsule_New(val, "{{rt}}", NULL);
                {% elif f.return_member.enum %}
                    PyObject* tmp = PyLong_FromLong((long) *val);
                {% elif f.return_member.struct %}
                    PyObject* tmp = _PyObject_New(&Py{{rt}}Type);
                    if (!tmp)
                        return NULL;
                    ((Py{{rt}}*)tmp)->base = val;
                {% else %}
                    PyObject* tmp = PyLong_FromLong((long) *val);
                {% endif %}
                PyList_Append(return_value, tmp);
            }
        {% else %}
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
        {% endif %}

    {% else %}
        {% set call_function = cname ~ '(' ~ f.members|join_comma(0, '') ~ ')' %}

        {% if f.return_boolean %}
            PyObject* return_value = PyBool_FromLong({{call_function}});
        {% else %}
            {{call_function}};
            Py_INCREF(Py_None);
            PyObject* return_value = Py_None;
        {% endif %}
    {% endif %}

    {{f.members|free_pyc}}

    return return_value;
{% endmacro %}
