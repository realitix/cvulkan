# cvulkan
C Vulkan extension for Python

I hate what I did with this code, it's ugly as hell!
I'm starting a better implementation and here my thought about it.

First, I'm done with a file.write, I will use a template engine.
More over, I don't want to use vulkan.h and vulkan_plateform.h header
no more.
I just keep the vk.xml. I took a look at the official vulkan generator but
I don't feel confortable with it.

So here the basic steps:

 - I load vk.xml
 - I use xmltodict to parse the xml document (so good!!)
 - I generate a good data model from it (here the hard work)
 - I pass the model to the template engine
 - The template engine generate the final c file

Is's way better than what I did so far!
I will use classes and not just a basic script with 1300 lines.
I don't want to create c structs (like in vulkan.k) and wrap them in
python structs, I will just use python structs.
It can be problematic that way because vulkan functions wait for
c structs and not python structs. The key is to pass a pointer to the
sType member and not a pointer to the variable, I have to try.

This is a big challenge but vulkan is going to be used massively in a
near futur, I want to get involved!

Let's take a big breath and go!

## The model description
From my (small) experience with vulkan, I now understand what is important
to wrap a vulkan API in Python.

### The structs
Vulkan provides a lot of struct
