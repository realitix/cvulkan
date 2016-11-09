static int PyVkClearValue_init(PyVkClearValue *self, PyObject *args, PyObject *kwds) {
        
            PyObject* color = NULL;
PyObject* depthStencil = NULL;

            static char *kwlist[] = {"color","depthStencil",NULL};
            
    if( !PyArg_ParseTupleAndKeywords(args, kwds,
        "|OO", kwlist, &color,&depthStencil))
        return 0;
    

            
             if (color != NULL) { 
                    
                    
                    
                        
                VkClearColorValue c_color = *(((PyVkClearColorValue*)color)->base);
                
                        (self->base)->color = c_color;
                    
             } 
            
             if (depthStencil != NULL) { 
                    
                    
                    
                        
                VkClearDepthStencilValue c_depthStencil = *(((PyVkClearDepthStencilValue*)depthStencil)->base);
                
                        (self->base)->depthStencil = c_depthStencil;
                    
             } 
            
        

        return 0;
    }
