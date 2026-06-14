{
  "targets": [
    {
      "target_name": "ice_bridge",
      "sources": [ "src/ice-bridge.cc" ],
      "include_dirs": [
        "node_modules/node-addon-api"
      ],
      "cflags!": [ "-fno-exceptions" ],
      "cflags_cc!": [ "-fno-exceptions" ],
      "xcode_settings": {
        "GCC_ENABLE_CPP_EXCEPTIONS": "YES",
        "CLANG_CXX_LIBRARY": "libc++",
        "MACOSX_DEPLOYMENT_TARGET": "10.7"
      },
      "msvs_settings": {
        "VCCLCompilerTool": { "ExceptionHandling": 1 }
      },
      "conditions": [
        ['OS=="mac" or OS=="linux"', {
          'link_settings': {
            'libraries': [ '-lcurl' ]
          }
        }]
      ]
    }
  ]
}
