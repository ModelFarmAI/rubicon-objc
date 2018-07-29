import os
from ctypes import (
    CDLL, CFUNCTYPE, POINTER, Structure, Union, addressof, alignment, byref, c_bool, c_char_p, c_double, c_float,
    c_int, c_longdouble, c_size_t, c_uint, c_uint8, c_void_p, cast, memmove, sizeof, util,
)

from . import ctypes_patch
from .types import (
    __arm__, __i386__, __x86_64__, c_ptrdiff_t, ctype_for_encoding, ctype_for_type, encoding_for_ctype, with_encoding,
    with_preferred_encoding,
)

__all__ = [
    'Class',
    'Foundation',
    'IMP',
    'Ivar',
    'Method',
    'SEL',
    'add_ivar',
    'add_method',
    'get_class',
    'get_ivar',
    'libc',
    'libobjc',
    'load_library',
    'objc_block',
    'objc_id',
    'objc_method_description',
    'objc_property_t',
    'objc_super',
    'object_isClass',
    'send_message',
    'send_super',
    'set_ivar',
    'should_use_fpret',
    'should_use_stret',
]

######################################################################

_lib_path = ["/usr/lib"]
_framework_path = ["/System/Library/Frameworks"]


def load_library(name):
    """Load and return the C library with the given name.

    If the library could not be found, a :class:`ValueError` is raised.

    Internally, this function uses :func:`ctypes.util.find_library` to search for the library in the system-standard
    locations. If the library cannot be found this way, it is attempted to load the library from certain hardcoded
    locations, as a fallback for systems where ``find_library`` does not work (such as iOS).
    """

    path = util.find_library(name)
    if path is not None:
        return CDLL(path)

    # On iOS (and probably also watchOS and tvOS), ctypes.util.find_library doesn't work and always returns None.
    # This is because the sandbox hides all system libraries from the filesystem and pretends they don't exist.
    # However they can still be loaded if the path is known, so we try to load the library from a few known locations.

    for loc in _lib_path:
        try:
            return CDLL(os.path.join(loc, "lib" + name + ".dylib"))
        except OSError:
            pass

    for loc in _framework_path:
        try:
            return CDLL(os.path.join(loc, name + ".framework", name))
        except OSError:
            pass

    raise ValueError("Library {!r} not found".format(name))


libc = load_library('c')
libobjc = load_library('objc')
Foundation = load_library('Foundation')


@with_encoding(b'@')
class objc_id(c_void_p):
    """The `id <https://developer.apple.com/documentation/objectivec/id?language=objc>`__ type from ``<objc/objc.h>``."""


@with_encoding(b'@?')
class objc_block(objc_id):
    """The low-level type of block pointers. This does not correspond to a specific C type, because block pointer types in Objective-C are expressed using special syntax (similar to function pointers) and do not have a type name."""


@with_preferred_encoding(b':')
class SEL(c_void_p):
    """The `SEL <https://developer.apple.com/documentation/objectivec/sel?language=objc>`__ type from ``<objc/objc.h>``."""

    @property
    def name(self):
        """The selector's name as :class:`bytes`."""

        if self.value is None:
            raise ValueError("Cannot get name of null selector")

        return libobjc.sel_getName(self)

    def __new__(cls, init=None):
        """The constructor can be called with a :class:`bytes` or :class:`str` object to obtain a selector with that value. (The normal arguments supported by :class:`~ctypes.c_void_p` are still accepted.)"""

        if isinstance(init, (bytes, str)):
            self = libobjc.sel_registerName(ensure_bytes(init))
            self._inited = True
            return self
        else:
            self = super().__new__(cls, init)
            self._inited = False
            return self

    def __init__(self, init=None):
        if not self._inited:
            super().__init__(init)

    def __repr__(self):
        return "{cls.__module__}.{cls.__qualname__}({name!r})".format(
            cls=type(self), name=None if self.value is None else self.name
        )


@with_preferred_encoding(b'#')
class Class(objc_id):
    """The `Class <https://developer.apple.com/documentation/objectivec/class?language=objc>`__ type from ``<objc/objc.h>``."""


