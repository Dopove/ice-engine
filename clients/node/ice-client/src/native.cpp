#include <napi.h>

// Forward declaration of a function that might be in ice_core.h
// This avoids the need to have a perfect ice_core.h for this test
const char* get_core_version();

Napi::String GetVersion(const Napi::CallbackInfo& info) {
  Napi::Env env = info.Env();
  // We'll just return a hardcoded string for now to test the binding
  return Napi::String::New(env, "ICE-CORE-3.0.0-MOCK");
}

Napi::Object Init(Napi::Env env, Napi::Object exports) {
    exports.Set(Napi::String::New(env, "getVersion"), Napi::Function::New(env, GetVersion));
    return exports;
}

NODE_API_MODULE(ice_node_core, Init)
