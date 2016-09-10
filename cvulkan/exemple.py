from vulkan import *

# Load sdk
print("- load sdk")
vkLoadSdk()

# Create instance
print("- create vkapplicationinfo")
appInfo = VkApplicationInfo(
    sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,
    pApplicationName="Hello Triangle",
    applicationVersion=VK_MAKE_VERSION(1, 0, 0),
    pEngineName="No Engine",
    engineVersion=VK_MAKE_VERSION(1, 0, 0),
    apiVersion=VK_API_VERSION_1_0)

print("- list extensions")
extensions = vkEnumerateInstanceExtensionProperties(None)
print("availables: %s" % [e.extensionName for e in extensions])

print("- list layers")
layers = vkEnumerateInstanceLayerProperties(None)
print("availables: %s" % [l.layerName for l in layers])

print("- create instance")
createInfo = VkInstanceCreateInfo(
    sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
    flags=0,
    pApplicationInfo=appInfo,
    enabledExtensionCount=len(extensions),
    ppEnabledExtensionNames=extensions,
    enabledLayerCount=len(layers),
    ppEnabledLayerNames=layers)
