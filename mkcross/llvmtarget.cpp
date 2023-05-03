#include <functional>
#include <iostream>
#include <sstream>
#include <Python.h>
#include "modsupport.h"
#include "structmember.h"

#include <llvm/ADT/Triple.h>
#include <llvm/MC/TargetRegistry.h>
#include <llvm/Support/TargetSelect.h>
#include <llvm/Support/VersionTuple.h>
#include <llvm/TargetParser/Triple.h>

struct LLVMTarget {
	PyObject_HEAD;
	llvm::Triple t;

	static int tp_init(PyObject* _self, PyObject* args, PyObject* kwds) {
		auto* self = reinterpret_cast<LLVMTarget*>(_self);
		const char* triple;
		int ret = PyArg_ParseTuple(args, "s", &triple);
		if (ret == 0) {
			return -1;
		}

		std::string normalized = llvm::Triple::normalize(triple);
		self->t = llvm::Triple(normalized);

		std::string error;
		const auto *target = llvm::TargetRegistry::lookupTarget(triple, error);

		if (target == nullptr) {
			auto errorstream = std::stringstream();
			errorstream << "could not parse triple " << triple << ", LLVM says: " << error;
			PyErr_SetString(PyExc_ValueError, errorstream.str().c_str());
			return -1;
		}

		// HACK: technically, none should be as part of OS
		if (self->t.getOS() == llvm::Triple::UnknownOS && self->t.getVendorName() != "none") {
			PyErr_SetString(PyExc_ValueError, "Unknown OS!");
		    return -1;
		}

		/* This is probably fine
		if (self->t.getEnvironment() == llvm::Triple::UnknownEnvironment) {
			PyErr_SetString(PyExc_ValueError, "Unknown Environment!");
			return -1;
		}*/


		return 0;
	}

	static struct PyGetSetDef getsets[];
};


inline PyObject* PyObject_From(const char* string) {
	return PyUnicode_FromString(string);
}

inline PyObject* PyObject_From(bool b) {
	return PyBool_FromLong(static_cast<long>(b));
}

/* TODO: uncomment when I figure out a way to do this
template<typename T>
consteval PyGetSetDef llvm_getset(std::string_view name, T wrapped) {
	return {
		name.data(), [&](PyObject* self, void* data) -> PyObject* {
			auto* target = reinterpret_cast<LLVMTarget*>(self);
			auto r = wrapped(target);
			auto result = target->t.getOSName();
			return pyobject_for_T(result);
		}
	};
}
*/

struct PyGetSetDef LLVMTarget::getsets[] = {
	{"arch", [](PyObject* self, void*) { return PyObject_From(llvm::Triple::getArchTypeName(reinterpret_cast<LLVMTarget*>(self)->t.getArch()).str().c_str()); }},
	{"os", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.getOSName().str().c_str()); }},
	{"vendor", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.getVendorName().str().c_str()); }},
	{"environment", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.getEnvironmentName().str().c_str()); }},

	{"triplestr", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.getTriple().c_str()); }},

	{"is_64bit", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isArch64Bit()); }},

	{"is_baremetal", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.getVendorName() == "none"); }},

	{"is_aarch64", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isAArch64()); }},
	{"is_arm", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isARM()); }},
	{"is_thumb", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isThumb()); }},
	{"is_mips", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isMIPS()); }},
	{"is_ppc", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isPPC()); }},
	{"is_ppc32", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isPPC32()); }},
	{"is_ppc64", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isPPC64()); }},
	{"is_riscv", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isRISCV()); }},
	{"is_sparc", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isSPARC()); }},
	{"is_sparc32", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isSPARC32()); }},
	{"is_sparc64", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isSPARC64()); }},
	{"is_systemz", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isSystemZ()); }},
	{"is_x86", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isX86()); }},

	{"is_linux", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isOSLinux()); }},
	{"is_mingw", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isWindowsGNUEnvironment()); }},
	{"is_musl", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isMusl()); }},
	{"is_windows_cygwin", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isWindowsCygwinEnvironment()); }},
	{"is_macosx", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isMacOSX()); }},
	{"is_ios", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isiOS()); }},
	{"is_hurd", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isOSHurd()); }},
	{"is_solaris", [](PyObject* self, void*) { return PyObject_From(reinterpret_cast<LLVMTarget*>(self)->t.isOSSolaris()); }},
	{nullptr},
};

// clang-format off
static PyTypeObject llvm_target_type {
	PyVarObject_HEAD_INIT(&PyType_Type, 0)
	"llvmtarget",
	sizeof(LLVMTarget),
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	Py_TPFLAGS_DEFAULT,
	"A wrapper for LLVM::Triple",
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	LLVMTarget::getsets,
	0,
	0,
	0,
	0,
	0,
	LLVMTarget::tp_init,
	0,
	PyType_GenericNew,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
};

// clang-format on

static PyModuleDef llvmtargetmodule = {PyModuleDef_HEAD_INIT,
									   "llvmtarget",
									   "Wrapper module for LLVM::Triple",
									   -1};

PyMODINIT_FUNC PyInit_llvmtarget(void) {
	if (PyType_Ready(&llvm_target_type) < 0) { return nullptr; }
	auto* m = PyModule_Create(&llvmtargetmodule);
	if (m == nullptr) { return nullptr; }

	Py_INCREF(&llvm_target_type);
	PyModule_AddObject(m, "LLVMTarget", (PyObject*) &llvm_target_type);

	llvm::InitializeAllTargets();
	llvm::InitializeAllTargetMCs();
	llvm::InitializeAllAsmPrinters();
	llvm::InitializeAllAsmParsers();

	return m;
}

int main() {
	return 1;
}
