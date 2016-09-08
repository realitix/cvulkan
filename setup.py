from setuptools import setup, find_packages, Extension

vulkanmodule = Extension('vulkan',
                         sources=['cvulkan/vulkanmodule.c'])
setup(
    name="vulkan",
    version="0.1",
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
    ext_modules=[vulkanmodule]
)