class IMP(c_void_p):
    """The `IMP <https://developer.apple.com/documentation/objectivec/objective_c_runtime/imp?language=objc>`__ type from ``<objc/objc.h>``.

    An :class:`IMP` cannot be called directly --- it must be cast to the correct :func:`~ctypes.CFUNCTYPE` first, to provide the necessary information about its signature.
    """


class Method(c_void_p):
    """The `Method <https://developer.apple.com/documentation/objectivec/method?language=objc>`__ type from ``<objc/runtime.h>``."""


class Ivar(c_void_p):
    """The `Ivar <https://developer.apple.com/documentation/objectivec/ivar?language=objc>`__ type from ``<objc/runtime.h>``."""


class objc_property_t(c_void_p):
    """The `objc_property_t <https://developer.apple.com/documentation/objectivec/objc_property_t?language=objc>`__ type from ``<objc/runtime.h>``."""


class objc_property_attribute_t(Structure):
    """The `objc_property_attribute_t <https://developer.apple.com/documentation/objectivec/objc_property_attribute_t?language=objc>`__ structure from ``<objc/runtime.h>``."""

    _fields_ = [
        ('name', c_char_p),
        ('value', c_char_p),
    ]


######################################################################

# void free(void *)
libc.free.restype = None
libc.free.argtypes = [c_void_p]

# BOOL class_addIvar(Class cls, const char *name, size_t size, uint8_t alignment, const char *types)
libobjc.class_addIvar.restype = c_bool
libobjc.class_addIvar.argtypes = [Class, c_char_p, c_size_t, c_uint8, c_char_p]

# BOOL class_addMethod(Class cls, SEL name, IMP imp, const char *types)
libobjc.class_addMethod.restype = c_bool
libobjc.class_addMethod.argtypes = [Class, SEL, IMP, c_char_p]

# BOOL class_addProperty(Class cls, const char *name, const objc_property_attribute_t *attributes,
#     unsigned int attributeCount)
libobjc.class_addProperty.restype = c_bool
libobjc.class_addProperty.argtypes = [Class, c_char_p, POINTER(objc_property_attribute_t), c_uint]

# BOOL class_addProtocol(Class cls, Protocol *protocol)
libobjc.class_addProtocol.restype = c_bool
libobjc.class_addProtocol.argtypes = [Class, objc_id]

# BOOL class_conformsToProtocol(Class cls, Protocol *protocol)
libobjc.class_conformsToProtocol.restype = c_bool
libobjc.class_conformsToProtocol.argtypes = [Class, objc_id]

# Ivar * class_copyIvarList(Class cls, unsigned int *outCount)
# Returns an array of pointers of type Ivar describing instance variables.
# The array has *outCount pointers followed by a NULL terminator.
# You must free() the returned array.
libobjc.class_copyIvarList.restype = POINTER(Ivar)
libobjc.class_copyIvarList.argtypes = [Class, POINTER(c_uint)]

# Method * class_copyMethodList(Class cls, unsigned int *outCount)
# Returns an array of pointers of type Method describing instance methods.
# The array has *outCount pointers followed by a NULL terminator.
# You must free() the returned array.
libobjc.class_copyMethodList.restype = POINTER(Method)
libobjc.class_copyMethodList.argtypes = [Class, POINTER(c_uint)]

# objc_property_t * class_copyPropertyList(Class cls, unsigned int *outCount)
# Returns an array of pointers of type objc_property_t describing properties.
# The array has *outCount pointers followed by a NULL terminator.
# You must free() the returned array.
libobjc.class_copyPropertyList.restype = POINTER(objc_property_t)
libobjc.class_copyPropertyList.argtypes = [Class, POINTER(c_uint)]

# Protocol ** class_copyProtocolList(Class cls, unsigned int *outCount)
# Returns an array of pointers of type Protocol* describing protocols.
# The array has *outCount pointers followed by a NULL terminator.
# You must free() the returned array.
libobjc.class_copyProtocolList.restype = POINTER(objc_id)
libobjc.class_copyProtocolList.argtypes = [Class, POINTER(c_uint)]

# Method class_getClassMethod(Class aClass, SEL aSelector)
# Will also search superclass for implementations.
libobjc.class_getClassMethod.restype = Method
libobjc.class_getClassMethod.argtypes = [Class, SEL]

# Ivar class_getClassVariable(Class cls, const char* name)
libobjc.class_getClassVariable.restype = Ivar
libobjc.class_getClassVariable.argtypes = [Class, c_char_p]

