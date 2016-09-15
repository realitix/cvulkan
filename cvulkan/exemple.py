# flake8: noqa
import ctypes
import sdl2
from vulkan import *

WIDTH = 400
HEIGHT = 400

# ----------
# Create instance
appInfo = VkApplicationInfo(
    sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,
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
    sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
    flags=0,
    pApplicationInfo=appInfo,
    enabledExtensionCount=len(extensions),
    ppEnabledExtensionNames=extensions,
    enabledLayerCount=len(layers),
    ppEnabledLayerNames=layers)

instance = vkCreateInstance(pCreateInfo=createInfo)


# ----------
# Debug instance
vkCreateDebugReportCallbackEXT = vkGetInstanceProcAddr(
    instance,
    "vkCreateDebugReportCallbackEXT")
vkDestroyDebugReportCallbackEXT = vkGetInstanceProcAddr(
    instance,
    "vkDestroyDebugReportCallbackEXT")


def debugCallback(*args):
    print(args)

debug_create = VkDebugReportCallbackCreateInfoEXT(
    sType=VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT,
    flags=VK_DEBUG_REPORT_ERROR_BIT_EXT | VK_DEBUG_REPORT_WARNING_BIT_EXT,
    pfnCallback=debugCallback)
callback = vkCreateDebugReportCallbackEXT(instance=instance,
                                          pCreateInfo=debug_create)


# ----------
# Init sdl2
if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
    raise Exception(sdl2.SDL_GetError())

window = sdl2.SDL_CreateWindow(
    'test'.encode('ascii'),
    sdl2.SDL_WINDOWPOS_UNDEFINED,
    sdl2.SDL_WINDOWPOS_UNDEFINED, WIDTH, HEIGHT, 0)

if not window:
    raise Exception(sdl2.SDL_GetError())

wm_info = sdl2.SDL_SysWMinfo()
sdl2.SDL_VERSION(wm_info.version)
sdl2.SDL_GetWindowWMInfo(window, ctypes.byref(wm_info))


# ----------
# Create surface
def surface_xlib():
    print("Create Xlib surface")
    vkCreateXlibSurfaceKHR = vkGetInstanceProcAddr(instance, "vkCreateXlibSurfaceKHR")
    surface_create = VkXlibSurfaceCreateInfoKHR(sType=VK_STRUCTURE_TYPE_XLIB_SURFACE_CREATE_INFO_KHR, dpy=wm_info.info.x11.display, window=wm_info.info.x11.window, flags=0)
    return vkCreateXlibSurfaceKHR(instance=instance, pCreateInfo=surface_create)


surface_mapping = {
    sdl2.SDL_SYSWM_X11: surface_xlib}

surface = surface_mapping[wm_info.subsystem]()

# ----------
# Select physical device
physical_devices = vkEnumeratePhysicalDevices(instance)
physical_devices_features = {physical_device: vkGetPhysicalDeviceFeatures(physical_device)
                    for physical_device in physical_devices}
physical_devices_properties = {physical_device: vkGetPhysicalDeviceProperties(physical_device)
                      for physical_device in physical_devices}
physical_device = physical_devices[0]
print("availables devices: %s" % [p.deviceName
                                  for p in physical_devices_properties.values()])
print("selected device: %s\n" % physical_devices_properties[physical_device].deviceName)


# ----------
# Select queue family
vkGetPhysicalDeviceSurfaceSupportKHR = vkGetInstanceProcAddr(
    instance, 'vkGetPhysicalDeviceSurfaceSupportKHR')
queue_families = vkGetPhysicalDeviceQueueFamilyProperties(physical_device)
print("%s available queue family" % len(queue_families))

queue_family_graphic_index = -1
queue_family_present_index = -1

for i, queue_family in enumerate(queue_families):
    support_present = vkGetPhysicalDeviceSurfaceSupportKHR(
        physicalDevice=physical_device,
        queueFamilyIndex=i,
        surface=surface)
    if (queue_family.queueCount > 0 and
       queue_family.queueFlags & VK_QUEUE_GRAPHICS_BIT):
        queue_family_graphic_index = i
    if queue_family.queueCount > 0 and support_present:
        queue_family_present_index = i

print("indice of selected queue families, graphic: %s, presentation: %s\n" % (
    queue_family_graphic_index, queue_family_present_index))


# ----------
# Create logical device and queues
extensions = vkEnumerateDeviceExtensionProperties(physicalDevice=physical_device, pLayerName=None)
extensions = [e.extensionName for e in extensions]
print("availables device extensions: %s\n" % extensions)

