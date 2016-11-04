typedef struct {
    PyObject_HEAD VkDebugReportCallbackCreateInfoEXT *base;
}
PyVkDebugReportCallbackCreateInfoEXT;

static void PyVkDebugReportCallbackCreateInfoEXT_del(PyVkDebugReportCallbackCreateInfoEXT* self) {
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject *
PyVkDebugReportCallbackCreateInfoEXT_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    PyVkDebugReportCallbackCreateInfoEXT *self;
    self = (PyVkDebugReportCallbackCreateInfoEXT *)type->tp_alloc(type, 0);
    if ( self != NULL) {
        self->base = malloc(sizeof(VkDebugReportCallbackCreateInfoEXT));
        if (self->base == NULL) {
            PyErr_SetString(PyExc_MemoryError, "Cannot allocate memory for VkDebugReportCallbackCreateInfoEXT");
            return NULL;
        }
    }

    return (PyObject *)self;
}

static PyObject *python_debug_callback = NULL;
static VKAPI_ATTR VkBool32 VKAPI_CALL debug_callback(
    VkDebugReportFlagsEXT flags,
    VkDebugReportObjectTypeEXT objType,
    uint64_t obj,
    size_t location,
    int32_t code,
    const char* layerPrefix,
    const char* msg,
    void* userData) {
    PyObject_CallFunction(python_debug_callback, "iiKIisss", flags,
                          objType, obj, location, code, layerPrefix, msg, NULL);
    return VK_FALSE;
}

static int
PyVkDebugReportCallbackCreateInfoEXT_init(
    PyVkDebugReportCallbackCreateInfoEXT *self, PyObject *args,
    PyObject *kwds) {
    int sType;
    int flags;
    PyObject* tmp = NULL;
    static char *kwlist[] = {"sType", "flags","pfnCallback",NULL};
    if(!PyArg_ParseTupleAndKeywords(args, kwds, "iiO", kwlist,
                                    &sType, &flags, &tmp))
        return -1;

    if (!PyCallable_Check(tmp)) {
        PyErr_SetString(PyExc_TypeError,
                        "pfnCallback must be callable");
        return -1;
    }
    // Renew callback
    Py_INCREF(tmp);
    Py_XDECREF(python_debug_callback);
    python_debug_callback = tmp;

    (self->base)->sType = sType;
    (self->base)->pNext = NULL;
    (self->base)->pUserData = NULL;
    (self->base)->flags = flags;
    (self->base)->pfnCallback =
        (PFN_vkDebugReportCallbackEXT)(&debug_callback);

    return 0;
}

static PyTypeObject PyVkDebugReportCallbackCreateInfoEXTType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "vulkan.VkDebugReportCallbackCreateInfoEXT", sizeof(PyVkDebugReportCallbackCreateInfoEXT), 0,
    (destructor)PyVkDebugReportCallbackCreateInfoEXT_del,
    0,0,0,0,0,0,0,0,0,0,0,0,0,0,Py_TPFLAGS_DEFAULT,
    "VkDebugReportCallbackCreateInfoEXT object",0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,(initproc)PyVkDebugReportCallbackCreateInfoEXT_init,0,PyVkDebugReportCallbackCreateInfoEXT_new,
};