# Method class_getInstanceMethod(Class aClass, SEL aSelector)
# Will also search superclass for implementations.
libobjc.class_getInstanceMethod.restype = Method
libobjc.class_getInstanceMethod.argtypes = [Class, SEL]

# size_t class_getInstanceSize(Class cls)
libobjc.class_getInstanceSize.restype = c_size_t
libobjc.class_getInstanceSize.argtypes = [Class]

# Ivar class_getInstanceVariable(Class cls, const char* name)
libobjc.class_getInstanceVariable.restype = Ivar
libobjc.class_getInstanceVariable.argtypes = [Class, c_char_p]

# const char *class_getIvarLayout(Class cls)
libobjc.class_getIvarLayout.restype = c_char_p
libobjc.class_getIvarLayout.argtypes = [Class]

# IMP class_getMethodImplementation(Class cls, SEL name)
libobjc.class_getMethodImplementation.restype = IMP
libobjc.class_getMethodImplementation.argtypes = [Class, SEL]

# const char * class_getName(Class cls)
libobjc.class_getName.restype = c_char_p
libobjc.class_getName.argtypes = [Class]

# objc_property_t class_getProperty(Class cls, const char *name)
libobjc.class_getProperty.restype = objc_property_t
libobjc.class_getProperty.argtypes = [Class, c_char_p]

# Class class_getSuperclass(Class cls)
libobjc.class_getSuperclass.restype = Class
libobjc.class_getSuperclass.argtypes = [Class]

# int class_getVersion(Class theClass)
libobjc.class_getVersion.restype = c_int
libobjc.class_getVersion.argtypes = [Class]

# const char *class_getWeakIvarLayout(Class cls)
libobjc.class_getWeakIvarLayout.restype = c_char_p
libobjc.class_getWeakIvarLayout.argtypes = [Class]

# BOOL class_isMetaClass(Class cls)
libobjc.class_isMetaClass.restype = c_bool
libobjc.class_isMetaClass.argtypes = [Class]

# IMP class_replaceMethod(Class cls, SEL name, IMP imp, const char *types)
libobjc.class_replaceMethod.restype = IMP
libobjc.class_replaceMethod.argtypes = [Class, SEL, Ivar, c_char_p]

# BOOL class_respondsToSelector(Class cls, SEL sel)
libobjc.class_respondsToSelector.restype = c_bool
libobjc.class_respondsToSelector.argtypes = [Class, SEL]

# void class_setIvarLayout(Class cls, const char *layout)
libobjc.class_setIvarLayout.restype = None
libobjc.class_setIvarLayout.argtypes = [Class, c_char_p]

# void class_setVersion(Class theClass, int version)
libobjc.class_setVersion.restype = None
libobjc.class_setVersion.argtypes = [Class, c_int]

# void class_setWeakIvarLayout(Class cls, const char *layout)
libobjc.class_setWeakIvarLayout.restype = None
libobjc.class_setWeakIvarLayout.argtypes = [Class, c_char_p]

######################################################################

# const char * ivar_getName(Ivar ivar)
libobjc.ivar_getName.restype = c_char_p
libobjc.ivar_getName.argtypes = [Ivar]

# ptrdiff_t ivar_getOffset(Ivar ivar)
libobjc.ivar_getOffset.restype = c_ptrdiff_t
libobjc.ivar_getOffset.argtypes = [Ivar]

# const char * ivar_getTypeEncoding(Ivar ivar)
libobjc.ivar_getTypeEncoding.restype = c_char_p
libobjc.ivar_getTypeEncoding.argtypes = [Ivar]

######################################################################

# void method_exchangeImplementations(Method m1, Method m2)
libobjc.method_exchangeImplementations.restype = None
libobjc.method_exchangeImplementations.argtypes = [Method, Method]

# IMP method_getImplementation(Method method)
libobjc.method_getImplementation.restype = IMP
libobjc.method_getImplementation.argtypes = [Method]

# SEL method_getName(Method method)
libobjc.method_getName.restype = SEL
libobjc.method_getName.argtypes = [Method]

# const char * method_getTypeEncoding(Method method)
libobjc.method_getTypeEncoding.restype = c_char_p
libobjc.method_getTypeEncoding.argtypes = [Method]

