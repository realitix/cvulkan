from vulkan import *

# Load sdk
print("- load sdk")
vkLoadSdk()

# Create instance
print("- create vkapplicationinfo")
appInfo = VkApplicationInfo(
    pApplicationName="Hello Triangle",
    applicationVersion=VK_MAKE_VERSION(1, 0, 0),
    pEngineName="No Engine",
    engineVersion=VK_MAKE_VERSION(1, 0, 0),
    apiVersion=VK_API_VERSION_1_0)

print("- list extensions")
extensions = vkEnumerateInstanceExtensionProperties(None)
extensions = [e.extensionName for e in extensions]
print("availables: %s" % extensions)

print("- list layers")
layers = vkEnumerateInstanceLayerProperties(None)
layers = [l.layerName for l in layers]
print("availables: %s" % layers)

print("- create instance info")
createInfo = VkInstanceCreateInfo(
    flags=0,
    pApplicationInfo=appInfo,
    enabledExtensionCount=len(extensions),
    ppEnabledExtensionNames=extensions,
    enabledLayerCount=len(layers),
    ppEnabledLayerNames=layers)

print("- create instance")
instance = vkCreateInstance(pCreateInfo=createInfo)

print("- get vkCreateDebugReportCallback function")
vkCreateDebugReportCallback = vkGetInstanceProcAddr(instance, "vkCreateDebugReportCallbackEXT")
