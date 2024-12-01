// NetworkCommon.h
#pragma once

#define WIN32_LEAN_AND_MEAN
#define _WINSOCK_DEPRECATED_NO_WARNINGS
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <winhttp.h>

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "winhttp.lib")