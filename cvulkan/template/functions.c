{% from 'macros.c' import content_function %}

{% for f in model['functions'] %}
   {% call check_define(f.define) %}

    static PyObject* Py{{f.name}}(PyObject *self, PyObject *args, PyObject *kwds) {
        {{content_function(f)}}
    }

    {% endcall %}
{% endfor %}
