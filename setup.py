from distutils.command.clean import clean
from setuptools import setup, find_packages, Extension
import os

import cvulkan


def get_include_paths():
    import subprocess
    import tempfile
    import time

    fp = tempfile.TemporaryFile()
    p = subprocess.Popen("gcc -v -x c -E -".split(), stdout=fp, stderr=fp)
    time.sleep(1)
    p.terminate()
    fp.seek(0)
    content = fp.read()
    fp.close()
    result = []
    for line in content.splitlines():
        line = line.decode('utf-8').strip()
        if os.path.isdir(line):
            result.append(line)
    return result

include_paths = get_include_paths()


def c_import_exists(import_file):
    for path in include_paths:
        if os.path.exists(os.path.join(path, import_file)):
            return True
    return False

define_mapping = {
    'android/native_window.h': 'VK_USE_PLATFORM_ANDROID_KHR',
    'mir_toolkit/client_types.h': 'VK_USE_PLATFORM_MIR_KHR',
    'wayland-client.h': 'VK_USE_PLATFORM_WAYLAND_KHR',
    'windows.h': 'VK_USE_PLATFORM_WIN32_KHR',
    'X11/Xlib.h': 'VK_USE_PLATFORM_XLIB_KHR',
    'xcb/xcb.h': 'VK_USE_PLATFORM_XCB_KHR'
}

enabled_defines = [value for key, value in define_mapping.items()
                   if c_import_exists(key)]
macros = [(d, None) for d in enabled_defines]
print("Extension compiled for : %s" % enabled_defines)

vulkanmodule = Extension('vulkan',
                         sources=['cvulkan/vulkanmodule2.c'],
                         define_macros=macros)


class CVulkanClean(clean):
    def run(self):
        super().run()

        # Clean tmp files
        app_path = os.path.dirname(os.path.realpath(__file__))
        for filepath in ['cvulkan/cache_vk_plateform.h',
                         'cvulkan/cache_vk.xml', 'cvulkan/cache_vulkan.h',
                         'cvulkan/template/vk_plateform.h',
                         'cvulkan/template/vulkan.h']:
            path = os.path.join(app_path, filepath)
            try:
                os.remove(path)
                print('Delete %s' % path)
            except Exception:
                print('%s not existant' % path)


setup(
    name="cvulkan",
    version=cvulkan.__version__,
    packages=find_packages(),
    author="realitix",
    author_email="realitix@gmail.com",
    description="C Vulkan Wrapper",
    long_description=open("README.md").read(),
    install_requires=[],
    setup_requires=[],
    tests_require=[],
    include_package_data=True,
    url="http://github.com/realitix/cvulkan",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.5",
        "Topic :: Multimedia :: Graphics :: 3D Rendering"
    ],
    license="Apache",
    ext_modules=[vulkanmodule],
    cmdclass={'clean': CVulkanClean}
)