queues_create = [VkDeviceQueueCreateInfo(sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
                                         queueFamilyIndex=i,
                                         queueCount=1,
                                         pQueuePriorities=[1],
                                         flags=0)
                 for i in {queue_family_graphic_index,
                           queue_family_present_index}]

device_create = VkDeviceCreateInfo(
    sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
    pQueueCreateInfos=queues_create,
    queueCreateInfoCount=len(queues_create),
    pEnabledFeatures=physical_devices_features[physical_device],
    flags=0,
    enabledLayerCount=len(layers),
    ppEnabledLayerNames=layers,
    enabledExtensionCount=len(extensions),
    ppEnabledExtensionNames=extensions
)

logical_device = vkCreateDevice(physicalDevice=physical_device,
                                pCreateInfo=device_create)
graphic_queue = vkGetDeviceQueue(
    device=logical_device,
    queueFamilyIndex=queue_family_graphic_index,
    queueIndex=0)
presentation_queue = vkGetDeviceQueue(
    device=logical_device,
    queueFamilyIndex=queue_family_present_index,
    queueIndex=0)
print("Logical device and graphic queue successfully created\n")


# ----------
# Create swapchain
vkGetPhysicalDeviceSurfaceCapabilitiesKHR = vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceSurfaceCapabilitiesKHR")
vkGetPhysicalDeviceSurfaceFormatsKHR = vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceSurfaceFormatsKHR")
vkGetPhysicalDeviceSurfacePresentModesKHR = vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceSurfacePresentModesKHR")
surface_capabilities = vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physicalDevice=physical_device, surface=surface)
surface_formats = vkGetPhysicalDeviceSurfaceFormatsKHR(physicalDevice=physical_device, surface=surface)
surface_present_modes = vkGetPhysicalDeviceSurfacePresentModesKHR(physicalDevice=physical_device, surface=surface)

if not surface_formats or not surface_present_modes:
    raise Exception('No available swapchain')

def get_surface_format(formats):
    for f in formats:
        if f.format == VK_FORMAT_UNDEFINED:
            return  f
        if (f.format == VK_FORMAT_B8G8R8A8_UNORM and
            f.colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR):
            return f
    return formats[0]

def get_surface_present_mode(present_modes):
    for p in present_modes:
        if p == VK_PRESENT_MODE_MAILBOX_KHR:
            return p
    return VK_PRESENT_MODE_FIFO_KHR;

def get_swap_extent(capabilities):
    uint32_max = 4294967295
    if capabilities.currentExtent.width != uint32_max:
        return capabilities.currentExtent

    actualExtent = VkExtent2D(width=WIDTH, height=HEIGHT);
    actualExtent.width = max(
        capabilities.minImageExtent.width,
        min(capabilities.maxImageExtent.width, actualExtent.width))
    actualExtent.height = max(
        capabilities.minImageExtent.height,
        min(capabilities.maxImageExtent.height, actualExtent.height))
    return actualExtent


surface_format = get_surface_format(surface_formats)
present_mode = get_surface_present_mode(surface_present_modes)
extent = get_swap_extent(surface_capabilities)
imageCount = surface_capabilities.minImageCount + 1;
if surface_capabilities.maxImageCount > 0 and imageCount > surface_capabilities.maxImageCount:
    imageCount = surface_capabilities.maxImageCount

print('selected format: %s' % selected_surface_format.format)
print('%s available swapchain present modes' % len(surface_present_modes))


imageSharingMode = VK_SHARING_MODE_EXCLUSIVE
queueFamilyIndexCount = 0
pQueueFamilyIndices = None

if queue_family_graphic_index != queue_family_present_index:
    imageSharingMode = VK_SHARING_MODE_CONCURREN
    queueFamilyIndexCount = 2
    pQueueFamilyIndices = queueFamilyIndices

swapchain_create = VkSwapchainCreateInfoKHR(
    sType=VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
    surface=surface,
    minImageCount=imageCount,
    imageFormat=surface_format.format,
    imageColorSpace=surface_format.colorSpace,
    imageExtent=extent,
    imageArrayLayers=1,
    imageUsage=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
    imageSharingMode=imageSharingMode,
    queueFamilyIndexCount=queueFamilyIndexCount,
    pQueueFamilyIndices=pQueueFamilyIndices,
    compositeAlpha=VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
    presentMode=present_mode,
    clipped=VK_TRUE,
    oldSwapchain=VK_NULL_HANDLE)

swapchain = vkCreateSwapchainKHR(device, swapchain_create)

# ----------
# Clean everything
# vkDestroyDebugReportCallbackEXT(instance, callback)
# We don't call it to see the error
vkDestroyInstance(instance)
