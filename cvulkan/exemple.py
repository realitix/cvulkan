from vulkan import *
import sdl2


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
devices_properties = {device: vkGetPhysicalDeviceProperties(device) for device in devices}
device = devices[0]
print("availables devices: %s" % [p.deviceName for p in devices_properties.values()])
print("selected device: %s\n" % devices_properties[device].deviceName)


#----------
# Select queue family
queue_families = vkGetPhysicalDeviceQueueFamilyProperties(device)
print("%s available queue family" % len(queue_families))
queue_family_indice = -1;
for i, queue_family in enumerate(queue_families):
    if queue_family.queueCount > 0 and queue_family.queueFlags & VK_QUEUE_GRAPHICS_BIT:
        queue_family_indice = i
        break
print("indice of selected queue family: %s\n" % queue_family_indice)


#----------
# Create logical device
queueCreateInfo = VkDeviceQueueCreateInfo(queueFamilyIndex=queue_family_indice, queueCount = 1, pQueuePriorities=[1], flags=0)
device_create = VkDeviceCreateInfo(
    pQueueCreateInfos=queueCreateInfo,
    queueCreateInfoCount=1,
    pEnabledFeatures=devices_features[device],
    flags=0,
    enabledLayerCount=len(layers),
    ppEnabledLayerNames=layers,
    enabledExtensionCount=0,
    ppEnabledExtensionNames=[]
)

logical_device = vkCreateDevice(physicalDevice=device, pCreateInfo=device_create)
graphic_queue = vkGetDeviceQueue(device=logical_device, queueFamilyIndex=queue_family_indice, queueIndex=0)
print("Logical device and graphic queue successfully created\n")


#----------
# Init sdl2
if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
    print(sdl2.SDL_GetError())


#----------
# Clean everything
#vkDestroyDebugReportCallback(instance, callback) We don't call it to see the error
vkDestroyInstance(instance)