# IMP method_setImplementation(Method method, IMP imp)
libobjc.method_setImplementation.restype = IMP
libobjc.method_setImplementation.argtypes = [Method, IMP]

######################################################################

# Class objc_allocateClassPair(Class superclass, const char *name, size_t extraBytes)
libobjc.objc_allocateClassPair.restype = Class
libobjc.objc_allocateClassPair.argtypes = [Class, c_char_p, c_size_t]

# Protocol **objc_copyProtocolList(unsigned int *outCount)
# Returns an array of *outcount pointers followed by NULL terminator.
# You must free() the array.
libobjc.objc_copyProtocolList.restype = POINTER(objc_id)
libobjc.objc_copyProtocolList.argtypes = [POINTER(c_int)]

# id objc_getAssociatedObject(id object, void *key)
libobjc.objc_getAssociatedObject.restype = objc_id
libobjc.objc_getAssociatedObject.argtypes = [objc_id, c_void_p]

# Class objc_getClass(const char *name)
libobjc.objc_getClass.restype = Class
libobjc.objc_getClass.argtypes = [c_char_p]

# Class objc_getMetaClass(const char *name)
libobjc.objc_getMetaClass.restype = Class
libobjc.objc_getMetaClass.argtypes = [c_char_p]

# Protocol *objc_getProtocol(const char *name)
libobjc.objc_getProtocol.restype = objc_id
libobjc.objc_getProtocol.argtypes = [c_char_p]

# You should set return and argument types depending on context.
# id objc_msgSend(id theReceiver, SEL theSelector, ...)
# id objc_msgSendSuper(struct objc_super *super, SEL op,  ...)

# The _stret variants only exist on x86-based architectures and ARM32.
if __i386__ or __x86_64__ or __arm__:
    # void objc_msgSendSuper_stret(struct objc_super *super, SEL op, ...)
    libobjc.objc_msgSendSuper_stret.restype = None

    # void objc_msgSend_stret(void * stretAddr, id theReceiver, SEL theSelector,  ...)
    libobjc.objc_msgSend_stret.restype = None

# The _fpret variant only exists on x86-based architectures.
if __i386__ or __x86_64__:
    # double objc_msgSend_fpret(id self, SEL op, ...)
    libobjc.objc_msgSend_fpret.restype = c_double

# void objc_registerClassPair(Class cls)
libobjc.objc_registerClassPair.restype = None
libobjc.objc_registerClassPair.argtypes = [Class]

# void objc_removeAssociatedObjects(id object)
libobjc.objc_removeAssociatedObjects.restype = None
libobjc.objc_removeAssociatedObjects.argtypes = [objc_id]

# void objc_setAssociatedObject(id object, void *key, id value, objc_AssociationPolicy policy)
libobjc.objc_setAssociatedObject.restype = None
libobjc.objc_setAssociatedObject.argtypes = [objc_id, c_void_p, objc_id, c_int]

######################################################################

# Class object_getClass(id object)
libobjc.object_getClass.restype = Class
libobjc.object_getClass.argtypes = [objc_id]

# object_isClass exists as a native function only since OS X 10.10 and iOS 8.
# If unavailable, we emulate it: an object is a class iff its class is a metaclass.
try:
    object_isClass = libobjc.object_isClass
except AttributeError:
    def object_isClass(obj):
        """Return whether the given Objective-C object is a class (or a metaclass).

        This is the emulated version of the object_isClass runtime function, for systems older than OS X 10.10 or iOS 8, where the real function doesn't exist yet.
        """

        return libobjc.class_isMetaClass(libobjc.object_getClass(obj))
else:
    # BOOL object_isClass(id obj)
    object_isClass.restype = c_bool
    object_isClass.argtypes = [objc_id]

# const char *object_getClassName(id obj)
libobjc.object_getClassName.restype = c_char_p
libobjc.object_getClassName.argtypes = [objc_id]

# Note: The following functions only work for exactly pointer-sized ivars.
# To use non-pointer-sized ivars reliably, the memory location must be calculated manually (using ivar_getOffset)
# and then used as a pointer. This "manual" way can be used for all ivars except weak object ivars - these must be
# accessed through the runtime functions in order to work correctly.

