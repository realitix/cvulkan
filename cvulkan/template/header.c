#include <Python.h>
#include <dlfcn.h>

#define VK_NO_PROTOTYPES

#ifdef __unix__

#define LOAD_SDK() dlopen("libvulkan.so", RTLD_NOW);

#elif defined(_WIN32) || defined(WIN32)

#define LOAD_SDK() LoadLibrary("vulkan-1.dll");
#define dlsym GetProcAddress

#endif

{% include 'vk_plateform.h' %}

{% include 'vulkan.h' %}
