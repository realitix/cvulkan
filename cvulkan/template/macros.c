{% macro check_define(define) %}
    {% if define %} #ifdef {{define}} {% endif %}
        {{ caller() }}
    {% if define %} #endif {% endif %}
{% endmacro %}