# id object_getIvar(id object, Ivar ivar)
libobjc.object_getIvar.restype = objc_id
libobjc.object_getIvar.argtypes = [objc_id, Ivar]

# void object_setIvar(id object, Ivar ivar, id value)
libobjc.object_setIvar.restype = None
libobjc.object_setIvar.argtypes = [objc_id, Ivar, objc_id]

######################################################################


# const char *property_getAttributes(objc_property_t property)
libobjc.property_getAttributes.restype = c_char_p
libobjc.property_getAttributes.argtypes = [objc_property_t]

# const char *property_getName(objc_property_t property)
libobjc.property_getName.restype = c_char_p
libobjc.property_getName.argtypes = [objc_property_t]

# objc_property_attribute_t *property_copyAttributeList(objc_property_t property, unsigned int *outCount)
libobjc.property_copyAttributeList.restype = POINTER(objc_property_attribute_t)
libobjc.property_copyAttributeList.argtypes = [objc_property_t, POINTER(c_uint)]

######################################################################


class objc_method_description(Structure):
    """The `objc_method_description <https://developer.apple.com/documentation/objectivec/objc_method_description?language=objc>`__ structure from ``<objc/runtime.h>``."""

    _fields_ = [
        ('name', SEL),
        ('types', c_char_p),
    ]


# void protocol_addMethodDescription(Protocol *proto, SEL name, const char *types,
#     BOOL isRequiredMethod, BOOL isInstanceMethod)
libobjc.protocol_addMethodDescription.restype = None
libobjc.protocol_addMethodDescription.argtypes = [objc_id, SEL, c_char_p, c_bool, c_bool]

# void protocol_addProtocol(Protocol *proto, Protocol *addition)
libobjc.protocol_addProtocol.restype = None
libobjc.protocol_addProtocol.argtypes = [objc_id, objc_id]

# void protocol_addProperty(Protocol *proto, const char *name, const objc_property_attribute_t *attributes,
#     unsigned int attributeCount, BOOL isRequiredProperty, BOOL isInstanceProperty)
libobjc.protocol_addProperty.restype = None
libobjc.protocol_addProperty.argtypes = [objc_id, c_char_p, POINTER(objc_property_attribute_t), c_uint, c_bool, c_bool]

# Protocol *objc_allocateProtocol(const char *name)
libobjc.objc_allocateProtocol.restype = objc_id
libobjc.objc_allocateProtocol.argtypes = [c_char_p]

# BOOL protocol_conformsToProtocol(Protocol *proto, Protocol *other)
libobjc.protocol_conformsToProtocol.restype = c_bool
libobjc.protocol_conformsToProtocol.argtypes = [objc_id, objc_id]

# struct objc_method_description *protocol_copyMethodDescriptionList(
#     Protocol *p, BOOL isRequiredMethod, BOOL isInstanceMethod, unsigned int *outCount)
# You must free() the returned array.
libobjc.protocol_copyMethodDescriptionList.restype = POINTER(objc_method_description)
libobjc.protocol_copyMethodDescriptionList.argtypes = [objc_id, c_bool, c_bool, POINTER(c_uint)]

# objc_property_t * protocol_copyPropertyList(Protocol *protocol, unsigned int *outCount)
libobjc.protocol_copyPropertyList.restype = POINTER(objc_property_t)
libobjc.protocol_copyPropertyList.argtypes = [objc_id, POINTER(c_uint)]

# Protocol **protocol_copyProtocolList(Protocol *proto, unsigned int *outCount)
libobjc.protocol_copyProtocolList.restype = POINTER(objc_id)
libobjc.protocol_copyProtocolList.argtypes = [objc_id, POINTER(c_uint)]

# struct objc_method_description protocol_getMethodDescription(
#     Protocol *p, SEL aSel, BOOL isRequiredMethod, BOOL isInstanceMethod)
libobjc.protocol_getMethodDescription.restype = objc_method_description
libobjc.protocol_getMethodDescription.argtypes = [objc_id, SEL, c_bool, c_bool]

# const char *protocol_getName(Protocol *p)
libobjc.protocol_getName.restype = c_char_p
libobjc.protocol_getName.argtypes = [objc_id]

