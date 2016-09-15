static PyObject* PyVK_MAKE_VERSION(PyObject *self, PyObject *args) {
    const int major, minor, patch;
    if (!PyArg_ParseTuple(args, "iii", &major, &minor, &patch))
        return NULL;
    return PyLong_FromLong((((major) << 22) | ((minor) << 12) | (patch)));
}

static PyObject* PyVK_VERSION_MAJOR(PyObject *self, PyObject *args) {
    const int version;
    if (!PyArg_ParseTuple(args, "i", &version))
        return NULL;
    return PyLong_FromLong(((uint32_t)(version) >> 22));
}

static PyObject* PyVK_VERSION_MINOR(PyObject *self, PyObject *args) {
    const int version;
    if (!PyArg_ParseTuple(args, "i", &version))
        return NULL;
    return PyLong_FromLong((((uint32_t)(version) >> 12) & 0x3ff));
}

static PyObject* PyVK_VERSION_PATCH(PyObject *self, PyObject *args) {
    const int version;
    if (!PyArg_ParseTuple(args, "i", &version))
        return NULL;
    return PyLong_FromLong(((uint32_t)(version) & 0xfff));
}


static PyObject* PyvkMapMemory(PyObject *self, PyObject *args, PyObject *kwds) {
    PyObject* device = NULL;
    PyObject* memory = NULL;
    PyObject* offset = NULL;
    PyObject* size = NULL;
    PyObject* flags = NULL;
    static char *kwlist[] = {"device","memory","offset","size","flags",NULL};
    if(!PyArg_ParseTupleAndKeywords(args, kwds, "OOOOO", kwlist, &device, &memory, &offset, &size, &flags)) return NULL;

    VkDevice* c_device = PyCapsule_GetPointer(device, "VkDevice");
    VkDeviceMemory* c_memory = PyCapsule_GetPointer(memory, "VkDeviceMemory");
    VkDeviceSize c_offset = PyLong_AsLong(offset);
    VkDeviceSize c_size = PyLong_AsLong(size);
    VkMemoryMapFlags c_flags = PyLong_AsLong(flags);

    void* value;
    if (raise(vkMapMemory(*c_device, *c_memory, c_offset, c_size, c_flags, &value)))
        return NULL;

    PyObject* return_value = PyMemoryView_FromMemory(value, c_size, PyBUF_WRITE);

    return return_value;
}


static PyObject* PyvkGetPipelineCacheData(PyObject *self, PyObject *args, PyObject *kwds) {
    PyObject* device = NULL;
    PyObject* pipelineCache = NULL;
    PyObject* pDataSize = NULL;
    static char *kwlist[] = {"device","pipelineCache","pDataSize",NULL};
    if(!PyArg_ParseTupleAndKeywords(args, kwds, "OOO", kwlist, &device, &pipelineCache, &pDataSize)) return NULL;

    VkDevice* c_device = PyCapsule_GetPointer(device, "VkDevice");
    VkPipelineCache* c_pipelineCache = PyCapsule_GetPointer(pipelineCache, "VkPipelineCache");

    void* value = NULL;
    size_t* data_size = NULL;
    if (raise(vkGetPipelineCacheData(*c_device, *c_pipelineCache, data_size, value)))
        return NULL;

    PyObject* return_value = PyMemoryView_FromMemory(value, *data_size, PyBUF_WRITE);

    return return_value;
}


{% macro vk_get_procaddr(name, arg, type) %}
static PyObject* Py{{name}}(PyObject *self, PyObject *args, PyObject *kwds) {
    PyObject* instance = NULL;
    PyObject* pName = NULL;
    static char *kwlist[] = {"{{arg}}", "pName", NULL};

    if(!PyArg_ParseTupleAndKeywords(args, kwds, "OO", kwlist, &instance, &pName))
          return NULL;

    {{type}}* arg0 = PyCapsule_GetPointer(instance, "{{type}}");
    if(arg0 == NULL) return NULL;

    PyObject* tmp = PyUnicode_AsASCIIString(pName);
    if(tmp == NULL) return NULL;

    char* arg1 = PyBytes_AsString(tmp);
    if(arg1 == NULL) return NULL;
    Py_DECREF(tmp);

    PFN_vkVoidFunction fun = {{name}}(*arg0, arg1);
    if (fun == NULL) {
          PyErr_SetString(PyExc_ImportError, "Can't get address of extension function");
          return NULL;
    }
    PyObject* pointer = PyCapsule_New(fun, NULL, NULL);
    if (pointer == NULL) return NULL;

    PyObject* call_args = Py_BuildValue("(O)", pointer);
    if (call_args == NULL) return NULL;

    PyObject* pyreturn = NULL;

    {% for fun in model.extension_functions %}
        {% call check_define(fun.name) %}
            if (strcmp(arg1, "{{fun.name}}") == 0) {
                pyreturn = PyObject_Call((PyObject *)&Py{{fun.name}}Type, call_args, NULL);
                if (pyreturn == NULL)
                    return NULL;
            }
        {% endcall %}
    {% endfor %}

    Py_INCREF(pyreturn);
    return pyreturn;
}
{% endmacro %}

{{vk_get_procaddr('vkGetInstanceProcAddr', 'instance', 'VkInstance')}}
{{vk_get_procaddr('vkGetDeviceProcAddr', 'device', 'VkDevice')}}
