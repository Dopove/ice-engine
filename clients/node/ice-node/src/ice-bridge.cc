#include <napi.h>
#include <string>
#include <curl/curl.h>

// Simple callback to handle CURL response data
static size_t WriteCallback(void *contents, size_t size, size_t nmemb, void *userp) {
    ((std::string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
}

Napi::Value CallIceEngine(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();

    if (info.Length() < 2 || !info[0].IsString() || !info[1].IsObject()) {
        Napi::TypeError::New(env, "String and Object expected").ThrowAsJavaScriptException();
        return env.Null();
    }

    std::string url = info[0].As<Napi::String>();
    Napi::Object options = info[1].As<Napi::Object>();
    
    CURL *curl;
    CURLcode res;
    std::string readBuffer;

    curl_global_init(CURL_GLOBAL_ALL);
    curl = curl_easy_init();
    if(curl) {
        struct curl_slist *headers = NULL;
        headers = curl_slist_append(headers, "Content-Type: application/json");

        // Extract headers from JS object
        Napi::Value headerVal = options.Get("headers");
        if (headerVal.IsObject()) {
            Napi::Object headerObj = headerVal.As<Napi::Object>();
            Napi::Array headerNames = headerObj.GetPropertyNames();
            for (uint32_t i = 0; i < headerNames.Length(); i++) {
                Napi::Value keyVal = headerNames[i];
                Napi::Value valVal = headerObj.Get(keyVal);
                std::string header_line = keyVal.ToString().Utf8Value() + ": " + valVal.ToString().Utf8Value();
                headers = curl_slist_append(headers, header_line.c_str());
            }
        }
        
        std::string body = options.Get("body").ToString().Utf8Value();

        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body.c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
        
        res = curl_easy_perform(curl);
        curl_easy_cleanup(curl);
        curl_slist_free_all(headers);
    }
    curl_global_cleanup();

    return Napi::String::New(env, readBuffer);
}

Napi::Object Init(Napi::Env env, Napi::Object exports) {
    exports.Set(Napi::String::New(env, "callIceEngine"), Napi::Function::New(env, CallIceEngine));
    return exports;
}

NODE_API_MODULE(ice_bridge, Init)