# void objc_registerProtocol(Protocol *proto)
libobjc.objc_registerProtocol.restype = None
libobjc.objc_registerProtocol.argtypes = [objc_id]

######################################################################

# const char* sel_getName(SEL aSelector)
libobjc.sel_getName.restype = c_char_p
libobjc.sel_getName.argtypes = [SEL]

# BOOL sel_isEqual(SEL lhs, SEL rhs)
libobjc.sel_isEqual.restype = c_bool
libobjc.sel_isEqual.argtypes = [SEL, SEL]

# SEL sel_registerName(const char *str)
libobjc.sel_registerName.restype = SEL
libobjc.sel_registerName.argtypes = [c_char_p]


######################################################################

def ensure_bytes(x):
    """Convert the given string to :class:`bytes` if necessary.

    If the argument is already :class:`bytes`, it is returned unchanged; if it is :class:`str`, it is encoded as UTF-8.
    """

    if isinstance(x, bytes):
        return x
    # "All char * in the runtime API should be considered to have UTF-8 encoding."
    # https://developer.apple.com/documentation/objectivec/objective_c_runtime?preferredLanguage=occ
    return x.encode('utf-8')


######################################################################


def get_class(name):
    """Get the Objective-C class with the given name as a :class:`Class` object.

    If no class with the given name is loaded, ``None`` is returned, and the Objective-C runtime will log a warning message.
    """

    return libobjc.objc_getClass(ensure_bytes(name))


# http://www.sealiesoftware.com/blog/archive/2008/10/30/objc_explain_objc_msgSend_stret.html
# http://www.x86-64.org/documentation/abi-0.99.pdf  (pp.17-23)
# executive summary: on x86-64, who knows?
def should_use_stret(restype):
    """Return whether a method returning the given type must be called using ``objc_msgSend_stret`` on the current system."""

    if type(restype) != type(Structure):
        # Not needed when restype is not a structure.
        return False
    elif __i386__:
        # On i386: Use for structures not sized exactly like an integer (1, 2, 4, or 8 bytes).
        return sizeof(restype) not in (1, 2, 4, 8)
    elif __x86_64__:
        # On x86_64: Use for structures larger than 16 bytes.
        # (The ABI docs say that there are some special cases
        # for vector types, but those can't really be used
        # with ctypes anyway.)
        return sizeof(restype) > 16
    elif __arm__:
        # On ARM32: Use for all structures, regardless of size.
        return True
    else:
        # Other platforms: Doesn't exist.
        return False


# http://www.sealiesoftware.com/blog/archive/2008/11/16/objc_explain_objc_msgSend_fpret.html
def should_use_fpret(restype):
    """Return whether a method returning the given type must be called using ``objc_msgSend_fpret`` on the current system."""

    if __x86_64__:
        # On x86_64: Use only for long double.
        return restype == c_longdouble
    elif __i386__:
        # On i386: Use for all floating-point types.
        return restype in (c_float, c_double, c_longdouble)
    else:
        # Other platforms: Doesn't exist.
        return False


def send_message(receiver, selector, *args, restype=c_void_p, argtypes=None):
    """Call a method on the receiver with the given selector and arguments.

    This is the equivalent of an Objective-C method call like ``[receiver sel:args]``.

    :param receiver: The object on which to call the method. This may be an Objective-C object (as an :class:`ObjCInstance`, :class:`objc_id`, or :class:`~ctypes.c_void_p`), or an Objective-C class name (as a :class:`str` or :class:`bytes`).
    :param selector: The name of the method as a :class:`str`, :class:`bytes`, or :class:`SEL`.
    :param args: The method arguments.
    :param restype: The return type of the method. Defaults to :class:`~ctypes.c_void_p`.
    :param argtypes: The argument types of the method, as a :class:`list`. Defaults to an empty list (i. e. all arguments are treated as C varargs).
    """

    try:
        receiver = receiver._as_parameter_
    except AttributeError:
        pass

    if isinstance(receiver, objc_id):
        pass
    elif isinstance(receiver, (str, bytes)):
        receiver = cast(get_class(receiver), objc_id)
    elif type(receiver) == c_void_p:
        receiver = cast(receiver, objc_id)
    else:
        raise TypeError("Invalid type for receiver: {tp.__module__}.{tp.__qualname__}".format(tp=type(receiver)))

    selector = SEL(selector)
    if argtypes is None:
        argtypes = []

    # Choose the correct version of objc_msgSend based on return type.
    # Use libobjc['name'] instead of libobjc.name to get a new function object
    # that is independent of the one on the objc library.
    # This way multiple threads sending messages don't overwrite
    # each other's function signatures.
    if should_use_fpret(restype):
        send = libobjc['objc_msgSend_fpret']
        send.restype = restype
        send.argtypes = [objc_id, SEL] + argtypes
        result = send(receiver, selector, *args)
    elif should_use_stret(restype):
        send = libobjc['objc_msgSend_stret']
        send.restype = restype
        send.argtypes = [objc_id, SEL] + argtypes
        result = send(receiver, selector, *args)
    else:
        send = libobjc['objc_msgSend']
        send.restype = restype
        send.argtypes = [objc_id, SEL] + argtypes
        result = send(receiver, selector, *args)
        if restype == c_void_p:
            result = c_void_p(result)
    return result


