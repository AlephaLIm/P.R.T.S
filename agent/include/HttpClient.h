#pragma once
#include "NetworkCommon.h"  // Already correct
#include <string>
#include <vector>
#include <fstream>
#include <stdexcept>
#include <filesystem>
#include <iostream>

struct HttpResponse {
    std::string content;
    DWORD statusCode;
};


class HttpClient {
public:
    HttpClient();
    ~HttpClient();

    // Disable copying
    HttpClient(const HttpClient&) = delete;
    HttpClient& operator=(const HttpClient&) = delete;

    std::wstring host;
    INTERNET_PORT port;
    // HTTP Methods
    std::string Get(const std::wstring& host, const std::wstring& path, INTERNET_PORT port = INTERNET_DEFAULT_HTTP_PORT);
    
    std::string Post(
        const std::wstring& host, 
        const std::wstring& path, 
        const std::string& data,
        const std::wstring& contentType = L"application/json",
        INTERNET_PORT port = INTERNET_DEFAULT_HTTP_PORT
    );

    HttpResponse UploadFileWithJson(
        const std::wstring& host,
        const std::wstring& path_with_guid,  // Should include the ?guid= part
        const std::wstring& filepath,
        const std::string& jsonpath,
        INTERNET_PORT port = INTERNET_DEFAULT_HTTP_PORT
    );

private:
    HINTERNET hSession;
    
    // Helper methods
    void ThrowLastError(const char* operation);
    std::string ReadResponse(HINTERNET hRequest);
    std::vector<char> ReadFile(const std::wstring& filepath);
    std::string CreateMultipartBody(
        const std::string& boundary,
        const std::vector<char>& fileData,
        const std::string& guid,
        const std::string& metadata
    );
};