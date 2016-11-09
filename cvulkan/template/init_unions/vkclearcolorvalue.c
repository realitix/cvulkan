static int PyVkClearColorValue_init(PyVkClearColorValue *self, PyObject *args, PyObject *kwds) {
    PyObject* float32 = NULL;
    PyObject* int32 = NULL;
    PyObject* uint32 = NULL;

    static char *kwlist[] = {"float32","int32","uint32",NULL};

    if( !PyArg_ParseTupleAndKeywords(args, kwds, "|OOO", kwlist, &float32,&int32,&uint32))
        return -1;

     if (float32 != NULL) {
        float* c_float32 = NULL;
        if (float32 == Py_None) {
            c_float32 = VK_NULL_HANDLE;
        }
        else if (PyBytes_CheckExact(float32)) {
            c_float32 = (float*) PyBytes_AsString(float32);
        }
        else {
            int size = PyList_Size(float32);
            c_float32 = malloc(sizeof(float) * size);
            int i;
            for (i = 0; i < size; i++) {
                float r = (float) PyFloat_AsDouble(
                    PyList_GetItem(float32, i));
                memcpy(c_float32 + i, &r, sizeof(float));
            }
        }

        memcpy((self->base)->float32, c_float32, 4 * sizeof(float));
    }

    if (int32 != NULL) {
        int32_t* c_int32 = NULL;
        if (int32 == Py_None) {
            c_int32 = VK_NULL_HANDLE;
        }
        else if (PyBytes_CheckExact(int32)) {
            c_int32 = (int32_t*) PyBytes_AsString(int32);
        }
        else {
            int size = PyList_Size(int32);
            c_int32 = malloc(sizeof(int32_t) * size);
            int i;
            for (i = 0; i < size; i++) {
                int32_t r = (int32_t) PyLong_AsLong(
                    PyList_GetItem(int32, i));
                memcpy(c_int32 + i, &r, sizeof(int32_t));
            }
        }
        memcpy((self->base)->int32, c_int32, 4 * sizeof(int32_t));
             }

             if (uint32 != NULL) {
        uint32_t* c_uint32 = NULL;
        if (uint32 == Py_None) {
            c_uint32 = VK_NULL_HANDLE;
        }
        else if (PyBytes_CheckExact(uint32)) {
            c_uint32 = (uint32_t*) PyBytes_AsString(uint32);
        }
        else {
            int size = PyList_Size(uint32);
            c_uint32 = malloc(sizeof(uint32_t) * size);
            int i;
            for (i = 0; i < size; i++) {
                uint32_t r = (uint32_t) PyLong_AsLong(
                    PyList_GetItem(uint32, i));
                memcpy(c_uint32 + i, &r, sizeof(uint32_t));
            }
        }
        memcpy((self->base)->uint32, c_uint32, 4 * sizeof(uint32_t));
             }
        return 0;
    }