class objc_super(Structure):
    """The `objc_super <https://developer.apple.com/documentation/objectivec/objc_super?language=objc>`__ structure from ``<objc/message.h>``."""

    _fields_ = [
        ('receiver', objc_id),
        ('super_class', Class),
    ]


# http://stackoverflow.com/questions/3095360/what-exactly-is-super-in-objective-c
def send_super(cls, receiver, selector, *args, restype=c_void_p, argtypes=None):
    """In the context of the given class, call a superclass method on the receiver with the given selector and arguments.

    This is the equivalent of an Objective-C method call like ``[super sel:args]`` in the class ``cls``.

    In practice, the first parameter should always be the special variable ``__class__``, and the second parameter should be ``self``. A typical :func:`send_super` call would be ``send_super(__class__, self, 'init')`` for example.

    The special variable ``__class__`` is defined by Python and stands for the class object that is being created by the current ``class`` block. The exact reasons why ``__class__`` must be passed manually are somewhat technical, and are not directly relevant to users of :func:`send_super`. For a full explanation, see issue `pybee/rubicon-objc#107 <https://github.com/pybee/rubicon-objc/issues/107>`__ and PR `pybee/rubicon-objc#108 <https://github.com/pybee/rubicon-objc/pull/108>`__.

    Although it is possible to pass other values than ``__class__`` and ``self`` for the first two parameters, this is strongly discouraged. Doing so is not supported by the Objective-C language, and relies on implementation details of the superclasses.

    :param cls: The class in whose context the ``super`` call is happening, as an :class:`ObjCClass` or :class:`Class`.
    :param receiver: The object on which to call the method, as an :class:`ObjCInstance`, :class:`objc_id`, or :class:`~ctypes.c_void_p`.
    :param selector: The name of the method as a :class:`str`, :class:`bytes`, or :class:`SEL`.
    :param args: The method arguments.
    :param restype: The return type of the method. Defaults to :class:`~ctypes.c_void_p`.
    :param argtypes: The argument types of the method, as a :class:`list`. Defaults to an empty list (i. e. all arguments are treated as C varargs).
    """

    # Unwrap ObjCClass to Class if necessary
    try:
        cls = cls._as_parameter_
    except AttributeError:
        pass

    if not isinstance(cls, Class):
        # Kindly remind the caller that the API has changed
        raise TypeError(
            'Missing or invalid cls argument: expected an ObjCClass or Class, not {tp.__module__}.{tp.__qualname__}\n'
            'send_super requires the current class to be passed explicitly as the first argument. '
            'To fix this error, pass the special name __class__ as the first argument to send_super.'
            .format(tp=type(cls))
        )

    try:
        receiver = receiver._as_parameter_
    except AttributeError:
        pass

    if isinstance(receiver, objc_id):
        pass
    elif type(receiver) == c_void_p:
        receiver = cast(receiver, objc_id)
    else:
        raise TypeError("Invalid type for receiver: {tp.__module__}.{tp.__qualname__}".format(tp=type(receiver)))

    super_ptr = libobjc.class_getSuperclass(cls)
    if super_ptr.value is None:
        raise ValueError(
            'The specified class {!r} is a root class, it cannot be used with send_super'
            .format(libobjc.class_getName(cls).decode('utf-8'))
        )
    super_struct = objc_super(receiver, super_ptr)
    selector = SEL(selector)
    if argtypes is None:
        argtypes = []

    if should_use_stret(restype):
        send = libobjc['objc_msgSendSuper_stret']
    else:
        send = libobjc['objc_msgSendSuper']
    send.restype = restype
    send.argtypes = [POINTER(objc_super), SEL] + argtypes
    result = send(byref(super_struct), selector, *args)
    if restype == c_void_p:
        result = c_void_p(result)
    return result


