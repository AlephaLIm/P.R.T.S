#include "HttpClient.h"

HttpClient::HttpClient() {
    hSession = WinHttpOpen(
        L"WinHTTP Client/1.0",
        WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,
        WINHTTP_NO_PROXY_NAME,
        WINHTTP_NO_PROXY_BYPASS,
        0
    );

    if (!hSession) {
        ThrowLastError("Failed to initialize WinHTTP session");
    }

    // Set timeouts
    WinHttpSetTimeouts(hSession,
        10000,  // Resolution timeout
        10000,  // Connect timeout
        10000,  // Send timeout
        10000   // Receive timeout
    );
}

HttpClient::~HttpClient() {
    if (hSession) {
        WinHttpCloseHandle(hSession);
    }
}

std::string HttpClient::Get(const std::wstring& host, const std::wstring& path, INTERNET_PORT port) {
    // Connect to server
    HINTERNET hConnect = WinHttpConnect(hSession, host.c_str(), port, 0);
    if (!hConnect) {
        ThrowLastError("Failed to connect to server");
    }

    // Create request
    HINTERNET hRequest = WinHttpOpenRequest(
        hConnect,
        L"GET",
        path.c_str(),
        NULL,
        WINHTTP_NO_REFERER,
        WINHTTP_DEFAULT_ACCEPT_TYPES,
        0
    );

    if (!hRequest) {
        WinHttpCloseHandle(hConnect);
        ThrowLastError("Failed to create request");
    }

    // Send request
    if (!WinHttpSendRequest(
            hRequest,
            WINHTTP_NO_ADDITIONAL_HEADERS,
            0,
            WINHTTP_NO_REQUEST_DATA,
            0,
            0,
            0)) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        ThrowLastError("Failed to send request");
    }

    // Receive response
    if (!WinHttpReceiveResponse(hRequest, NULL)) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        ThrowLastError("Failed to receive response");
    }

    std::string response = ReadResponse(hRequest);

    // Cleanup
    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);

    return response;
}

std::string HttpClient::Post(
    const std::wstring& host, 
    const std::wstring& path, 
    const std::string& data,
    const std::wstring& contentType,
    INTERNET_PORT port
) {
    // Connect to server
    HINTERNET hConnect = WinHttpConnect(hSession, host.c_str(), port, 0);
    if (!hConnect) {
        ThrowLastError("Failed to connect to server");
    }

    // Create request
    HINTERNET hRequest = WinHttpOpenRequest(
        hConnect,
        L"POST",
        path.c_str(),
        NULL,
        WINHTTP_NO_REFERER,
        WINHTTP_DEFAULT_ACCEPT_TYPES,
        0
    );

    if (!hRequest) {
        WinHttpCloseHandle(hConnect);
        ThrowLastError("Failed to create request");
    }

    // Add Content-Type header
    std::wstring headerText = L"Content-Type: " + contentType + L"\r\n";
    if (!WinHttpAddRequestHeaders(
            hRequest,
            headerText.c_str(),
            -1L,
            WINHTTP_ADDREQ_FLAG_ADD)) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        ThrowLastError("Failed to add headers");
    }

    // Send request
    if (!WinHttpSendRequest(
            hRequest,
            WINHTTP_NO_ADDITIONAL_HEADERS,
            0,
            (LPVOID)data.c_str(),
            data.length(),
            data.length(),
            0)) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        ThrowLastError("Failed to send request");
    }

    // Receive response
    if (!WinHttpReceiveResponse(hRequest, NULL)) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        ThrowLastError("Failed to receive response");
    }

    std::string response = ReadResponse(hRequest);

    // Cleanup
    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);

    return response;
}



