from vulkan import *

#----------
# Load sdk
vkLoadSdk()


#----------
# Create instance
appInfo = VkApplicationInfo(
    pApplicationName="Hello Triangle",
    applicationVersion=VK_MAKE_VERSION(1, 0, 0),
    pEngineName="No Engine",
    engineVersion=VK_MAKE_VERSION(1, 0, 0),
    apiVersion=VK_API_VERSION_1_0)

extensions = vkEnumerateInstanceExtensionProperties(None)
extensions = [e.extensionName for e in extensions]
print("availables extensions: %s\n" % extensions)

layers = vkEnumerateInstanceLayerProperties(None)
layers = [l.layerName for l in layers]
print("availables layers: %s\n" % layers)

createInfo = VkInstanceCreateInfo(
    flags=0,
    pApplicationInfo=appInfo,
    enabledExtensionCount=len(extensions),
    ppEnabledExtensionNames=extensions,
    enabledLayerCount=len(layers),
    ppEnabledLayerNames=layers)

instance = vkCreateInstance(pCreateInfo=createInfo)


#----------
# Debug instance
vkCreateDebugReportCallback = vkGetInstanceProcAddr(instance, "vkCreateDebugReportCallbackEXT")
vkDestroyDebugReportCallback = vkGetInstanceProcAddr(instance, "vkDestroyDebugReportCallbackEXT")

def debugCallback(*args):
    print(args)

debug_create = VkDebugReportCallbackCreateInfoEXT(flags = VK_DEBUG_REPORT_ERROR_BIT_EXT | VK_DEBUG_REPORT_WARNING_BIT_EXT, pfnCallback = debugCallback)
callback = vkCreateDebugReportCallback(instance=instance, pCreateInfo=debug_create)


#----------
# Select device
devices = vkEnumeratePhysicalDevices(instance)
devices_features = {device: vkGetPhysicalDeviceFeatures(device) for device in devices}
#devices_properties = {device: vkGetPhysicalDeviceProperties(device) for device in devices}
#print("availables devices: %s\n" % [p.deviceName for p in devices_features.values()])


#----------
# Clean everything
#vkDestroyDebugReportCallback(instance, callback) We don't call it to see the error
vkDestroyInstance(instance)