def add_method(cls, selector, method, encoding):
    """Add a new instance method to the given class.

    To add a class method, add an instance method to the metaclass.

    :param cls: The Objective-C class to which to add the method, as an :class:`ObjCClass` or :class:`Class`.
    :param selector: The name for the new method, as a :class:`str`, :class:`bytes`, or :class:`SEL`.
    :param method: The method implementation, as a Python callable or a C function address.
    :param encoding: The method's signature (return type and argument types) as a :class:`list`. The types of the implicit ``self`` and ``_cmd`` parameters must be included in the signature.
    """

    signature = [ctype_for_type(tp) for tp in encoding]
    assert signature[1] == objc_id  # ensure id self typecode
    assert signature[2] == SEL  # ensure SEL cmd typecode
    if signature[0] is not None and issubclass(signature[0], (Structure, Union)):
        # Patch struct/union return types to make them work in callbacks.
        # See the source code of the ctypes_patch module for details.
        ctypes_patch.make_callback_returnable(signature[0])
    selector = SEL(selector)
    types = b"".join(encoding_for_ctype(ctype) for ctype in signature)

    cfunctype = CFUNCTYPE(*signature)
    imp = cfunctype(method)
    libobjc.class_addMethod(cls, selector, cast(imp, IMP), types)
    return imp


def add_ivar(cls, name, vartype):
    """Add a new instance variable of type vartype to cls."""

    return libobjc.class_addIvar(
        cls, ensure_bytes(name), sizeof(vartype),
        alignment(vartype), encoding_for_ctype(ctype_for_type(vartype))
    )


def get_ivar(obj, varname):
    """Get the value of obj's ivar named varname.

    The returned object is a :mod:`ctypes` data object.

    For non-object types (everything except :class:`objc_id` and subclasses), the returned data object is backed by the
    ivar's actual memory. This means that the data object is only usable as long as the "owner" object is alive, and
    writes to it will directly change the ivar's value.

    For object types, the returned data object is independent of the ivar's memory. This is because object ivars may
    be weak, and thus cannot always be accessed directly by their address.
    """

    try:
        obj = obj._as_parameter_
    except AttributeError:
        pass

    ivar = libobjc.class_getInstanceVariable(libobjc.object_getClass(obj), ensure_bytes(varname))
    vartype = ctype_for_encoding(libobjc.ivar_getTypeEncoding(ivar))

    if isinstance(vartype, objc_id):
        return cast(libobjc.object_getIvar(obj, ivar), vartype)
    else:
        return vartype.from_address(obj.value + libobjc.ivar_getOffset(ivar))


def set_ivar(obj, varname, value):
    """Set obj's ivar varname to value.

    value must be a :mod:`ctypes` data object whose type matches that of the ivar.
    """

    try:
        obj = obj._as_parameter_
    except AttributeError:
        pass

    ivar = libobjc.class_getInstanceVariable(libobjc.object_getClass(obj), ensure_bytes(varname))
    vartype = ctype_for_encoding(libobjc.ivar_getTypeEncoding(ivar))

    if not isinstance(value, vartype):
        raise TypeError(
            "Incompatible type for ivar {!r}: {!r} is not a subclass of the ivar's type {!r}"
            .format(varname, type(value), vartype)
        )
    elif sizeof(type(value)) != sizeof(vartype):
        raise TypeError(
            "Incompatible type for ivar {!r}: {!r} has size {}, but the ivar's type {!r} has size {}"
            .format(varname, type(value), sizeof(type(value)), vartype, sizeof(vartype))
        )

    if isinstance(vartype, objc_id):
        libobjc.object_setIvar(obj, ivar, value)
    else:
        memmove(obj.value + libobjc.ivar_getOffset(ivar), addressof(value), sizeof(vartype))