HttpResponse HttpClient::UploadFileWithJson(
    const std::wstring& host,
    const std::wstring& path_with_guid,
    const std::wstring& filepath,
    const std::string& jsonString,  // Changed parameter
    INTERNET_PORT port
) {
   std::string boundary = "boundary" + std::to_string(GetTickCount64());
    std::vector<char> fileData = ReadFile(filepath);
    std::cout << L"\n\n\n\n\nFILEPATH:\n ";
    std::cout << std::filesystem::path(filepath).filename().string();
    std::string body;
    std::string delimiter = "--" + boundary + "\r\n";

    // Add video file part
    body += delimiter;
    body += "Content-Disposition: form-data; name=\"file\"; filename=\"" + 
            std::filesystem::path(filepath).filename().string() + "\"\r\n";
    body += "Content-Type: application/octet-stream\r\n\r\n";
    std::cout << "\n\n\n\n\n\n\n\nFORM DATA\n\n\n";
    std::cout << body;
    body.insert(body.end(), fileData.begin(), fileData.end());
    body += "\r\n";

    // Add JSON part as a file
    body += delimiter;
    body += "Content-Disposition: form-data; name=\"json\"; filename=\"data.json\"\r\n";  // Changed this line
    body += "Content-Type: application/json\r\n\r\n";
    body += jsonString;
    body += "\r\n";

    // Add final boundary
    body += "--" + boundary + "--\r\n";
    
   // Connect to server using provided host and port
   HINTERNET hConnect = WinHttpConnect(hSession, host.c_str(), port, 0);
   if (!hConnect) {
       ThrowLastError("Failed to connect to server");
   }

   // Create request
   HINTERNET hRequest = WinHttpOpenRequest(
       hConnect,
       L"POST",
       path_with_guid.c_str(),
       NULL,
       WINHTTP_NO_REFERER,
       WINHTTP_DEFAULT_ACCEPT_TYPES,
       0
   );

   if (!hRequest) {
       WinHttpCloseHandle(hConnect);
       ThrowLastError("Failed to create request");
   }

   // Add Content-Type header with boundary
   std::wstring contentType = L"Content-Type: multipart/form-data; boundary=" + 
                             std::wstring(boundary.begin(), boundary.end()) + L"\r\n";
   
   if (!WinHttpAddRequestHeaders(
           hRequest,
           contentType.c_str(),
           -1L,
           WINHTTP_ADDREQ_FLAG_ADD)) {
       WinHttpCloseHandle(hRequest);
       WinHttpCloseHandle(hConnect);
       ThrowLastError("Failed to add headers");
   }

   // Send request
   if (!WinHttpSendRequest(
           hRequest,
           WINHTTP_NO_ADDITIONAL_HEADERS,
           0,
           (LPVOID)body.c_str(),
           body.length(),
           body.length(),
           0)) {
       WinHttpCloseHandle(hRequest);
       WinHttpCloseHandle(hConnect);
       ThrowLastError("Failed to send request");
   }

   // Receive response
   if (!WinHttpReceiveResponse(hRequest, NULL)) {
       WinHttpCloseHandle(hRequest);
       WinHttpCloseHandle(hConnect);
       ThrowLastError("Failed to receive response");
   }

   // Get status code
   DWORD statusCode = 0;
   DWORD statusCodeSize = sizeof(DWORD);
   
   if (!WinHttpQueryHeaders(
       hRequest,
       WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
       WINHTTP_HEADER_NAME_BY_INDEX,
       &statusCode,
       &statusCodeSize,
       WINHTTP_NO_HEADER_INDEX)) 
   {
       WinHttpCloseHandle(hRequest);
       WinHttpCloseHandle(hConnect);
       ThrowLastError("Failed to get status code");
   }

   std::string response = ReadResponse(hRequest);

   // Cleanup
   WinHttpCloseHandle(hRequest);
   WinHttpCloseHandle(hConnect);

   return HttpResponse{ response, statusCode };
}

std::string HttpClient::ReadResponse(HINTERNET hRequest) {
    std::string response;
    DWORD bytesAvailable = 0;
    DWORD bytesRead = 0;
    char buffer[4096];

    while (WinHttpQueryDataAvailable(hRequest, &bytesAvailable)) {
        if (bytesAvailable == 0) break;

        if (bytesAvailable > sizeof(buffer)) {
            bytesAvailable = sizeof(buffer);
        }

        if (!WinHttpReadData(hRequest, buffer, bytesAvailable, &bytesRead)) {
            ThrowLastError("Failed to read response data");
        }

        response.append(buffer, bytesRead);
    }

    return response;
}

std::string WStringToString(const std::wstring& wstr) {
    if (wstr.empty()) return std::string();
    
    int size = WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), (int)wstr.size(), nullptr, 0, nullptr, nullptr);
    std::string result(size, 0);
    WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), (int)wstr.size(), &result[0], size, nullptr, nullptr);
    return result;
}

std::vector<char> HttpClient::ReadFile(const std::wstring& filepath) {
    std::ifstream file(filepath, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open file: " + WStringToString(filepath));
    }
    
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);

    std::vector<char> buffer(size);
    if (!file.read(buffer.data(), size)) {
        throw std::runtime_error("Failed to read file: " + WStringToString(filepath));
    }

    return buffer;
}
std::string HttpClient::CreateMultipartBody(
    const std::string& boundary,
    const std::vector<char>& fileData,
    const std::string& guid,
    const std::string& metadata
) {
    std::string body;
    std::string delimiter = "--" + boundary + "\r\n";

    // Add GUID
    body += delimiter;
    body += "Content-Disposition: form-data; name=\"guid\"\r\n\r\n";
    body += guid + "\r\n";

    // Add metadata
    body += delimiter;
    body += "Content-Disposition: form-data; name=\"metadata\"\r\n\r\n";
    body += metadata + "\r\n";

    // Add file
    body += delimiter;
    body += "Content-Disposition: form-data; name=\"file\"; filename=\"video.mp4\"\r\n";
    body += "Content-Type: video/mp4\r\n\r\n";
    body.insert(body.end(), fileData.begin(), fileData.end());
    body += "\r\n";

    // Add final boundary
    body += "--" + boundary + "--\r\n";

    return body;
}

void HttpClient::ThrowLastError(const char* operation) {
    DWORD error = GetLastError();
    throw std::runtime_error(std::string(operation) + ": Error code " + std::to_string(error));
}